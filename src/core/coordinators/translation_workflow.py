"""
TranslationWorkflow - OCR, translation, and TTS pipeline coordinator

Single Responsibility: Manages the complete translation pipeline from screenshot
to spoken translation, including OCR processing, translation, TTS, and history.

Responsibilities:
- OCR text extraction from screenshots
- Translation processing with language detection
- Text-to-speech synthesis
- Translation history management
- Performance monitoring of pipeline operations
"""

import threading
from typing import TYPE_CHECKING, Any, List, Optional

import pyperclip

from src.models.translation import Translation
from src.services.config_manager import ConfigManager
from src.utils.exceptions import OCRError, TranslationFailedError, TTSError
from src.utils.logger import logger
from src.utils.performance_monitor import get_performance_monitor

if TYPE_CHECKING:
    from src.core.ocr_engine import OCRProcessor
    from src.core.translation_engine import TranslationProcessor
    from src.core.tts_engine import TTSProcessor


class TranslationWorkflow:
    """Coordinates the complete translation pipeline"""

    def __init__(
        self,
        ocr_processor: "OCRProcessor",
        translation_processor: "TranslationProcessor",
        tts_processor: "TTSProcessor",
        config_manager: ConfigManager,
    ):
        self.ocr_processor = ocr_processor
        self.translation_processor = translation_processor
        self.tts_processor = tts_processor
        self.config_manager = config_manager
        self.performance_monitor = get_performance_monitor()

        self._lock = threading.Lock()

        # Translation state
        self.last_translation = ""
        self.translation_history: List[Translation] = []
        self.current_language_index = self.config_manager.get_config().languages.default_target

    def process_screenshot_translation(
        self, screenshot_data, target_language: Optional[str] = None
    ) -> Optional[Translation]:
        """Process complete translation pipeline from screenshot to result"""
        try:
            # Use provided target language or get current one
            if target_language is None:
                target_language = self.get_current_target_language()

            config = self.config_manager.get_config()

            # Step 1: OCR text extraction
            text, ocr_confidence = self._extract_text_from_screenshot(screenshot_data, config)

            if not text.strip():
                logger.warning("No text extracted from screenshot")
                return None

            # Step 2: Translation
            translation = self._translate_text(text, target_language)

            if not translation:
                logger.error("Translation failed")
                return None

            # Step 3: Handle result (history, clipboard, TTS)
            self._handle_translation_result(translation)

            return translation

        except Exception as e:
            logger.error("Error in translation workflow", error=e)
            raise

    def _extract_text_from_screenshot(self, screenshot_data, config) -> tuple[str, float]:
        """Extract text from screenshot using OCR"""
        with self.performance_monitor.measure_operation("ocr_extraction"):
            if hasattr(self.ocr_processor, "extract_text"):
                # Plugin interface
                text, confidence = self.ocr_processor.extract_text(
                    screenshot_data.image_bytes, config.languages.ocr_languages
                )
            else:
                # Direct processor
                text, confidence = self.ocr_processor.process_screenshot(
                    screenshot_data, config.languages.ocr_languages
                )

        if not text.strip():
            raise OCRError("No text could be extracted from the image")

        logger.debug(f"OCR extracted text: {text[:50]}... (confidence: {confidence})")
        return text, confidence

    def _translate_text(self, text: str, target_language: str) -> Optional[Translation]:
        """Translate text to target language"""
        with self.performance_monitor.measure_operation(
            "translation", {"target_lang": target_language, "text_length": len(text)}
        ):
            if hasattr(self.translation_processor, "translate"):
                # Plugin interface
                translated_text, confidence = self.translation_processor.translate(
                    text, "auto", target_language  # auto-detect source language
                )
                # Create Translation object for consistency
                translation = Translation(
                    original_text=text,
                    translated_text=translated_text,
                    source_language="auto",
                    target_language=target_language,
                    confidence=confidence,
                )
            else:
                # Direct processor
                translation = self.translation_processor.translate_text(text, target_language)

        if not translation:
            raise TranslationFailedError(
                "Translation service returned no result", text, target_language
            )

        logger.debug(f"Translation successful: {translation.translated_text[:50]}...")
        return translation

    def _handle_translation_result(self, translation: Translation) -> None:
        """Handle successful translation result"""
        # Store for history and repeat (thread-safe)
        with self._lock:
            self.last_translation = translation.translated_text
            self._add_to_history_unsafe(translation)

        # Copy to clipboard if enabled
        if self.config_manager.get_config().features.copy_to_clipboard:
            self._copy_to_clipboard(translation.translated_text)

        # Speak translation if TTS enabled
        if self.config_manager.get_config().tts.enabled:
            self._speak_translation(translation)

    def _add_to_history_unsafe(self, translation: Translation) -> None:
        """Add translation to history (must be called with lock held)"""
        self.translation_history.append(translation)

        # Limit history size
        if len(self.translation_history) > 50:
            self.translation_history = self.translation_history[-50:]

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard"""
        try:
            pyperclip.copy(text)
            logger.debug("Text copied to clipboard")
        except ImportError:
            logger.warning("pyperclip not available for clipboard operations")
        except Exception as e:
            logger.error("Failed to copy to clipboard", error=e)

    def _speak_translation(self, translation: Translation) -> None:
        """Speak translation using TTS"""
        try:
            if hasattr(self.tts_processor, "speak"):
                # Plugin interface
                self.tts_processor.speak(translation.translated_text, translation.target_language)
            else:
                # Direct processor
                with self._lock:
                    self.tts_processor.speak_text(translation.translated_text)
            logger.debug("Translation spoken via TTS")
        except Exception as e:
            logger.error("TTS failed", error=e)
            raise TTSError(f"Text-to-speech failed: {str(e)}")

    def repeat_last_translation(self) -> None:
        """Repeat last translation using TTS"""
        with self._lock:
            translation = self.last_translation

        if translation:
            try:
                # Check if using plugin or direct processor
                if hasattr(self.tts_processor, "speak"):
                    # Plugin interface
                    current_lang = self.get_current_target_language()
                    self.tts_processor.speak(translation, current_lang)
                else:
                    # Direct processor
                    with self._lock:
                        self.tts_processor.speak_text(translation)
                logger.debug("Last translation repeated")
            except Exception as e:
                logger.error("Failed to repeat translation", error=e)
                raise TTSError(f"Could not repeat translation: {str(e)}")
        else:
            logger.warning("No translation available to repeat")

    def switch_language(self) -> str:
        """Switch target language and return new language"""
        with self._lock:
            languages = self.config_manager.get_config().languages.target_languages
            self.current_language_index = (self.current_language_index + 1) % len(languages)
            current_lang = languages[self.current_language_index]

        logger.info(f"Switched to language: {current_lang}")
        return current_lang

    def get_current_target_language(self) -> str:
        """Get current target language"""
        with self._lock:
            languages = self.config_manager.get_config().languages.target_languages
            index = self.current_language_index

        if index < len(languages):
            return languages[index]
        return languages[0] if languages else "en"

    def get_translation_history(self) -> List[Translation]:
        """Get copy of translation history"""
        with self._lock:
            return list(self.translation_history)

    def clear_translation_history(self) -> None:
        """Clear translation history"""
        with self._lock:
            self.translation_history.clear()
            self.last_translation = ""
        logger.info("Translation history cleared")

    def get_translation_stats(self) -> dict:
        """Get translation statistics"""
        with self._lock:
            history_copy = list(self.translation_history)

        if not history_copy:
            return {"total": 0, "languages": {}, "average_confidence": 0.0}

        # Calculate statistics
        total_translations = len(history_copy)
        languages = {}
        total_confidence = 0.0

        for translation in history_copy:
            # Count target languages
            target_lang = translation.target_language
            languages[target_lang] = languages.get(target_lang, 0) + 1

            # Sum confidence scores
            if hasattr(translation, "confidence") and translation.confidence:
                total_confidence += translation.confidence

        average_confidence = (
            total_confidence / total_translations if total_translations > 0 else 0.0
        )

        return {
            "total": total_translations,
            "languages": languages,
            "average_confidence": average_confidence,
            "last_translation_time": history_copy[-1].timestamp if history_copy else None,
        }

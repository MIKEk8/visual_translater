import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from src.models.translation import Translation
from src.services.cache_service import TranslationCache
from src.services.circuit_breaker import (
    TRANSLATION_SERVICE_CONFIG,
    CircuitBreakerError,
    get_circuit_breaker_manager,
)
from src.utils.exceptions import (
    TranslationEngineNotAvailableError,
    TranslationFailedError,
    UnsupportedLanguageError,
)
from src.utils.logger import logger


class TranslationEngine(ABC):
    """Abstract base class for translation engines"""

    @abstractmethod
    def translate(
        self, text: str, target_language: str, source_language: str = "auto"
    ) -> Optional[str]:
        """Translate text to target language"""

    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes"""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if translation engine is available"""


class GoogleTranslationEngine(TranslationEngine):
    """Google Translate implementation with circuit breaker protection"""

    def __init__(self):
        self.translator = None
        self.translator_type = None
        self._initialize()

        # Initialize circuit breaker
        manager = get_circuit_breaker_manager()
        self.circuit_breaker = manager.create_circuit_breaker(
            "google_translate", TRANSLATION_SERVICE_CONFIG
        )

        if self.is_available():
            logger.info("Google Translation Engine initialized with circuit breaker protection")
        else:
            logger.warning("Google Translation Engine not available - will fail at runtime")

    def _initialize(self):
        """Initialize Translator (googletrans or deep-translator)"""
        try:
            # Try googletrans first (for Python < 3.13)
            from googletrans import Translator

            self.translator = Translator()
            self.translator_type = "googletrans"
            logger.info("Using googletrans for translation")
        except ImportError:
            try:
                # Fallback to deep-translator (for Python >= 3.13)
                from deep_translator import GoogleTranslator

                self.translator = GoogleTranslator
                self.translator_type = "deep_translator"
                logger.info("Using deep-translator for translation")
            except ImportError:
                logger.error("No translation libraries available (googletrans or deep-translator)")
                self.translator = None
                self.translator_type = None

    def translate(
        self, text: str, target_language: str, source_language: str = "auto"
    ) -> Optional[str]:
        """Translate text using Google Translate with circuit breaker protection"""
        self._validate_translation_request(text, target_language, source_language)

        try:
            return self._execute_translation(text, target_language, source_language)
        except CircuitBreakerError as e:
            logger.warning(f"Translation circuit breaker triggered: {e}")
            raise TranslationFailedError(text, source_language, target_language, str(e)) from e
        except Exception as e:
            logger.error(
                "Google translation failed",
                error=e,
                text_length=len(text),
                target_lang=target_language,
            )
            raise TranslationFailedError(text, source_language, target_language, str(e)) from e

    def _validate_translation_request(
        self, text: str, target_language: str, source_language: str
    ) -> None:
        """Validate translation request parameters."""
        if not self.translator:
            raise TranslationEngineNotAvailableError("GoogleTranslate", "Engine not initialized")

        if not text.strip():
            raise TranslationFailedError(text, source_language, target_language, "Empty text")

        if target_language not in self.get_supported_languages():
            raise UnsupportedLanguageError(target_language, "GoogleTranslate")

    def _execute_translation(
        self, text: str, target_language: str, source_language: str
    ) -> Optional[str]:
        """Execute the actual translation with circuit breaker protection."""

        async def _translate():
            return self._perform_translation(text, target_language, source_language)

        # Run the protected translation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.circuit_breaker.call(_translate))
        finally:
            loop.close()

    def _perform_translation(self, text: str, target_language: str, source_language: str) -> str:
        """Perform translation using the appropriate translator library."""
        if self.translator_type == "googletrans":
            result = self.translator.translate(text, dest=target_language, src=source_language)
            return result.text
        elif self.translator_type == "deep_translator":
            translator_instance = self.translator(source=source_language, target=target_language)
            return translator_instance.translate(text)
        else:
            raise TranslationEngineNotAvailableError("GoogleTranslate", "No translator available")

    def get_supported_languages(self) -> List[str]:
        """Get supported language codes"""
        return [
            "ru",  # Russian
            "en",  # English
            "ja",  # Japanese
            "de",  # German
            "fr",  # French
            "es",  # Spanish
            "it",  # Italian
            "pt",  # Portuguese
            "zh",  # Chinese
            "ko",  # Korean
            "ar",  # Arabic
            "hi",  # Hindi
            "th",  # Thai
            "vi",  # Vietnamese
            "pl",  # Polish
            "nl",  # Dutch
        ]

    def is_available(self) -> bool:
        """Check if Google Translate is available"""
        return self.translator is not None and self.translator_type is not None


class TranslationProcessor:
    """Main translation processing class with caching"""

    def __init__(self, cache_enabled: bool = True):
        self.engines = [GoogleTranslationEngine()]  # Can add more engines
        self.active_engine = self._get_available_engine()
        self.cache = TranslationCache() if cache_enabled else None
        self.cache_enabled = cache_enabled

        if self.active_engine:
            logger.info(
                f"Translation processor initialized with {type(self.active_engine).__name__}"
            )
        else:
            logger.error("No translation engines available")

    def _get_available_engine(self) -> Optional[TranslationEngine]:
        """Get first available translation engine"""
        for engine in self.engines:
            if engine.is_available():
                return engine
        return None

    def translate_text(
        self, text: str, target_language: str, source_language: str = "auto"
    ) -> Optional[Translation]:
        """Translate text with caching support"""
        if not self.active_engine or not text.strip():
            return None

        start_time = time.time()

        # Check cache first
        cached_translation = None
        if self.cache:
            cached_translation = self.cache.get(text, target_language)
            if cached_translation:
                duration = time.time() - start_time
                logger.log_translation(
                    original=text,
                    translated=cached_translation.translated_text,
                    source_lang=cached_translation.source_language,
                    target_lang=target_language,
                    duration=duration,
                    cached=True,
                )
                return cached_translation

        # Perform translation
        try:
            translated_text = self.active_engine.translate(text, target_language, source_language)

            if not translated_text:
                return None

            # Create translation object
            translation = Translation(
                original_text=text,
                translated_text=translated_text,
                source_language=source_language,
                target_language=target_language,
                timestamp=datetime.now(),
                cached=False,
            )

            # Cache the translation
            if self.cache:
                self.cache.set(text, target_language, translation)

            duration = time.time() - start_time
            logger.log_translation(
                original=text,
                translated=translated_text,
                source_lang=source_language,
                target_lang=target_language,
                duration=duration,
                cached=False,
            )

            return translation

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Translation failed",
                error=e,
                text_length=len(text),
                target_lang=target_language,
                duration=duration,
            )
            return None

    def get_supported_languages(self) -> List[str]:
        """Get supported languages from active engine"""
        if not self.active_engine:
            return []
        return self.active_engine.get_supported_languages()

    def is_available(self) -> bool:
        """Check if translation is available"""
        return self.active_engine is not None

    def clear_cache(self) -> bool:
        """Clear translation cache"""
        if self.cache:
            self.cache.clear()
            logger.info("Translation cache cleared")
            return True
        return False

    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        if self.cache:
            return self.cache.get_stats()
        return {"cache_enabled": False}

    def enable_cache(self, enabled: bool = True):
        """Enable or disable caching"""
        if enabled and not self.cache:
            self.cache = TranslationCache()
            logger.info("Translation cache enabled")
        elif not enabled and self.cache:
            self.cache = None
            logger.info("Translation cache disabled")

        self.cache_enabled = enabled

    def get_engine_info(self) -> dict:
        """Get information about active translation engine"""
        if not self.active_engine:
            return {"engine": "None", "available": False}

        return {
            "engine": type(self.active_engine).__name__,
            "available": True,
            "supported_languages": len(self.get_supported_languages()),
            "cache_enabled": self.cache_enabled,
        }

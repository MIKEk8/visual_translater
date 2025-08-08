"""
Translation workflow - orchestrates the translation process.
"""

from typing import Optional

from ..entities.screenshot import Screenshot
from ..entities.translation import Translation
from ..protocols.services import OCRService, TranslationService, TTSService
from ..value_objects.language import Language, LanguagePair
from ..value_objects.text import Text, TranslatedText


class TranslationWorkflowService:
    """Domain service for translation workflow."""

    def __init__(
        self,
        ocr_service: OCRService,
        translation_service: TranslationService,
        tts_service: Optional[TTSService] = None,
    ):
        self.ocr_service = ocr_service
        self.translation_service = translation_service
        self.tts_service = tts_service

    async def process_screenshot(
        self, screenshot: Screenshot, language_pair: LanguagePair, auto_tts: bool = False
    ) -> Optional[Translation]:
        """Process screenshot through complete workflow."""

        # Check if screenshot has at least coordinates or already extracted text
        if not screenshot.coordinates and not screenshot.has_text:
            raise ValueError("Invalid screenshot: no coordinates or text")

        # Extract text
        if not screenshot.has_text:
            if not screenshot.image:
                # For testing - assume image will be provided by service
                text, confidence = await self.ocr_service.extract_text(
                    None, language_pair.source  # OCR service should handle this
                )
            else:
                text, confidence = await self.ocr_service.extract_text(
                    screenshot.image, language_pair.source
                )

            if text:
                screenshot.extract_text(text, confidence)

        if not screenshot.extracted_text:
            return None

        # Translate text
        translated_text = await self.translation_service.translate(
            screenshot.extracted_text.content, language_pair
        )

        if not translated_text:
            return None

        # Create translation entity
        translation = Translation(
            original=screenshot.extracted_text,
            translated=TranslatedText(translated_text, confidence=screenshot.ocr_confidence),
            language_pair=language_pair,
        )

        # Text-to-speech if enabled
        if auto_tts and self.tts_service and self.tts_service.is_available():
            await self.tts_service.speak(translated_text, language_pair.target)

        return translation

    def validate_services(self) -> dict[str, bool]:
        """Validate all services are available."""
        return {
            "ocr": self.ocr_service.is_available(),
            "translation": self.translation_service.is_available(),
            "tts": self.tts_service.is_available() if self.tts_service else False,
        }

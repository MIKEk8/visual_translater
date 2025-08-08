"""
Translation service implementation.
"""

from typing import List, Optional

from ...domain.protocols.services import TranslationService
from ...domain.value_objects.language import Language, LanguagePair
from ...utils.logger import logger


class GoogleTranslationService(TranslationService):
    """Google Translate service implementation."""

    def __init__(self):
        self._translator = None
        self._initialize()

    def _initialize(self):
        """Initialize Google Translator."""
        try:
            from googletrans import Translator

            self._translator = Translator()
            logger.info("Google Translate service initialized")
        except ImportError:
            logger.error("googletrans library not available")
        except Exception as e:
            logger.error(f"Failed to initialize Google Translate: {e}")

    async def translate(self, text: str, language_pair: LanguagePair) -> Optional[str]:
        """Translate text."""
        if not self._translator or not text.strip():
            return None

        try:
            source_lang = None if language_pair.source.code == "auto" else language_pair.source.code
            target_lang = language_pair.target.code

            result = self._translator.translate(text, src=source_lang, dest=target_lang)

            if result and result.text:
                logger.info(
                    f"Translation completed",
                    source_lang=language_pair.source.code,
                    target_lang=target_lang,
                    text_length=len(text),
                    result_length=len(result.text),
                )
                return result.text

            return None

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return None

    def is_available(self) -> bool:
        """Check if translation service is available."""
        return self._translator is not None

    def get_supported_languages(self) -> List[Language]:
        """Get supported languages."""
        supported_codes = [
            "ru",
            "en",
            "ja",
            "de",
            "fr",
            "es",
            "it",
            "pt",
            "zh",
            "ko",
            "ar",
            "hi",
            "th",
            "vi",
            "pl",
            "nl",
        ]

        return [Language(code) for code in supported_codes]

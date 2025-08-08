"""
Built-in Google Translate plugin for Screen Translator v2.0.
Wraps the existing GoogleTranslationEngine as a plugin.
"""

from typing import Any, Dict, List, Tuple

from src.plugins.base_plugin import PluginMetadata, PluginType, TranslationPlugin
from src.utils.logger import logger


class GoogleTranslatePlugin(TranslationPlugin):
    """Plugin wrapper for Google Translate API."""

    def __init__(self):
        super().__init__()
        self._translation_engine = None

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="google_translate",
            version="1.0.0",
            description="Google Translate API plugin for text translation",
            author="Screen Translator Team",
            plugin_type=PluginType.TRANSLATION,
            dependencies=["googletrans", "deep-translator"],  # Alternative libs
            config_schema={
                "service_url": {
                    "type": "string",
                    "description": "Google Translate service URL",
                    "default": "translate.google.com",
                },
                "timeout": {
                    "type": "number",
                    "description": "Request timeout in seconds",
                    "default": 10,
                },
                "rate_limit": {
                    "type": "number",
                    "description": "Requests per minute limit",
                    "default": 100,
                },
            },
        )

    def is_available(self) -> bool:
        """Check if Google Translate dependencies are available."""
        try:
            # Check for googletrans first
            import googletrans  # noqa: F401

            return True
        except ImportError:
            try:
                # Fallback to deep-translator
                import deep_translator  # noqa: F401

                return True
            except ImportError:
                return False

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the Google Translate plugin."""
        try:
            if not self.is_available():
                logger.error("Google Translate dependencies not available")
                return False

            # Import here to avoid import errors if dependencies missing
            from src.core.translation_engine import GoogleTranslationEngine

            # Create translation engine instance
            self._translation_engine = GoogleTranslationEngine()

            self._config = config
            self._initialized = True

            logger.info("Google Translate plugin initialized successfully")
            return True

        except Exception as e:
            logger.error("Failed to initialize Google Translate plugin", error=e)
            return False

    def cleanup(self) -> None:
        """Cleanup plugin resources."""
        self._translation_engine = None
        self._initialized = False
        logger.info("Google Translate plugin cleaned up")

    def translate(self, text: str, source_lang: str, target_lang: str) -> Tuple[str, float]:
        """
        Translate text using Google Translate.

        Args:
            text: Text to translate
            source_lang: Source language code ('auto' for detection)
            target_lang: Target language code

        Returns:
            Tuple of (translated_text, confidence_score)
        """
        if not self._initialized or not self._translation_engine:
            raise RuntimeError("Plugin not initialized")

        try:
            # Use the existing translation engine
            translated_text = self._translation_engine.translate(text, target_lang, source_lang)

            # Google Translate doesn't provide confidence scores, so we estimate
            confidence = 0.9 if len(translated_text) > 0 else 0.0

            logger.debug(f"Google Translate: {source_lang}->{target_lang}, {len(text)} chars")
            return translated_text, confidence

        except Exception as e:
            logger.error("Google Translate failed", error=e)
            return "", 0.0

    def get_supported_languages(self) -> List[str]:
        """Return list of supported language codes."""
        # Common Google Translate language codes
        return [
            "auto",  # Auto-detect
            "en",  # English
            "es",  # Spanish
            "fr",  # French
            "de",  # German
            "it",  # Italian
            "pt",  # Portuguese
            "ru",  # Russian
            "ja",  # Japanese
            "ko",  # Korean
            "zh",  # Chinese
            "ar",  # Arabic
            "hi",  # Hindi
            "th",  # Thai
            "vi",  # Vietnamese
            "nl",  # Dutch
            "sv",  # Swedish
            "da",  # Danish
            "no",  # Norwegian
            "fi",  # Finnish
            "pl",  # Polish
            "cs",  # Czech
            "hu",  # Hungarian
            "ro",  # Romanian
            "bg",  # Bulgarian
            "hr",  # Croatian
            "sk",  # Slovak
            "sl",  # Slovenian
            "et",  # Estonian
            "lv",  # Latvian
            "lt",  # Lithuanian
            "tr",  # Turkish
            "uk",  # Ukrainian
            "he",  # Hebrew
            "fa",  # Persian
            "ur",  # Urdu
            "bn",  # Bengali
            "ta",  # Tamil
            "te",  # Telugu
            "ml",  # Malayalam
            "kn",  # Kannada
            "gu",  # Gujarati
            "pa",  # Punjabi
            "mr",  # Marathi
            "ne",  # Nepali
            "si",  # Sinhala
            "my",  # Myanmar
            "km",  # Khmer
            "lo",  # Lao
            "ka",  # Georgian
            "am",  # Amharic
            "sw",  # Swahili
            "zu",  # Zulu
            "af",  # Afrikaans
        ]

    def detect_language(self, text: str) -> str:
        """Detect language of text."""
        if not self._initialized or not self._translation_engine:
            return "auto"

        try:
            # Use Google Translate's detection capability
            import googletrans

            translator = googletrans.Translator()
            detection = translator.detect(text)

            logger.debug(
                f"Language detected: {detection.lang} (confidence: {detection.confidence:.2f})"
            )
            return detection.lang

        except Exception as e:
            logger.error("Language detection failed", error=e)
            return "auto"

    def get_usage_cost(self, text: str) -> float:
        """Calculate estimated cost for translating text."""
        # Google Translate pricing is roughly $20 per 1M characters
        character_count = len(text)
        cost_per_char = 20.0 / 1_000_000  # $20 per 1M chars

        return character_count * cost_per_char

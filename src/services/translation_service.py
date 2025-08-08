"""
Translation service for Screen Translator v2.0.
Provides translation functionality with multiple backends.
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from src.utils.logger import logger


class TranslationProvider(Enum):
    """Supported translation providers."""

    GOOGLE = "google"
    MICROSOFT = "microsoft"
    YANDEX = "yandex"
    DEEPL = "deepl"
    OFFLINE = "offline"


@dataclass
class TranslationConfig:
    """Configuration for translation service."""

    default_provider: TranslationProvider = TranslationProvider.GOOGLE
    source_language: str = "auto"
    target_language: str = "en"
    max_retries: int = 3
    timeout: float = 10.0
    cache_enabled: bool = True
    offline_fallback: bool = True


@dataclass
class TranslationResult:
    """Result of translation operation."""

    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    provider: TranslationProvider
    confidence: float
    timestamp: float

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()


class TranslationBackend:
    """Base class for translation backends."""

    def __init__(self, config: TranslationConfig):
        self.config = config
        self.available = False

    def is_available(self) -> bool:
        """Check if backend is available."""
        return self.available

    def translate(
        self, text: str, source_lang: str = "auto", target_lang: str = "en"
    ) -> TranslationResult:
        """Translate text."""
        raise NotImplementedError

    def detect_language(self, text: str) -> str:
        """Detect language of text."""
        raise NotImplementedError


class GoogleTranslationBackend(TranslationBackend):
    """Google Translate backend."""

    def __init__(self, config: TranslationConfig):
        super().__init__(config)
        try:
            from googletrans import Translator

            self.translator = Translator()
            self.available = True
            logger.debug("Google Translate backend initialized")
        except ImportError:
            logger.warning("Google Translate backend not available - googletrans not installed")
            self.available = False

    def translate(
        self, text: str, source_lang: str = "auto", target_lang: str = "en"
    ) -> TranslationResult:
        """Translate text using Google Translate."""
        if not self.available:
            raise RuntimeError("Google Translate backend not available")

        try:
            result = self.translator.translate(text, src=source_lang, dest=target_lang)

            return TranslationResult(
                original_text=text,
                translated_text=result.text,
                source_language=result.src,
                target_language=target_lang,
                provider=TranslationProvider.GOOGLE,
                confidence=0.95,  # Google doesn't provide confidence
                timestamp=time.time(),
            )

        except Exception as e:
            logger.error(f"Google Translate error: {e}")
            raise


class MockTranslationBackend(TranslationBackend):
    """Mock translation backend for testing."""

    def __init__(self, config: TranslationConfig):
        super().__init__(config)
        self.available = True
        logger.debug("Mock translation backend initialized")

    def translate(
        self, text: str, source_lang: str = "auto", target_lang: str = "en"
    ) -> TranslationResult:
        """Mock translation - returns uppercase text."""

        # Simple mock translations
        mock_translations = {
            "hello": "привет",
            "world": "мир",
            "test": "тест",
            "screen translator": "переводчик экрана",
            "translation complete": "перевод завершен",
        }

        text_lower = text.lower().strip()
        translated = mock_translations.get(text_lower, f"TRANSLATED_{text.upper()}")

        return TranslationResult(
            original_text=text,
            translated_text=translated,
            source_language="en",
            target_language=target_lang,
            provider=TranslationProvider.OFFLINE,
            confidence=0.85,
            timestamp=time.time(),
        )

    def detect_language(self, text: str) -> str:
        """Mock language detection."""
        # Simple heuristic - if contains Cyrillic, assume Russian
        if any("\u0400" <= char <= "\u04ff" for char in text):
            return "ru"
        return "en"


class TranslationService:
    """Main translation service with multiple backends."""

    def __init__(self, config: Optional[TranslationConfig] = None):
        """Initialize translation service."""
        self.config = config or TranslationConfig()
        self.backends: Dict[TranslationProvider, TranslationBackend] = {}
        self.cache: Dict[str, TranslationResult] = {}

        # Initialize backends
        self._initialize_backends()

        # Find primary backend
        self.primary_backend = self._get_primary_backend()

        logger.info(f"Translation service initialized with {len(self.backends)} backends")
        if self.primary_backend:
            logger.debug(f"Primary backend: {type(self.primary_backend).__name__}")

    def _initialize_backends(self) -> None:
        """Initialize all available translation backends."""

        # Google Translate
        google_backend = GoogleTranslationBackend(self.config)
        if google_backend.is_available():
            self.backends[TranslationProvider.GOOGLE] = google_backend

        # Mock backend (always available)
        mock_backend = MockTranslationBackend(self.config)
        self.backends[TranslationProvider.OFFLINE] = mock_backend

    def _get_primary_backend(self) -> Optional[TranslationBackend]:
        """Get primary translation backend."""
        # Prefer real backends over mock
        for provider in [
            TranslationProvider.GOOGLE,
            TranslationProvider.MICROSOFT,
            TranslationProvider.DEEPL,
            TranslationProvider.OFFLINE,
        ]:
            if provider in self.backends:
                return self.backends[provider]

        return None

    def translate(
        self, text: str, source_lang: str = "auto", target_lang: Optional[str] = None
    ) -> TranslationResult:
        """
        Translate text.

        Args:
            text: Text to translate
            source_lang: Source language code (auto for detection)
            target_lang: Target language code

        Returns:
            Translation result
        """
        if not text.strip():
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language="unknown",
                target_language=target_lang or self.config.target_language,
                provider=TranslationProvider.OFFLINE,
                confidence=1.0,
                timestamp=time.time(),
            )

        target_lang = target_lang or self.config.target_language

        # Check cache
        cache_key = f"{text}|{source_lang}|{target_lang}"
        if self.config.cache_enabled and cache_key in self.cache:
            logger.debug("Translation found in cache")
            return self.cache[cache_key]

        # Try translation with primary backend
        if not self.primary_backend:
            raise RuntimeError("No translation backends available")

        try:
            result = self.primary_backend.translate(text, source_lang, target_lang)

            # Cache result
            if self.config.cache_enabled:
                self.cache[cache_key] = result

            logger.debug(f"Translated '{text[:30]}...' -> '{result.translated_text[:30]}...'")
            return result

        except Exception as e:
            logger.error(f"Translation failed: {e}")

            # Fallback to mock if available
            if TranslationProvider.OFFLINE in self.backends and self.config.offline_fallback:
                logger.warning("Using offline fallback for translation")
                return self.backends[TranslationProvider.OFFLINE].translate(
                    text, source_lang, target_lang
                )

            raise

    def detect_language(self, text: str) -> str:
        """Detect language of text."""
        if not self.primary_backend:
            return "unknown"

        try:
            if hasattr(self.primary_backend, "detect_language"):
                return self.primary_backend.detect_language(text)
            else:
                # Fallback to simple detection
                if any("\u0400" <= char <= "\u04ff" for char in text):
                    return "ru"
                return "en"

        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return "unknown"

    def get_available_providers(self) -> List[TranslationProvider]:
        """Get list of available translation providers."""
        return list(self.backends.keys())

    def clear_cache(self) -> None:
        """Clear translation cache."""
        self.cache.clear()
        logger.debug("Translation cache cleared")

    def get_cache_size(self) -> int:
        """Get number of cached translations."""
        return len(self.cache)


# Global translation service instance
_translation_service: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    """Get global translation service instance."""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service


def initialize_translation_service(
    config: Optional[TranslationConfig] = None,
) -> TranslationService:
    """Initialize global translation service."""
    global _translation_service
    _translation_service = TranslationService(config)
    return _translation_service


# Convenience functions
def translate_text(text: str, target_lang: str = "en") -> str:
    """Quick translation function."""
    service = get_translation_service()
    result = service.translate(text, target_lang=target_lang)
    return result.translated_text


def detect_language(text: str) -> str:
    """Quick language detection function."""
    service = get_translation_service()
    return service.detect_language(text)

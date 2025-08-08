"""
Service protocols - define interfaces for domain services.
"""

from abc import abstractmethod
from typing import Optional, Protocol

try:
    from PIL import Image

    ImageType = Image.Image
except ImportError:
    from typing import Any

    Image = Any
    ImageType = Any

from ..entities.screenshot import Screenshot
from ..entities.translation import Translation
from ..value_objects.coordinates import ScreenCoordinates
from ..value_objects.language import Language, LanguagePair


class OCRService(Protocol):
    """OCR service protocol."""

    @abstractmethod
    async def extract_text(self, image: ImageType, language: Language) -> tuple[str, float]:
        """Extract text from image with confidence score."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if OCR service is available."""
        ...


class TranslationService(Protocol):
    """Translation service protocol."""

    @abstractmethod
    async def translate(self, text: str, language_pair: LanguagePair) -> Optional[str]:
        """Translate text."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if translation service is available."""
        ...

    @abstractmethod
    def get_supported_languages(self) -> list[Language]:
        """Get supported languages."""
        ...


class TTSService(Protocol):
    """Text-to-speech service protocol."""

    @abstractmethod
    async def speak(self, text: str, language: Language) -> None:
        """Convert text to speech."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if TTS service is available."""
        ...

    @abstractmethod
    def set_voice(self, voice_id: str) -> None:
        """Set TTS voice."""
        ...

    @abstractmethod
    def set_rate(self, rate: int) -> None:
        """Set speech rate."""
        ...


class ScreenCaptureService(Protocol):
    """Screen capture service protocol."""

    @abstractmethod
    async def capture_area(self, coordinates: ScreenCoordinates) -> ImageType:
        """Capture screen area."""
        ...

    @abstractmethod
    async def select_area(self) -> Optional[ScreenCoordinates]:
        """Let user select screen area."""
        ...

"""Translation Data Transfer Objects."""

from dataclasses import dataclass
from typing import List, Optional

from ...domain.entities.translation import Translation


@dataclass
class TranslationRequest:
    """Request for translation operations."""

    text: str
    source_language: str = "auto"
    target_language: str = "ru"
    auto_tts: bool = False


@dataclass
class TranslationResponse:
    """Response for translation operations."""

    success: bool
    translation: Optional[Translation] = None
    errors: List[str] = None

    @classmethod
    def success(cls, translation: Translation) -> "TranslationResponse":
        """Create success response."""
        return cls(success=True, translation=translation)

    @classmethod
    def error(cls, errors: List[str]) -> "TranslationResponse":
        """Create error response."""
        return cls(success=False, errors=errors or [])

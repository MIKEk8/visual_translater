"""Translation Data Transfer Objects."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TranslationRequest:
    """Request for translation operations."""

    text: str
    source_language: str = "auto"
    target_language: str = "ru"
    auto_tts: bool = False


@dataclass
class TranslationResponse:
    """Simplified translation result returned by use cases."""

    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    is_cached: bool = False
    confidence: Optional[float] = None

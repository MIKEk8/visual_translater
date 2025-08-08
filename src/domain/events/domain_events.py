"""
Domain events - represent important business events.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

from ..value_objects.domain_id import DomainId


@dataclass
class DomainEvent:
    """Base domain event."""

    event_id: DomainId = field(default_factory=DomainId.generate)
    event_type: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    aggregate_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.event_type:
            self.event_type = self.__class__.__name__


@dataclass
class TranslationCreated(DomainEvent):
    """Translation created event."""

    translation_id: str = ""
    original_text: str = ""
    translated_text: str = ""
    source_language: str = ""
    target_language: str = ""
    cached: bool = False

    def __post_init__(self):
        super().__post_init__()
        self.aggregate_id = self.translation_id
        self.payload = {
            "original_text": self.original_text,
            "translated_text": self.translated_text,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "cached": self.cached,
        }


@dataclass
class ScreenshotCaptured(DomainEvent):
    """Screenshot captured event."""

    screenshot_id: str = ""
    coordinates: tuple[int, int, int, int] = (0, 0, 0, 0)
    has_text: bool = False

    def __post_init__(self):
        super().__post_init__()
        self.aggregate_id = self.screenshot_id
        self.payload = {"coordinates": self.coordinates, "has_text": self.has_text}


@dataclass
class TextExtracted(DomainEvent):
    """Text extracted from screenshot event."""

    screenshot_id: str = ""
    text: str = ""
    confidence: float = 0.0
    language: str = ""

    def __post_init__(self):
        super().__post_init__()
        self.aggregate_id = self.screenshot_id
        self.payload = {"text": self.text, "confidence": self.confidence, "language": self.language}

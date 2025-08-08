"""
Translation entity - core business object.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..value_objects.domain_id import DomainId
from ..value_objects.language import Language, LanguagePair
from ..value_objects.text import Text, TranslatedText


@dataclass
class Translation:
    """Translation entity with business logic."""

    original: Text
    translated: TranslatedText
    language_pair: LanguagePair
    id: DomainId = field(default_factory=DomainId.generate)
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: Optional[float] = None
    cached: bool = False

    def __post_init__(self):
        """Validate translation entity."""
        if not self.id:
            self.id = DomainId.generate()

    @property
    def is_valid(self) -> bool:
        """Check if translation is valid."""
        return bool(self.original.content and self.translated.content)

    @property
    def confidence(self) -> Optional[float]:
        """Get translation confidence."""
        return self.translated.confidence

    def mark_as_cached(self) -> None:
        """Mark translation as retrieved from cache."""
        self.cached = True

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "original": self.original.content,
            "translated": self.translated.content,
            "source_language": self.language_pair.source.code,
            "target_language": self.language_pair.target.code,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "cached": self.cached,
            "confidence": self.confidence,
        }

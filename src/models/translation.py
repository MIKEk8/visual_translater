from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4


@dataclass
class Translation:
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: Optional[datetime] = None
    confidence: Optional[float] = None
    cached: bool = False
    metadata: Optional[dict] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "original_text": self.original_text,
            "translated_text": self.translated_text,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "confidence": self.confidence,
            "cached": self.cached,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Translation":
        timestamp = (
            datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now()
        )
        return cls(
            id=data.get("id", str(uuid4())),
            original_text=data["original_text"],
            translated_text=data["translated_text"],
            source_language=data["source_language"],
            target_language=data["target_language"],
            timestamp=timestamp,
            confidence=data.get("confidence"),
            cached=data.get("cached", False),
            metadata=data.get("metadata", {}),
        )


# Import ScreenshotData from its proper module

"""
Text value object - represents text content with validation.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Text:
    """Immutable text content with validation."""

    content: str
    max_length: int = 5000

    def __post_init__(self):
        """Validate text content."""
        if not self.content:
            raise ValueError("Text content cannot be empty")

        if len(self.content) > self.max_length:
            raise ValueError(f"Text exceeds maximum length of {self.max_length}")

    @property
    def length(self) -> int:
        """Get text length."""
        return len(self.content)

    @property
    def preview(self) -> str:
        """Get text preview (first 50 chars)."""
        if self.length <= 50:
            return self.content
        return self.content[:47] + "..."

    def __str__(self) -> str:
        return self.content


@dataclass(frozen=True)
class TranslatedText(Text):
    """Text with translation metadata."""

    confidence: Optional[float] = None

    def __post_init__(self):
        """Validate translated text."""
        super().__post_init__()

        if self.confidence is not None:
            if not 0.0 <= self.confidence <= 1.0:
                raise ValueError("Confidence must be between 0 and 1")

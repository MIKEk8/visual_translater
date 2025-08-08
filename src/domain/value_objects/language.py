"""
Language value object - represents a language code with validation.
"""

from dataclasses import dataclass
from typing import ClassVar, Set


@dataclass(frozen=True)
class Language:
    """Immutable language representation."""

    code: str

    # Supported language codes
    SUPPORTED: ClassVar[Set[str]] = {
        "auto",
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
    }

    def __post_init__(self):
        """Validate language code."""
        if not self.code:
            raise ValueError("Language code cannot be empty")

        if self.code not in self.SUPPORTED:
            raise ValueError(f"Unsupported language: {self.code}")

    def __str__(self) -> str:
        return self.code

    @classmethod
    def auto(cls) -> "Language":
        """Create auto-detect language."""
        return cls("auto")

    @staticmethod
    def is_auto(code: str) -> bool:
        """Check if language is auto-detect."""
        return code == "auto"


@dataclass(frozen=True)
class LanguagePair:
    """Immutable language pair for translation."""

    source: Language
    target: Language

    def __post_init__(self):
        """Validate language pair."""
        if self.source == self.target and not Language.is_auto(self.source.code):
            raise ValueError("Source and target languages must be different")

    def __str__(self) -> str:
        return f"{self.source} → {self.target}"

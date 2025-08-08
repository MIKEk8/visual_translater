"""Translation-related commands for CQRS pattern."""

from dataclasses import dataclass
from typing import List, Optional

from .base_command import Command


@dataclass
class TranslateTextCommand(Command):
    """Command to translate text."""

    text: str = ""
    source_language: str = "auto"
    target_language: str = "en"
    use_cache: bool = True
    context: Optional[str] = None

    def validate(self) -> bool:
        """Validate translation command."""
        if not self.text or not self.text.strip():
            return False

        if len(self.text) > 5000:  # Max text length
            return False

        if not self.target_language:
            return False

        # Language code validation (basic)
        valid_langs = {
            "auto",
            "en",
            "es",
            "fr",
            "de",
            "it",
            "pt",
            "ru",
            "ja",
            "ko",
            "zh",
            "ar",
            "hi",
            "th",
            "vi",
            "tr",
            "pl",
            "nl",
            "sv",
            "da",
            "no",
            "fi",
            "cs",
            "sk",
            "hu",
            "ro",
            "bg",
            "hr",
            "sl",
            "et",
            "lv",
            "lt",
            "uk",
            "be",
            "mk",
            "sq",
            "eu",
            "ca",
            "gl",
            "cy",
        }

        if self.source_language not in valid_langs:
            return False

        if self.target_language not in valid_langs:
            return False

        return True

    @property
    def text_length(self) -> int:
        """Get text length for metrics."""
        return len(self.text)

    @property
    def word_count(self) -> int:
        """Get word count for pricing estimation."""
        return len(self.text.split())


@dataclass
class SaveTranslationCommand(Command):
    """Command to save translation to history."""

    original_text: str = ""
    translated_text: str = ""
    source_language: str = ""
    target_language: str = ""
    confidence: Optional[float] = None
    translation_time_ms: float = 0.0
    provider: str = "google"

    def validate(self) -> bool:
        """Validate save translation command."""
        if not self.original_text or not self.translated_text:
            return False

        if not self.source_language or not self.target_language:
            return False

        if self.confidence is not None:
            if not (0.0 <= self.confidence <= 1.0):
                return False

        if self.translation_time_ms < 0:
            return False

        return True


@dataclass
class BatchTranslateCommand(Command):
    """Command to translate multiple text items."""

    texts: Optional[List[str]] = None
    source_language: str = "auto"
    target_language: str = "en"
    use_cache: bool = True
    max_concurrent: int = 3

    def __post_init__(self):
        if self.texts is None:
            self.texts = []

    def validate(self) -> bool:
        """Validate batch translation command."""
        if not self.texts:
            return False

        if len(self.texts) > 100:  # Max batch size
            return False

        for text in self.texts:
            if not text or not text.strip():
                return False
            if len(text) > 5000:
                return False

        if self.max_concurrent < 1 or self.max_concurrent > 10:
            return False

        return True

    @property
    def total_characters(self) -> int:
        """Get total character count."""
        if self.texts is None:
            return 0
        return sum(len(text) for text in self.texts)

    @property
    def batch_size(self) -> int:
        """Get batch size."""
        return len(self.texts)


@dataclass
class UpdateTranslationCacheCommand(Command):
    """Command to update translation cache settings."""

    enable_cache: bool = True
    max_cache_size: int = 1000
    cache_ttl_hours: int = 24
    clear_existing: bool = False

    def validate(self) -> bool:
        """Validate cache update command."""
        if self.max_cache_size < 0 or self.max_cache_size > 10000:
            return False

        if self.cache_ttl_hours < 1 or self.cache_ttl_hours > 168:  # Max 1 week
            return False

        return True


@dataclass
class ExportTranslationsCommand(Command):
    """Command to export translation history."""

    file_path: str = ""
    format_type: str = "json"  # json, csv, txt, html, xml
    include_metadata: bool = True
    date_range_days: Optional[int] = None
    max_records: Optional[int] = None

    def validate(self) -> bool:
        """Validate export command."""
        if not self.file_path:
            return False

        valid_formats = ["json", "csv", "txt", "html", "xml"]
        if self.format_type not in valid_formats:
            return False

        if self.date_range_days is not None:
            if self.date_range_days < 1 or self.date_range_days > 365:
                return False

        if self.max_records is not None:
            if self.max_records < 1 or self.max_records > 10000:
                return False

        return True

"""Configuration-related queries for CQRS pattern."""

from dataclasses import dataclass
from typing import Optional

from .base_query import Query


@dataclass
class GetConfigQuery(Query):
    """Query to get application configuration."""

    section: Optional[str] = None  # Get specific section or all
    include_defaults: bool = False
    include_metadata: bool = False

    def validate(self) -> bool:
        """Validate config query."""
        valid_sections = [
            "languages",
            "hotkeys",
            "tts",
            "features",
            "image_processing",
            "ui",
            "performance",
        ]

        if self.section and self.section not in valid_sections:
            return False

        return True


@dataclass
class GetAvailableLanguagesQuery(Query):
    """Query to get available languages for OCR and translation."""

    include_ocr_languages: bool = True
    include_translation_languages: bool = True
    include_tts_languages: bool = True

    def validate(self) -> bool:
        """Always valid query."""
        return True


@dataclass
class GetHotkeyConfigQuery(Query):
    """Query to get hotkey configuration."""

    include_global: bool = True
    include_local: bool = True
    include_available_keys: bool = False

    def validate(self) -> bool:
        """Always valid query."""
        return True

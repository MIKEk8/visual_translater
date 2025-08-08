"""Application-level commands for CQRS pattern."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base_command import Command


@dataclass
class ChangeLanguageCommand(Command):
    """Command to change application language settings."""

    target_language: str = ""
    ocr_languages: Optional[List[str]] = None
    set_as_default: bool = True

    def validate(self) -> bool:
        """Validate language change command."""
        if not self.target_language:
            return False

        # Basic language code validation
        valid_langs = {
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

        if self.target_language not in valid_langs:
            return False

        if self.ocr_languages:
            for lang in self.ocr_languages:
                if lang not in valid_langs:
                    return False

        return True


@dataclass
class UpdateConfigCommand(Command):
    """Command to update application configuration."""

    config_updates: Optional[Dict[str, Any]] = None
    merge_with_existing: bool = True

    validate_changes: bool = True

    def __post_init__(self):
        if self.config_updates is None:
            self.config_updates = {}

    def validate(self) -> bool:
        """Validate configuration update."""
        if not self.config_updates:
            return False

        # Basic validation of config structure
        valid_sections = {
            "languages",
            "hotkeys",
            "tts",
            "features",
            "image_processing",
            "ui",
            "performance",
        }

        for key in self.config_updates.keys():
            if "." in key:
                section = key.split(".")[0]
                if section not in valid_sections:
                    return False

        return True


@dataclass
class ExportHistoryCommand(Command):
    """Command to export application history data."""

    export_type: str = "all"  # "translations", "screenshots", "performance", "all"
    file_path: str = ""
    format_type: str = "json"
    include_metadata: bool = True
    date_range_days: Optional[int] = None

    def validate(self) -> bool:
        """Validate export history command."""
        valid_types = ["translations", "screenshots", "performance", "all"]
        if self.export_type not in valid_types:
            return False

        if not self.file_path:
            return False

        valid_formats = ["json", "csv", "html", "xml", "txt"]
        if self.format_type not in valid_formats:
            return False

        if self.date_range_days is not None:
            if self.date_range_days < 1 or self.date_range_days > 365:
                return False

        return True


@dataclass
class ClearHistoryCommand(Command):
    """Command to clear application history."""

    history_type: str = "all"  # "translations", "screenshots", "performance", "all"
    older_than_days: Optional[int] = None
    confirm_deletion: bool = False

    def validate(self) -> bool:
        """Validate clear history command."""
        valid_types = ["translations", "screenshots", "performance", "all"]
        if self.history_type not in valid_types:
            return False

        if not self.confirm_deletion:
            return False  # Require explicit confirmation

        if self.older_than_days is not None:
            if self.older_than_days < 1:
                return False

        return True


@dataclass
class BackupDataCommand(Command):
    """Command to backup application data."""

    backup_path: str = ""
    include_config: bool = True
    include_history: bool = True
    include_cache: bool = False
    compress: bool = True

    def validate(self) -> bool:
        """Validate backup command."""
        if not self.backup_path:
            return False

        return True


@dataclass
class RestoreDataCommand(Command):
    """Command to restore application data from backup."""

    backup_path: str = ""
    restore_config: bool = True
    restore_history: bool = True
    restore_cache: bool = False
    confirm_overwrite: bool = False

    def validate(self) -> bool:
        """Validate restore command."""
        if not self.backup_path:
            return False

        if not self.confirm_overwrite:
            return False  # Require explicit confirmation

        return True


@dataclass
class UpdateApplicationCommand(Command):
    """Command to trigger application update process."""

    check_for_updates: bool = True
    auto_install: bool = False
    backup_before_update: bool = True

    def validate(self) -> bool:
        """Always valid command."""
        return True


@dataclass
class RestartApplicationCommand(Command):
    """Command to restart the application."""

    save_state: bool = True
    restart_delay_seconds: int = 2

    def validate(self) -> bool:
        """Validate restart command."""
        if self.restart_delay_seconds < 0 or self.restart_delay_seconds > 60:
            return False

        return True


@dataclass
class ShutdownApplicationCommand(Command):
    """Command to shutdown the application gracefully."""

    save_state: bool = True
    force_shutdown: bool = False
    shutdown_delay_seconds: int = 0

    def validate(self) -> bool:
        """Validate shutdown command."""
        if self.shutdown_delay_seconds < 0 or self.shutdown_delay_seconds > 60:
            return False

        return True

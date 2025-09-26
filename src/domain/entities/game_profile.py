"""
Game Profile domain entity for representing game-specific configurations.

This module defines the domain model for game profiles with their
associated translation settings and metadata.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class GameProfile:
    """Domain entity representing a game profile."""

    name: str
    executable: str
    window_title_patterns: List[str]
    hotkey_profile: Optional[str] = None
    translation_settings: Optional[Dict[str, Any]] = None
    glossary: Optional[str] = None
    ocr_presets: Optional[Dict[str, Any]] = None
    detection_confidence: float = 1.0
    last_detected: Optional[datetime] = None
    play_count: int = 0
    total_playtime: float = 0.0  # in hours

    def __post_init__(self):
        """Post-initialization validation and setup."""
        if not self.window_title_patterns:
            self.window_title_patterns = [self.name]

        if self.translation_settings is None:
            self.translation_settings = {}

        if self.ocr_presets is None:
            self.ocr_presets = {}

    def matches_process(self, process_name: str) -> bool:
        """Check if this profile matches a process name."""
        normalized_process = process_name.lower().replace('.exe', '')
        normalized_executable = self.executable.lower().replace('.exe', '')

        return normalized_process == normalized_executable

    def matches_window_title(self, window_title: str) -> bool:
        """Check if this profile matches a window title."""
        for pattern in self.window_title_patterns:
            if pattern.lower() in window_title.lower():
                return True
        return False

    def update_usage_stats(self) -> None:
        """Update usage statistics when game is detected."""
        self.play_count += 1
        self.last_detected = datetime.now()

    def get_translation_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific translation setting."""
        return self.translation_settings.get(key, default)

    def set_translation_setting(self, key: str, value: Any) -> None:
        """Set a translation setting."""
        self.translation_settings[key] = value

    def get_ocr_preset(self, key: str, default: Any = None) -> Any:
        """Get a specific OCR preset."""
        return self.ocr_presets.get(key, default)

    def set_ocr_preset(self, key: str, value: Any) -> None:
        """Set an OCR preset."""
        self.ocr_presets[key] = value
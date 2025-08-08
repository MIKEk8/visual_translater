"""
User preferences entity - manages user settings.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

from ..value_objects.language import Language


@dataclass
class UserPreferences:
    """User preferences with validation."""

    id: str = "default"
    target_language: Language = field(default_factory=lambda: Language("ru"))
    ocr_language: Language = field(default_factory=lambda: Language("en"))
    auto_tts: bool = False
    tts_voice: Optional[str] = None
    tts_rate: int = 150
    tts_volume: float = 1.0
    cache_enabled: bool = True
    theme: str = "light"
    hotkeys: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate preferences."""
        if not 50 <= self.tts_rate <= 300:
            raise ValueError("TTS rate must be between 50 and 300")

        if not 0.0 <= self.tts_volume <= 1.0:
            raise ValueError("TTS volume must be between 0 and 1")

        if self.theme not in ["light", "dark", "auto"]:
            raise ValueError("Theme must be light, dark, or auto")

    def update_language_pair(self, source: str, target: str) -> None:
        """Update language preferences."""
        self.ocr_language = Language(source)
        self.target_language = Language(target)

    def update_hotkey(self, action: str, key_combination: str) -> None:
        """Update hotkey binding."""
        self.hotkeys[action] = key_combination

    def get_hotkey(self, action: str) -> Optional[str]:
        """Get hotkey for action."""
        return self.hotkeys.get(action)

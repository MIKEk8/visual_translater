"""
Configuration system adapter.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from ...domain.entities.preferences import UserPreferences
from ...domain.value_objects.language import Language
from ...utils.logger import logger


class ConfigurationAdapter:
    """Adapter for configuration management."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("config.json")

    def load_preferences(self) -> UserPreferences:
        """Load user preferences from configuration."""
        try:
            if not self.config_path.exists():
                return UserPreferences()

            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            # Convert config to preferences
            preferences = UserPreferences()

            # Language settings
            if "target_language" in config_data:
                preferences.target_language = Language(config_data["target_language"])

            if "ocr_language" in config_data:
                preferences.ocr_language = Language(config_data["ocr_language"])

            # TTS settings
            tts_config = config_data.get("tts", {})
            preferences.auto_tts = tts_config.get("auto_tts", False)
            preferences.tts_voice = tts_config.get("voice_id")
            preferences.tts_rate = tts_config.get("rate", 150)
            preferences.tts_volume = tts_config.get("volume", 1.0)

            # Other settings
            preferences.cache_enabled = config_data.get("cache_enabled", True)
            preferences.theme = config_data.get("theme", "light")
            preferences.hotkeys = config_data.get("hotkeys", {})

            logger.info("User preferences loaded from configuration")
            return preferences

        except Exception as e:
            logger.error(f"Failed to load preferences: {e}")
            return UserPreferences()

    def save_preferences(self, preferences: UserPreferences) -> bool:
        """Save user preferences to configuration."""
        try:
            config_data = {
                "target_language": preferences.target_language.code,
                "ocr_language": preferences.ocr_language.code,
                "tts": {
                    "auto_tts": preferences.auto_tts,
                    "voice_id": preferences.tts_voice,
                    "rate": preferences.tts_rate,
                    "volume": preferences.tts_volume,
                },
                "cache_enabled": preferences.cache_enabled,
                "theme": preferences.theme,
                "hotkeys": preferences.hotkeys,
            }

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

            logger.info("User preferences saved to configuration")
            return True

        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")
            return False

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get specific configuration value."""
        try:
            if not self.config_path.exists():
                return default

            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            return config_data.get(key, default)

        except Exception:
            return default

    def set_config_value(self, key: str, value: Any) -> bool:
        """Set specific configuration value."""
        try:
            config_data = {}
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)

            config_data[key] = value

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            logger.error(f"Failed to set config value: {e}")
            return False

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List

from src.models.config import DEFAULT_CONFIG_PATH, AppConfig
from src.utils.logger import logger


class ConfigObserver(ABC):
    """Abstract base class for configuration observers"""

    @abstractmethod
    def on_config_changed(self, key: str, old_value: Any, new_value: Any) -> None:
        """Called when configuration value changes"""


class ConfigManager:
    """Configuration manager with Observer pattern support"""

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        self.config_path = config_path
        self.config = AppConfig.load_from_file(config_path)
        self.observers: List[ConfigObserver] = []
        self.change_callbacks: Dict[str, List[Callable]] = {}

        logger.info(f"Configuration loaded from {config_path}")

    def add_observer(self, observer: ConfigObserver) -> None:
        """Add a configuration observer"""
        if observer not in self.observers:
            self.observers.append(observer)
            logger.debug(f"Added config observer: {type(observer).__name__}")

    def remove_observer(self, observer: ConfigObserver) -> None:
        """Remove a configuration observer"""
        if observer in self.observers:
            self.observers.remove(observer)
            logger.debug(f"Removed config observer: {type(observer).__name__}")

    def add_change_callback(self, key: str, callback: Callable[[Any, Any], None]) -> None:
        """Add a callback for specific configuration key changes"""
        if key not in self.change_callbacks:
            self.change_callbacks[key] = []
        self.change_callbacks[key].append(callback)

    def get_config(self) -> AppConfig:
        """Get current configuration"""
        return self.config

    def get_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key (e.g., 'tts.enabled')"""
        try:
            keys = key.split(".")
            value = self.config
            for k in keys:
                value = getattr(value, k)
            return value
        except (AttributeError, KeyError):
            return default

    def set_value(self, key: str, value: Any) -> bool:
        """Set configuration value by dot-notation key"""
        try:
            keys = key.split(".")
            current = self.config

            # Navigate to the parent object
            for k in keys[:-1]:
                current = getattr(current, k)

            # Get old value for notification
            old_value = getattr(current, keys[-1], None)

            # Set new value
            setattr(current, keys[-1], value)

            # Notify observers
            self._notify_observers(key, old_value, value)

            # Call specific callbacks
            if key in self.change_callbacks:
                for callback in self.change_callbacks[key]:
                    try:
                        callback(old_value, value)
                    except Exception as e:
                        logger.error(f"Error in config callback for {key}", error=e)

            logger.log_config_change(key, old_value, value)
            return True

        except (AttributeError, KeyError) as e:
            logger.error(f"Failed to set config value {key}", error=e)
            return False

    def update_config(self, new_config: AppConfig) -> None:
        """Update entire configuration"""
        old_config = self.config
        self.config = new_config

        # Notify about full config change
        self._notify_observers("*", old_config, new_config)
        logger.info("Configuration updated completely")

    def save_config(self) -> bool:
        """Save current configuration to file"""
        try:
            success = self.config.save_to_file(self.config_path)
            if success:
                logger.info(f"Configuration saved to {self.config_path}")
            else:
                logger.error(f"Failed to save configuration to {self.config_path}")
            return success
        except Exception as e:
            logger.error("Error saving configuration", error=e)
            return False

    def reload_config(self) -> bool:
        """Reload configuration from file"""
        try:
            old_config = self.config
            self.config = AppConfig.load_from_file(self.config_path)
            self._notify_observers("*", old_config, self.config)
            logger.info(f"Configuration reloaded from {self.config_path}")
            return True
        except Exception as e:
            logger.error("Error reloading configuration", error=e)
            return False

    def reset_to_defaults(self) -> None:
        """Reset configuration to default values"""
        old_config = self.config
        self.config = AppConfig()
        self._notify_observers("*", old_config, self.config)
        logger.info("Configuration reset to defaults")

    def _notify_observers(self, key: str, old_value: Any, new_value: Any) -> None:
        """Notify all observers about configuration change"""
        for observer in self.observers:
            try:
                observer.on_config_changed(key, old_value, new_value)
            except Exception as e:
                logger.error(
                    f"Error in config observer {type(observer).__name__}", error=e, key=key
                )

    def get_section(self, section: str) -> Any:
        """Get entire configuration section"""
        return getattr(self.config, section, None)

    def validate_config(self) -> List[str]:
        """Validate current configuration and return list of issues"""
        issues = []

        # Validate hotkeys
        hotkeys = self.config.hotkeys
        if not hotkeys.area_select:
            issues.append("area_select hotkey is empty")

        # Validate languages
        languages = self.config.languages
        if not languages.target_languages:
            issues.append("No target languages configured")
        if languages.default_target >= len(languages.target_languages):
            issues.append("Default target language index out of range")

        # Validate TTS
        tts = self.config.tts
        if tts.rate < 50 or tts.rate > 500:
            issues.append("TTS rate out of valid range (50-500)")

        # Validate image processing
        img = self.config.image_processing
        if img.upscale_factor < 0.5 or img.upscale_factor > 10:
            issues.append("Upscale factor out of valid range (0.5-10)")

        return issues

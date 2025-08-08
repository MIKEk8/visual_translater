"""
Refactored Application Components - Single Responsibility Classes
Extracted from large Application class (15+ methods → 4 focused classes)
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple


class ConfigurationManager:
    """
    Single Responsibility: Application configuration management
    Methods: 5 (was part of 20+ method Application class)
    """

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.config_data = {}
        self._default_config = {
            "source_language": "auto",
            "target_language": "en",
            "screenshot_hotkey": "ctrl+shift+s",
            "translate_hotkey": "ctrl+shift+t",
            "theme": "light",
            "tts_enabled": True,
            "auto_copy": False,
        }

    def load_configuration(self) -> Dict[str, Any]:
        """Load configuration from file - complexity 3"""
        try:
            if self.config_file and self._config_file_exists():  # +1
                self.config_data = self._read_config_file()
            else:  # +1
                self.config_data = self._default_config.copy()
            return self.config_data
        except Exception:
            return self._default_config.copy()

    def save_configuration(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file - complexity 3"""
        try:
            # Validate config before saving
            if not self._validate_config_structure(config):  # +1
                return False

            self.config_data = config
            if self.config_file:  # +1
                return self._write_config_file(config)
            return True
        except Exception:
            return False

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get specific setting - complexity 2"""
        if key not in self.config_data:  # +1
            return default
        return self.config_data[key]

    def update_setting(self, key: str, value: Any) -> bool:
        """Update specific setting - complexity 2"""
        try:
            self.config_data[key] = value
            return True
        except Exception:  # +1
            return False

    def _config_file_exists(self) -> bool:
        """Check if config file exists - complexity 1"""
        # Implementation would check file system
        return True

    def _read_config_file(self) -> Dict[str, Any]:
        """Read config from file - complexity 1"""
        # Implementation would read JSON/YAML file
        return self._default_config.copy()

    def _write_config_file(self, config: Dict[str, Any]) -> bool:
        """Write config to file - complexity 1"""
        # Implementation would write to JSON/YAML file
        return True

    def _validate_config_structure(self, config: Dict[str, Any]) -> bool:
        """Validate config structure - complexity 1"""
        required_keys = ["source_language", "target_language"]
        return all(key in config for key in required_keys)


class HotkeyManager:
    """
    Single Responsibility: Global hotkey registration and handling
    Methods: 4 (was part of 20+ method Application class)
    """

    def __init__(self):
        self.registered_hotkeys = {}
        self.active = False

    def register_hotkey(self, key_combination: str, callback: Callable) -> bool:
        """Register global hotkey - complexity 3"""
        if not key_combination or not callback:  # +1
            return False

        if key_combination in self.registered_hotkeys:  # +1
            # Unregister existing first
            self.unregister_hotkey(key_combination)

        try:
            self.registered_hotkeys[key_combination] = callback
            return self._register_system_hotkey(key_combination, callback)
        except Exception:
            return False

    def unregister_hotkey(self, key_combination: str) -> bool:
        """Unregister global hotkey - complexity 3"""
        if key_combination not in self.registered_hotkeys:  # +1
            return False

        try:
            callback = self.registered_hotkeys[key_combination]
            if self._unregister_system_hotkey(key_combination):  # +1
                del self.registered_hotkeys[key_combination]
                return True
        except Exception:
            pass

        return False

    def start_monitoring(self) -> bool:
        """Start hotkey monitoring - complexity 2"""
        if self.active:  # +1
            return True

        self.active = True
        return self._start_system_monitoring()

    def stop_monitoring(self) -> bool:
        """Stop hotkey monitoring - complexity 2"""
        if not self.active:  # +1
            return True

        self.active = False
        return self._stop_system_monitoring()

    def _register_system_hotkey(self, key: str, callback: Callable) -> bool:
        """Register with system - complexity 1"""
        # Platform-specific implementation
        return True

    def _unregister_system_hotkey(self, key: str) -> bool:
        """Unregister from system - complexity 1"""
        # Platform-specific implementation
        return True

    def _start_system_monitoring(self) -> bool:
        """Start system monitoring - complexity 1"""
        # Platform-specific implementation
        return True

    def _stop_system_monitoring(self) -> bool:
        """Stop system monitoring - complexity 1"""
        # Platform-specific implementation
        return True


class WindowManager:
    """
    Single Responsibility: Application window lifecycle management
    Methods: 6 (was part of 20+ method Application class)
    """

    def __init__(self):
        self.windows = {}
        self.active_window = None

    def create_window(self, window_id: str, window_class: str, **kwargs) -> bool:
        """Create application window - complexity 4"""
        if window_id in self.windows:  # +1
            return False

        try:
            window = self._create_window_instance(window_class, **kwargs)
            if not window:  # +1
                return False

            self.windows[window_id] = window
            if not self.active_window:  # +1
                self.active_window = window_id

            return True
        except Exception:
            return False

    def show_window(self, window_id: str) -> bool:
        """Show specific window - complexity 3"""
        if window_id not in self.windows:  # +1
            return False

        try:
            window = self.windows[window_id]
            window.show()
            self.active_window = window_id
            return True
        except Exception:  # +1
            return False

    def hide_window(self, window_id: str) -> bool:
        """Hide specific window - complexity 3"""
        if window_id not in self.windows:  # +1
            return False

        try:
            window = self.windows[window_id]
            window.hide()
            if self.active_window == window_id:  # +1
                self.active_window = None
            return True
        except Exception:
            return False

    def close_window(self, window_id: str) -> bool:
        """Close and destroy window - complexity 3"""
        if window_id not in self.windows:  # +1
            return False

        try:
            window = self.windows[window_id]
            window.close()
            del self.windows[window_id]
            if self.active_window == window_id:  # +1
                self.active_window = None
            return True
        except Exception:
            return False

    def get_active_window(self) -> Optional[str]:
        """Get active window ID - complexity 1"""
        return self.active_window

    def list_windows(self) -> List[str]:
        """List all window IDs - complexity 1"""
        return list(self.windows.keys())

    def _create_window_instance(self, window_class: str, **kwargs):
        """Create window instance by class name - complexity 3"""
        # Factory method for creating different window types
        if window_class == "settings":  # +1
            from ..ui.settings_window import SettingsWindow

            return SettingsWindow(**kwargs)
        elif window_class == "history":  # +1
            from ..ui.history_window import HistoryWindow

            return HistoryWindow(**kwargs)
        else:
            # Default or unknown window type
            return None


class RefactoredApplication:
    """
    Main Application Coordinator - Single Responsibility: Application lifecycle
    Methods: 6 (down from 20+ in monolithic Application class)
    Complexity: All methods ≤ 5
    """

    def __init__(self, config_file: Optional[str] = None):
        # Composed managers with single responsibilities
        self.config_manager = ConfigurationManager(config_file)
        self.hotkey_manager = HotkeyManager()
        self.window_manager = WindowManager()

        # Application state
        self.running = False
        self.initialized = False

    def initialize(self) -> bool:
        """Initialize application - complexity 5"""
        if self.initialized:  # +1
            return True

        # Step 1: Load configuration
        config = self.config_manager.load_configuration()
        if not config:  # +1
            return False

        # Step 2: Register hotkeys
        screenshot_hotkey = config.get("screenshot_hotkey", "ctrl+shift+s")
        if not self.hotkey_manager.register_hotkey(
            screenshot_hotkey, self._on_screenshot_hotkey
        ):  # +1
            return False

        translate_hotkey = config.get("translate_hotkey", "ctrl+shift+t")
        if not self.hotkey_manager.register_hotkey(
            translate_hotkey, self._on_translate_hotkey
        ):  # +1
            return False

        # Step 3: Start hotkey monitoring
        if not self.hotkey_manager.start_monitoring():
            return False

        self.initialized = True
        return True

    def start(self) -> bool:
        """Start application - complexity 3"""
        if not self.initialized:  # +1
            if not self.initialize():  # +1
                return False

        self.running = True
        return True

    def shutdown(self) -> bool:
        """Shutdown application - complexity 3"""
        if not self.running:  # +1
            return True

        # Stop hotkey monitoring
        self.hotkey_manager.stop_monitoring()

        # Close all windows
        for window_id in self.window_manager.list_windows():
            self.window_manager.close_window(window_id)

        self.running = False
        return True

    def show_settings(self) -> bool:
        """Show settings window - complexity 2"""
        if not self.window_manager.create_window("settings", "settings"):  # +1
            return False

        return self.window_manager.show_window("settings")

    def show_history(self) -> bool:
        """Show history window - complexity 2"""
        if not self.window_manager.create_window("history", "history"):  # +1
            return False

        return self.window_manager.show_window("history")

    def is_running(self) -> bool:
        """Check if application is running - complexity 1"""
        return self.running

    def _on_screenshot_hotkey(self):
        """Handle screenshot hotkey - complexity 1"""
        # Implementation would trigger screenshot capture
        pass

    def _on_translate_hotkey(self):
        """Handle translate hotkey - complexity 1"""
        # Implementation would trigger translation
        pass

"""
Plugin service for integrating plugin system with DI container.
Provides a service layer for plugin management in Screen Translator v2.0.
"""

from typing import Any, Dict, List, Optional

from src.plugins.base_plugin import OCRPlugin, PluginType, TranslationPlugin, TTSPlugin
from src.plugins.plugin_manager import PluginManager
from src.services.config_manager import ConfigManager, ConfigObserver
from src.utils.logger import logger


class PluginService(ConfigObserver):
    """Service for managing plugins within the application."""

    def __init__(
        self, config_manager: ConfigManager, plugin_directories: Optional[List[str]] = None
    ):
        """
        Initialize plugin service.

        Args:
            config_manager: Configuration manager instance
            plugin_directories: Additional plugin directories to search
        """
        self.config_manager = config_manager
        self.plugin_manager = PluginManager(plugin_directories)
        self._initialized = False

        # Register as config observer for plugin-related config changes
        self.config_manager.add_observer(self)

        logger.info("Plugin service initialized")

    def initialize(self) -> bool:
        """Initialize the plugin service and load plugins."""
        try:
            # Load plugin configurations
            plugin_config_path = "plugins_config.json"
            self.plugin_manager.load_plugin_config(plugin_config_path)

            # Discover and load all available plugins
            loaded_count = self.plugin_manager.load_all_plugins()

            self._initialized = True
            logger.info(f"Plugin service initialized with {loaded_count} plugins")
            return True

        except Exception as e:
            logger.error("Failed to initialize plugin service", error=e)
            return False

    def cleanup(self) -> None:
        """Cleanup plugin service."""
        if self._initialized:
            # Save plugin configuration
            plugin_config_path = "plugins_config.json"
            self.plugin_manager.save_plugin_config(plugin_config_path)

            # Unregister all plugins
            for plugin_name in list(self.plugin_manager.registered_plugins.keys()):
                self.plugin_manager.unregister_plugin(plugin_name)

            self._initialized = False
            logger.info("Plugin service cleaned up")

    def on_config_changed(self, key: str, old_value: Any, new_value: Any) -> None:
        """Handle configuration changes that affect plugins."""
        if key.startswith("plugins."):
            # Plugin-specific configuration changed
            plugin_name = key.split(".")[1]
            self._update_plugin_config(plugin_name)
            logger.debug(f"Updated plugin config for: {plugin_name}")

    def get_available_ocr_engines(self) -> List[OCRPlugin]:
        """Get all available OCR plugins."""
        return self.plugin_manager.get_plugins_by_type(PluginType.OCR)

    def get_available_translation_engines(self) -> List[TranslationPlugin]:
        """Get all available translation plugins."""
        return self.plugin_manager.get_plugins_by_type(PluginType.TRANSLATION)

    def get_available_tts_engines(self) -> List[TTSPlugin]:
        """Get all available TTS plugins."""
        return self.plugin_manager.get_plugins_by_type(PluginType.TTS)

    def get_best_ocr_engine(self) -> Optional[OCRPlugin]:
        """Get the best available OCR engine."""
        ocr_engines = self.get_available_ocr_engines()

        # Simple selection: return first available enabled engine
        for engine in ocr_engines:
            if engine.enabled and engine.is_available():
                return engine

        return None

    def get_best_translation_engine(self) -> Optional[TranslationPlugin]:
        """Get the best available translation engine."""
        translation_engines = self.get_available_translation_engines()

        # Simple selection: return first available enabled engine
        for engine in translation_engines:
            if engine.enabled and engine.is_available():
                return engine

        return None

    def get_best_tts_engine(self) -> Optional[TTSPlugin]:
        """Get the best available TTS engine."""
        tts_engines = self.get_available_tts_engines()

        # Simple selection: return first available enabled engine
        for engine in tts_engines:
            if engine.enabled and engine.is_available():
                return engine

        return None

    def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a plugin."""
        return self.plugin_manager.enable_plugin(plugin_name)

    def disable_plugin(self, plugin_name: str) -> bool:
        """Disable a plugin."""
        return self.plugin_manager.disable_plugin(plugin_name)

    def get_plugin_info(self) -> List[Dict[str, Any]]:
        """Get information about all registered plugins."""
        return self.plugin_manager.get_plugin_info()

    def configure_plugin(self, plugin_name: str, config: Dict[str, Any]) -> bool:
        """
        Configure a plugin with new settings.

        Args:
            plugin_name: Name of plugin to configure
            config: New configuration dict

        Returns:
            True if configuration successful
        """
        plugin = self.plugin_manager.get_plugin(plugin_name)
        if not plugin:
            logger.error(f"Plugin not found: {plugin_name}")
            return False

        try:
            # Validate configuration
            valid, errors = plugin.validate_config(config)
            if not valid:
                logger.error(f"Invalid config for {plugin_name}: {errors}")
                return False

            # Update plugin configuration
            self.plugin_manager.plugin_configs[plugin_name] = config

            # If plugin is initialized, reinitialize with new config
            if plugin.initialized:
                plugin.cleanup()
                if not plugin.initialize(config):
                    logger.error(f"Failed to reinitialize plugin: {plugin_name}")
                    return False

            logger.info(f"Configured plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to configure plugin {plugin_name}", error=e)
            return False

    def test_plugin(self, plugin_name: str) -> bool:
        """
        Test a plugin's basic functionality.

        Args:
            plugin_name: Name of plugin to test

        Returns:
            True if test successful
        """
        plugin = self.plugin_manager.get_plugin(plugin_name)
        if not plugin:
            return False

        try:
            # Basic availability test
            if not plugin.is_available():
                logger.warning(f"Plugin dependencies not available: {plugin_name}")
                return False

            # Type-specific tests
            if isinstance(plugin, TTSPlugin):
                # Test TTS with simple text
                return plugin.speak("Test", "en")

            elif isinstance(plugin, TranslationPlugin):
                # Test translation with simple text
                result, confidence = plugin.translate("Hello", "en", "es")
                return len(result) > 0 and confidence > 0

            elif isinstance(plugin, OCRPlugin):
                # OCR test would require image data, skip for now
                return True

            return True

        except Exception as e:
            logger.error(f"Plugin test failed for {plugin_name}", error=e)
            return False

    def get_plugin_statistics(self) -> Dict[str, Any]:
        """Get statistics about plugin usage."""
        info = self.get_plugin_info()

        stats = {
            "total_plugins": len(info),
            "enabled_plugins": len([p for p in info if p["enabled"]]),
            "plugins_by_type": {},
            "available_plugins": len([p for p in info if p["enabled"]]),
        }

        # Count by type
        for plugin_type in PluginType:
            type_plugins = [p for p in info if p["type"] == plugin_type.value]
            stats["plugins_by_type"][plugin_type.value] = {
                "total": len(type_plugins),
                "enabled": len([p for p in type_plugins if p["enabled"]]),
            }

        return stats

    def _update_plugin_config(self, plugin_name: str) -> None:
        """Update plugin configuration from config manager."""
        # This would be called when plugin-specific config changes
        # Implementation depends on how plugin configs are stored in main config

    @property
    def initialized(self) -> bool:
        """Check if plugin service is initialized."""
        return self._initialized

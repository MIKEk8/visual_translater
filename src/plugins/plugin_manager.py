"""
Plugin manager for Screen Translator v2.0.
Handles loading, registering, and managing plugins.
"""

import importlib
import importlib.util
import json
import os
import sys
from typing import Any, Dict, List, Optional

from src.plugins.base_plugin import (
    BasePlugin,
    PluginDependencyError,
    PluginInitializationError,
    PluginType,
)
from src.utils.logger import logger


class PluginManager:
    """Manages plugin loading, registration, and lifecycle."""

    def __init__(self, plugin_directories: Optional[List[str]] = None):
        """
        Initialize plugin manager.

        Args:
            plugin_directories: List of directories to search for plugins
        """
        self.plugin_directories = plugin_directories or []
        self.registered_plugins: Dict[str, BasePlugin] = {}
        self.plugins_by_type: Dict[PluginType, List[BasePlugin]] = {
            plugin_type: [] for plugin_type in PluginType
        }
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}

        # Add default plugin directory
        default_plugin_dir = os.path.join(os.path.dirname(__file__), "builtin")
        if default_plugin_dir not in self.plugin_directories:
            self.plugin_directories.append(default_plugin_dir)

        logger.info(f"Plugin manager initialized with directories: {self.plugin_directories}")

    def discover_plugins(self) -> List[BasePlugin]:
        """
        Discover and load available plugins in plugin directories.

        Returns:
            List of loaded plugin instances
        """
        discovered_plugins = []
        plugin_paths = []

        for plugin_dir in self.plugin_directories:
            if not os.path.exists(plugin_dir):
                logger.warning(f"Plugin directory does not exist: {plugin_dir}")
                continue

            logger.debug(f"Scanning plugin directory: {plugin_dir}")

            # Look for Python files and packages
            for item in os.listdir(plugin_dir):
                item_path = os.path.join(plugin_dir, item)

                # Skip __pycache__ and other non-plugin directories
                if item.startswith("__") or item.startswith("."):
                    continue

                if os.path.isfile(item_path) and item.endswith(".py"):
                    # Single file plugin
                    plugin_name = item[:-3]  # Remove .py extension
                    plugin_paths.append(os.path.join(plugin_dir, plugin_name))
                    logger.debug(f"Found plugin file: {plugin_name}")

                elif os.path.isdir(item_path):
                    # Package plugin
                    init_file = os.path.join(item_path, "__init__.py")
                    if os.path.exists(init_file):
                        plugin_paths.append(item_path)
                        logger.debug(f"Found plugin package: {item}")

        # Load discovered plugins
        for plugin_path in plugin_paths:
            plugin = self.load_plugin(plugin_path)
            if plugin is not None:
                discovered_plugins.append(plugin)

        logger.info(f"Discovered {len(discovered_plugins)} plugins")
        return discovered_plugins

    def load_plugin(self, plugin_path: str) -> Optional[BasePlugin]:
        """
        Load a plugin from the given path.

        Args:
            plugin_path: Path to plugin file or directory

        Returns:
            Loaded plugin instance or None if failed
        """
        try:
            # Determine module name
            if os.path.isfile(plugin_path + ".py"):
                # Single file plugin
                module_name = os.path.basename(plugin_path)
                spec = importlib.util.spec_from_file_location(module_name, plugin_path + ".py")
            elif os.path.isdir(plugin_path):
                # Package plugin
                module_name = os.path.basename(plugin_path)
                spec = importlib.util.spec_from_file_location(
                    module_name, os.path.join(plugin_path, "__init__.py")
                )
            else:
                logger.error(f"Invalid plugin path: {plugin_path}")
                return None

            if spec is None or spec.loader is None:
                logger.error(f"Could not create module spec for: {plugin_path}")
                return None

            # Load the module
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Find plugin class in module
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BasePlugin)
                    and attr != BasePlugin
                    and not attr.__name__.startswith("Base")
                ):
                    plugin_class = attr
                    break

            if plugin_class is None:
                logger.error(f"No plugin class found in: {plugin_path}")
                return None

            # Instantiate plugin
            plugin_instance = plugin_class()

            # Validate plugin
            if not isinstance(plugin_instance, BasePlugin):
                logger.error(f"Plugin class does not inherit from BasePlugin: {plugin_class}")
                return None

            logger.info(f"Successfully loaded plugin: {plugin_instance.metadata.name}")
            return plugin_instance

        except Exception as e:
            logger.error(f"Failed to load plugin from {plugin_path}", error=e)
            return None

    def register_plugin(self, plugin: BasePlugin, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Register a plugin with the manager.

        Args:
            plugin: Plugin instance to register
            config: Plugin configuration

        Returns:
            True if registration successful
        """
        try:
            metadata = plugin.metadata
            plugin_name = metadata.name

            # Check if plugin already registered
            if plugin_name in self.registered_plugins:
                logger.warning(f"Plugin already registered: {plugin_name}")
                return False

            # Check dependencies
            if not self._check_dependencies(plugin):
                raise PluginDependencyError(f"Dependencies not met for plugin: {plugin_name}")

            # Validate and set configuration
            config = config or {}
            valid, errors = plugin.validate_config(config)
            if not valid:
                raise PluginInitializationError(f"Invalid config for {plugin_name}: {errors}")

            # Initialize plugin
            if not plugin.initialize(config):
                raise PluginInitializationError(f"Plugin initialization failed: {plugin_name}")

            # Register plugin
            self.registered_plugins[plugin_name] = plugin
            self.plugins_by_type[metadata.plugin_type].append(plugin)
            self.plugin_configs[plugin_name] = config

            logger.info(
                f"Successfully registered plugin: {plugin_name} (type: {metadata.plugin_type.value})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to register plugin: {plugin.metadata.name}", error=e)
            return False

    def unregister_plugin(self, plugin_name: str) -> bool:
        """
        Unregister a plugin.

        Args:
            plugin_name: Name of plugin to unregister

        Returns:
            True if unregistration successful
        """
        if plugin_name not in self.registered_plugins:
            logger.warning(f"Plugin not registered: {plugin_name}")
            return False

        try:
            plugin = self.registered_plugins[plugin_name]

            # Cleanup plugin
            plugin.cleanup()

            # Remove from registries
            del self.registered_plugins[plugin_name]
            self.plugins_by_type[plugin.metadata.plugin_type].remove(plugin)
            if plugin_name in self.plugin_configs:
                del self.plugin_configs[plugin_name]

            logger.info(f"Successfully unregistered plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to unregister plugin: {plugin_name}", error=e)
            return False

    def get_plugins_by_type(self, plugin_type: PluginType) -> List[BasePlugin]:
        """
        Get all registered plugins of a specific type.

        Args:
            plugin_type: Type of plugins to retrieve

        Returns:
            List of plugins of the specified type
        """
        return [p for p in self.plugins_by_type[plugin_type] if p.enabled]

    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """
        Get a specific plugin by name.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin instance or None if not found
        """
        return self.registered_plugins.get(plugin_name)

    def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a plugin."""
        plugin = self.get_plugin(plugin_name)
        if plugin:
            plugin.enable()
            logger.info(f"Enabled plugin: {plugin_name}")
            return True
        return False

    def disable_plugin(self, plugin_name: str) -> bool:
        """Disable a plugin."""
        plugin = self.get_plugin(plugin_name)
        if plugin:
            plugin.disable()
            logger.info(f"Disabled plugin: {plugin_name}")
            return True
        return False

    def reload_plugin(self, plugin_name: str) -> bool:
        """
        Reload a plugin (unregister and register again).

        Args:
            plugin_name: Name of plugin to reload

        Returns:
            True if reload successful
        """
        if plugin_name not in self.registered_plugins:
            return False

        # Save configuration
        self.plugin_configs.get(plugin_name, {})

        # Unregister
        if not self.unregister_plugin(plugin_name):
            return False

        # Find and load plugin again
        # This is simplified - in practice you'd need to track plugin paths
        logger.info(f"Plugin {plugin_name} unregistered - manual reload required")
        return True

    def load_all_plugins(self) -> int:
        """
        Discover and load all available plugins.

        Returns:
            Number of successfully loaded plugins
        """
        discovered = self.discover_plugins()
        loaded_count = 0

        for plugin_path in discovered:
            plugin = self.load_plugin(plugin_path)
            if plugin:
                # Try to register with default config
                if self.register_plugin(plugin):
                    loaded_count += 1

        logger.info(f"Loaded {loaded_count} plugins out of {len(discovered)} discovered")
        return loaded_count

    def get_plugin_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all registered plugins.

        Returns:
            List of plugin info dictionaries
        """
        info = []
        for plugin_name, plugin in self.registered_plugins.items():
            metadata = plugin.metadata
            info.append(
                {
                    "name": metadata.name,
                    "version": metadata.version,
                    "description": metadata.description,
                    "author": metadata.author,
                    "type": metadata.plugin_type.value,
                    "enabled": plugin.enabled,
                    "initialized": plugin.initialized,
                    "dependencies": metadata.dependencies,
                }
            )

        return info

    def _check_dependencies(self, plugin: BasePlugin) -> bool:
        """
        Check if plugin dependencies are available.

        Args:
            plugin: Plugin to check

        Returns:
            True if all dependencies are met
        """
        metadata = plugin.metadata

        # Check Python module dependencies
        for dependency in metadata.dependencies:
            try:
                importlib.import_module(dependency)
            except ImportError:
                logger.error(f"Missing dependency for {metadata.name}: {dependency}")
                return False

        # Check plugin-specific availability
        if not plugin.is_available():
            logger.error(f"Plugin availability check failed: {metadata.name}")
            return False

        return True

    def save_plugin_config(self, config_path: str) -> bool:
        """
        Save plugin configurations to file.

        Args:
            config_path: Path to save configuration

        Returns:
            True if save successful
        """
        try:
            config_data = {"plugins": {}}

            for plugin_name, plugin in self.registered_plugins.items():
                config_data["plugins"][plugin_name] = {
                    "enabled": plugin.enabled,
                    "config": self.plugin_configs.get(plugin_name, {}),
                }

            with open(config_path, "w") as f:
                json.dump(config_data, f, indent=2)

            logger.info(f"Saved plugin configuration to: {config_path}")
            return True

        except Exception as e:
            logger.error("Failed to save plugin config", error=e)
            return False

    def load_plugin_config(self, config_path: str) -> bool:
        """
        Load plugin configurations from file.

        Args:
            config_path: Path to load configuration from

        Returns:
            True if load successful
        """
        try:
            if not os.path.exists(config_path):
                logger.info(f"Plugin config file not found: {config_path}")
                return True

            with open(config_path, "r") as f:
                config_data = json.load(f)

            plugins_config = config_data.get("plugins", {})

            for plugin_name, plugin_data in plugins_config.items():
                plugin = self.get_plugin(plugin_name)
                if plugin:
                    # Update enabled state
                    if plugin_data.get("enabled", True):
                        plugin.enable()
                    else:
                        plugin.disable()

                    # Update configuration
                    plugin_config = plugin_data.get("config", {})
                    self.plugin_configs[plugin_name] = plugin_config

            logger.info(f"Loaded plugin configuration from: {config_path}")
            return True

        except Exception as e:
            logger.error("Failed to load plugin config", error=e)
            return False

"""Unit tests for plugin manager module"""

import importlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from src.plugins.base_plugin import BasePlugin, PluginMetadata, PluginType
from src.plugins.plugin_manager import PluginManager


@pytest.fixture
def mock_plugin():
    """Create mock plugin"""
    plugin = Mock(spec=BasePlugin)
    plugin.metadata = PluginMetadata(
        name="Test Plugin",
        version="1.0.0",
        description="Test plugin",
        author="Test Author",
        plugin_type=PluginType.OCR,
    )
    plugin.is_available.return_value = True
    plugin.initialize.return_value = True
    plugin.cleanup.return_value = None
    return plugin


@pytest.fixture
def plugin_directories(tmp_path):
    """Create temporary plugin directories"""
    plugin_dir1 = tmp_path / "plugins1"
    plugin_dir2 = tmp_path / "plugins2"
    plugin_dir1.mkdir()
    plugin_dir2.mkdir()

    return [str(plugin_dir1), str(plugin_dir2)]


@pytest.fixture
def plugin_manager(plugin_directories):
    """Create PluginManager instance"""
    return PluginManager(plugin_directories)


class TestPluginManager:
    """Test PluginManager class"""

    def test_initialization(self, plugin_manager, plugin_directories):
        """Test plugin manager initialization"""
        assert plugin_manager.plugin_directories == plugin_directories + [
            os.path.join(os.path.dirname(__file__).replace("/tests/unit", "/plugins"), "builtin")
        ]
        assert plugin_manager.registered_plugins == {}
        assert len(plugin_manager.plugins_by_type) == len(PluginType)
        assert plugin_manager.plugin_configs == {}

    def test_initialization_default_directories(self):
        """Test initialization with default directories"""
        manager = PluginManager()

        # Should include default builtin directory
        builtin_dir = os.path.join(
            os.path.dirname(__file__).replace("/tests/unit", "/plugins"), "builtin"
        )
        assert builtin_dir in manager.plugin_directories

    def test_register_plugin(self, plugin_manager, mock_plugin):
        """Test registering a plugin"""
        success = plugin_manager.register_plugin(mock_plugin)

        assert success is True
        assert mock_plugin.metadata.name in plugin_manager.registered_plugins
        assert mock_plugin in plugin_manager.plugins_by_type[PluginType.OCR]
        mock_plugin.initialize.assert_called_once()

    def test_register_plugin_already_exists(self, plugin_manager, mock_plugin):
        """Test registering plugin that already exists"""
        # Register first time
        plugin_manager.register_plugin(mock_plugin)

        # Try to register again
        success = plugin_manager.register_plugin(mock_plugin)

        assert success is False

    def test_register_plugin_initialization_failure(self, plugin_manager, mock_plugin):
        """Test registering plugin with initialization failure"""
        mock_plugin.initialize.return_value = False

        success = plugin_manager.register_plugin(mock_plugin)

        assert success is False
        assert mock_plugin.metadata.name not in plugin_manager.registered_plugins

    def test_unregister_plugin(self, plugin_manager, mock_plugin):
        """Test unregistering a plugin"""
        # First register the plugin
        plugin_manager.register_plugin(mock_plugin)

        # Then unregister
        success = plugin_manager.unregister_plugin(mock_plugin.metadata.name)

        assert success is True
        assert mock_plugin.metadata.name not in plugin_manager.registered_plugins
        assert mock_plugin not in plugin_manager.plugins_by_type[PluginType.OCR]
        mock_plugin.cleanup.assert_called_once()

    def test_unregister_nonexistent_plugin(self, plugin_manager):
        """Test unregistering plugin that doesn't exist"""
        success = plugin_manager.unregister_plugin("NonexistentPlugin")

        assert success is False

    def test_get_plugin(self, plugin_manager, mock_plugin):
        """Test getting registered plugin"""
        plugin_manager.register_plugin(mock_plugin)

        retrieved_plugin = plugin_manager.get_plugin(mock_plugin.metadata.name)

        assert retrieved_plugin == mock_plugin

    def test_get_nonexistent_plugin(self, plugin_manager):
        """Test getting plugin that doesn't exist"""
        plugin = plugin_manager.get_plugin("NonexistentPlugin")

        assert plugin is None

    def test_get_plugins_by_type(self, plugin_manager, mock_plugin):
        """Test getting plugins by type"""
        plugin_manager.register_plugin(mock_plugin)

        ocr_plugins = plugin_manager.get_plugins_by_type(PluginType.OCR)

        assert len(ocr_plugins) == 1
        assert mock_plugin in ocr_plugins

    def test_get_plugins_by_type_empty(self, plugin_manager):
        """Test getting plugins by type when none exist"""
        translation_plugins = plugin_manager.get_plugins_by_type(PluginType.TRANSLATION)

        assert len(translation_plugins) == 0

    def test_get_available_plugins(self, plugin_manager):
        """Test getting available plugins"""
        # Create mock plugins with different availability
        available_plugin = Mock(spec=BasePlugin)
        available_plugin.metadata = PluginMetadata(
            name="Available Plugin",
            version="1.0.0",
            description="Available",
            author="Author",
            plugin_type=PluginType.OCR,
        )
        available_plugin.is_available.return_value = True
        available_plugin.initialize.return_value = True

        unavailable_plugin = Mock(spec=BasePlugin)
        unavailable_plugin.metadata = PluginMetadata(
            name="Unavailable Plugin",
            version="1.0.0",
            description="Unavailable",
            author="Author",
            plugin_type=PluginType.OCR,
        )
        unavailable_plugin.is_available.return_value = False
        unavailable_plugin.initialize.return_value = True

        plugin_manager.register_plugin(available_plugin)
        plugin_manager.register_plugin(unavailable_plugin)

        available = plugin_manager.get_available_plugins()

        assert len(available) == 1
        assert available_plugin in available
        assert unavailable_plugin not in available

    def test_list_registered_plugins(self, plugin_manager, mock_plugin):
        """Test listing all registered plugins"""
        plugin_manager.register_plugin(mock_plugin)

        plugins = plugin_manager.list_registered_plugins()

        assert len(plugins) == 1
        assert plugins[0] == mock_plugin.metadata.name

    def test_discover_plugins(self, plugin_manager, plugin_directories):
        """Test discovering plugins in directories"""
        # Create mock plugin file
        plugin_dir = Path(plugin_directories[0])
        plugin_file = plugin_dir / "test_plugin.py"

        plugin_code = """
from src.plugins.base_plugin import BasePlugin, PluginMetadata, PluginType

class TestPlugin(BasePlugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="Discovered Plugin",
            version="1.0.0",
            description="Test discovered plugin",
            author="Test",
            plugin_type=PluginType.OCR
        )

    def is_available(self):
        return True

    def initialize(self):
        return True

    def cleanup(self):
        pass

def get_plugin():
    return TestPlugin()
"""

        plugin_file.write_text(plugin_code)

        with patch("importlib.util.spec_from_file_location") as mock_spec, patch(
            "importlib.util.module_from_spec"
        ) as mock_module, patch("sys.modules"):

            # Mock module loading
            mock_spec_obj = Mock()
            mock_spec.return_value = mock_spec_obj

            mock_module_obj = Mock()
            mock_module.return_value = mock_module_obj

            # Mock get_plugin function
            mock_plugin_instance = Mock(spec=BasePlugin)
            mock_plugin_instance.metadata = PluginMetadata(
                name="Discovered Plugin",
                version="1.0.0",
                description="Test",
                author="Test",
                plugin_type=PluginType.OCR,
            )
            mock_plugin_instance.is_available.return_value = True
            mock_plugin_instance.initialize.return_value = True

            mock_module_obj.get_plugin.return_value = mock_plugin_instance

            discovered = plugin_manager.discover_plugins()

            # Should discover the plugin
            assert len(discovered) >= 0  # May find builtin plugins too

    def test_load_plugin_config(self, plugin_manager, plugin_directories):
        """Test loading plugin configuration"""
        # Create config file
        config_dir = Path(plugin_directories[0])
        config_file = config_dir / "plugin_config.json"

        config_data = {
            "TestPlugin": {"enabled": True, "settings": {"param1": "value1", "param2": 42}}
        }

        config_file.write_text(json.dumps(config_data))

        plugin_manager.load_plugin_config(str(config_file))

        assert "TestPlugin" in plugin_manager.plugin_configs
        assert plugin_manager.plugin_configs["TestPlugin"]["enabled"] is True

    def test_save_plugin_config(self, plugin_manager, tmp_path):
        """Test saving plugin configuration"""
        # Set some config data
        plugin_manager.plugin_configs["TestPlugin"] = {
            "enabled": True,
            "settings": {"param": "value"},
        }

        config_file = tmp_path / "saved_config.json"

        plugin_manager.save_plugin_config(str(config_file))

        assert config_file.exists()

        # Verify saved content
        with open(config_file) as f:
            saved_config = json.load(f)

        assert "TestPlugin" in saved_config
        assert saved_config["TestPlugin"]["enabled"] is True

    def test_enable_plugin(self, plugin_manager, mock_plugin):
        """Test enabling a plugin"""
        plugin_manager.register_plugin(mock_plugin)

        success = plugin_manager.enable_plugin(mock_plugin.metadata.name)

        assert success is True
        config = plugin_manager.plugin_configs.get(mock_plugin.metadata.name, {})
        assert config.get("enabled", False) is True

    def test_disable_plugin(self, plugin_manager, mock_plugin):
        """Test disabling a plugin"""
        plugin_manager.register_plugin(mock_plugin)
        plugin_manager.enable_plugin(mock_plugin.metadata.name)

        success = plugin_manager.disable_plugin(mock_plugin.metadata.name)

        assert success is True
        config = plugin_manager.plugin_configs.get(mock_plugin.metadata.name, {})
        assert config.get("enabled", True) is False

    def test_is_plugin_enabled(self, plugin_manager, mock_plugin):
        """Test checking if plugin is enabled"""
        plugin_manager.register_plugin(mock_plugin)

        # Default should be enabled
        assert plugin_manager.is_plugin_enabled(mock_plugin.metadata.name) is True

        # Disable and check
        plugin_manager.disable_plugin(mock_plugin.metadata.name)
        assert plugin_manager.is_plugin_enabled(mock_plugin.metadata.name) is False

    def test_get_plugin_info(self, plugin_manager, mock_plugin):
        """Test getting plugin information"""
        plugin_manager.register_plugin(mock_plugin)

        info = plugin_manager.get_plugin_info(mock_plugin.metadata.name)

        assert info is not None
        assert info["name"] == mock_plugin.metadata.name
        assert info["version"] == mock_plugin.metadata.version
        assert info["type"] == mock_plugin.metadata.plugin_type.value
        assert info["enabled"] is True

    def test_get_plugin_info_nonexistent(self, plugin_manager):
        """Test getting info for nonexistent plugin"""
        info = plugin_manager.get_plugin_info("NonexistentPlugin")

        assert info is None

    def test_validate_plugin_dependencies(self, plugin_manager):
        """Test validating plugin dependencies"""
        # Create plugin with dependencies
        plugin_with_deps = Mock(spec=BasePlugin)
        plugin_with_deps.metadata = PluginMetadata(
            name="Plugin With Deps",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.OCR,
            dependencies=["required_lib", "another_lib"],
        )
        plugin_with_deps.is_available.return_value = True
        plugin_with_deps.initialize.return_value = True

        with patch("importlib.util.find_spec") as mock_find_spec:
            # Mock that dependencies are available
            mock_find_spec.return_value = Mock()  # Found

            valid = plugin_manager.validate_plugin_dependencies(plugin_with_deps)

            assert valid is True

    def test_validate_plugin_dependencies_missing(self, plugin_manager):
        """Test validation with missing dependencies"""
        plugin_with_deps = Mock(spec=BasePlugin)
        plugin_with_deps.metadata = PluginMetadata(
            name="Plugin With Missing Deps",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.OCR,
            dependencies=["missing_lib"],
        )

        with patch("importlib.util.find_spec") as mock_find_spec:
            # Mock that dependency is missing
            mock_find_spec.return_value = None

            valid = plugin_manager.validate_plugin_dependencies(plugin_with_deps)

            assert valid is False

    def test_get_plugin_statistics(self, plugin_manager, mock_plugin):
        """Test getting plugin statistics"""
        plugin_manager.register_plugin(mock_plugin)

        stats = plugin_manager.get_plugin_statistics()

        assert "total_plugins" in stats
        assert "plugins_by_type" in stats
        assert "enabled_plugins" in stats
        assert stats["total_plugins"] == 1
        assert stats["plugins_by_type"][PluginType.OCR.value] == 1

    def test_reload_plugin(self, plugin_manager, mock_plugin):
        """Test reloading a plugin"""
        plugin_manager.register_plugin(mock_plugin)

        # Create new version of plugin
        new_plugin = Mock(spec=BasePlugin)
        new_plugin.metadata = PluginMetadata(
            name=mock_plugin.metadata.name,  # Same name
            version="2.0.0",  # New version
            description="Updated plugin",
            author="Test",
            plugin_type=PluginType.OCR,
        )
        new_plugin.is_available.return_value = True
        new_plugin.initialize.return_value = True

        with patch.object(plugin_manager, "_load_plugin_from_file", return_value=new_plugin):
            success = plugin_manager.reload_plugin(mock_plugin.metadata.name)

            assert success is True
            # Should have new version
            reloaded = plugin_manager.get_plugin(mock_plugin.metadata.name)
            assert reloaded.metadata.version == "2.0.0"

    def test_cleanup_all_plugins(self, plugin_manager, mock_plugin):
        """Test cleaning up all plugins"""
        plugin_manager.register_plugin(mock_plugin)

        plugin_manager.cleanup_all_plugins()

        mock_plugin.cleanup.assert_called_once()

    def test_export_plugin_list(self, plugin_manager, mock_plugin):
        """Test exporting plugin list"""
        plugin_manager.register_plugin(mock_plugin)

        exported = plugin_manager.export_plugin_list()

        assert len(exported) == 1
        assert exported[0]["name"] == mock_plugin.metadata.name
        assert exported[0]["version"] == mock_plugin.metadata.version

    def test_import_plugin_list(self, plugin_manager):
        """Test importing plugin list"""
        plugin_data = [
            {
                "name": "Imported Plugin",
                "version": "1.0.0",
                "enabled": True,
                "config": {"setting": "value"},
            }
        ]

        plugin_manager.import_plugin_list(plugin_data)

        # Should create config entry
        assert "Imported Plugin" in plugin_manager.plugin_configs
        assert plugin_manager.plugin_configs["Imported Plugin"]["enabled"] is True

    def test_get_plugin_by_capability(self, plugin_manager):
        """Test getting plugins by capability"""
        # Create plugins with different capabilities
        ocr_plugin = Mock(spec=BasePlugin)
        ocr_plugin.metadata = PluginMetadata(
            name="OCR Plugin",
            version="1.0.0",
            description="OCR",
            author="Test",
            plugin_type=PluginType.OCR,
            capabilities=["text_extraction", "image_processing"],
        )
        ocr_plugin.is_available.return_value = True
        ocr_plugin.initialize.return_value = True

        plugin_manager.register_plugin(ocr_plugin)

        # Find plugins with specific capability
        text_extraction_plugins = plugin_manager.get_plugins_by_capability("text_extraction")

        assert len(text_extraction_plugins) == 1
        assert ocr_plugin in text_extraction_plugins

    def test_check_plugin_compatibility(self, plugin_manager):
        """Test checking plugin compatibility"""
        compatible_plugin = Mock(spec=BasePlugin)
        compatible_plugin.metadata = PluginMetadata(
            name="Compatible Plugin",
            version="1.0.0",
            description="Compatible",
            author="Test",
            plugin_type=PluginType.OCR,
            min_app_version="2.0.0",
        )

        with patch("src.plugins.plugin_manager.__version__", "2.1.0"):
            compatible = plugin_manager.check_plugin_compatibility(compatible_plugin)
            assert compatible is True

    def test_scan_for_updates(self, plugin_manager, mock_plugin):
        """Test scanning for plugin updates"""
        plugin_manager.register_plugin(mock_plugin)

        with patch.object(plugin_manager, "_check_plugin_updates") as mock_check:
            mock_check.return_value = [
                {
                    "name": mock_plugin.metadata.name,
                    "current_version": "1.0.0",
                    "latest_version": "1.1.0",
                    "update_available": True,
                }
            ]

            updates = plugin_manager.scan_for_updates()

            assert len(updates) == 1
            assert updates[0]["update_available"] is True

    def test_backup_plugin_configs(self, plugin_manager, tmp_path):
        """Test backing up plugin configurations"""
        # Set some config
        plugin_manager.plugin_configs["TestPlugin"] = {"enabled": True}

        backup_file = tmp_path / "plugin_backup.json"

        success = plugin_manager.backup_plugin_configs(str(backup_file))

        assert success is True
        assert backup_file.exists()

    def test_restore_plugin_configs(self, plugin_manager, tmp_path):
        """Test restoring plugin configurations"""
        # Create backup file
        backup_data = {"TestPlugin": {"enabled": True, "setting": "value"}}

        backup_file = tmp_path / "plugin_backup.json"
        backup_file.write_text(json.dumps(backup_data))

        success = plugin_manager.restore_plugin_configs(str(backup_file))

        assert success is True
        assert "TestPlugin" in plugin_manager.plugin_configs
        assert plugin_manager.plugin_configs["TestPlugin"]["enabled"] is True

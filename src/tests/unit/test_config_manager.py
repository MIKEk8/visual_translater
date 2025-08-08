import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from src.models.config import AppConfig, HotkeyConfig, LanguageConfig, TTSConfig
from src.services.config_manager import ConfigManager, ConfigObserver


class MockObserver(ConfigObserver):
    """Mock observer for testing"""

    def __init__(self):
        self.changes = []

    def on_config_changed(self, key: str, old_value, new_value) -> None:
        self.changes.append((key, old_value, new_value))


class TestConfigManager(unittest.TestCase):
    """Test ConfigManager functionality"""

    def setUp(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        self.config_manager = ConfigManager(config_path=self.config_file)

    def tearDown(self):
        """Cleanup test environment"""
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        os.rmdir(self.temp_dir)

    def test_default_config_creation(self):
        """Test that default config is created"""
        config = self.config_manager.get_config()
        self.assertIsInstance(config, AppConfig)
        # Check that config has expected structure
        self.assertIsNotNone(config.hotkeys)
        self.assertIsNotNone(config.languages)
        self.assertIsNotNone(config.tts)
        self.assertIsNotNone(config.features)
        self.assertIsNotNone(config.image_processing)

    def test_config_persistence(self):
        """Test config save and load"""
        # Modify config
        config = self.config_manager.get_config()
        original_enabled = config.tts.enabled
        self.config_manager.set_value("tts.enabled", not original_enabled)
        self.config_manager.save_config()  # Save after modification

        # Create new manager with same file
        new_manager = ConfigManager(config_path=self.config_file)
        new_config = new_manager.get_config()

        # Verify persistence
        self.assertEqual(new_config.tts.enabled, not original_enabled)

    def test_observer_notification(self):
        """Test observer pattern"""
        observer = MockObserver()
        self.config_manager.add_observer(observer)

        # Change config
        self.config_manager.set_value("tts.enabled", False)

        # Verify notification
        self.assertEqual(len(observer.changes), 1)
        key, old_val, new_val = observer.changes[0]
        self.assertEqual(key, "tts.enabled")
        self.assertEqual(new_val, False)

    def test_nested_config_access(self):
        """Test nested configuration access"""
        config = self.config_manager.get_config()

        # Test nested access
        self.assertIsNotNone(config.languages.ocr_languages)
        self.assertIsNotNone(config.languages.target_languages)
        self.assertIsNotNone(config.tts.voice_id)

    def test_invalid_config_key(self):
        """Test handling of invalid config keys"""
        # Invalid config keys should return False, not raise exceptions
        result = self.config_manager.set_value("invalid.key.path", "value")
        self.assertFalse(result)

    def test_remove_observer(self):
        """Test observer removal"""
        observer = MockObserver()
        self.config_manager.add_observer(observer)
        self.config_manager.remove_observer(observer)

        # Change should not notify removed observer
        self.config_manager.set_value("tts.enabled", False)
        self.assertEqual(len(observer.changes), 0)

    def test_config_observer_abstract(self):
        """Test that ConfigObserver is abstract"""
        with self.assertRaises(TypeError):
            ConfigObserver()

    def test_add_duplicate_observer(self):
        """Test adding the same observer twice"""
        observer = MockObserver()
        self.config_manager.add_observer(observer)
        self.config_manager.add_observer(observer)  # Add same observer again

        # Should only appear once
        self.assertEqual(len(self.config_manager.observers), 1)

    def test_remove_nonexistent_observer(self):
        """Test removing an observer that wasn't added"""
        observer = MockObserver()

        # Should not raise exception
        self.config_manager.remove_observer(observer)
        self.assertEqual(len(self.config_manager.observers), 0)

    def test_add_change_callback(self):
        """Test adding change callbacks"""
        callback = Mock()
        self.config_manager.add_change_callback("tts.rate", callback)

        # Change the value
        self.config_manager.set_value("tts.rate", 200)

        # Callback should be called
        callback.assert_called_once()

    def test_add_multiple_callbacks(self):
        """Test adding multiple callbacks for same key"""
        callback1 = Mock()
        callback2 = Mock()

        self.config_manager.add_change_callback("tts.rate", callback1)
        self.config_manager.add_change_callback("tts.rate", callback2)

        # Change the value
        self.config_manager.set_value("tts.rate", 200)

        # Both callbacks should be called
        callback1.assert_called_once()
        callback2.assert_called_once()

    def test_callback_exception_handling(self):
        """Test handling of callback exceptions"""
        callback = Mock(side_effect=Exception("Callback failed"))
        self.config_manager.add_change_callback("tts.rate", callback)

        # Should not raise exception despite callback failure
        result = self.config_manager.set_value("tts.rate", 200)
        self.assertTrue(result)

    def test_get_value_with_default(self):
        """Test getting value with default fallback"""
        # Non-existent key should return default
        result = self.config_manager.get_value("nonexistent.key", "default_value")
        self.assertEqual(result, "default_value")

    def test_get_value_nested(self):
        """Test getting nested configuration values"""
        # Test existing nested value
        result = self.config_manager.get_value("tts.enabled")
        self.assertIsInstance(result, bool)

        # Test deeper nesting
        result = self.config_manager.get_value("languages.target_languages")
        self.assertIsInstance(result, list)

    def test_set_value_creates_observer_notification(self):
        """Test that set_value properly notifies observers"""
        observer = MockObserver()
        self.config_manager.add_observer(observer)

        old_value = self.config_manager.get_value("tts.rate")
        new_value = old_value + 50

        self.config_manager.set_value("tts.rate", new_value)

        # Check observer was notified
        self.assertEqual(len(observer.changes), 1)
        key, old_val, new_val = observer.changes[0]
        self.assertEqual(key, "tts.rate")
        self.assertEqual(old_val, old_value)
        self.assertEqual(new_val, new_value)

    def test_update_config(self):
        """Test updating entire configuration"""
        observer = MockObserver()
        self.config_manager.add_observer(observer)

        old_config = self.config_manager.get_config()
        new_config = AppConfig()
        new_config.tts.enabled = not old_config.tts.enabled

        self.config_manager.update_config(new_config)

        # Check config was updated
        self.assertEqual(self.config_manager.get_config(), new_config)

        # Check observer was notified with wildcard key
        self.assertEqual(len(observer.changes), 1)
        key, old_val, new_val = observer.changes[0]
        self.assertEqual(key, "*")
        self.assertEqual(old_val, old_config)
        self.assertEqual(new_val, new_config)

    @patch("src.models.config.AppConfig.load_from_file")
    def test_reload_config(self, mock_load):
        """Test reloading configuration from file"""
        # Setup initial config
        initial_config = AppConfig()
        new_config = AppConfig()
        new_config.tts.enabled = not initial_config.tts.enabled

        mock_load.side_effect = [initial_config, new_config]

        manager = ConfigManager(self.config_file)
        observer = MockObserver()
        manager.add_observer(observer)

        result = manager.reload_config()

        self.assertTrue(result)
        self.assertEqual(manager.get_config(), new_config)
        self.assertEqual(len(observer.changes), 1)

    @patch("src.models.config.AppConfig.load_from_file")
    def test_reload_config_failure(self, mock_load):
        """Test reload config with exception"""
        mock_load.side_effect = [AppConfig(), Exception("Load failed")]

        manager = ConfigManager(self.config_file)
        result = manager.reload_config()

        self.assertFalse(result)

    def test_reset_to_defaults(self):
        """Test resetting configuration to defaults"""
        observer = MockObserver()
        self.config_manager.add_observer(observer)

        # Change some values first
        self.config_manager.set_value("tts.enabled", False)
        old_config = self.config_manager.get_config()

        # Reset to defaults
        self.config_manager.reset_to_defaults()

        # Check config was reset
        self.assertNotEqual(self.config_manager.get_config(), old_config)
        self.assertIsInstance(self.config_manager.get_config(), AppConfig)

        # Check observer was notified (2 changes: set_value + reset)
        self.assertGreaterEqual(len(observer.changes), 1)
        # Last change should be the reset with "*" key
        last_change = observer.changes[-1]
        self.assertEqual(last_change[0], "*")

    def test_observer_exception_handling(self):
        """Test handling of observer exceptions"""
        failing_observer = Mock()
        failing_observer.on_config_changed.side_effect = Exception("Observer failed")

        working_observer = MockObserver()

        self.config_manager.add_observer(failing_observer)
        self.config_manager.add_observer(working_observer)

        # Should not raise exception despite failing observer
        self.config_manager.set_value("tts.rate", 200)

        # Working observer should still be notified
        self.assertEqual(len(working_observer.changes), 1)

    def test_get_section(self):
        """Test getting configuration sections"""
        tts_section = self.config_manager.get_section("tts")
        self.assertIsInstance(tts_section, TTSConfig)

        languages_section = self.config_manager.get_section("languages")
        self.assertIsInstance(languages_section, LanguageConfig)

        # Non-existent section should return None
        result = self.config_manager.get_section("nonexistent")
        self.assertIsNone(result)

    def test_validate_config_valid(self):
        """Test validating a valid configuration"""
        issues = self.config_manager.validate_config()
        # Default config should be valid
        self.assertIsInstance(issues, list)

    def test_validate_config_empty_hotkey(self):
        """Test validation with empty hotkey"""
        # Set empty hotkey
        self.config_manager.set_value("hotkeys.area_select", "")

        issues = self.config_manager.validate_config()

        # Should find the empty hotkey issue
        self.assertTrue(any("hotkey is empty" in issue for issue in issues))

    def test_validate_config_no_target_languages(self):
        """Test validation with no target languages"""
        # Set empty target languages
        self.config_manager.set_value("languages.target_languages", [])

        issues = self.config_manager.validate_config()

        # Should find the missing languages issue
        self.assertTrue(any("No target languages" in issue for issue in issues))

    def test_validate_config_invalid_tts_rate(self):
        """Test validation with invalid TTS rate"""
        # Set invalid rate (too low)
        self.config_manager.set_value("tts.rate", 25)

        issues = self.config_manager.validate_config()

        # Should find the rate issue
        self.assertTrue(any("TTS rate out of valid range" in issue for issue in issues))

    def test_validate_config_invalid_upscale_factor(self):
        """Test validation with invalid upscale factor"""
        # Set invalid upscale factor (too high)
        self.config_manager.set_value("image_processing.upscale_factor", 15.0)

        issues = self.config_manager.validate_config()

        # Should find the upscale factor issue
        self.assertTrue(any("Upscale factor out of valid range" in issue for issue in issues))

    def test_validate_config_default_target_out_of_range(self):
        """Test validation with default target index out of range"""
        # Set target languages and invalid default index
        self.config_manager.set_value("languages.target_languages", ["en"])
        self.config_manager.set_value("languages.default_target", 5)  # Out of range

        issues = self.config_manager.validate_config()

        # Should find the default target issue
        self.assertTrue(
            any("Default target language index out of range" in issue for issue in issues)
        )

    @patch("src.services.config_manager.logger")
    def test_save_config_success(self, mock_logger):
        """Test successful config save"""
        with patch.object(self.config_manager.config, "save_to_file", return_value=True):
            result = self.config_manager.save_config()

            self.assertTrue(result)
            mock_logger.info.assert_called()

    @patch("src.services.config_manager.logger")
    def test_save_config_failure(self, mock_logger):
        """Test config save failure"""
        with patch.object(self.config_manager.config, "save_to_file", return_value=False):
            result = self.config_manager.save_config()

            self.assertFalse(result)
            mock_logger.error.assert_called()

    @patch("src.services.config_manager.logger")
    def test_save_config_exception(self, mock_logger):
        """Test config save with exception"""
        with patch.object(
            self.config_manager.config, "save_to_file", side_effect=Exception("Save failed")
        ):
            result = self.config_manager.save_config()

            self.assertFalse(result)
            mock_logger.error.assert_called()

    def test_notify_observers_internal(self):
        """Test internal _notify_observers method"""
        observer1 = MockObserver()
        observer2 = MockObserver()

        self.config_manager.add_observer(observer1)
        self.config_manager.add_observer(observer2)

        # Call internal method directly
        self.config_manager._notify_observers("test.key", "old_val", "new_val")

        # Both observers should be notified
        self.assertEqual(len(observer1.changes), 1)
        self.assertEqual(len(observer2.changes), 1)
        self.assertEqual(observer1.changes[0], ("test.key", "old_val", "new_val"))
        self.assertEqual(observer2.changes[0], ("test.key", "old_val", "new_val"))


if __name__ == "__main__":
    unittest.main()

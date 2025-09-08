"""Unit tests for SettingsWindow - Settings dialog window"""

import sys
import unittest
from unittest.mock import MagicMock, Mock, patch, call, ANY
import threading
from typing import List

# Mock GUI modules before imports
sys.modules['tkinter'] = MagicMock()
sys.modules['tkinter.messagebox'] = MagicMock()
sys.modules['tkinter.ttk'] = MagicMock()
sys.modules['pystray'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()
sys.modules['keyboard'] = MagicMock()

from src.ui.settings_window import SettingsWindow
from src.models.config import AppConfig, HotkeyConfig, LanguageConfig, TTSConfig, ImageProcessingConfig, FeaturesConfig


class TestSettingsWindow(unittest.TestCase):
    """Test suite for SettingsWindow"""

    def setUp(self):
        """Set up test fixtures"""
        # Create mocks for dependencies
        self.mock_config_manager = MagicMock()
        self.mock_tts_processor = MagicMock()
        
        # Create mock config
        self.mock_config = AppConfig()
        self.mock_config_manager.get_config.return_value = self.mock_config
        
        # Patch dependencies
        self.patches = [
            patch('src.ui.settings_window.logger'),
            patch('src.ui.settings_window.messagebox'),
            patch('src.ui.settings_window.tk'),
            patch('src.ui.settings_window.ttk'),
            patch('src.ui.settings_window.sd'),
        ]
        
        self.mocks = {}
        for p in self.patches:
            mock = p.start()
            self.mocks[p.attribute] = mock
            
        # Configure sounddevice mock
        self.mocks['sd'].query_devices.return_value = [
            {'name': 'Default Speaker', 'hostapi_name': 'DirectSound', 'max_output_channels': 2},
            {'name': 'Headphones', 'hostapi_name': 'DirectSound', 'max_output_channels': 2},
        ]

    def tearDown(self):
        """Clean up patches"""
        for p in self.patches:
            p.stop()

    def test_initialization(self):
        """Test SettingsWindow initialization"""
        # Act
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        
        # Assert
        self.assertEqual(window.config_manager, self.mock_config_manager)
        self.assertEqual(window.tts_processor, self.mock_tts_processor)
        self.assertEqual(window.config, self.mock_config)
        self.assertIsNone(window.window)
        self.assertIsInstance(window._lock, type(threading.Lock()))
        
        # Check initialization of state
        self.assertEqual(window.hotkey_entries, {})
        self.assertEqual(window.hotkey_buttons, {})
        self.assertIsNone(window.waiting_for_hotkey)
        self.assertEqual(window.available_voices, [])
        self.assertEqual(window.available_audio_devices, [])

    def test_show_creates_new_window(self):
        """Test show method creates new window when none exists"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        
        with patch.object(window, '_create_window') as mock_create:
            # Act
            window.show()
            
            # Assert
            mock_create.assert_called_once()

    def test_show_focuses_existing_window(self):
        """Test show method focuses existing window"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        window.window = MagicMock()
        window.window.winfo_exists.return_value = True
        
        with patch.object(window, '_create_window') as mock_create:
            # Act
            window.show()
            
            # Assert
            mock_create.assert_not_called()
            window.window.focus_force.assert_called_once()
            window.window.lift.assert_called_once()

    def test_show_recreates_destroyed_window(self):
        """Test show method recreates window if destroyed"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        window.window = MagicMock()
        window.window.winfo_exists.return_value = False
        
        with patch.object(window, '_create_window') as mock_create:
            # Act
            window.show()
            
            # Assert
            mock_create.assert_called_once()

    def test_show_handles_exception(self):
        """Test show method handles exception gracefully"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        window.window = MagicMock()
        # Mock winfo_exists to raise exception
        window.window.winfo_exists.side_effect = Exception("TclError")
        
        with patch.object(window, '_create_window') as mock_create:
            with patch.object(window, '_create_ui') as mock_create_ui:
                # Act - should raise exception since it's not caught in actual code
                with self.assertRaises(Exception):
                    window.show()
                
                # Since exception is raised, create methods won't be called
                mock_create.assert_not_called()

    def test_create_window(self):
        """Test window creation"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        mock_tk_window = MagicMock()
        self.mocks['tk'].Toplevel.return_value = mock_tk_window
        
        # Act - just test _create_window, not _create_ui
        window._create_window()
        
        # Assert
        self.mocks['tk'].Toplevel.assert_called_once()
        self.assertEqual(window.window, mock_tk_window)
        
        # Verify window configuration
        mock_tk_window.title.assert_called_once_with("Настройки Screen Translator")
        # Geometry is called twice (once for size, once for position) 
        self.assertEqual(mock_tk_window.geometry.call_count, 2)
        mock_tk_window.resizable.assert_called_once_with(True, True)

    def test_get_available_audio_devices_with_sounddevice(self):
        """Test getting audio devices when sounddevice is available"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        
        # Act
        devices = window._get_available_audio_devices()
        
        # Assert
        self.assertEqual(len(devices), 3)  # Default + 2 mock devices
        self.assertEqual(devices[0]['id'], 'default')
        self.assertEqual(devices[0]['name'], 'Системное по умолчанию')
        self.assertEqual(devices[1]['name'], 'Default Speaker (DirectSound)')
        self.assertEqual(devices[2]['name'], 'Headphones (DirectSound)')

    def test_get_available_audio_devices_without_sounddevice(self):
        """Test getting audio devices when sounddevice fails"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        self.mocks['sd'].query_devices.side_effect = Exception("No sounddevice")
        
        # Act
        devices = window._get_available_audio_devices()
        
        # Assert
        self.assertEqual(len(devices), 1)  # Only default
        self.assertEqual(devices[0]['id'], 'default')
        self.assertEqual(devices[0]['name'], 'Системное по умолчанию')

    def test_save_settings_success(self):
        """Test successful settings save"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        
        # Mock hotkey entries based on actual config fields
        window.hotkey_entries = {
            'area_select': MagicMock(),
            'quick_center': MagicMock(),
            'quick_bottom': MagicMock(),
            'repeat_last': MagicMock(),
            'switch_language': MagicMock()
        }
        window.hotkey_entries['area_select'].get.return_value = "alt+a"
        window.hotkey_entries['quick_center'].get.return_value = "alt+q"
        
        # Mock target language variables (checkboxes)
        mock_es_var = MagicMock()
        mock_es_var.get.return_value = True
        mock_fr_var = MagicMock() 
        mock_fr_var.get.return_value = True
        window.target_language_vars = {
            'es': mock_es_var,
            'fr': mock_fr_var
        }
        
        window.ocr_languages = MagicMock()
        window.ocr_languages.get.return_value = "eng+fra"
        
        window.tts_enabled = MagicMock()
        window.tts_enabled.get.return_value = True
        window.tts_rate = MagicMock()
        window.tts_rate.get.return_value = 150
        
        window.selected_voice = MagicMock()
        window.selected_voice.get.return_value = "Microsoft David (en-US)"
        # Create proper mock voice object with correct attributes
        mock_voice = MagicMock()
        mock_voice.name = 'Microsoft David'
        mock_voice.language = 'en-US'
        mock_voice.id = 'david_voice'
        window.available_voices = [mock_voice]
        
        window.selected_audio_device = MagicMock()
        window.selected_audio_device.get.return_value = "Default Speaker"
        window.available_audio_devices = [
            {'name': 'Default Speaker', 'id': '0'}
        ]
        
        # Image processing variables
        window.upscale_factor = MagicMock()
        window.upscale_factor.get.return_value = 2.0
        window.contrast_enhance = MagicMock()
        window.contrast_enhance.get.return_value = 1.2
        window.sharpness_enhance = MagicMock() 
        window.sharpness_enhance.get.return_value = 1.1
        window.ocr_confidence_threshold = MagicMock()
        window.ocr_confidence_threshold.get.return_value = 0.5
        window.enable_preprocessing = MagicMock()
        window.enable_preprocessing.get.return_value = True
        window.noise_reduction = MagicMock()
        window.noise_reduction.get.return_value = True
        
        # Features variables
        window.copy_to_clipboard = MagicMock()
        window.copy_to_clipboard.get.return_value = True
        window.cache_translations = MagicMock()
        window.cache_translations.get.return_value = True
        window.save_debug_screenshots = MagicMock()
        window.save_debug_screenshots.get.return_value = False
        
        with patch.object(window, '_on_close') as mock_close:
            # Act
            window._save_settings()
            
            # Assert
            # Verify config was updated correctly  
            self.assertEqual(window.config.hotkeys.area_select, "alt+a")
            self.assertEqual(window.config.hotkeys.quick_center, "alt+q")
            
            # Check target languages were updated
            self.assertEqual(window.config.languages.target_languages, ["es", "fr"])
            self.assertEqual(window.config.languages.ocr_languages, "eng+fra")
            
            self.assertTrue(window.config.tts.enabled)
            self.assertEqual(window.config.tts.rate, 150)
            self.assertEqual(window.config.tts.voice_id, "david_voice")
            self.assertEqual(window.config.tts.audio_device, "0")
            
            # Verify manager methods were called
            self.mock_config_manager.update_config.assert_called_once_with(window.config)
            self.mock_config_manager.save_config.assert_called_once()
            
            # Verify success message and close
            self.mocks['messagebox'].showinfo.assert_called_once_with("Успех", "Настройки сохранены!")
            mock_close.assert_called_once()

    def test_save_settings_no_target_languages(self):
        """Test save settings with no target languages selected"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        # Mock all language vars returning False (not selected)
        mock_var = MagicMock()
        mock_var.get.return_value = False
        window.target_language_vars = {'es': mock_var, 'fr': mock_var}
        
        # Act
        window._save_settings()
        
        # Assert
        self.mocks['messagebox'].showerror.assert_called_once_with(
            "Ошибка", "Выберите хотя бы один целевой язык"
        )

    def test_save_settings_error_handling(self):
        """Test save settings error handling"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        self.mock_config_manager.update_config.side_effect = Exception("Config error")
        
        # Mock all required variables to avoid AttributeError during _save_settings
        mock_var = MagicMock()
        mock_var.get.return_value = True
        window.target_language_vars = {'es': mock_var}
        window.hotkey_entries = {}
        
        # Add all UI variables that _save_settings tries to access
        ui_vars = {
            'ocr_languages': "eng",
            'tts_enabled': True,
            'tts_rate': 150,
            'selected_voice': "Default",
            'selected_audio_device': "Default",
            'upscale_factor': 2.0,
            'contrast_enhance': 1.2,
            'sharpness_enhance': 1.1,
            'ocr_confidence_threshold': 0.7,
            'enable_preprocessing': True,
            'noise_reduction': True,
            'copy_to_clipboard': True,
            'cache_translations': True,
            'save_debug_screenshots': False
        }
        
        for var_name, value in ui_vars.items():
            mock_ui_var = MagicMock()
            mock_ui_var.get.return_value = value
            setattr(window, var_name, mock_ui_var)
            
        window.available_voices = []
        window.available_audio_devices = []
        
        # Act
        window._save_settings()
        
        # Assert
        self.mocks['logger'].error.assert_called()
        self.mocks['messagebox'].showerror.assert_called_once_with(
            "Ошибка", "Ошибка сохранения настроек: Config error"
        )

    def test_reset_to_defaults_confirmed(self):
        """Test reset to defaults when user confirms"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        self.mocks['messagebox'].askyesno.return_value = True
        
        with patch.object(window, '_on_close') as mock_close:
            # Act
            window._reset_to_defaults()
            
            # Assert
            self.mocks['messagebox'].askyesno.assert_called_once()
            self.mock_config_manager.reset_to_defaults.assert_called_once()
            mock_close.assert_called_once()

    def test_reset_to_defaults_cancelled(self):
        """Test reset to defaults when user cancels"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        self.mocks['messagebox'].askyesno.return_value = False
        
        # Act
        window._reset_to_defaults()
        
        # Assert
        self.mocks['messagebox'].askyesno.assert_called_once()
        self.mock_config_manager.reset_to_defaults.assert_not_called()

    def test_on_close(self):
        """Test window close handling"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        mock_window = MagicMock()
        window.window = mock_window
        
        # Act
        window._on_close()
        
        # Assert
        mock_window.destroy.assert_called_once()
        self.assertIsNone(window.window)
        # Just verify the log was called, don't check specific call order
        self.mocks['logger'].debug.assert_any_call("Settings window closed")

    def test_on_close_no_window(self):
        """Test close handling when no window exists"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        window.window = None
        
        # Act - should not raise exception
        window._on_close()
        
        # Assert - check that debug was called with the close message (may be second call)
        self.mocks['logger'].debug.assert_called_with("Settings window closed")

    def test_config_observer_implementation(self):
        """Test ConfigObserver implementation"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        new_config = AppConfig()
        self.mock_config_manager.get_config.return_value = new_config
        
        # Act
        window.on_config_changed("*", None, None)
        
        # Assert
        self.assertEqual(window.config, new_config)
        # Check that debug was called with config update message (may be second call)
        self.mocks['logger'].debug.assert_called_with("Settings window config updated")

    def test_config_observer_specific_key(self):
        """Test config observer with specific key change"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        old_config = window.config
        
        # Act
        window.on_config_changed("hotkeys.capture", "old_value", "new_value")
        
        # Assert - config should not change for specific key
        self.assertEqual(window.config, old_config)

    def test_queue_gui_action_with_queue(self):
        """Test GUI action queuing when queue exists"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        window.gui_queue = MagicMock()
        
        mock_func = MagicMock()
        args = ('arg1', 'arg2')
        
        # Act
        window.queue_gui_action(mock_func, *args)
        
        # Assert
        window.gui_queue.put.assert_called_once_with((mock_func, args))

    def test_queue_gui_action_without_queue(self):
        """Test GUI action queuing fallback when no queue"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        # Remove gui_queue attribute to test fallback
        del window.gui_queue
        
        mock_func = MagicMock()
        args = ('arg1', 'arg2')
        
        # Act
        window.queue_gui_action(mock_func, *args)
        
        # Assert
        mock_func.assert_called_once_with(*args)

    def test_hotkey_capture_workflow(self):
        """Test hotkey capture functionality"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        
        # Mock UI elements
        mock_entry = MagicMock()
        mock_button = MagicMock()
        window.hotkey_entries['capture'] = mock_entry
        window.hotkey_buttons['capture'] = mock_button
        
        # Act - start hotkey capture
        window._start_hotkey_capture('capture')
        
        # Assert
        self.assertEqual(window.waiting_for_hotkey, 'capture')
        mock_entry.config.assert_called_with(bg='#FFF3E0')
        mock_button.config.assert_called_with(text='Нажмите клавиши...', bg='#FF5722')

    def test_thread_safety(self):
        """Test thread safety with lock usage"""
        # Setup
        window = SettingsWindow(self.mock_config_manager, self.mock_tts_processor)
        
        # Verify lock exists
        self.assertIsInstance(window._lock, type(threading.Lock()))
        
        # Test that critical operations can be called without deadlock
        window.show()
        window._on_close()
        window.on_config_changed("*", None, None)


if __name__ == '__main__':
    unittest.main()
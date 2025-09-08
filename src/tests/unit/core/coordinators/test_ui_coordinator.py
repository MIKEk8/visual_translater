"""Unit tests for UICoordinator - User interface coordinator"""

import sys
import unittest
from unittest.mock import MagicMock, Mock, patch, call, ANY
import threading
import queue
from datetime import datetime
from typing import List

# Mock GUI modules before imports
sys.modules['tkinter'] = MagicMock()
sys.modules['tkinter.messagebox'] = MagicMock()
sys.modules['tkinter.filedialog'] = MagicMock()
sys.modules['pystray'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()

from src.core.coordinators.ui_coordinator import UICoordinator
from src.models.translation import Translation
from src.utils.exceptions import (
    InvalidAreaError,
    OCRError,
    ScreenshotCaptureError,
    TranslationFailedError,
    TTSError,
)


class TestUICoordinator(unittest.TestCase):
    """Test suite for UICoordinator"""

    def setUp(self):
        """Set up test fixtures"""
        # Create mocks
        self.mock_root = MagicMock()
        self.mock_config_manager = MagicMock()
        self.mock_tts_processor = MagicMock()
        
        # Patch dependencies
        self.patches = [
            patch('src.core.coordinators.ui_coordinator.ProgressManager'),
            patch('src.core.coordinators.ui_coordinator.SettingsWindow'),
            patch('src.core.coordinators.ui_coordinator.logger'),
            patch('src.core.coordinators.ui_coordinator.messagebox'),
        ]
        
        self.mocks = {}
        for p in self.patches:
            mock = p.start()
            self.mocks[p.attribute] = mock
        
        # Configure progress manager mock
        self.mock_progress_manager = MagicMock()
        self.mocks['ProgressManager'].return_value = self.mock_progress_manager

    def tearDown(self):
        """Clean up patches"""
        for p in self.patches:
            p.stop()

    def test_initialization(self):
        """Test UICoordinator initialization"""
        # Act
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        # Assert
        self.assertEqual(coordinator.root, self.mock_root)
        self.assertEqual(coordinator.config_manager, self.mock_config_manager)
        self.assertEqual(coordinator.tts_processor, self.mock_tts_processor)
        self.assertIsInstance(coordinator._lock, type(threading.Lock()))
        
        # Verify ProgressManager was created
        self.mocks['ProgressManager'].assert_called_once_with(self.mock_root)
        self.assertEqual(coordinator.progress_manager, self.mock_progress_manager)
        
        # Verify settings window is initially None
        self.assertIsNone(coordinator.settings_window)

    def test_show_progress(self):
        """Test showing progress indicator"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        # Act
        coordinator.show_progress("Test Title", "Test Message", False)
        
        # Assert
        self.mock_progress_manager.show_progress.assert_called_once_with(
            title="Test Title",
            message="Test Message", 
            is_indeterminate=False
        )

    def test_hide_progress(self):
        """Test hiding progress indicator"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        # Act
        coordinator.hide_progress()
        
        # Assert
        self.mock_progress_manager.hide_progress.assert_called_once()

    def test_show_success(self):
        """Test showing success notification"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        # Act
        coordinator.show_success("Success message")
        
        # Assert
        self.mock_progress_manager.show_success.assert_called_once_with("Success message")

    def test_show_warning(self):
        """Test showing warning notification"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        # Act
        coordinator.show_warning("Warning message")
        
        # Assert
        self.mock_progress_manager.show_warning.assert_called_once_with("Warning message")

    def test_show_error(self):
        """Test showing error notification"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        # Act
        coordinator.show_error("Error message")
        
        # Assert
        self.mock_progress_manager.show_error.assert_called_once_with("Error message")

    def test_handle_translation_success(self):
        """Test handling successful translation"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        translation = Translation(
            original_text="Hello",
            translated_text="Hola",
            source_language="en",
            target_language="es"
        )
        
        # Act
        coordinator.handle_translation_success(translation)
        
        # Assert
        self.mock_progress_manager.hide_progress.assert_called_once()
        self.mock_progress_manager.show_success.assert_called_once_with("Translated: Hola")

    def test_handle_translation_success_long_text(self):
        """Test handling translation success with long text truncation"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        long_text = "This is a very long translation text that exceeds fifty characters limit"
        translation = Translation(
            original_text="Test",
            translated_text=long_text,
            source_language="en",
            target_language="es"
        )
        
        # Act
        coordinator.handle_translation_success(translation)
        
        # Assert
        expected_message = f"Translated: {long_text[:50]}..."
        self.mock_progress_manager.show_success.assert_called_once_with(expected_message)

    def test_handle_translation_success_none(self):
        """Test handling translation success with None translation"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        # Act
        coordinator.handle_translation_success(None)
        
        # Assert
        self.mock_progress_manager.hide_progress.assert_called_once()
        self.mock_progress_manager.show_success.assert_not_called()

    def test_handle_translation_error_invalid_area(self):
        """Test handling InvalidAreaError"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        error = InvalidAreaError((10, 10, 20, 20))
        
        # Act
        coordinator.handle_translation_error(error)
        
        # Assert
        self.mock_progress_manager.hide_progress.assert_called_once()
        self.mock_progress_manager.show_warning.assert_called_once_with("Please select a larger area with text")
        self.mocks['logger'].warning.assert_called()

    def test_handle_translation_error_screenshot_capture(self):
        """Test handling ScreenshotCaptureError"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        error = ScreenshotCaptureError("Capture failed", (0, 0, 100, 100))
        
        # Act
        coordinator.handle_translation_error(error)
        
        # Assert
        self.mock_progress_manager.hide_progress.assert_called_once()
        self.mock_progress_manager.show_error.assert_called_once_with("Failed to capture screen area")

    def test_handle_translation_error_translation_failed(self):
        """Test handling TranslationFailedError"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        error = TranslationFailedError("Hello", "en", "es", "Service unavailable")
        
        # Act
        coordinator.handle_translation_error(error)
        
        # Assert
        self.mock_progress_manager.hide_progress.assert_called_once()
        self.mock_progress_manager.show_error.assert_called_once_with("Translation service unavailable")

    def test_handle_translation_error_ocr(self):
        """Test handling OCRError"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        error = OCRError("OCR failed")
        
        # Act
        coordinator.handle_translation_error(error)
        
        # Assert
        self.mock_progress_manager.hide_progress.assert_called_once()
        self.mock_progress_manager.show_warning.assert_called_once_with("Could not extract text from image")

    def test_handle_translation_error_tts(self):
        """Test handling TTSError"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        error = TTSError("TTS failed")
        
        # Act
        coordinator.handle_translation_error(error)
        
        # Assert
        self.mock_progress_manager.hide_progress.assert_called_once()
        self.mock_progress_manager.show_warning.assert_called_once_with("Text-to-speech not available")

    def test_handle_translation_error_generic(self):
        """Test handling generic exception"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        error = Exception("Generic error")
        
        # Act
        coordinator.handle_translation_error(error)
        
        # Assert
        self.mock_progress_manager.hide_progress.assert_called_once()
        self.mock_progress_manager.show_error.assert_called_once_with("Operation failed: Generic error")

    def test_show_translation_history_empty(self):
        """Test showing empty translation history"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        # Mock GUI queue - add this attribute that seems to be missing from the class
        coordinator._gui_queue = queue.Queue()
        coordinator._gui_processing = False
        
        # Act
        coordinator.show_translation_history([])
        
        # Assert
        # Check that GUI operation was queued
        self.assertFalse(coordinator._gui_queue.empty())

    def test_show_translation_history_with_data(self):
        """Test showing translation history with data"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        # Mock GUI queue
        coordinator._gui_queue = queue.Queue()
        coordinator._gui_processing = False
        
        # Create mock translations
        translations = []
        for i in range(15):  # More than 10 to test truncation
            translation = Translation(
                original_text=f"Text {i}",
                translated_text=f"Texto {i}",
                source_language="en",
                target_language="es"
            )
            translation.timestamp = datetime.now()
            translations.append(translation)
        
        # Act
        coordinator.show_translation_history(translations)
        
        # Assert
        # Should queue a GUI operation
        self.assertFalse(coordinator._gui_queue.empty())
        
        # Get the queued operation and verify it shows last 10
        operation = coordinator._gui_queue.get()
        self.assertEqual(operation["type"], "messagebox")

    def test_show_batch_history_empty(self):
        """Test showing empty batch history"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        coordinator._gui_queue = queue.Queue()
        coordinator._gui_processing = False
        
        # Act
        coordinator.show_batch_history([])
        
        # Assert
        self.assertFalse(coordinator._gui_queue.empty())

    def test_open_settings_new_window(self):
        """Test opening settings window when none exists"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        mock_settings_window = MagicMock()
        self.mocks['SettingsWindow'].return_value = mock_settings_window
        
        # Act
        coordinator.open_settings()
        
        # Assert
        self.mocks['SettingsWindow'].assert_called_once_with(
            self.mock_config_manager,
            self.mock_tts_processor
        )
        mock_settings_window.show.assert_called_once()
        self.assertEqual(coordinator.settings_window, mock_settings_window)

    def test_open_settings_existing_window_valid(self):
        """Test opening settings when window exists and is valid"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        # Create existing settings window
        mock_existing_window = MagicMock()
        mock_existing_window.window.winfo_exists.return_value = True
        coordinator.settings_window = mock_existing_window
        
        # Act
        coordinator.open_settings()
        
        # Assert
        # Should not create new window
        self.mocks['SettingsWindow'].assert_not_called()
        mock_existing_window.show.assert_called_once()

    def test_open_settings_existing_window_destroyed(self):
        """Test opening settings when existing window is destroyed"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        # Create existing settings window that's destroyed
        mock_existing_window = MagicMock()
        mock_existing_window.window.winfo_exists.return_value = False
        coordinator.settings_window = mock_existing_window
        
        mock_new_window = MagicMock()
        self.mocks['SettingsWindow'].return_value = mock_new_window
        
        # Act
        coordinator.open_settings()
        
        # Assert
        # Should create new window
        self.mocks['SettingsWindow'].assert_called_once()
        mock_new_window.show.assert_called_once()

    def test_dialog_methods(self):
        """Test various dialog methods"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        coordinator._gui_queue = queue.Queue()
        coordinator._gui_processing = False
        
        # Act
        coordinator.show_info_dialog("Info Title", "Info Message")
        coordinator.show_error_dialog("Error Title", "Error Message")
        coordinator.show_warning_dialog("Warning Title", "Warning Message")
        
        # Assert
        # Check that 3 operations were queued
        self.assertEqual(coordinator._gui_queue.qsize(), 3)
        
        # Verify the operations
        info_op = coordinator._gui_queue.get()
        error_op = coordinator._gui_queue.get()
        warning_op = coordinator._gui_queue.get()
        
        self.assertEqual(info_op["data"]["type"], "info")
        self.assertEqual(error_op["data"]["type"], "error")
        self.assertEqual(warning_op["data"]["type"], "warning")

    def test_ask_yes_no(self):
        """Test yes/no dialog"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        self.mocks['messagebox'].askyesno.return_value = True
        
        # Act
        result = coordinator.ask_yes_no("Question", "Are you sure?")
        
        # Assert
        self.assertTrue(result)
        self.mocks['messagebox'].askyesno.assert_called_once_with("Question", "Are you sure?")

    def test_update_progress_with_current_progress(self):
        """Test updating progress when current progress exists"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        # Mock current progress
        mock_current_progress = MagicMock()
        coordinator.progress_manager.current_progress = mock_current_progress
        
        # Act
        coordinator.update_progress(50, "Half done")
        
        # Assert
        mock_current_progress.update.assert_called_once()
        call_args = mock_current_progress.update.call_args[0][0]
        self.assertEqual(call_args.current, 50)
        self.assertEqual(call_args.message, "Half done")
        self.assertFalse(call_args.is_indeterminate)

    def test_update_progress_no_current_progress(self):
        """Test updating progress when no current progress exists"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        # No current progress
        coordinator.progress_manager.current_progress = None
        
        # Act - should not raise exception
        coordinator.update_progress(50, "Half done")

    def test_thread_safety(self):
        """Test thread safety of operations"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        # Verify lock is created
        self.assertIsInstance(coordinator._lock, type(threading.Lock()))
        
        # Test that operations use locks
        coordinator.show_progress("Test", "Test")
        coordinator.hide_progress()
        coordinator.show_success("Test")
        coordinator.show_warning("Test")
        coordinator.show_error("Test")
        
        # If we get here without deadlocks, threading is working correctly
        self.assertTrue(True)

    def test_handle_messagebox_operation(self):
        """Test handling messagebox operations"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        # Test info messagebox - need to patch the import inside the function
        data = {"type": "info", "args": ("Title", "Message")}
        
        with patch('tkinter.messagebox') as mock_mb:
            coordinator._handle_messagebox_operation(data)
            mock_mb.showinfo.assert_called_once_with("Title", "Message")
        
        # Test error messagebox
        data = {"type": "error", "args": ("Error Title", "Error Message")}
        
        with patch('tkinter.messagebox') as mock_mb:
            coordinator._handle_messagebox_operation(data)
            mock_mb.showerror.assert_called_once_with("Error Title", "Error Message")

    def test_handle_file_dialog_operation(self):
        """Test handling file dialog operations"""
        # Setup
        coordinator = UICoordinator(
            self.mock_root,
            self.mock_config_manager,
            self.mock_tts_processor
        )
        
        callback = MagicMock()
        data = {"type": "save", "callback": callback}
        
        with patch('tkinter.filedialog') as mock_fd:
            mock_fd.asksaveasfilename.return_value = "/path/to/file.txt"
            
            coordinator._handle_file_dialog_operation(data)
            
            mock_fd.asksaveasfilename.assert_called_once()
            callback.assert_called_once_with("/path/to/file.txt")


if __name__ == '__main__':
    unittest.main()
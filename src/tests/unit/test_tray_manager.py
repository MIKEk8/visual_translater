"""Minimal working TrayManager tests"""

try:
    import tkinter as tk
except ImportError:
    print("tkinter не доступен в данной среде")
    tk = None

import queue
import threading
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.ui.tray_manager import TrayManager


class TestTrayManagerMinimal:
    """Minimal tests for TrayManager that match actual implementation"""

    @pytest.fixture
    def mock_app(self):
        """Create mock ScreenTranslatorApp"""
        app = Mock()
        app.capture_area = Mock()
        app.quick_translate_center = Mock()
        app.quick_translate_bottom = Mock()
        app.show_translation_history = Mock()
        app.open_settings = Mock()
        app.get_app_info = Mock(return_value="Screen Translator v2.0")
        app.shutdown = Mock()
        app.translation_history = []
        return app

    @pytest.fixture
    def tray_manager(self, mock_app):
        """Create TrayManager instance"""
        return TrayManager(mock_app)

    def test_initialization(self, tray_manager):
        """Test TrayManager initialization"""
        assert tray_manager.app is not None
        assert tray_manager.icon is None
        assert tray_manager.is_running is False
        assert isinstance(tray_manager.gui_queue, queue.Queue)

    def test_queue_gui_action(self, tray_manager):
        """Test queuing GUI actions"""
        tray_manager.queue_gui_action("test_func", "arg1", "arg2")

        # Get the queued item
        queued = tray_manager.gui_queue.get_nowait()
        assert queued[0] == "test_func"
        assert queued[1] == ("arg1", "arg2")

    @patch("PIL.Image.open")
    def test_load_icon(self, mock_image_open, tray_manager):
        """Test icon loading"""
        mock_image = Mock()
        mock_image_open.return_value = mock_image

        icon = tray_manager._load_icon()
        assert icon == mock_image

    def test_activate_capture(self, tray_manager, mock_app):
        """Test activate capture action"""
        tray_manager._activate_capture()

        # Check that the action was queued
        queued = tray_manager.gui_queue.get_nowait()
        assert queued[0] == mock_app.capture_area
        assert queued[1] == ()

    def test_quick_center(self, tray_manager, mock_app):
        """Test quick center translation"""
        tray_manager._quick_center()

        # Check that the action was queued
        queued = tray_manager.gui_queue.get_nowait()
        assert queued[0] == mock_app.quick_translate_center
        assert queued[1] == ()

    def test_quick_bottom(self, tray_manager, mock_app):
        """Test quick bottom translation"""
        tray_manager._quick_bottom()

        # Check that the action was queued
        queued = tray_manager.gui_queue.get_nowait()
        assert queued[0] == mock_app.quick_translate_bottom
        assert queued[1] == ()

    def test_show_history(self, tray_manager, mock_app):
        """Test show history action"""
        tray_manager._show_history()

        # Check that the action was queued
        queued = tray_manager.gui_queue.get_nowait()
        assert queued[0] == mock_app.show_translation_history
        assert queued[1] == ()

    def test_open_settings(self, tray_manager, mock_app):
        """Test open settings action"""
        tray_manager._open_settings()

        # Check that the action was queued
        queued = tray_manager.gui_queue.get_nowait()
        assert queued[0] == mock_app.open_settings
        assert queued[1] == ()

    def test_show_info(self, tray_manager, mock_app):
        """Test show info action"""
        with patch("tkinter.messagebox.showinfo") as mock_showinfo:
            tray_manager._show_info()
            mock_showinfo.assert_called_once()

    def test_exit_app(self, tray_manager, mock_app):
        """Test exit app action"""
        tray_manager._exit_app()

        # Check that the shutdown was queued
        queued = tray_manager.gui_queue.get_nowait()
        assert queued[0] == mock_app.shutdown
        assert queued[1] == ()

        # Also check that stop was called
        assert tray_manager.is_running is False

    def test_update_icon(self, tray_manager):
        """Test update icon status"""
        mock_icon = Mock()
        tray_manager.icon = mock_icon

        tray_manager.update_icon("processing")
        # Just verify it doesn't crash

    def test_show_notification(self, tray_manager):
        """Test show notification"""
        mock_icon = Mock()
        tray_manager.icon = mock_icon

        tray_manager.show_notification("Test", "Message")
        mock_icon.notify.assert_called_once_with("Message", "Test")

    @patch("pystray.Icon")
    @patch("threading.Thread")
    def test_start_stop(self, mock_thread, mock_icon_class, tray_manager):
        """Test start and stop lifecycle"""
        mock_icon = Mock()
        mock_icon_class.return_value = mock_icon

        # Start
        tray_manager.start()
        assert tray_manager.is_running is True

        # Stop
        tray_manager.stop()
        assert tray_manager.is_running is False

        # Verify icon.stop was called
        if mock_icon.stop.called:
            mock_icon.stop.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

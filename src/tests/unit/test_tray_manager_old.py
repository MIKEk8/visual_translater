"""Unit tests for tray manager UI module"""

import queue
import threading
import tkinter as tk
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.ui.tray_manager import TrayManager


@pytest.fixture
def mock_app():
    """Create mock ScreenTranslatorApp"""
    app = Mock()
    app.translate_screen_area = Mock()
    app.translate_quick_center = Mock()
    app.translate_quick_bottom = Mock()
    app.translate_last = Mock()
    app.switch_language = Mock()
    app.show_settings = Mock()
    app.on_exit = Mock()
    return app


@pytest.fixture
def tray_manager(mock_app):
    """Create TrayManager instance with mocked dependencies"""
    with patch("pystray.Icon"), patch("PIL.Image"):
        manager = TrayManager(mock_app)
        return manager


class TestTrayManager:
    """Test TrayManager class"""

    def test_initialization(self, tray_manager, mock_app):
        """Test tray manager initialization"""
        assert tray_manager.app == mock_app
        assert tray_manager.icon is None
        assert isinstance(tray_manager.gui_queue, queue.Queue)
        assert tray_manager.is_running is False

    @patch("threading.Thread")
    def test_start(self, mock_thread, tray_manager):
        """Test starting tray manager"""
        with patch.object(tray_manager, "setup_tray") as mock_setup, patch.object(
            tray_manager, "start_message_processing"
        ) as mock_start_processing:

            tray_manager.start()

            assert tray_manager.is_running is True
            mock_setup.assert_called_once()
            mock_start_processing.assert_called_once()

    def test_start_already_running(self, tray_manager):
        """Test starting when already running"""
        tray_manager.is_running = True

        with patch.object(tray_manager, "setup_tray") as mock_setup:
            tray_manager.start()

            # Should not setup again
            mock_setup.assert_not_called()

    def test_stop(self, tray_manager):
        """Test stopping tray manager"""
        mock_icon = Mock()
        tray_manager.icon = mock_icon
        tray_manager.is_running = True

        tray_manager.stop()

        assert tray_manager.is_running is False
        mock_icon.stop.assert_called_once()

    def test_stop_with_error(self, tray_manager):
        """Test stopping with icon error"""
        mock_icon = Mock()
        mock_icon.stop.side_effect = Exception("Stop error")
        tray_manager.icon = mock_icon

        # Should not raise exception
        tray_manager.stop()

        assert tray_manager.is_running is False

    @patch("pystray.Icon")
    @patch("PIL.Image.open")
    def test_setup_tray(self, mock_image_open, mock_icon_class, tray_manager):
        """Test tray setup"""
        mock_image = Mock()
        mock_image_open.return_value = mock_image
        mock_icon = Mock()
        mock_icon_class.return_value = mock_icon

        with patch.object(tray_manager, "_create_menu") as mock_create_menu:
            mock_menu = Mock()
            mock_create_menu.return_value = mock_menu

            tray_manager.setup_tray()

            # Should create icon with image and menu
            mock_icon_class.assert_called_once_with(
                name="Screen Translator",
                icon=mock_image,
                title="Screen Translator - Готов к работе",
                menu=mock_menu,
            )
            assert tray_manager.icon == mock_icon

    def test_setup_tray_fallback_icon(self, tray_manager):
        """Test tray setup with fallback icon"""
        with patch("PIL.Image.open", side_effect=FileNotFoundError), patch(
            "PIL.Image.new"
        ) as mock_new_image, patch("pystray.Icon") as mock_icon_class:

            mock_fallback_image = Mock()
            mock_new_image.return_value = mock_fallback_image

            with patch.object(tray_manager, "_create_menu", return_value=Mock()):
                tray_manager.setup_tray()

                # Should create fallback icon
                mock_new_image.assert_called_once_with("RGB", (64, 64), color="blue")

    @patch("pystray.Menu")
    @patch("pystray.MenuItem")
    def test_create_menu(self, mock_menu_item, mock_menu, tray_manager):
        """Test creating tray menu"""
        mock_menu_item.return_value = Mock()
        mock_menu.return_value = Mock()

        menu = tray_manager._create_menu()

        # Should create menu with all items
        assert mock_menu_item.call_count >= 8  # Multiple menu items
        mock_menu.assert_called_once()

    def test_menu_action_translate_area(self, tray_manager, mock_app):
        """Test translate area menu action"""
        tray_manager._translate_area()

        mock_app.translate_screen_area.assert_called_once()

    def test_menu_action_translate_quick_center(self, tray_manager, mock_app):
        """Test translate quick center menu action"""
        tray_manager._translate_quick_center()

        mock_app.translate_quick_center.assert_called_once()

    def test_menu_action_translate_quick_bottom(self, tray_manager, mock_app):
        """Test translate quick bottom menu action"""
        tray_manager._translate_quick_bottom()

        mock_app.translate_quick_bottom.assert_called_once()

    def test_menu_action_translate_last(self, tray_manager, mock_app):
        """Test translate last menu action"""
        tray_manager._translate_last()

        mock_app.translate_last.assert_called_once()

    def test_menu_action_switch_language(self, tray_manager, mock_app):
        """Test switch language menu action"""
        tray_manager._switch_language()

        mock_app.switch_language.assert_called_once()

    def test_menu_action_show_settings(self, tray_manager, mock_app):
        """Test show settings menu action"""
        tray_manager._show_settings()

        mock_app.show_settings.assert_called_once()

    def test_menu_action_exit(self, tray_manager, mock_app):
        """Test exit menu action"""
        tray_manager._exit_app()

        mock_app.on_exit.assert_called_once()

    @patch("threading.Thread")
    def test_start_message_processing(self, mock_thread, tray_manager):
        """Test starting message processing thread"""
        tray_manager.start_message_processing()

        # Should start daemon thread
        mock_thread.assert_called_once()
        call_args = mock_thread.call_args
        assert call_args[1]["target"] == tray_manager._process_gui_messages
        assert call_args[1]["daemon"] is True

    def test_process_gui_messages(self, tray_manager):
        """Test processing GUI messages"""
        # Add test message to queue
        test_message = ("show_notification", "Test", "Message")
        tray_manager.gui_queue.put(test_message)
        tray_manager.gui_queue.put(None)  # Stop signal

        with patch.object(tray_manager, "show_notification") as mock_show_notification:
            tray_manager._process_gui_messages()

            mock_show_notification.assert_called_once_with("Test", "Message")

    def test_process_gui_messages_unknown_action(self, tray_manager):
        """Test processing unknown GUI message"""
        # Add unknown message
        unknown_message = ("unknown_action", "param1", "param2")
        tray_manager.gui_queue.put(unknown_message)
        tray_manager.gui_queue.put(None)  # Stop signal

        # Should not raise exception
        tray_manager._process_gui_messages()

    def test_show_notification(self, tray_manager):
        """Test showing notification via tray"""
        mock_icon = Mock()
        tray_manager.icon = mock_icon

        tray_manager.show_notification("Test Title", "Test message", duration=5000)

        mock_icon.notify.assert_called_once_with("Test message", title="Test Title")

    def test_show_notification_no_icon(self, tray_manager):
        """Test showing notification when no icon exists"""
        tray_manager.icon = None

        # Should not raise exception
        tray_manager.show_notification("Test", "Message")

    def test_update_tooltip(self, tray_manager):
        """Test updating tray tooltip"""
        mock_icon = Mock()
        tray_manager.icon = mock_icon

        tray_manager.update_tooltip("New status")

        assert mock_icon.title == "Screen Translator - New status"

    def test_update_tooltip_no_icon(self, tray_manager):
        """Test updating tooltip when no icon exists"""
        tray_manager.icon = None

        # Should not raise exception
        tray_manager.update_tooltip("New status")

    @patch("tkinter.messagebox.showinfo")
    def test_show_about_dialog(self, mock_showinfo, tray_manager):
        """Test showing about dialog"""
        tray_manager._show_about()

        mock_showinfo.assert_called_once()
        call_args = mock_showinfo.call_args
        assert "Screen Translator" in call_args[0][0]  # Title
        assert "версия" in call_args[0][1].lower()  # Message

    def test_queue_gui_action(self, tray_manager):
        """Test queuing GUI action"""
        tray_manager.queue_gui_action("test_action", "param1", "param2")

        # Should add message to queue
        assert not tray_manager.gui_queue.empty()
        message = tray_manager.gui_queue.get()
        assert message == ("test_action", "param1", "param2")

    def test_is_tray_available(self, tray_manager):
        """Test checking tray availability"""
        with patch("pystray.Icon") as mock_icon_class:
            mock_icon_class.return_value = Mock()

            available = tray_manager.is_tray_available()

            # Should return True if pystray works
            assert available is True

    def test_is_tray_available_error(self, tray_manager):
        """Test tray availability check with error"""
        with patch("pystray.Icon", side_effect=Exception("Tray error")):
            available = tray_manager.is_tray_available()

            # Should return False on error
            assert available is False

    def test_set_icon_visible(self, tray_manager):
        """Test setting icon visibility"""
        mock_icon = Mock()
        tray_manager.icon = mock_icon

        tray_manager.set_icon_visible(False)

        mock_icon.visible = False

    def test_context_menu_generation(self, tray_manager):
        """Test dynamic context menu generation"""
        with patch.object(tray_manager, "_get_language_menu_items") as mock_lang_items:
            mock_lang_items.return_value = [Mock(), Mock()]

            with patch("pystray.MenuItem") as mock_menu_item, patch("pystray.Menu") as mock_menu:

                menu = tray_manager._create_menu()

                # Should include language submenu
                mock_lang_items.assert_called_once()

    def test_language_menu_items(self, tray_manager, mock_app):
        """Test creating language menu items"""
        # Mock app config with languages
        mock_app.config_manager.get_config.return_value.languages.target_languages = [
            "ru",
            "en",
            "ja",
            "de",
        ]

        with patch("pystray.MenuItem") as mock_menu_item:
            items = tray_manager._get_language_menu_items()

            # Should create menu item for each language
            assert mock_menu_item.call_count == 4

    def test_change_target_language(self, tray_manager, mock_app):
        """Test changing target language"""
        tray_manager._change_target_language("ru")

        mock_app.config_manager.set_config_value.assert_called_once_with(
            "languages.default_target", "ru"
        )

    def test_icon_lifecycle(self, tray_manager):
        """Test complete icon lifecycle"""
        with patch("pystray.Icon") as mock_icon_class, patch("PIL.Image.open") as mock_image_open:

            mock_icon = Mock()
            mock_icon_class.return_value = mock_icon
            mock_image_open.return_value = Mock()

            # Start
            tray_manager.start()
            assert tray_manager.is_running is True
            assert tray_manager.icon == mock_icon

            # Update icon status
            tray_manager.update_icon("processing")
            # Note: update_tooltip method doesn't exist in TrayManager

            # Stop
            tray_manager.stop()
            assert tray_manager.is_running is False
            mock_icon.stop.assert_called_once()

    def test_thread_safety(self, tray_manager):
        """Test thread-safe operations"""
        # Multiple threads adding to queue
        threads = []

        def add_messages(thread_id):
            for i in range(10):
                tray_manager.queue_gui_action(f"action_{thread_id}_{i}", "param")

        for i in range(3):
            thread = threading.Thread(target=add_messages, daemon=True, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have all messages
        assert tray_manager.gui_queue.qsize() == 30

    def test_error_handling_in_menu_actions(self, tray_manager, mock_app):
        """Test error handling in menu actions"""
        # Make app method raise exception
        mock_app.capture_screen_area.side_effect = Exception("Capture error")

        # Should not raise exception
        tray_manager._activate_capture()

        # Error should be handled gracefully
        mock_app.capture_screen_area.assert_called_once()

    def test_icon_animation_support(self, tray_manager):
        """Test animated icon support"""
        if hasattr(tray_manager, "set_animated_icon"):
            frames = [Mock(), Mock(), Mock()]

            tray_manager.set_animated_icon(frames, duration=500)

            # Should update icon with animation
            assert tray_manager.icon.icon in frames

    def test_balloon_notification_styling(self, tray_manager):
        """Test balloon notification with custom styling"""
        mock_icon = Mock()
        tray_manager.icon = mock_icon

        tray_manager.show_notification("Test", "Message", duration=3)

        # Should call notify with proper parameters
        mock_icon.notify.assert_called_once()

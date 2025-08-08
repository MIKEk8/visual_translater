"""Unit tests for notification service module"""

import queue
import threading
import time
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.services.notification_service import (
    FallbackBackend,
    Notification,
    NotificationBackend,
    NotificationConfig,
    NotificationPriority,
    NotificationService,
    NotificationType,
    PlyerNotificationBackend,
    SystemTrayBackend,
    Win10ToastBackend,
    get_notification_service,
)


@pytest.fixture
def notification():
    """Create a sample notification"""
    return Notification(
        title="Test Title",
        message="Test message",
        type=NotificationType.INFO,
        duration=5,
        icon="test.ico",
    )


@pytest.fixture
def notification_service():
    """Create NotificationService with mock provider"""
    mock_provider = Mock(spec=NotificationProvider)
    mock_provider.is_available.return_value = True
    mock_provider.show.return_value = True

    service = NotificationService(provider=mock_provider)
    return service


@pytest.fixture
def notification_queue():
    """Create NotificationQueue instance"""
    return NotificationQueue(max_size=10)


@pytest.fixture
def notification_history():
    """Create NotificationHistory instance"""
    return NotificationHistory(max_size=100)


class TestNotification:
    """Test Notification dataclass"""

    def test_notification_creation(self):
        """Test creating notification"""
        notif = Notification(
            title="Title",
            message="Message",
            type=NotificationType.SUCCESS,
            duration=10,
            icon="icon.png",
            actions=["OK", "Cancel"],
            sound=True,
        )

        assert notif.title == "Title"
        assert notif.message == "Message"
        assert notif.type == NotificationType.SUCCESS
        assert notif.duration == 10
        assert notif.timestamp is not None

    def test_notification_defaults(self):
        """Test notification default values"""
        notif = Notification(
            title="Title",
            message="Message",
        )

        assert notif.type == NotificationType.INFO
        assert notif.duration == 5
        assert notif.icon is None
        assert notif.actions is None
        assert notif.sound is False

    def test_notification_to_dict(self, notification):
        """Test converting notification to dict"""
        notif_dict = notification.to_dict()

        assert notif_dict["title"] == "Test Title"
        assert notif_dict["message"] == "Test message"
        assert notif_dict["type"] == "info"
        assert "timestamp" in notif_dict


class TestNotificationQueue:
    """Test NotificationQueue class"""

    def test_initialization(self, notification_queue):
        """Test queue initialization"""
        assert notification_queue.max_size == 10
        assert notification_queue._queue.maxsize == 10
        assert not notification_queue._processing

    def test_add_notification(self, notification_queue, notification):
        """Test adding notification to queue"""
        success = notification_queue.add(notification)

        assert success is True
        assert notification_queue._queue.qsize() == 1

    def test_queue_overflow(self, notification_queue, notification):
        """Test queue overflow handling"""
        # Fill queue
        for i in range(10):
            notification_queue.add(notification)

        # Try to add one more
        success = notification_queue.add(notification, block=False)

        assert success is False  # Should fail when full

    def test_process_queue(self, notification_queue, notification):
        """Test processing notification queue"""
        callback = Mock()
        notification_queue.add(notification)

        # Process one notification
        notification_queue.process_next(callback)

        callback.assert_called_once_with(notification)
        assert notification_queue._queue.qsize() == 0

    def test_clear_queue(self, notification_queue, notification):
        """Test clearing the queue"""
        # Add some notifications
        for i in range(5):
            notification_queue.add(notification)

        notification_queue.clear()

        assert notification_queue._queue.qsize() == 0

    def test_start_stop_processing(self, notification_queue):
        """Test starting and stopping queue processing"""
        callback = Mock()

        notification_queue.start_processing(callback, interval=0.1)
        assert notification_queue._processing is True
        assert notification_queue._process_thread is not None

        notification_queue.stop_processing()
        assert notification_queue._processing is False


class TestNotificationHistory:
    """Test NotificationHistory class"""

    def test_initialization(self, notification_history):
        """Test history initialization"""
        assert notification_history.max_size == 100
        assert len(notification_history._history) == 0

    def test_add_to_history(self, notification_history, notification):
        """Test adding notifications to history"""
        notification_history.add(notification)

        assert len(notification_history._history) == 1
        assert notification_history._history[0] == notification

    def test_history_max_size(self, notification_history, notification):
        """Test history max size enforcement"""
        # Add more than max size
        for i in range(150):
            notification_history.add(notification)

        assert len(notification_history._history) == 100

    def test_get_by_type(self, notification_history):
        """Test getting notifications by type"""
        # Add different types
        notification_history.add(Notification("Info", "msg", type=NotificationType.INFO))
        notification_history.add(Notification("Error", "msg", type=NotificationType.ERROR))
        notification_history.add(Notification("Info2", "msg", type=NotificationType.INFO))

        info_notifs = notification_history.get_by_type(NotificationType.INFO)

        assert len(info_notifs) == 2
        assert all(n.type == NotificationType.INFO for n in info_notifs)

    def test_get_recent(self, notification_history, notification):
        """Test getting recent notifications"""
        # Add notifications with delays
        for i in range(5):
            notification_history.add(notification)
            time.sleep(0.01)

        recent = notification_history.get_recent(count=3)

        assert len(recent) == 3
        # Should be in reverse chronological order
        assert recent[0].timestamp >= recent[1].timestamp

    def test_clear_history(self, notification_history, notification):
        """Test clearing history"""
        # Add some notifications
        for i in range(5):
            notification_history.add(notification)

        notification_history.clear()

        assert len(notification_history._history) == 0

    def test_export_history(self, notification_history, notification):
        """Test exporting history"""
        notification_history.add(notification)

        exported = notification_history.export()

        assert len(exported) == 1
        assert exported[0]["title"] == "Test Title"


class TestPlyerNotificationProvider:
    """Test PlyerNotificationProvider"""

    @patch("src.services.notification_service.PLYER_AVAILABLE", True)
    def test_is_available(self):
        """Test provider availability check"""
        provider = PlyerNotificationProvider()
        assert provider.is_available() is True

    @patch("src.services.notification_service.PLYER_AVAILABLE", False)
    def test_not_available(self):
        """Test when plyer is not available"""
        provider = PlyerNotificationProvider()
        assert provider.is_available() is False

    @patch("src.services.notification_service.plyer_notification")
    def test_show_notification(self, mock_plyer, notification):
        """Test showing notification with plyer"""
        provider = PlyerNotificationProvider()

        success = provider.show(notification)

        assert success is True
        mock_plyer.notify.assert_called_once_with(
            title="Test Title",
            message="Test message",
            timeout=5,
            app_icon="test.ico",
        )

    @patch("src.services.notification_service.plyer_notification")
    def test_show_notification_error(self, mock_plyer, notification):
        """Test handling plyer notification error"""
        mock_plyer.notify.side_effect = Exception("Plyer error")
        provider = PlyerNotificationProvider()

        success = provider.show(notification)

        assert success is False


class TestWindowsToastProvider:
    """Test WindowsToastProvider"""

    @patch("src.services.notification_service.WIN10_TOAST_AVAILABLE", True)
    @patch("src.services.notification_service.sys.platform", "win32")
    def test_is_available_windows(self):
        """Test provider availability on Windows"""
        provider = WindowsToastProvider()
        assert provider.is_available() is True

    @patch("src.services.notification_service.sys.platform", "linux")
    def test_not_available_linux(self):
        """Test provider not available on Linux"""
        provider = WindowsToastProvider()
        assert provider.is_available() is False

    @patch("src.services.notification_service.ToastNotifier")
    def test_show_notification(self, mock_toast_class, notification):
        """Test showing Windows toast notification"""
        mock_toaster = Mock()
        mock_toast_class.return_value = mock_toaster

        provider = WindowsToastProvider()
        success = provider.show(notification)

        assert success is True
        mock_toaster.show_toast.assert_called_once()

    def test_supports_actions(self):
        """Test that Windows toast supports actions"""
        provider = WindowsToastProvider()
        assert provider.supports_actions() is True


class TestSystemTrayProvider:
    """Test SystemTrayProvider"""

    def test_initialization(self):
        """Test provider initialization"""
        mock_tray = Mock()
        provider = SystemTrayProvider(mock_tray)

        assert provider.tray_manager == mock_tray

    def test_show_notification(self, notification):
        """Test showing tray notification"""
        mock_tray = Mock()
        mock_tray.show_notification = Mock(return_value=True)

        provider = SystemTrayProvider(mock_tray)
        success = provider.show(notification)

        assert success is True
        mock_tray.show_notification.assert_called_once_with(
            "Test Title",
            "Test message",
            5000,  # Duration in milliseconds
        )


class TestNotificationService:
    """Test main NotificationService class"""

    def test_initialization(self, notification_service):
        """Test service initialization"""
        assert notification_service.provider is not None
        assert notification_service.history is not None
        assert notification_service.queue is not None
        assert notification_service._enabled is True

    def test_show_notification(self, notification_service, notification):
        """Test showing notification"""
        success = notification_service.show(
            "Title",
            "Message",
            type=NotificationType.SUCCESS,
        )

        assert success is True
        notification_service.provider.show.assert_called_once()
        assert len(notification_service.history._history) == 1

    def test_show_notification_disabled(self, notification_service):
        """Test showing notification when disabled"""
        notification_service.disable()

        success = notification_service.show("Title", "Message")

        assert success is False
        notification_service.provider.show.assert_not_called()

    def test_show_translation_notification(self, notification_service):
        """Test showing translation-specific notification"""
        success = notification_service.show_translation(
            original="Hello",
            translated="Привет",
            target_language="ru",
        )

        assert success is True
        call_args = notification_service.provider.show.call_args[0][0]
        assert call_args.type == NotificationType.TRANSLATION
        assert "Hello" in call_args.message
        assert "Привет" in call_args.message

    def test_show_error_notification(self, notification_service):
        """Test showing error notification"""
        success = notification_service.show_error(
            "Operation failed",
            details="Connection timeout",
        )

        assert success is True
        call_args = notification_service.provider.show.call_args[0][0]
        assert call_args.type == NotificationType.ERROR
        assert call_args.sound is True  # Errors should have sound

    def test_queue_notification(self, notification_service):
        """Test queuing notification"""
        notification_service.queue_notification(
            "Title",
            "Message",
            type=NotificationType.INFO,
        )

        assert notification_service.queue._queue.qsize() == 1

    def test_process_queued_notifications(self, notification_service, notification):
        """Test processing queued notifications"""
        # Add to queue
        notification_service.queue.add(notification)

        # Process queue
        notification_service.process_queue()

        notification_service.provider.show.assert_called_once()

    def test_get_history(self, notification_service, notification):
        """Test getting notification history"""
        notification_service.show("Title1", "Message1")
        notification_service.show("Title2", "Message2")

        history = notification_service.get_history()

        assert len(history) == 2
        assert history[0]["title"] == "Title2"  # Most recent first

    def test_clear_history(self, notification_service):
        """Test clearing notification history"""
        notification_service.show("Title", "Message")
        notification_service.clear_history()

        assert len(notification_service.history._history) == 0

    def test_set_provider(self, notification_service):
        """Test changing notification provider"""
        new_provider = Mock(spec=NotificationProvider)
        new_provider.is_available.return_value = True

        notification_service.set_provider(new_provider)

        assert notification_service.provider == new_provider

    def test_fallback_providers(self):
        """Test provider fallback mechanism"""
        # All providers fail
        with patch("src.services.notification_service.PLYER_AVAILABLE", False), patch(
            "src.services.notification_service.WIN10_TOAST_AVAILABLE", False
        ), patch("src.services.notification_service.PYSTRAY_AVAILABLE", False):

            service = NotificationService()

            # Should use console provider as last resort
            assert service.provider is not None
            assert type(service.provider).__name__ == "ConsoleNotificationProvider"

    def test_notification_filtering(self, notification_service):
        """Test notification filtering by type"""
        # Configure to only show certain types
        notification_service.set_filter([NotificationType.ERROR, NotificationType.WARNING])

        # Try to show info notification
        success = notification_service.show("Info", "Message", type=NotificationType.INFO)
        assert success is False  # Should be filtered

        # Show error notification
        success = notification_service.show("Error", "Message", type=NotificationType.ERROR)
        assert success is True  # Should pass filter

    def test_rate_limiting(self, notification_service):
        """Test notification rate limiting"""
        notification_service.set_rate_limit(max_per_minute=2)

        # First two should succeed
        assert notification_service.show("Test1", "Message") is True
        assert notification_service.show("Test2", "Message") is True

        # Third should be rate limited
        assert notification_service.show("Test3", "Message") is False

    def test_notification_grouping(self, notification_service):
        """Test notification grouping"""
        # Enable grouping for similar notifications
        notification_service.enable_grouping(threshold=3, window=5)

        # Send similar notifications
        for i in range(5):
            notification_service.show("Translation", f"Word {i}")

        # Should group into single notification
        assert notification_service.provider.show.call_count < 5


def test_get_notification_service_singleton():
    """Test notification service singleton"""
    service1 = get_notification_service()
    service2 = get_notification_service()

    assert service1 is service2

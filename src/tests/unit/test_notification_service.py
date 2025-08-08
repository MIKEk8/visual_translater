"""Unit tests for notification service module - Fixed version"""

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
    """Create sample notification"""
    return Notification(
        title="Test Notification",
        message="This is a test message",
        notification_type=NotificationType.INFO,
        priority=NotificationPriority.NORMAL,
    )


@pytest.fixture
def notification_service():
    """Create NotificationService with mock backend"""
    mock_backend = Mock(spec=NotificationBackend)
    mock_backend.is_available.return_value = True
    mock_backend.show.return_value = True

    service = NotificationService()
    service.backend = mock_backend
    return service


@pytest.fixture
def notification_config():
    """Create notification config"""
    return NotificationConfig()


class TestNotification:
    """Test Notification dataclass"""

    def test_notification_creation(self):
        """Test creating notification"""
        notification = Notification(
            title="Test",
            message="Test message",
            notification_type=NotificationType.INFO,
            priority=NotificationPriority.NORMAL,
        )

        assert notification.title == "Test"
        assert notification.message == "Test message"
        assert notification.notification_type == NotificationType.INFO
        assert notification.priority == NotificationPriority.NORMAL
        assert notification.id is not None
        assert notification.timestamp is not None

    def test_notification_with_icon(self):
        """Test notification with custom icon"""
        notification = Notification(
            title="Test",
            message="Test message",
            notification_type=NotificationType.SUCCESS,
            icon="custom_icon.png",
        )

        assert notification.icon == "custom_icon.png"

    def test_notification_with_duration(self):
        """Test notification with custom duration"""
        notification = Notification(
            title="Test",
            message="Test message",
            notification_type=NotificationType.WARNING,
            duration=10,
        )

        assert notification.duration == 10


class TestNotificationService:
    """Test NotificationService class"""

    def test_service_creation(self, notification_config):
        """Test creating notification service"""
        service = NotificationService(config=notification_config)
        assert service is not None
        assert service.config == notification_config

    def test_show_notification(self, notification_service, notification):
        """Test showing notification"""
        notification_id = notification_service.show(notification)

        assert notification_id is not None
        notification_service.backend.show.assert_called_once_with(notification)

    def test_show_notification_backend_failure(self, notification_service, notification):
        """Test showing notification when backend fails"""
        notification_service.backend.show.return_value = False

        notification_id = notification_service.show(notification)
        assert notification_id is None

    def test_get_notification_service_singleton(self):
        """Test that get_notification_service returns singleton"""
        service1 = get_notification_service()
        service2 = get_notification_service()

        assert service1 is service2


class TestNotificationBackends:
    """Test notification backend implementations"""

    @patch("src.services.notification_service.platform.system")
    def test_win10toast_backend_windows(self, mock_platform):
        """Test Win10ToastBackend on Windows"""
        mock_platform.return_value = "Windows"

        backend = Win10ToastBackend()
        assert backend.is_available() is True

    @patch("src.services.notification_service.platform.system")
    def test_win10toast_backend_non_windows(self, mock_platform):
        """Test Win10ToastBackend on non-Windows"""
        mock_platform.return_value = "Linux"

        backend = Win10ToastBackend()
        assert backend.is_available() is False

    def test_fallback_backend_always_available(self):
        """Test FallbackBackend is always available"""
        backend = FallbackBackend()
        assert backend.is_available() is True

    def test_system_tray_backend(self):
        """Test SystemTrayBackend"""
        mock_tray_manager = Mock()
        backend = SystemTrayBackend(tray_manager=mock_tray_manager)

        notification = Notification(
            title="Test",
            message="Test message",
            notification_type=NotificationType.INFO,
        )

        # Should delegate to tray manager
        backend.show(notification)
        mock_tray_manager.show_notification.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

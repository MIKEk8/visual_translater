"""
Notification service for Screen Translator v2.0.
Provides cross-platform desktop notifications with advanced features.
"""

import os
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    # Windows notifications
    from plyer import notification as plyer_notification

    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

try:
    # Windows toast notifications (advanced)
    from win10toast import ToastNotifier

    WIN10_TOAST_AVAILABLE = True
except ImportError:
    WIN10_TOAST_AVAILABLE = False

try:
    # System tray notifications via pystray
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False

from src.utils.logger import logger


class NotificationType(Enum):
    """Types of notifications."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    TRANSLATION = "translation"
    OCR = "ocr"
    HOTKEY = "hotkey"


class NotificationPriority(Enum):
    """Notification priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class NotificationConfig:
    """Configuration for notification system."""

    enabled: bool = True
    duration: int = 5000  # milliseconds
    position: str = "bottom-right"  # top-left, top-right, bottom-left, bottom-right
    show_icon: bool = True
    play_sound: bool = True
    max_notifications: int = 5
    group_similar: bool = True
    fade_animation: bool = True
    click_action: str = "focus"  # focus, dismiss, none

    # Notification type filters
    show_translation: bool = True
    show_ocr: bool = True
    show_errors: bool = True
    show_success: bool = True
    show_hotkeys: bool = False

    # Advanced settings
    auto_dismiss_success: bool = True
    persistent_errors: bool = True
    batch_similar: bool = True


@dataclass
class Notification:
    """Individual notification data."""

    id: str
    title: str
    message: str
    type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    duration: Optional[int] = None
    icon: Optional[str] = None
    actions: Optional[List[Dict[str, Any]]] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    dismissed: bool = False
    clicked: bool = False

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.actions is None:
            self.actions = []
        if self.data is None:
            self.data = {}


class NotificationBackend:
    """Base class for notification backends."""

    def __init__(self, config: NotificationConfig):
        self.config = config
        self.available = False

    def is_available(self) -> bool:
        """Check if backend is available on current system."""
        return self.available

    def show_notification(self, notification: Notification) -> bool:
        """Show notification using this backend."""
        raise NotImplementedError

    def dismiss_notification(self, notification_id: str) -> bool:
        """Dismiss notification by ID."""
        return False  # Default implementation

    def dismiss_all(self) -> bool:
        """Dismiss all notifications."""
        return False  # Default implementation


class PlyerNotificationBackend(NotificationBackend):
    """Plyer-based notification backend (cross-platform)."""

    def __init__(self, config: NotificationConfig):
        super().__init__(config)
        self.available = PLYER_AVAILABLE

    def show_notification(self, notification: Notification) -> bool:
        """Show notification using plyer."""
        if not self.available:
            return False

        try:
            duration = notification.duration or self.config.duration

            plyer_notification.notify(
                title=notification.title,
                message=notification.message,
                timeout=duration // 1000,  # plyer uses seconds
                app_name="Screen Translator",
                app_icon=notification.icon or self._get_default_icon(notification.type),
            )

            logger.debug(f"Plyer notification shown: {notification.title}")
            return True

        except Exception as e:
            logger.error(f"Plyer notification failed: {e}")
            return False

    def _get_default_icon(self, notification_type: NotificationType) -> Optional[str]:
        """Get default icon for notification type."""
        _ = notification_type  # Unused parameter - could be extended for type-specific icons
        # Return None to use system default
        return None


class Win10ToastBackend(NotificationBackend):
    """Windows 10 Toast notification backend."""

    def __init__(self, config: NotificationConfig):
        super().__init__(config)
        self.available = WIN10_TOAST_AVAILABLE and sys.platform == "win32"
        if self.available:
            self.toaster = ToastNotifier()

    def show_notification(self, notification: Notification) -> bool:
        """Show Windows 10 toast notification."""
        if not self.available:
            return False

        try:
            duration = notification.duration or self.config.duration

            # Prepare callback if needed
            callback = None
            if notification.actions:

                def _notification_callback():
                    return self._handle_notification_click(notification)

                callback = _notification_callback

            self.toaster.show_toast(
                title=notification.title,
                msg=notification.message,
                duration=duration // 1000,  # win10toast uses seconds
                icon_path=notification.icon or self._get_default_icon(notification.type),
                threaded=True,
                callback_on_click=callback,
            )

            logger.debug(f"Win10Toast notification shown: {notification.title}")
            return True

        except Exception as e:
            logger.error(f"Win10Toast notification failed: {e}")
            return False

    def _handle_notification_click(self, notification: Notification) -> None:
        """Handle notification click."""
        notification.clicked = True
        logger.debug(f"Notification clicked: {notification.id}")

    def _get_default_icon(self, notification_type: NotificationType) -> Optional[str]:
        """Get default icon path for notification type."""
        _ = notification_type  # Unused parameter - could be extended for type-specific icons
        # Try to find icon file in project directory
        icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "icon.ico")
        if os.path.exists(icon_path):
            return icon_path
        return None


class SystemTrayBackend(NotificationBackend):
    """System tray notification backend using pystray."""

    def __init__(self, config: NotificationConfig):
        super().__init__(config)
        self.available = PYSTRAY_AVAILABLE
        self.notifications: List[Notification] = []

    def show_notification(self, notification: Notification) -> bool:
        """Show notification in system tray."""
        if not self.available:
            return False

        try:
            # Add to internal list
            self.notifications.append(notification)

            # Limit number of notifications
            if len(self.notifications) > self.config.max_notifications:
                self.notifications = self.notifications[-self.config.max_notifications :]

            # For system tray, we could show a tooltip or balloon
            # This is a simplified implementation
            logger.info(f"System tray notification: {notification.title} - {notification.message}")
            return True

        except Exception as e:
            logger.error(f"System tray notification failed: {e}")
            return False

    def get_recent_notifications(self, count: int = 5) -> List[Notification]:
        """Get recent notifications for tray menu."""
        return self.notifications[-count:] if self.notifications else []


class FallbackBackend(NotificationBackend):
    """Fallback notification backend (console/log only)."""

    def __init__(self, config: NotificationConfig):
        super().__init__(config)
        self.available = True  # Always available

    def show_notification(self, notification: Notification) -> bool:
        """Show notification in console/log."""
        type_icon = {
            NotificationType.INFO: "ℹ️",
            NotificationType.SUCCESS: "✅",
            NotificationType.WARNING: "⚠️",
            NotificationType.ERROR: "❌",
            NotificationType.TRANSLATION: "🌐",
            NotificationType.OCR: "👁️",
            NotificationType.HOTKEY: "⌨️",
        }.get(notification.type, "📢")

        message = f"{type_icon} {notification.title}: {notification.message}"

        if notification.priority == NotificationPriority.CRITICAL:
            logger.critical(message)
        elif notification.priority == NotificationPriority.HIGH:
            logger.error(message)
        elif notification.priority == NotificationPriority.NORMAL:
            logger.info(message)
        else:
            logger.debug(message)

        # Also print to console for immediate visibility
        print(f"[NOTIFICATION] {message}")

        return True


class NotificationService:
    """Main notification service with multiple backends."""

    def __init__(self, config: Optional[NotificationConfig] = None):
        """
        Initialize notification service.

        Args:
            config: Notification configuration
        """
        self.config = config or NotificationConfig()
        self.backends: List[NotificationBackend] = []
        self.notifications: Dict[str, Notification] = {}
        self.notification_counter = 0
        self.group_timers: Dict[str, threading.Timer] = {}

        # Initialize backends
        self._initialize_backends()

        # Find best available backend
        self.primary_backend = self._get_primary_backend()

        logger.info(f"Notification service initialized with {len(self.backends)} backends")
        logger.debug(f"Primary backend: {type(self.primary_backend).__name__}")

    def _initialize_backends(self) -> None:
        """Initialize all available notification backends."""
        # Windows 10 Toast (best for Windows)
        if sys.platform == "win32":
            win10_backend = Win10ToastBackend(self.config)
            if win10_backend.is_available():
                self.backends.append(win10_backend)

        # Plyer (cross-platform)
        plyer_backend = PlyerNotificationBackend(self.config)
        if plyer_backend.is_available():
            self.backends.append(plyer_backend)

        # System tray
        tray_backend = SystemTrayBackend(self.config)
        if tray_backend.is_available():
            self.backends.append(tray_backend)

        # Fallback (always available)
        fallback_backend = FallbackBackend(self.config)
        self.backends.append(fallback_backend)

    def _get_primary_backend(self) -> NotificationBackend:
        """Get the primary notification backend to use."""
        if not self.backends:
            return FallbackBackend(self.config)

        # Prefer Win10Toast on Windows, then Plyer, then others
        for backend in self.backends:
            if isinstance(backend, Win10ToastBackend):
                return backend

        for backend in self.backends:
            if isinstance(backend, PlyerNotificationBackend):
                return backend

        # Return first available backend
        return self.backends[0]

    def show_notification(
        self,
        title: str,
        message: str,
        type: NotificationType = NotificationType.INFO,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        duration: Optional[int] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Show a notification.

        Args:
            title: Notification title
            message: Notification message
            type: Notification type
            priority: Notification priority
            duration: Duration in milliseconds (None for default)
            actions: List of action buttons
            data: Additional data

        Returns:
            Notification ID
        """
        if not self.config.enabled:
            return ""

        # Check type filters
        if not self._should_show_notification(type):
            return ""

        # Generate notification ID
        self.notification_counter += 1
        notification_id = f"notif_{self.notification_counter}_{int(time.time())}"

        # Create notification
        notification = Notification(
            id=notification_id,
            title=title,
            message=message,
            type=type,
            priority=priority,
            duration=duration,
            actions=actions or [],
            data=data or {},
        )

        # Check for grouping
        if self.config.group_similar:
            group_key = f"{type.value}_{title}"
            if group_key in self.group_timers:
                # Cancel previous timer and batch notifications
                self.group_timers[group_key].cancel()
                return self._schedule_grouped_notification(group_key, notification)

        # Store notification
        self.notifications[notification_id] = notification

        # Show notification
        success = self._show_notification_with_fallback(notification)

        if success:
            # Schedule auto-dismiss if configured
            if self._should_auto_dismiss(notification):
                self._schedule_auto_dismiss(notification)

        logger.debug(f"Notification created: {notification_id} - {title}")
        return notification_id

    def _should_show_notification(self, type: NotificationType) -> bool:
        """Check if notification type should be shown based on config."""
        filters = {
            NotificationType.TRANSLATION: self.config.show_translation,
            NotificationType.OCR: self.config.show_ocr,
            NotificationType.ERROR: self.config.show_errors,
            NotificationType.SUCCESS: self.config.show_success,
            NotificationType.HOTKEY: self.config.show_hotkeys,
            NotificationType.INFO: True,
            NotificationType.WARNING: True,
        }

        return filters.get(type, True)

    def _show_notification_with_fallback(self, notification: Notification) -> bool:
        """Show notification with fallback to other backends."""
        # Try primary backend first
        if self.primary_backend.show_notification(notification):
            return True

        # Try other backends
        for backend in self.backends:
            if backend != self.primary_backend:
                if backend.show_notification(notification):
                    logger.warning(
                        f"Primary backend failed, used fallback: {type(backend).__name__}"
                    )
                    return True

        logger.error("All notification backends failed")
        return False

    def _should_auto_dismiss(self, notification: Notification) -> bool:
        """Check if notification should be auto-dismissed."""
        if notification.type == NotificationType.SUCCESS and self.config.auto_dismiss_success:
            return True

        if notification.type == NotificationType.ERROR and self.config.persistent_errors:
            return False

        return True

    def _schedule_auto_dismiss(self, notification: Notification) -> None:
        """Schedule automatic dismissal of notification."""
        duration = notification.duration or self.config.duration

        def auto_dismiss():
            self.dismiss_notification(notification.id)

        timer = threading.Timer(duration / 1000.0, auto_dismiss)
        timer.start()

    def _schedule_grouped_notification(self, group_key: str, notification: Notification) -> str:
        """Schedule grouped notification to reduce spam."""

        def show_grouped():
            if group_key in self.group_timers:
                del self.group_timers[group_key]
            self._show_notification_with_fallback(notification)

        # Delay showing notification to allow grouping
        timer = threading.Timer(0.5, show_grouped)
        self.group_timers[group_key] = timer
        timer.start()

        return notification.id

    def dismiss_notification(self, notification_id: str) -> bool:
        """
        Dismiss a specific notification.

        Args:
            notification_id: ID of notification to dismiss

        Returns:
            True if dismissed successfully
        """
        if notification_id not in self.notifications:
            return False

        notification = self.notifications[notification_id]
        notification.dismissed = True

        # Try to dismiss using primary backend
        success = self.primary_backend.dismiss_notification(notification_id)

        # Remove from tracking
        del self.notifications[notification_id]

        logger.debug(f"Notification dismissed: {notification_id}")
        return success

    def dismiss_all(self) -> bool:
        """Dismiss all notifications."""
        for notification_id in list(self.notifications.keys()):
            self.dismiss_notification(notification_id)

        # Try backend dismiss all
        success = self.primary_backend.dismiss_all()

        logger.debug("All notifications dismissed")
        return success

    def get_active_notifications(self) -> List[Notification]:
        """Get list of active notifications."""
        return [notif for notif in self.notifications.values() if not notif.dismissed]

    def update_config(self, config: NotificationConfig) -> None:
        """Update notification configuration."""
        self.config = config

        # Update backend configs
        for backend in self.backends:
            backend.config = config

        logger.debug("Notification config updated")

    # Convenience methods for common notification types

    def show_success(self, title: str, message: str, **kwargs) -> str:
        """Show success notification."""
        return self.show_notification(
            title, message, NotificationType.SUCCESS, NotificationPriority.NORMAL, **kwargs
        )

    def show_error(self, title: str, message: str, **kwargs) -> str:
        """Show error notification."""
        return self.show_notification(
            title, message, NotificationType.ERROR, NotificationPriority.HIGH, **kwargs
        )

    def show_warning(self, title: str, message: str, **kwargs) -> str:
        """Show warning notification."""
        return self.show_notification(
            title, message, NotificationType.WARNING, NotificationPriority.NORMAL, **kwargs
        )

    def show_info(self, title: str, message: str, **kwargs) -> str:
        """Show info notification."""
        return self.show_notification(
            title, message, NotificationType.INFO, NotificationPriority.LOW, **kwargs
        )

    def show_translation_complete(self, original: str, translated: str, **kwargs) -> str:
        """Show translation completion notification."""
        title = "Translation Complete"
        # Use ASCII arrow to avoid Unicode encoding issues
        message = f"'{original[:30]}...' -> '{translated[:30]}...'"
        return self.show_notification(
            title, message, NotificationType.TRANSLATION, NotificationPriority.NORMAL, **kwargs
        )

    def show_ocr_complete(self, text: str, confidence: float, **kwargs) -> str:
        """Show OCR completion notification."""
        title = "Text Recognition Complete"
        message = f"Extracted: '{text[:50]}...' (Confidence: {confidence:.1%})"
        return self.show_notification(
            title, message, NotificationType.OCR, NotificationPriority.NORMAL, **kwargs
        )

    def show_hotkey_registered(self, hotkey: str, action: str, **kwargs) -> str:
        """Show hotkey registration notification."""
        title = "Hotkey Registered"
        message = f"{hotkey} → {action}"
        return self.show_notification(
            title, message, NotificationType.HOTKEY, NotificationPriority.LOW, **kwargs
        )


# Global notification service instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get global notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


def initialize_notifications(config: Optional[NotificationConfig] = None) -> NotificationService:
    """Initialize global notification service."""
    global _notification_service
    _notification_service = NotificationService(config)
    return _notification_service


# Convenience functions for global access
def notify_success(title: str, message: str, **kwargs) -> str:
    """Show global success notification."""
    return get_notification_service().show_success(title, message, **kwargs)


def notify_error(title: str, message: str, **kwargs) -> str:
    """Show global error notification."""
    return get_notification_service().show_error(title, message, **kwargs)


def notify_warning(title: str, message: str, **kwargs) -> str:
    """Show global warning notification."""
    return get_notification_service().show_warning(title, message, **kwargs)


def notify_info(title: str, message: str, **kwargs) -> str:
    """Show global info notification."""
    return get_notification_service().show_info(title, message, **kwargs)

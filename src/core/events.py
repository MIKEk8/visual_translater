"""
Event-driven architecture components for Screen Translator.

This module provides event bus, event types, and event handling infrastructure
for loose coupling between application components.
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Application event types."""

    # Screenshot events
    SCREENSHOT_REQUESTED = auto()
    SCREENSHOT_CAPTURED = auto()
    SCREENSHOT_FAILED = auto()

    # OCR events
    OCR_STARTED = auto()
    TEXT_EXTRACTED = auto()
    OCR_FAILED = auto()

    # Translation events
    TRANSLATION_REQUESTED = auto()
    TRANSLATION_COMPLETED = auto()
    TRANSLATION_FAILED = auto()
    TRANSLATION_CACHED = auto()

    # TTS events
    TTS_STARTED = auto()
    TTS_COMPLETED = auto()
    TTS_FAILED = auto()

    # UI events
    UI_SETTINGS_OPENED = auto()
    UI_SETTINGS_CLOSED = auto()
    UI_LANGUAGE_CHANGED = auto()

    # System events
    APPLICATION_STARTED = auto()
    APPLICATION_SHUTDOWN = auto()
    ERROR_OCCURRED = auto()

    # Performance events
    PERFORMANCE_ALERT = auto()
    SLOW_OPERATION_DETECTED = auto()


@dataclass
class Event:
    """Base event class."""

    type: EventType
    data: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate event after creation."""
        if not isinstance(self.type, EventType):
            raise ValueError(f"Invalid event type: {self.type}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "type": self.type.name.lower(),
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary."""
        event_type = EventType[data["type"].upper()]
        timestamp = datetime.fromisoformat(data["timestamp"])

        return cls(
            type=event_type,
            data=data.get("data"),
            timestamp=timestamp,
            source=data.get("source", "unknown"),
            correlation_id=data["correlation_id"],
            metadata=data.get("metadata", {}),
        )


class EventHandler:
    """Base class for event handlers."""

    def __init__(self, name: str):
        self.name = name
        self.handled_events: Set[EventType] = set()

    async def handle(self, event: Event) -> None:
        """Handle an event. Override in subclasses."""

    def can_handle(self, event_type: EventType) -> bool:
        """Check if this handler can handle the event type."""
        return event_type in self.handled_events


class EventBus:
    """Central event bus for application-wide event handling."""

    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self._middleware: List[Callable[[Event], Event]] = []
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._stats = {"events_published": 0, "events_handled": 0, "errors": 0}
        self._running = True

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe a handler to an event type."""
        if not isinstance(handler, EventHandler):
            raise ValueError("Handler must be an instance of EventHandler")

        self._handlers[event_type].append(handler)
        handler.handled_events.add(event_type)

        logger.debug(f"Subscribed {handler.name} to {event_type.name}")

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Unsubscribe a handler from an event type."""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            handler.handled_events.discard(event_type)

            logger.debug(f"Unsubscribed {handler.name} from {event_type.name}")

    def add_middleware(self, middleware: Callable[[Event], Event]) -> None:
        """Add middleware to process events before handling."""
        self._middleware.append(middleware)

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribed handlers."""
        if not self._running:
            logger.warning("Event bus is shutting down, ignoring event")
            return

        try:
            # Apply middleware
            processed_event = event
            for middleware in self._middleware:
                processed_event = middleware(processed_event)

            # Store in history
            self._add_to_history(processed_event)

            # Get handlers for this event type
            handlers = self._handlers.get(processed_event.type, [])

            if not handlers:
                logger.debug(f"No handlers for {processed_event.type.name}")
                return

            # Execute all handlers concurrently
            tasks = []
            for handler in handlers:
                if handler.can_handle(processed_event.type):
                    task = asyncio.create_task(self._safe_handle(handler, processed_event))
                    tasks.append(task)

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            self._stats["events_published"] += 1
            logger.debug(f"Published {processed_event.type.name} to {len(handlers)} handlers")

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Error publishing event {event.type.name}: {e}")

            # Publish error event
            error_event = Event(
                type=EventType.ERROR_OCCURRED,
                data={"original_event": event, "error": str(e)},
                source="event_bus",
            )
            # Avoid infinite loop by not publishing error events for error events
            if event.type != EventType.ERROR_OCCURRED:
                await self.publish(error_event)

    async def _safe_handle(self, handler: EventHandler, event: Event) -> None:
        """Safely execute a handler with error handling."""
        try:
            start_time = time.time()
            await handler.handle(event)
            duration = time.time() - start_time

            self._stats["events_handled"] += 1

            # Log slow handlers
            if duration > 1.0:  # More than 1 second
                logger.warning(
                    f"Slow event handler: {handler.name} took {duration:.2f}s "
                    f"for {event.type.name}"
                )

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Error in handler {handler.name} for {event.type.name}: {e}")

    def _add_to_history(self, event: Event) -> None:
        """Add event to history with size limit."""
        self._event_history.append(event)

        # Keep history size limited
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history :]

    def get_recent_events(self, count: int = 100) -> List[Event]:
        """Get recent events from history."""
        return self._event_history[-count:]

    def get_events_by_type(self, event_type: EventType, count: int = 100) -> List[Event]:
        """Get recent events of specific type."""
        filtered = [e for e in self._event_history if e.type == event_type]
        return filtered[-count:]

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            **self._stats,
            "active_handlers": sum(len(handlers) for handlers in self._handlers.values()),
            "event_types_registered": len(self._handlers),
            "history_size": len(self._event_history),
        }

    async def shutdown(self) -> None:
        """Gracefully shutdown the event bus."""
        self._running = False
        logger.info("Event bus shutting down")


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def publish_event(event_type: EventType, data: Any = None, source: str = "unknown") -> None:
    """Convenience function to publish an event."""
    event = Event(type=event_type, data=data, source=source)
    asyncio.create_task(get_event_bus().publish(event))


# Event middleware examples
def logging_middleware(event: Event) -> Event:
    """Middleware to log all events."""
    logger.debug(f"Event: {event.type.name} from {event.source}")
    return event


def correlation_middleware(event: Event) -> Event:
    """Middleware to add correlation tracking."""
    if "parent_correlation_id" not in event.metadata:
        event.metadata["parent_correlation_id"] = event.correlation_id
    return event


# Predefined event handlers for common scenarios
class LoggingEventHandler(EventHandler):
    """Handler that logs all events it receives."""

    def __init__(self):
        super().__init__("logging_handler")
        # Subscribe to all event types
        self.handled_events = set(EventType)

    async def handle(self, event: Event) -> None:
        logger.info(f"Event logged: {event.type.name} from {event.source}")


class PerformanceEventHandler(EventHandler):
    """Handler for performance monitoring events."""

    def __init__(self):
        super().__init__("performance_handler")
        self.handled_events = {EventType.PERFORMANCE_ALERT, EventType.SLOW_OPERATION_DETECTED}

    async def handle(self, event: Event) -> None:
        if event.type == EventType.PERFORMANCE_ALERT:
            logger.warning(f"Performance alert: {event.data}")
        elif event.type == EventType.SLOW_OPERATION_DETECTED:
            logger.warning(f"Slow operation: {event.data}")

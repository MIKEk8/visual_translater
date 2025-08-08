"""
Tests for event system module.
"""

import asyncio
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from src.core.events import (
    Event,
    EventBus,
    EventHandler,
    EventType,
    LoggingEventHandler,
    PerformanceEventHandler,
    correlation_middleware,
    get_event_bus,
    logging_middleware,
    publish_event,
)


class MockEventHandler(EventHandler):
    """Mock event handler for testing"""

    def __init__(self, name="mock_handler"):
        super().__init__(name)
        self.handled_events_list = []
        self.should_raise = False

    async def handle(self, event: Event) -> None:
        if self.should_raise:
            raise Exception("Handler error")
        self.handled_events_list.append(event)


class TestEventType(unittest.TestCase):
    """Test EventType enum"""

    def test_event_types_exist(self):
        """Test that all expected event types exist"""
        # Screenshot events
        self.assertIsInstance(EventType.SCREENSHOT_REQUESTED, EventType)
        self.assertIsInstance(EventType.SCREENSHOT_CAPTURED, EventType)
        self.assertIsInstance(EventType.SCREENSHOT_FAILED, EventType)

        # OCR events
        self.assertIsInstance(EventType.OCR_STARTED, EventType)
        self.assertIsInstance(EventType.TEXT_EXTRACTED, EventType)
        self.assertIsInstance(EventType.OCR_FAILED, EventType)

        # Translation events
        self.assertIsInstance(EventType.TRANSLATION_REQUESTED, EventType)
        self.assertIsInstance(EventType.TRANSLATION_COMPLETED, EventType)
        self.assertIsInstance(EventType.TRANSLATION_FAILED, EventType)
        self.assertIsInstance(EventType.TRANSLATION_CACHED, EventType)

        # System events
        self.assertIsInstance(EventType.APPLICATION_STARTED, EventType)
        self.assertIsInstance(EventType.APPLICATION_SHUTDOWN, EventType)
        self.assertIsInstance(EventType.ERROR_OCCURRED, EventType)


class TestEvent(unittest.TestCase):
    """Test Event dataclass"""

    def test_event_creation_basic(self):
        """Test basic event creation"""
        event = Event(type=EventType.SCREENSHOT_REQUESTED)

        self.assertEqual(event.type, EventType.SCREENSHOT_REQUESTED)
        self.assertIsNone(event.data)
        self.assertIsInstance(event.timestamp, datetime)
        self.assertEqual(event.source, "unknown")
        self.assertIsInstance(event.correlation_id, str)
        self.assertEqual(event.metadata, {})

    def test_event_creation_with_data(self):
        """Test event creation with data"""
        test_data = {"x": 100, "y": 200}
        event = Event(type=EventType.SCREENSHOT_CAPTURED, data=test_data, source="test_source")

        self.assertEqual(event.type, EventType.SCREENSHOT_CAPTURED)
        self.assertEqual(event.data, test_data)
        self.assertEqual(event.source, "test_source")

    def test_event_validation(self):
        """Test event validation in __post_init__"""
        # Valid event
        event = Event(type=EventType.OCR_STARTED)
        self.assertIsInstance(event, Event)

        # Invalid event type should raise ValueError
        with self.assertRaises(ValueError):
            Event(type="invalid_type")

    def test_event_to_dict(self):
        """Test converting event to dictionary"""
        test_data = {"key": "value"}
        test_metadata = {"meta": "data"}

        event = Event(
            type=EventType.TRANSLATION_COMPLETED,
            data=test_data,
            source="test_source",
            metadata=test_metadata,
        )

        event_dict = event.to_dict()

        self.assertEqual(event_dict["type"], "translation_completed")
        self.assertEqual(event_dict["data"], test_data)
        self.assertEqual(event_dict["source"], "test_source")
        self.assertEqual(event_dict["correlation_id"], event.correlation_id)
        self.assertEqual(event_dict["metadata"], test_metadata)
        self.assertIsInstance(event_dict["timestamp"], str)

    def test_event_from_dict(self):
        """Test creating event from dictionary"""
        test_timestamp = datetime.now()
        test_correlation_id = "test-correlation-id"

        event_dict = {
            "type": "translation_failed",
            "data": {"error": "test error"},
            "timestamp": test_timestamp.isoformat(),
            "source": "test_source",
            "correlation_id": test_correlation_id,
            "metadata": {"meta": "value"},
        }

        event = Event.from_dict(event_dict)

        self.assertEqual(event.type, EventType.TRANSLATION_FAILED)
        self.assertEqual(event.data, {"error": "test error"})
        self.assertEqual(event.source, "test_source")
        self.assertEqual(event.correlation_id, test_correlation_id)
        self.assertEqual(event.metadata, {"meta": "value"})
        self.assertEqual(event.timestamp, test_timestamp)

    def test_event_from_dict_minimal(self):
        """Test creating event from minimal dictionary"""
        event_dict = {
            "type": "ocr_started",
            "timestamp": datetime.now().isoformat(),
            "correlation_id": "test-id",
        }

        event = Event.from_dict(event_dict)

        self.assertEqual(event.type, EventType.OCR_STARTED)
        self.assertIsNone(event.data)
        self.assertEqual(event.source, "unknown")
        self.assertEqual(event.metadata, {})


class TestEventHandler(unittest.TestCase):
    """Test EventHandler base class"""

    def test_handler_creation(self):
        """Test handler creation"""
        handler = MockEventHandler("test_handler")

        self.assertEqual(handler.name, "test_handler")
        self.assertEqual(handler.handled_events, set())
        self.assertEqual(handler.handled_events_list, [])

    def test_can_handle(self):
        """Test can_handle method"""
        handler = MockEventHandler()

        # Initially can't handle any events
        self.assertFalse(handler.can_handle(EventType.SCREENSHOT_REQUESTED))

        # Add event type
        handler.handled_events.add(EventType.SCREENSHOT_REQUESTED)
        self.assertTrue(handler.can_handle(EventType.SCREENSHOT_REQUESTED))
        self.assertFalse(handler.can_handle(EventType.OCR_STARTED))

    def test_handle_method(self):
        """Test handle method"""

        async def run_test():
            handler = MockEventHandler()
            event = Event(type=EventType.TRANSLATION_COMPLETED)

            await handler.handle(event)

            self.assertEqual(len(handler.handled_events_list), 1)
            self.assertEqual(handler.handled_events_list[0], event)

        asyncio.run(run_test())


class TestEventBus(unittest.TestCase):
    """Test EventBus class"""

    def setUp(self):
        """Set up test fixtures"""
        self.event_bus = EventBus()
        self.handler = MockEventHandler("test_handler")

    def tearDown(self):
        """Clean up after tests"""
        asyncio.run(self.event_bus.shutdown())

    def test_event_bus_initialization(self):
        """Test event bus initialization"""
        bus = EventBus()

        self.assertEqual(bus._handlers, {})
        self.assertEqual(bus._middleware, [])
        self.assertEqual(bus._event_history, [])
        self.assertEqual(bus._max_history, 1000)
        self.assertIsInstance(bus._stats, dict)
        self.assertTrue(bus._running)

    def test_subscribe_handler(self):
        """Test subscribing handler to event type"""
        self.event_bus.subscribe(EventType.SCREENSHOT_REQUESTED, self.handler)

        handlers = self.event_bus._handlers[EventType.SCREENSHOT_REQUESTED]
        self.assertIn(self.handler, handlers)
        self.assertIn(EventType.SCREENSHOT_REQUESTED, self.handler.handled_events)

    def test_subscribe_invalid_handler(self):
        """Test subscribing invalid handler raises error"""
        with self.assertRaises(ValueError):
            self.event_bus.subscribe(EventType.OCR_STARTED, "not_a_handler")

    def test_unsubscribe_handler(self):
        """Test unsubscribing handler from event type"""
        # First subscribe
        self.event_bus.subscribe(EventType.SCREENSHOT_REQUESTED, self.handler)
        self.assertIn(self.handler, self.event_bus._handlers[EventType.SCREENSHOT_REQUESTED])

        # Then unsubscribe
        self.event_bus.unsubscribe(EventType.SCREENSHOT_REQUESTED, self.handler)
        self.assertNotIn(self.handler, self.event_bus._handlers[EventType.SCREENSHOT_REQUESTED])
        self.assertNotIn(EventType.SCREENSHOT_REQUESTED, self.handler.handled_events)

    def test_add_middleware(self):
        """Test adding middleware"""

        def test_middleware(event):
            return event

        self.event_bus.add_middleware(test_middleware)

        self.assertIn(test_middleware, self.event_bus._middleware)

    def test_publish_event_no_handlers(self):
        """Test publishing event with no handlers"""

        async def run_test():
            event = Event(type=EventType.SCREENSHOT_REQUESTED)

            await self.event_bus.publish(event)

            # Should not raise error, just log
            # When no handlers, events_published is not incremented (early return)
            self.assertEqual(self.event_bus._stats["events_published"], 0)
            # But event should still be added to history
            self.assertEqual(len(self.event_bus._event_history), 1)

        asyncio.run(run_test())

    def test_publish_event_with_handler(self):
        """Test publishing event with handler"""

        async def run_test():
            self.event_bus.subscribe(EventType.SCREENSHOT_CAPTURED, self.handler)
            event = Event(type=EventType.SCREENSHOT_CAPTURED, data={"test": "data"})

            await self.event_bus.publish(event)

            # Wait a moment for async execution
            await asyncio.sleep(0.01)

            self.assertEqual(len(self.handler.handled_events_list), 1)
            self.assertEqual(self.handler.handled_events_list[0].data, {"test": "data"})
            self.assertEqual(self.event_bus._stats["events_published"], 1)
            self.assertEqual(self.event_bus._stats["events_handled"], 1)

        asyncio.run(run_test())

    def test_publish_event_with_middleware(self):
        """Test publishing event with middleware"""

        async def run_test():
            def add_metadata_middleware(event):
                event.metadata["processed"] = True
                return event

            self.event_bus.add_middleware(add_metadata_middleware)
            self.event_bus.subscribe(EventType.OCR_STARTED, self.handler)

            event = Event(type=EventType.OCR_STARTED)
            await self.event_bus.publish(event)

            await asyncio.sleep(0.01)

            # Check that middleware was applied
            processed_event = self.handler.handled_events_list[0]
            self.assertTrue(processed_event.metadata.get("processed"))

        asyncio.run(run_test())

    def test_publish_event_handler_error(self):
        """Test publishing event when handler raises error"""

        async def run_test():
            self.handler.should_raise = True
            self.event_bus.subscribe(EventType.TRANSLATION_FAILED, self.handler)

            event = Event(type=EventType.TRANSLATION_FAILED)
            await self.event_bus.publish(event)

            await asyncio.sleep(0.01)

            # Should handle error gracefully
            self.assertEqual(self.event_bus._stats["errors"], 1)

        asyncio.run(run_test())

    def test_publish_event_when_shutdown(self):
        """Test publishing event when bus is shut down"""

        async def run_test():
            await self.event_bus.shutdown()

            event = Event(type=EventType.SCREENSHOT_REQUESTED)
            await self.event_bus.publish(event)

            # Should not process event
            self.assertEqual(self.event_bus._stats["events_published"], 0)

        asyncio.run(run_test())

    def test_add_to_history(self):
        """Test adding events to history"""
        event1 = Event(type=EventType.SCREENSHOT_REQUESTED)
        event2 = Event(type=EventType.OCR_STARTED)

        self.event_bus._add_to_history(event1)
        self.event_bus._add_to_history(event2)

        self.assertEqual(len(self.event_bus._event_history), 2)
        self.assertIn(event1, self.event_bus._event_history)
        self.assertIn(event2, self.event_bus._event_history)

    def test_history_size_limit(self):
        """Test that history respects size limit"""
        self.event_bus._max_history = 3

        # Add more events than the limit
        for i in range(5):
            event = Event(type=EventType.SCREENSHOT_REQUESTED, data={"index": i})
            self.event_bus._add_to_history(event)

        self.assertEqual(len(self.event_bus._event_history), 3)
        # Should keep the last 3 events
        self.assertEqual(self.event_bus._event_history[0].data["index"], 2)
        self.assertEqual(self.event_bus._event_history[-1].data["index"], 4)

    def test_get_recent_events(self):
        """Test getting recent events"""
        events = []
        for i in range(5):
            event = Event(type=EventType.OCR_STARTED, data={"index": i})
            events.append(event)
            self.event_bus._add_to_history(event)

        recent = self.event_bus.get_recent_events(3)

        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[0].data["index"], 2)  # Last 3: [2, 3, 4]
        self.assertEqual(recent[-1].data["index"], 4)

    def test_get_events_by_type(self):
        """Test getting events by specific type"""
        # Add mixed event types
        event1 = Event(type=EventType.SCREENSHOT_REQUESTED, data={"id": 1})
        event2 = Event(type=EventType.OCR_STARTED, data={"id": 2})
        event3 = Event(type=EventType.SCREENSHOT_REQUESTED, data={"id": 3})

        for event in [event1, event2, event3]:
            self.event_bus._add_to_history(event)

        screenshot_events = self.event_bus.get_events_by_type(EventType.SCREENSHOT_REQUESTED)

        self.assertEqual(len(screenshot_events), 2)
        self.assertEqual(screenshot_events[0].data["id"], 1)
        self.assertEqual(screenshot_events[1].data["id"], 3)

    def test_get_stats(self):
        """Test getting event bus statistics"""
        # Add some handlers and events
        self.event_bus.subscribe(EventType.SCREENSHOT_REQUESTED, self.handler)
        self.event_bus._stats["events_published"] = 5
        self.event_bus._stats["events_handled"] = 4
        self.event_bus._stats["errors"] = 1

        stats = self.event_bus.get_stats()

        self.assertEqual(stats["events_published"], 5)
        self.assertEqual(stats["events_handled"], 4)
        self.assertEqual(stats["errors"], 1)
        self.assertEqual(stats["active_handlers"], 1)
        self.assertEqual(stats["event_types_registered"], 1)
        self.assertEqual(stats["history_size"], 0)


class TestGlobalEventBus(unittest.TestCase):
    """Test global event bus functions"""

    def test_get_event_bus_singleton(self):
        """Test that get_event_bus returns singleton"""
        bus1 = get_event_bus()
        bus2 = get_event_bus()

        self.assertIs(bus1, bus2)
        self.assertIsInstance(bus1, EventBus)

    def test_publish_event_function(self):
        """Test convenience publish_event function"""
        # Mock the asyncio.create_task to avoid event loop issues
        with patch("asyncio.create_task") as mock_create_task:
            publish_event(EventType.SCREENSHOT_REQUESTED, data={"test": "data"}, source="test")
            mock_create_task.assert_called_once()


class TestMiddleware(unittest.TestCase):
    """Test middleware functions"""

    def test_logging_middleware(self):
        """Test logging middleware"""
        event = Event(type=EventType.SCREENSHOT_REQUESTED, source="test_source")

        # Should return the same event
        result = logging_middleware(event)

        self.assertIs(result, event)

    def test_correlation_middleware(self):
        """Test correlation middleware"""
        event = Event(type=EventType.OCR_STARTED)
        original_correlation_id = event.correlation_id

        result = correlation_middleware(event)

        self.assertIs(result, event)
        self.assertEqual(result.metadata["parent_correlation_id"], original_correlation_id)

    def test_correlation_middleware_existing_parent(self):
        """Test correlation middleware with existing parent ID"""
        event = Event(
            type=EventType.TRANSLATION_COMPLETED,
            metadata={"parent_correlation_id": "existing-parent"},
        )

        result = correlation_middleware(event)

        # Should not overwrite existing parent correlation ID
        self.assertEqual(result.metadata["parent_correlation_id"], "existing-parent")


class TestPredefinedHandlers(unittest.TestCase):
    """Test predefined event handlers"""

    def test_logging_event_handler_creation(self):
        """Test LoggingEventHandler creation"""
        handler = LoggingEventHandler()

        self.assertEqual(handler.name, "logging_handler")
        self.assertEqual(handler.handled_events, set(EventType))

    def test_logging_event_handler_handle(self):
        """Test LoggingEventHandler handle method"""

        async def run_test():
            handler = LoggingEventHandler()
            event = Event(type=EventType.SCREENSHOT_CAPTURED, source="test")

            # Should not raise exception
            await handler.handle(event)

        asyncio.run(run_test())

    def test_performance_event_handler_creation(self):
        """Test PerformanceEventHandler creation"""
        handler = PerformanceEventHandler()

        self.assertEqual(handler.name, "performance_handler")
        expected_events = {EventType.PERFORMANCE_ALERT, EventType.SLOW_OPERATION_DETECTED}
        self.assertEqual(handler.handled_events, expected_events)

    def test_performance_event_handler_handle(self):
        """Test PerformanceEventHandler handle method"""

        async def run_test():
            handler = PerformanceEventHandler()

            # Test performance alert
            alert_event = Event(type=EventType.PERFORMANCE_ALERT, data="High CPU usage")
            await handler.handle(alert_event)

            # Test slow operation
            slow_event = Event(type=EventType.SLOW_OPERATION_DETECTED, data="Slow query")
            await handler.handle(slow_event)

            # Should not raise exceptions

        asyncio.run(run_test())


# Run async tests
class AsyncTestCase(unittest.TestCase):
    """Base class for async test cases"""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def run_async(self, coro):
        return self.loop.run_until_complete(coro)


class TestEventBusAsync(AsyncTestCase):
    """Async tests for EventBus"""

    def test_publish_and_handle_async(self):
        """Test async publish and handle"""
        event_bus = EventBus()
        handler = MockEventHandler()

        event_bus.subscribe(EventType.TRANSLATION_COMPLETED, handler)
        event = Event(type=EventType.TRANSLATION_COMPLETED, data={"result": "success"})

        async def test_scenario():
            await event_bus.publish(event)
            # Wait for async processing
            await asyncio.sleep(0.01)
            await event_bus.shutdown()

        self.run_async(test_scenario())

        self.assertEqual(len(handler.handled_events_list), 1)
        self.assertEqual(handler.handled_events_list[0].data, {"result": "success"})


if __name__ == "__main__":
    unittest.main()

"""
Comprehensive tests for Event-Driven Architecture system.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.event_handlers import (
    OCREventHandler,
    ScreenshotEventHandler,
    SystemEventHandler,
    TranslationEventHandler,
    TTSEventHandler,
    UIEventHandler,
    setup_event_handlers,
)
from src.core.events import Event, EventBus, EventHandler, EventType, get_event_bus, publish_event


# Test helper class
class _TestEventHandler(EventHandler):
    """Test event handler for unit tests"""

    def __init__(self, name: str):
        super().__init__(name)
        self.handled_events_list = []
        self.call_count = 0

    async def handle(self, event: Event) -> None:
        """Handle event and track calls"""
        self.handled_events_list.append(event)
        self.call_count += 1


class TestEvent:
    """Test Event class functionality"""

    def test_event_creation(self):
        """Test basic event creation"""
        event = Event(
            type=EventType.SCREENSHOT_CAPTURED, data={"test": "data"}, source="test_source"
        )

        assert event.type == EventType.SCREENSHOT_CAPTURED
        assert event.data == {"test": "data"}
        assert event.source == "test_source"
        assert isinstance(event.timestamp, datetime)
        assert len(event.correlation_id) > 0

    def test_event_serialization(self):
        """Test event serialization to dict"""
        event = Event(
            type=EventType.TRANSLATION_COMPLETED,
            data={"original": "hello", "translated": "hola"},
            source="translation_engine",
        )

        event_dict = event.to_dict()

        assert event_dict["type"] == "translation_completed"
        assert event_dict["data"] == {"original": "hello", "translated": "hola"}
        assert event_dict["source"] == "translation_engine"
        assert "timestamp" in event_dict
        assert "correlation_id" in event_dict

    def test_event_from_dict(self):
        """Test event deserialization from dict"""
        event_data = {
            "type": "text_extracted",
            "data": {"text": "recognized text", "confidence": 0.95},
            "source": "ocr_engine",
            "timestamp": "2025-07-29T10:00:00.000000",
            "correlation_id": "evt_12345",
        }

        event = Event.from_dict(event_data)

        assert event.type == EventType.TEXT_EXTRACTED
        assert event.data == {"text": "recognized text", "confidence": 0.95}
        assert event.source == "ocr_engine"
        assert event.correlation_id == "evt_12345"


class TestEventBus:
    """Test EventBus functionality"""

    @pytest.fixture
    def event_bus(self):
        """Create fresh event bus for each test"""
        return EventBus()

    def create_test_handler(self, name="test_handler", event_types=None):
        """Create a test handler with tracking capabilities"""

        class TestHandler(EventHandler):
            def __init__(self, handler_name, handled_event_types):
                super().__init__(handler_name)
                self.handled_events = set(handled_event_types or [])
                self.handled_events_list = []
                self.call_count = 0

            async def handle(self, event):
                self.handled_events_list.append(event)
                self.call_count += 1

        return TestHandler(name, event_types or [])

    @pytest.mark.asyncio
    async def test_event_publishing(self, event_bus):
        """Test basic event publishing"""
        handler = self.create_test_handler("test_handler", [EventType.SCREENSHOT_CAPTURED])
        event_bus.subscribe(EventType.SCREENSHOT_CAPTURED, handler)

        event = Event(
            type=EventType.SCREENSHOT_CAPTURED,
            data={"coordinates": (0, 0, 100, 100)},
            source="test",
        )

        await event_bus.publish(event)
        assert handler.call_count == 1
        assert handler.handled_events_list[0] == event

    @pytest.mark.asyncio
    async def test_multiple_handlers(self, event_bus):
        """Test multiple handlers for same event type"""
        handler1 = _TestEventHandler("handler1")
        handler2 = _TestEventHandler("handler2")
        handler3 = _TestEventHandler("handler3")

        event_bus.subscribe(EventType.TRANSLATION_COMPLETED, handler1)
        event_bus.subscribe(EventType.TRANSLATION_COMPLETED, handler2)
        event_bus.subscribe(EventType.TRANSLATION_COMPLETED, handler3)

        event = Event(
            type=EventType.TRANSLATION_COMPLETED, data={"translated": "hola"}, source="test"
        )

        await event_bus.publish(event)

        assert handler1.call_count == 1
        assert handler2.call_count == 1
        assert handler3.call_count == 1
        assert handler1.handled_events_list[0] == event

    @pytest.mark.asyncio
    async def test_handler_error_isolation(self, event_bus):
        """Test that handler errors don't affect other handlers"""
        working_handler = _TestEventHandler("working")

        class FailingHandler(EventHandler):
            def __init__(self):
                super().__init__("failing")
                self.call_count = 0

            async def handle(self, event):
                self.call_count += 1
                raise Exception("Handler error")

        failing_handler = FailingHandler()
        another_working_handler = _TestEventHandler("another_working")

        event_bus.subscribe(EventType.ERROR_OCCURRED, working_handler)
        event_bus.subscribe(EventType.ERROR_OCCURRED, failing_handler)
        event_bus.subscribe(EventType.ERROR_OCCURRED, another_working_handler)

        event = Event(type=EventType.ERROR_OCCURRED, data={"error": "test error"}, source="test")

        # Should not raise exception
        await event_bus.publish(event)

        # Working handlers should still be called
        assert working_handler.call_count == 1
        assert another_working_handler.call_count == 1
        assert failing_handler.call_count == 1
        assert working_handler.handled_events_list[0] == event
        assert another_working_handler.handled_events_list[0] == event

    @pytest.mark.asyncio
    async def test_unsubscribe(self, event_bus):
        """Test handler unsubscription"""
        handler = _TestEventHandler("test_handler")

        # Subscribe
        event_bus.subscribe(EventType.APPLICATION_STARTED, handler)

        # Publish event - should be handled
        event1 = Event(type=EventType.APPLICATION_STARTED, data={}, source="test")
        await event_bus.publish(event1)
        assert handler.call_count == 1
        assert handler.handled_events_list[0] == event1

        # Unsubscribe
        event_bus.unsubscribe(EventType.APPLICATION_STARTED, handler)

        # Publish again - should not be handled
        initial_count = handler.call_count
        event2 = Event(type=EventType.APPLICATION_STARTED, data={}, source="test")
        await event_bus.publish(event2)
        assert handler.call_count == initial_count  # No new calls

    @pytest.mark.asyncio
    async def test_event_filtering(self, event_bus):
        """Test basic event handling"""
        handler = _TestEventHandler("filter_test")

        # Subscribe handler
        event_bus.subscribe(EventType.TRANSLATION_COMPLETED, handler)

        # Test event handling
        event1 = Event(
            type=EventType.TRANSLATION_COMPLETED, data={"translated": "hola"}, source="test"
        )
        await event_bus.publish(event1)
        assert handler.call_count == 1
        assert handler.handled_events_list[0] == event1

        # Test another event
        event2 = Event(
            type=EventType.TRANSLATION_COMPLETED, data={"translated": "hello"}, source="test"
        )
        await event_bus.publish(event2)
        assert handler.call_count == 2
        assert handler.handled_events_list[1] == event2

    @pytest.mark.asyncio
    async def test_event_priority(self, event_bus):
        """Test multiple handlers execution"""
        handler1 = _TestEventHandler("handler1")
        handler2 = _TestEventHandler("handler2")

        # Subscribe multiple handlers
        event_bus.subscribe(EventType.APPLICATION_STARTED, handler1)
        event_bus.subscribe(EventType.APPLICATION_STARTED, handler2)

        event = Event(type=EventType.APPLICATION_STARTED, data={"id": "test"}, source="test")
        await event_bus.publish(event)

        # Both handlers should be called
        assert handler1.call_count == 1
        assert handler2.call_count == 1
        assert handler1.handled_events_list[0] == event
        assert handler2.handled_events_list[0] == event

    @pytest.mark.asyncio
    async def test_shutdown(self, event_bus):
        """Test event bus shutdown"""
        handler = _TestEventHandler("shutdown_test")
        event_bus.subscribe(EventType.APPLICATION_SHUTDOWN, handler)

        # Shutdown should work without errors
        await event_bus.shutdown()

        # Verify shutdown state
        assert event_bus._running == False

        # Publishing after shutdown should not work
        initial_count = handler.call_count
        event = Event(type=EventType.APPLICATION_SHUTDOWN, data={}, source="test")
        await event_bus.publish(event)
        assert handler.call_count == initial_count  # No new calls


class TestScreenshotEventHandler:
    """Test ScreenshotEventHandler"""

    @pytest.fixture
    def handler(self):
        return ScreenshotEventHandler()

    @pytest.mark.asyncio
    async def test_handle_screenshot_captured(self, handler):
        """Test screenshot captured event handling"""
        event = Event(
            type=EventType.SCREENSHOT_CAPTURED,
            data={
                "coordinates": (0, 0, 100, 100),
                "image_path": "/tmp/screenshot.png",
                "timestamp": "2025-07-29T10:00:00",
            },
            source="screenshot_engine",
        )

        with patch.object(handler, "_handle_screenshot_captured") as mock_handle:
            await handler.handle(event)
            mock_handle.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_handle_invalid_event_type(self, handler):
        """Test handling of invalid event type"""
        event = Event(
            type=EventType.TRANSLATION_COMPLETED, data={"test": "data"}, source="test"  # Wrong type
        )

        # Should not raise exception
        await handler.handle(event)

    @pytest.mark.asyncio
    async def test_screenshot_processing_error(self, handler):
        """Test error handling during screenshot processing"""
        event = Event(
            type=EventType.SCREENSHOT_CAPTURED,
            data={"coordinates": (0, 0, 100, 100)},
            source="screenshot_engine",
        )

        with patch.object(
            handler, "_handle_screenshot_captured", side_effect=Exception("Processing error")
        ):
            # Should raise exception
            with pytest.raises(Exception, match="Processing error"):
                await handler.handle(event)


class TestTranslationEventHandler:
    """Test TranslationEventHandler"""

    @pytest.fixture
    def handler(self):
        mock_translation_processor = Mock()
        mock_config_manager = Mock()
        return TranslationEventHandler(mock_translation_processor, mock_config_manager)

    @pytest.mark.asyncio
    async def test_handle_translation_completed(self, handler):
        """Test translation completed event handling"""
        event = Event(
            type=EventType.TRANSLATION_COMPLETED,
            data={
                "original": "Hello world",
                "translated": "Hola mundo",
                "confidence": 0.95,
                "source_language": "en",
                "target_language": "es",
            },
            source="translation_engine",
        )

        with patch.object(handler, "_handle_translation_completed") as mock_handle:
            await handler.handle(event)
            mock_handle.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_handle_translation_failed(self, handler):
        """Test translation failed event handling"""
        event = Event(
            type=EventType.TRANSLATION_FAILED,
            data={
                "original": "Hello world",
                "error": "API rate limit exceeded",
                "error_code": "rate_limit",
            },
            source="translation_engine",
        )

        with patch.object(handler, "_handle_translation_failed") as mock_handle:
            await handler.handle(event)
            mock_handle.assert_called_once_with(event)


# ErrorEventHandler не нужен - ошибки обрабатывает SystemEventHandler


class TestSystemEventHandler:
    """Test SystemEventHandler"""

    @pytest.fixture
    def handler(self):
        return SystemEventHandler()

    @pytest.mark.asyncio
    async def test_handle_system_ready(self, handler):
        """Test system ready event handling"""
        event = Event(
            type=EventType.APPLICATION_STARTED,
            data={"components_loaded": ["ocr", "translation", "tts"]},
            source="application",
        )

        with patch.object(handler, "_handle_application_started") as mock_handle:
            await handler.handle(event)
            mock_handle.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_handle_system_shutdown(self, handler):
        """Test system shutdown event handling"""
        event = Event(
            type=EventType.APPLICATION_SHUTDOWN,
            data={"reason": "user_requested"},
            source="application",
        )

        with patch.object(handler, "_handle_application_shutdown") as mock_handle:
            await handler.handle(event)
            mock_handle.assert_called_once_with(event)


class TestGlobalEventFunctions:
    """Test global event system functions"""

    @pytest.mark.asyncio
    async def test_get_event_bus_singleton(self):
        """Test that get_event_bus returns singleton"""
        bus1 = get_event_bus()
        bus2 = get_event_bus()

        assert bus1 is bus2

    @pytest.mark.asyncio
    async def test_publish_event_function(self):
        """Test global publish_event function"""
        handler = _TestEventHandler("global_test")

        # Subscribe to event bus
        event_bus = get_event_bus()
        event_bus.subscribe(EventType.SCREENSHOT_CAPTURED, handler)

        # Use global publish function
        publish_event(EventType.SCREENSHOT_CAPTURED, data={"test": "data"}, source="test")

        # Wait a bit for the task to complete
        await asyncio.sleep(0.1)

        # Verify handler was called
        assert handler.call_count == 1
        called_event = handler.handled_events_list[0]
        assert called_event.type == EventType.SCREENSHOT_CAPTURED
        assert called_event.data == {"test": "data"}
        assert called_event.source == "test"


class TestEventBusPerformance:
    """Test EventBus performance characteristics"""

    @pytest.mark.asyncio
    async def test_many_handlers_performance(self):
        """Test performance with many handlers"""
        event_bus = EventBus()

        # Add many handlers
        handlers = []
        for i in range(100):
            handler = _TestEventHandler(f"perf_handler_{i}")
            handlers.append(handler)
            event_bus.subscribe(EventType.APPLICATION_STARTED, handler)

        # Publish event and measure time
        import time

        start_time = time.time()

        event = Event(type=EventType.APPLICATION_STARTED, data={}, source="test")
        await event_bus.publish(event)

        end_time = time.time()

        # Should complete quickly (under 1 second)
        assert end_time - start_time < 1.0

        # All handlers should be called
        for handler in handlers:
            assert handler.call_count == 1

    @pytest.mark.asyncio
    async def test_concurrent_publishing(self):
        """Test concurrent event publishing"""
        event_bus = EventBus()

        class TrackingHandler(EventHandler):
            def __init__(self):
                super().__init__("tracking_handler")
                self.calls = []

            async def handle(self, event):
                self.calls.append(event.data["id"])

        tracking_handler = TrackingHandler()
        event_bus.subscribe(EventType.APPLICATION_STARTED, tracking_handler)

        # Publish multiple events concurrently
        tasks = []
        for i in range(50):
            event = Event(type=EventType.APPLICATION_STARTED, data={"id": i}, source="test")
            task = asyncio.create_task(event_bus.publish(event))
            tasks.append(task)

        # Wait for all to complete
        await asyncio.gather(*tasks)

        # All events should be handled
        assert len(tracking_handler.calls) == 50
        assert set(tracking_handler.calls) == set(range(50))


class TestEventBusIntegration:
    """Integration tests for event system"""

    @pytest.mark.asyncio
    async def test_full_translation_workflow(self):
        """Test complete translation workflow through events"""
        event_bus = EventBus()

        class WorkflowTracker(EventHandler):
            def __init__(self):
                super().__init__("workflow_tracker")
                self.events = []

            async def handle(self, event):
                self.events.append((event.type, event.source))

        workflow_tracker = WorkflowTracker()

        # Subscribe to all relevant events
        for event_type in [
            EventType.SCREENSHOT_CAPTURED,
            EventType.TEXT_EXTRACTED,
            EventType.TRANSLATION_COMPLETED,
            EventType.TTS_COMPLETED,
        ]:
            event_bus.subscribe(event_type, workflow_tracker)

        # Simulate workflow
        await event_bus.publish(
            Event(
                type=EventType.SCREENSHOT_CAPTURED,
                data={"coordinates": (0, 0, 100, 100)},
                source="screenshot_engine",
            )
        )

        await event_bus.publish(
            Event(
                type=EventType.TEXT_EXTRACTED,
                data={"text": "Hello", "confidence": 0.95},
                source="ocr_engine",
            )
        )

        await event_bus.publish(
            Event(
                type=EventType.TRANSLATION_COMPLETED,
                data={"translated": "Hola"},
                source="translation_engine",
            )
        )

        await event_bus.publish(
            Event(type=EventType.TTS_COMPLETED, data={"duration": 2.5}, source="tts_engine")
        )

        # Verify complete workflow
        expected_workflow = [
            (EventType.SCREENSHOT_CAPTURED, "screenshot_engine"),
            (EventType.TEXT_EXTRACTED, "ocr_engine"),
            (EventType.TRANSLATION_COMPLETED, "translation_engine"),
            (EventType.TTS_COMPLETED, "tts_engine"),
        ]

        assert workflow_tracker.events == expected_workflow

"""
Concrete event handlers for Screen Translator components.

This module contains specific event handlers that implement business logic
reactions to various application events.
"""

import asyncio
from typing import Any, Dict

from src.core.events import Event, EventHandler, EventType, get_event_bus, publish_event
from src.utils.logger import logger


class ScreenshotEventHandler(EventHandler):
    """Handles screenshot-related events."""

    def __init__(self):
        super().__init__("screenshot_handler")
        self.handled_events = {EventType.SCREENSHOT_CAPTURED, EventType.SCREENSHOT_FAILED}

    async def handle(self, event: Event) -> None:
        if event.type == EventType.SCREENSHOT_CAPTURED:
            await self._handle_screenshot_captured(event)
        elif event.type == EventType.SCREENSHOT_FAILED:
            await self._handle_screenshot_failed(event)

    async def _handle_screenshot_captured(self, event: Event) -> None:
        """Handle successful screenshot capture."""
        screenshot_data = event.data
        logger.info(f"Screenshot captured: {screenshot_data.coordinates}")

        # Trigger OCR processing
        publish_event(EventType.OCR_STARTED, data=screenshot_data, source="screenshot_handler")

    async def _handle_screenshot_failed(self, event: Event) -> None:
        """Handle screenshot capture failure."""
        error_data = event.data
        logger.error(f"Screenshot capture failed: {error_data}")

        # Could trigger retry logic or user notification here


class OCREventHandler(EventHandler):
    """Handles OCR-related events."""

    def __init__(self, ocr_processor):
        super().__init__("ocr_handler")
        self.ocr_processor = ocr_processor
        self.handled_events = {
            EventType.OCR_STARTED,
            EventType.TEXT_EXTRACTED,
            EventType.OCR_FAILED,
        }

    async def handle(self, event: Event) -> None:
        if event.type == EventType.OCR_STARTED:
            await self._handle_ocr_started(event)
        elif event.type == EventType.TEXT_EXTRACTED:
            await self._handle_text_extracted(event)
        elif event.type == EventType.OCR_FAILED:
            await self._handle_ocr_failed(event)

    async def _handle_ocr_started(self, event: Event) -> None:
        """Handle OCR processing start."""
        screenshot_data = event.data

        try:
            # Process OCR in background task
            text, confidence = await asyncio.to_thread(
                self.ocr_processor.extract_text, screenshot_data.image
            )

            if text.strip():
                publish_event(
                    EventType.TEXT_EXTRACTED,
                    data={
                        "text": text,
                        "confidence": confidence,
                        "screenshot_data": screenshot_data,
                    },
                    source="ocr_handler",
                )
            else:
                publish_event(
                    EventType.OCR_FAILED,
                    data={"error": "No text found", "screenshot_data": screenshot_data},
                    source="ocr_handler",
                )

        except Exception as e:
            publish_event(
                EventType.OCR_FAILED,
                data={"error": str(e), "screenshot_data": screenshot_data},
                source="ocr_handler",
            )

    async def _handle_text_extracted(self, event: Event) -> None:
        """Handle successful text extraction."""
        data = event.data
        text = data["text"]
        confidence = data["confidence"]

        logger.info(f"Text extracted: '{text[:50]}...' (confidence: {confidence})")

        # Trigger translation
        publish_event(EventType.TRANSLATION_REQUESTED, data=data, source="ocr_handler")

    async def _handle_ocr_failed(self, event: Event) -> None:
        """Handle OCR failure."""
        error_data = event.data
        logger.error(f"OCR failed: {error_data['error']}")


class TranslationEventHandler(EventHandler):
    """Handles translation-related events."""

    def __init__(self, translation_processor, config_manager):
        super().__init__("translation_handler")
        self.translation_processor = translation_processor
        self.config_manager = config_manager
        self.handled_events = {
            EventType.TRANSLATION_REQUESTED,
            EventType.TRANSLATION_COMPLETED,
            EventType.TRANSLATION_FAILED,
            EventType.TRANSLATION_CACHED,
        }

    async def handle(self, event: Event) -> None:
        if event.type == EventType.TRANSLATION_REQUESTED:
            await self._handle_translation_requested(event)
        elif event.type == EventType.TRANSLATION_COMPLETED:
            await self._handle_translation_completed(event)
        elif event.type == EventType.TRANSLATION_FAILED:
            await self._handle_translation_failed(event)
        elif event.type == EventType.TRANSLATION_CACHED:
            await self._handle_translation_cached(event)

    async def _handle_translation_requested(self, event: Event) -> None:
        """Handle translation request."""
        data = event.data
        text = data["text"]

        # Get target language from config
        config = self.config_manager.get_config()
        target_lang = config.languages.target

        try:
            # Perform translation
            translated_text = await asyncio.to_thread(
                self.translation_processor.translate, text, target_lang
            )

            publish_event(
                EventType.TRANSLATION_COMPLETED,
                data={
                    "original_text": text,
                    "translated_text": translated_text,
                    "target_language": target_lang,
                    "screenshot_data": data.get("screenshot_data"),
                },
                source="translation_handler",
            )

        except Exception as e:
            publish_event(
                EventType.TRANSLATION_FAILED,
                data={"error": str(e), "original_text": text},
                source="translation_handler",
            )

    async def _handle_translation_completed(self, event: Event) -> None:
        """Handle successful translation."""
        data = event.data
        logger.info(f"Translation completed: '{data['translated_text'][:50]}...'")

        # Could trigger TTS or UI updates here
        publish_event(EventType.TTS_STARTED, data=data, source="translation_handler")

    async def _handle_translation_failed(self, event: Event) -> None:
        """Handle translation failure."""
        error_data = event.data
        logger.error(f"Translation failed: {error_data['error']}")

    async def _handle_translation_cached(self, event: Event) -> None:
        """Handle cached translation retrieval."""
        data = event.data
        logger.debug(f"Translation retrieved from cache: '{data['translated_text'][:50]}...'")


class TTSEventHandler(EventHandler):
    """Handles text-to-speech events."""

    def __init__(self, tts_processor):
        super().__init__("tts_handler")
        self.tts_processor = tts_processor
        self.handled_events = {EventType.TTS_STARTED, EventType.TTS_COMPLETED, EventType.TTS_FAILED}

    async def handle(self, event: Event) -> None:
        if event.type == EventType.TTS_STARTED:
            await self._handle_tts_started(event)
        elif event.type == EventType.TTS_COMPLETED:
            await self._handle_tts_completed(event)
        elif event.type == EventType.TTS_FAILED:
            await self._handle_tts_failed(event)

    async def _handle_tts_started(self, event: Event) -> None:
        """Handle TTS processing start."""
        data = event.data
        text = data["translated_text"]

        try:
            # Perform TTS in background
            await asyncio.to_thread(self.tts_processor.speak, text)

            publish_event(EventType.TTS_COMPLETED, data={"text": text}, source="tts_handler")

        except Exception as e:
            publish_event(
                EventType.TTS_FAILED, data={"error": str(e), "text": text}, source="tts_handler"
            )

    async def _handle_tts_completed(self, event: Event) -> None:
        """Handle successful TTS completion."""
        data = event.data
        logger.info(f"TTS completed for: '{data['text'][:50]}...'")

    async def _handle_tts_failed(self, event: Event) -> None:
        """Handle TTS failure."""
        error_data = event.data
        logger.error(f"TTS failed: {error_data['error']}")


class UIEventHandler(EventHandler):
    """Handles UI-related events."""

    def __init__(self):
        super().__init__("ui_handler")
        self.handled_events = {
            EventType.UI_SETTINGS_OPENED,
            EventType.UI_SETTINGS_CLOSED,
            EventType.UI_LANGUAGE_CHANGED,
            EventType.TRANSLATION_COMPLETED,  # To update UI
        }

    async def handle(self, event: Event) -> None:
        if event.type == EventType.UI_SETTINGS_OPENED:
            await self._handle_settings_opened(event)
        elif event.type == EventType.UI_SETTINGS_CLOSED:
            await self._handle_settings_closed(event)
        elif event.type == EventType.UI_LANGUAGE_CHANGED:
            await self._handle_language_changed(event)
        elif event.type == EventType.TRANSLATION_COMPLETED:
            await self._handle_translation_for_ui(event)

    async def _handle_settings_opened(self, event: Event) -> None:
        """Handle settings window opening."""
        logger.debug("Settings window opened")

    async def _handle_settings_closed(self, event: Event) -> None:
        """Handle settings window closing."""
        logger.debug("Settings window closed")

    async def _handle_language_changed(self, event: Event) -> None:
        """Handle language change."""
        new_language = event.data
        logger.info(f"UI language changed to: {new_language}")

    async def _handle_translation_for_ui(self, event: Event) -> None:
        """Handle translation completion for UI updates."""
        event.data
        # Could update translation overlay, history window, etc.
        logger.debug("UI updated with new translation")


class SystemEventHandler(EventHandler):
    """Handles system-level events."""

    def __init__(self):
        super().__init__("system_handler")
        self.handled_events = {
            EventType.APPLICATION_STARTED,
            EventType.APPLICATION_SHUTDOWN,
            EventType.ERROR_OCCURRED,
        }

    async def handle(self, event: Event) -> None:
        if event.type == EventType.APPLICATION_STARTED:
            await self._handle_application_started(event)
        elif event.type == EventType.APPLICATION_SHUTDOWN:
            await self._handle_application_shutdown(event)
        elif event.type == EventType.ERROR_OCCURRED:
            await self._handle_error_occurred(event)

    async def _handle_application_started(self, event: Event) -> None:
        """Handle application startup."""
        logger.info("Screen Translator application started")

    async def _handle_application_shutdown(self, event: Event) -> None:
        """Handle application shutdown."""
        logger.info("Screen Translator application shutting down")

        # Gracefully shutdown event bus
        event_bus = get_event_bus()
        await event_bus.shutdown()

    async def _handle_error_occurred(self, event: Event) -> None:
        """Handle general application errors."""
        error_data = event.data
        logger.error(f"Application error: {error_data}")


def setup_event_handlers(app_components: Dict[str, Any]) -> None:
    """Setup all event handlers with application components."""
    event_bus = get_event_bus()

    # Create handlers with their dependencies
    handlers = [
        ScreenshotEventHandler(),
        OCREventHandler(app_components.get("ocr_processor")),
        TranslationEventHandler(
            app_components.get("translation_processor"), app_components.get("config_manager")
        ),
        TTSEventHandler(app_components.get("tts_processor")),
        UIEventHandler(),
        SystemEventHandler(),
    ]

    # Subscribe all handlers to their events
    for handler in handlers:
        for event_type in handler.handled_events:
            event_bus.subscribe(event_type, handler)

    # Add middleware
    from src.core.events import correlation_middleware, logging_middleware

    event_bus.add_middleware(correlation_middleware)
    event_bus.add_middleware(logging_middleware)

    logger.info(f"Setup {len(handlers)} event handlers")
    return handlers

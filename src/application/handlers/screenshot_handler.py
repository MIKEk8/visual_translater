"""
Screenshot event handlers.
"""

from ...domain.events.domain_events import DomainEvent, ScreenshotCaptured, TextExtracted
from ...utils.logger import logger


class ScreenshotEventHandler:
    """Handler for screenshot-related domain events."""

    def __init__(self):
        self._handlers = {
            "ScreenshotCaptured": self._handle_screenshot_captured,
            "TextExtracted": self._handle_text_extracted,
        }

    def handle(self, event: DomainEvent) -> None:
        """Handle domain event."""
        handler = self._handlers.get(event.event_type)
        if handler:
            handler(event)
        else:
            logger.warning(f"No handler for event type: {event.event_type}")

    def _handle_screenshot_captured(self, event: ScreenshotCaptured) -> None:
        """Handle screenshot captured event."""
        logger.info(
            f"Screenshot captured: {event.screenshot_id}",
            coordinates=event.coordinates,
            has_text=event.has_text,
        )

    def _handle_text_extracted(self, event: TextExtracted) -> None:
        """Handle text extracted event."""
        logger.info(
            f"Text extracted from screenshot: {event.screenshot_id}",
            text_length=len(event.text),
            confidence=event.confidence,
            language=event.language,
        )

"""
Translation event handlers.
"""

from ...domain.events.domain_events import DomainEvent, TranslationCreated
from ...utils.logger import logger


class TranslationEventHandler:
    """Handler for translation-related domain events."""

    def __init__(self):
        self._handlers = {
            "TranslationCreated": self._handle_translation_created,
        }

    def handle(self, event: DomainEvent) -> None:
        """Handle domain event."""
        handler = self._handlers.get(event.event_type)
        if handler:
            handler(event)
        else:
            logger.warning(f"No handler for event type: {event.event_type}")

    def _handle_translation_created(self, event: TranslationCreated) -> None:
        """Handle translation created event."""
        logger.info(
            f"Translation created: {event.translation_id}",
            source_language=event.source_language,
            target_language=event.target_language,
            cached=event.cached,
        )

        # Could trigger additional actions:
        # - Update statistics
        # - Send notifications
        # - Update cache metrics
        # - etc.

"""Input Event Manager - UI Event Handling"""

import logging
from typing import Any, Callable, Dict, List


class InputEventManager:
    """Manage UI events - complexity ≤ 4"""

    def __init__(self):
        self.event_handlers = {}
        self.event_history = []
        self.logger = logging.getLogger(__name__)

    def handle_event(self, event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle UI event - complexity 4"""
        if not event_type:  # +1
            return {"success": False, "error": "No event type"}

        try:
            # Log event
            self.event_history.append({"type": event_type, "data": event_data})

            # Find handler
            if event_type in self.event_handlers:  # +1
                handler = self.event_handlers[event_type]
                result = handler(event_data)  # +1
                return {"success": True, "result": result}
            else:
                return self._default_handler(event_type, event_data)  # +1

        except Exception as e:
            self.logger.error(f"Event handling error: {e}")
            return {"success": False, "error": str(e)}

    def register_handler(self, event_type: str, handler: Callable) -> None:
        """Register event handler - complexity 1"""
        self.event_handlers[event_type] = handler

    def _default_handler(self, event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Default event handler - complexity 1"""
        return {"success": True, "message": f"No specific handler for {event_type}"}

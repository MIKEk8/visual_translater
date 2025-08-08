"""Input Error Handler - UI Error Management"""

from typing import Any, Dict, List


class InputErrorHandler:
    """Handle input errors - complexity ≤ 3"""

    def __init__(self):
        self.errors = []
        self.error_counts = {"validation": 0, "processing": 0, "event": 0}

    def handle_input_error(
        self, error: Exception, input_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Handle input error - complexity 3"""
        error_type = self._classify_error(error)
        error_info = {"type": error_type, "message": str(error), "context": input_context or {}}

        self.errors.append(error_info)
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1  # +1

        return error_info

    def get_user_friendly_message(self, error_info: Dict[str, Any]) -> str:
        """Get user-friendly error message - complexity 2"""
        error_type = error_info.get("type", "unknown")

        messages = {
            "validation": "Please check your input and try again",
            "processing": "Unable to process your request",
            "event": "Action could not be completed",
        }

        return messages.get(error_type, "An error occurred")  # +1

    def _classify_error(self, error: Exception) -> str:
        """Classify error type - complexity 2"""
        if "validation" in str(error).lower():  # +1
            return "validation"
        return "processing"

"""
Stream Error Manager Component - Single Responsibility: Stream Error Handling
"""

import logging
from typing import Any, Dict, List


class StreamErrorManager:
    """Handle streaming errors - complexity ≤ 4 per method"""

    def __init__(self):
        self.errors = []
        self.error_counts = {"validation": 0, "transformation": 0, "buffer": 0, "stream": 0}
        self.logger = logging.getLogger(__name__)

    def handle_stream_error(
        self, error: Exception, error_type: str, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Handle streaming error - complexity 3"""
        error_info = {"type": error_type, "message": str(error), "context": context or {}}

        self.errors.append(error_info)
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1  # +1

        self.logger.error(f"Stream error [{error_type}]: {error_info['message']}")

        return error_info

    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary - complexity 2"""
        return {
            "total_errors": len(self.errors),
            "error_breakdown": self.error_counts.copy(),
            "recent_errors": self.errors[-5:] if len(self.errors) >= 5 else self.errors,  # +1
        }

    def suggest_recovery(self, error_type: str) -> List[str]:
        """Suggest recovery actions - complexity 3"""
        suggestions = []

        if error_type == "validation":  # +1
            suggestions.extend(["Check data format", "Verify schema compliance"])
        elif error_type == "transformation":  # +1
            suggestions.extend(["Review transformation rules", "Check data types"])
        elif error_type == "buffer":
            suggestions.extend(["Increase buffer size", "Reduce batch size"])

        return suggestions

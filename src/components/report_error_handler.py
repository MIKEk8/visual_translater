"""Report Error Handler - Report Error Management"""

from typing import Any, Dict, List


class ReportErrorHandler:
    """Handle report errors - complexity ≤ 3"""

    def __init__(self):
        self.errors = []

    def handle_format_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle formatting error - complexity 3"""
        error_info = {"type": "format_error", "message": str(error), "context": context or {}}

        self.errors.append(error_info)

        if "data_type" in context:  # +1
            error_info["suggestion"] = f"Check {context['data_type']} format"

        return error_info

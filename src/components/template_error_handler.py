"""
Template Error Handler Component - Single Responsibility: Template Error Handling
"""

import logging
from typing import Any, Dict, List


class TemplateErrorHandler:
    """Handle template rendering errors and provide diagnostics"""

    def __init__(self):
        self.errors = []
        self.logger = logging.getLogger(__name__)

    def handle_error(
        self, error: Exception, template: str, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Handle template error - complexity 3"""
        context = context or {}

        error_info = {
            "error_type": type(error).__name__,
            "message": str(error),
            "template": template[:100] if len(template) > 100 else template,  # +1
            "context": context,
        }

        self.errors.append(error_info)
        self.logger.error(f"Template error: {error_info['message']}")

        return error_info

    def generate_error_report(self) -> Dict[str, Any]:
        """Generate error report - complexity 2"""
        if not self.errors:  # +1
            return {"total_errors": 0}

        return {"total_errors": len(self.errors), "errors": self.errors.copy()}

    def suggest_fixes(self, error_info: Dict[str, Any]) -> List[str]:
        """Suggest error fixes - complexity 3"""
        suggestions = []
        error_type = error_info.get("error_type", "")

        if "not found" in error_info.get("message", "").lower():  # +1
            suggestions.append("Check variable name spelling in template")
            suggestions.append("Ensure variable exists in provided data")

        if error_type == "KeyError":  # +1
            suggestions.append("Verify data structure matches template variables")

        if not suggestions:  # +1
            suggestions.append("Check template syntax and data binding")

        return suggestions

    def clear_errors(self) -> int:
        """Clear all errors - complexity 1"""
        count = len(self.errors)
        self.errors.clear()
        return count

"""
Config Error Collector Component - Single Responsibility: Error Collection
"""

from typing import Any, Dict, List


class ConfigErrorCollector:
    """Collect and categorize configuration validation errors"""

    def __init__(self):
        self.errors = {}

    def collect_errors(self, category: str, errors: List[str]) -> None:
        """Collect errors by category - complexity 2"""
        if category not in self.errors:  # +1
            self.errors[category] = []
        self.errors[category].extend(errors)

    def generate_report(self) -> Dict[str, Any]:
        """Generate error report - complexity 2"""
        total_errors = sum(len(error_list) for error_list in self.errors.values())
        return {"total_errors": total_errors, "errors_by_category": self.errors.copy()}

    def categorize_errors(self, errors: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize errors by severity - complexity 2"""
        categorized = {"high": [], "medium": [], "low": []}
        for error in errors:  # +1
            severity = error.get("severity", "medium")
            if severity in categorized:
                categorized[severity].append(error)
        return categorized

    def get_total_errors(self) -> int:
        """Get total error count - complexity 1"""
        return sum(len(error_list) for error_list in self.errors.values())

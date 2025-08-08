"""Refactored Format Report Data - Main Coordinator"""

from typing import Any, Dict, Optional

from .report_aggregator import ReportAggregator
from .report_data_validator import ReportDataValidator
from .report_error_handler import ReportErrorHandler
from .report_formatter import ReportFormatter


class RefactoredFormatReportData:
    """Main coordinator for report formatting - complexity ≤ 5"""

    def __init__(self):
        self.validator = ReportDataValidator()
        self.formatter = ReportFormatter()
        self.aggregator = ReportAggregator()
        self.error_handler = ReportErrorHandler()

    def format_report_data(
        self, data: Dict[str, Any], options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Format complete report data - complexity 5"""
        options = options or {}

        try:
            # Step 1: Validate data
            is_valid, errors = self.validator.validate_report_data(data)
            if not is_valid:  # +1
                return {"success": False, "stage": "validation", "errors": errors}

            # Step 2: Aggregate if requested
            if options.get("aggregations"):  # +1
                agg_result = self.aggregator.aggregate_data(
                    data.get("records", []), options["aggregations"]
                )
                if not agg_result["success"]:  # +1
                    return {"success": False, "stage": "aggregation", "error": agg_result["error"]}
                data["aggregated"] = agg_result["aggregations"]

            # Step 3: Format data
            format_type = options.get("format", "json")
            format_result = self.formatter.format_data(data, format_type)

            if not format_result["success"]:  # +1
                return {"success": False, "stage": "formatting", "error": format_result["error"]}

            return {
                "success": True,
                "formatted_data": format_result["formatted_data"],
                "stage": "completed",
            }

        except Exception as e:  # +1
            error_info = self.error_handler.handle_format_error(
                e, {"data_type": type(data).__name__}
            )
            return {"success": False, "error": str(e), "stage": "error"}

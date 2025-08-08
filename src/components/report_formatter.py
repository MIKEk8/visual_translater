"""Report Formatter - Report Data Formatting"""

import json
from typing import Any, Dict, List


class ReportFormatter:
    """Format report data - complexity ≤ 4"""

    def __init__(self):
        self.format_options = {}

    def format_data(self, data: Dict[str, Any], format_type: str) -> Dict[str, Any]:
        """Format report data - complexity 4"""
        if not data:  # +1
            return {"success": False, "error": "No data to format"}

        try:
            if format_type == "json":  # +1
                formatted = json.dumps(data, indent=2)
            elif format_type == "csv":  # +1
                formatted = self._format_as_csv(data)
            elif format_type == "xml":  # +1
                formatted = self._format_as_xml(data)
            else:
                formatted = str(data)

            return {"success": True, "formatted_data": formatted}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _format_as_csv(self, data: Dict[str, Any]) -> str:
        """Format as CSV - complexity 2"""
        if "records" not in data:  # +1
            return ""
        return ",".join(str(r) for r in data["records"])

    def _format_as_xml(self, data: Dict[str, Any]) -> str:
        """Format as XML - complexity 2"""
        if "records" not in data:  # +1
            return "<data></data>"
        return f'<data>{data["records"]}</data>'

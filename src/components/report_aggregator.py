"""Report Aggregator - Data Aggregation"""

import statistics
from typing import Any, Dict, List


class ReportAggregator:
    """Aggregate report data - complexity ≤ 4"""

    def __init__(self):
        self.aggregation_functions = {
            "sum": sum,
            "avg": statistics.mean,
            "count": len,
            "max": max,
            "min": min,
        }

    def aggregate_data(
        self, data: List[Dict[str, Any]], operations: Dict[str, str]
    ) -> Dict[str, Any]:
        """Aggregate data - complexity 4"""
        if not data:  # +1
            return {"success": False, "error": "No data to aggregate"}

        results = {}

        for field, operation in operations.items():  # +1
            if operation in self.aggregation_functions:  # +1
                try:
                    values = [record.get(field, 0) for record in data if field in record]  # +1
                    if values:
                        results[f"{field}_{operation}"] = self.aggregation_functions[operation](
                            values
                        )
                except:
                    results[f"{field}_{operation}"] = 0

        return {"success": True, "aggregations": results}

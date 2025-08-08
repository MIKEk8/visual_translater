"""Report Data Validator - Report Data Validation"""

from typing import Any, Dict, List


class ReportDataValidator:
    """Validate report data - complexity ≤ 3"""

    def __init__(self):
        self.validation_errors = []

    def validate_report_data(self, data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate report data - complexity 3"""
        self.validation_errors.clear()

        if not data:  # +1
            self.validation_errors.append("Empty report data")
            return False, self.validation_errors

        if "records" not in data:  # +1
            self.validation_errors.append("No records in report data")
            return False, self.validation_errors

        for record in data["records"]:  # +1
            if not self._validate_record(record):
                return False, self.validation_errors

        return True, []

    def _validate_record(self, record: Dict[str, Any]) -> bool:
        """Validate individual record - complexity 2"""
        if not isinstance(record, dict):  # +1
            self.validation_errors.append("Invalid record format")
            return False
        return True

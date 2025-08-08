"""
Stream Validator Component - Single Responsibility: Stream Data Validation
"""

import logging
from typing import Any, Dict, Iterator, List, Optional


class StreamValidator:
    """Validate incoming data streams - complexity ≤ 3 per method"""

    def __init__(self):
        self.validation_rules = {}
        self.errors = []
        self.logger = logging.getLogger(__name__)

    def validate_stream(self, data_stream: Iterator[Dict[str, Any]]) -> tuple[bool, List[str]]:
        """Validate data stream - complexity 3"""
        self.errors.clear()
        valid_count = 0
        total_count = 0

        try:
            for item in data_stream:  # +1
                total_count += 1
                if self._validate_item(item):  # +1
                    valid_count += 1

            if total_count == 0:  # +1
                self.errors.append("Empty data stream")
                return False, self.errors

        except Exception as e:
            self.errors.append(f"Stream validation error: {str(e)}")
            return False, self.errors

        success_rate = valid_count / total_count if total_count > 0 else 0
        return success_rate > 0.8, self.errors  # 80% threshold

    def validate_stream_format(self, stream_metadata: Dict[str, Any]) -> bool:
        """Validate stream format - complexity 2"""
        required_fields = ["format", "encoding", "schema"]

        for field in required_fields:  # +1
            if field not in stream_metadata:
                self.errors.append(f"Missing required field: {field}")
                return False

        return True

    def set_validation_rules(self, rules: Dict[str, Any]) -> None:
        """Set validation rules - complexity 1"""
        self.validation_rules = rules.copy() if rules else {}

    def _validate_item(self, item: Dict[str, Any]) -> bool:
        """Validate individual item - complexity 2"""
        if not isinstance(item, dict):  # +1
            self.errors.append("Item must be dictionary")
            return False
        return True

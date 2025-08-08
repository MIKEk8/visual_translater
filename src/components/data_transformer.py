"""
Data Transformer Component - Single Responsibility: Stream Data Transformation
"""

import json
from typing import Any, Callable, Dict, Iterator, List


class DataTransformer:
    """Transform streaming data - complexity ≤ 4 per method"""

    def __init__(self):
        self.transformations = []
        self.transform_stats = {"processed": 0, "errors": 0}

    def transform_stream(
        self, data_stream: Iterator[Dict[str, Any]], transformations: List[Callable] = None
    ) -> Iterator[Dict[str, Any]]:
        """Transform data stream - complexity 4"""
        transformations = transformations or self.transformations

        for item in data_stream:  # +1
            try:
                transformed_item = item.copy()

                for transform_func in transformations:  # +1
                    if callable(transform_func):  # +1
                        transformed_item = transform_func(transformed_item)

                self.transform_stats["processed"] += 1
                yield transformed_item

            except Exception as e:  # +1
                self.transform_stats["errors"] += 1
                self.logger.error(f"Transformation error: {e}")
                # Yield original item on transformation failure
                yield item

    def apply_mapping(self, data: Dict[str, Any], field_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Apply field mapping - complexity 3"""
        if not field_mapping:  # +1
            return data

        mapped_data = {}
        for old_field, new_field in field_mapping.items():  # +1
            if old_field in data:  # +1
                mapped_data[new_field] = data[old_field]
            else:
                mapped_data[new_field] = None

        return mapped_data

    def filter_stream(
        self, data_stream: Iterator[Dict[str, Any]], filter_criteria: Dict[str, Any]
    ) -> Iterator[Dict[str, Any]]:
        """Filter stream data - complexity 3"""
        for item in data_stream:  # +1
            if self._matches_criteria(item, filter_criteria):  # +1
                yield item

    def get_transform_stats(self) -> Dict[str, int]:
        """Get transformation statistics - complexity 1"""
        return self.transform_stats.copy()

    def _matches_criteria(self, item: Dict[str, Any], criteria: Dict[str, Any]) -> bool:
        """Check if item matches filter criteria - complexity 2"""
        for key, expected_value in criteria.items():  # +1
            if key not in item or item[key] != expected_value:
                return False
        return True

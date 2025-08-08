"""
Batch Item Validator Component - Single Responsibility: Batch Item Validation
Extracted from _process_batch_item (complexity 16 → 3 per method)
"""

import logging
from typing import Any, Dict, List, Optional, Tuple


class BatchItemValidator:
    """
    Single Responsibility: Validate and preprocess batch items
    All methods ≤ 3 complexity
    """

    def __init__(self):
        self.validation_errors = []
        self.required_fields = ["id", "type"]
        self.valid_item_types = {"data_record", "file_record", "batch_command", "metadata"}
        self.logger = logging.getLogger(__name__)

    def validate_item(self, item: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate batch item structure and content
        Complexity: 3
        """
        self.validation_errors.clear()

        # Check if item exists and is a dict
        if not item or not isinstance(item, dict):  # +1
            self.validation_errors.append("Item must be a non-empty dictionary")
            return False, self.validation_errors

        # Check required fields
        if not self._check_required_fields(item):  # +1
            return False, self.validation_errors

        # Check item type validity
        if not self._check_item_type(item):  # +1
            return False, self.validation_errors

        return True, []

    def preprocess_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess item for batch processing
        Complexity: 3
        """
        if not item:  # +1
            return {}

        processed_item = item.copy()

        # Add processing metadata
        processed_item["processed"] = True
        processed_item["validation_status"] = "validated"

        # Normalize item type
        if "type" in processed_item:  # +1
            processed_item["type"] = processed_item["type"].lower().strip()

        # Ensure ID is string
        if "id" in processed_item:  # +1
            processed_item["id"] = str(processed_item["id"])

        return processed_item

    def check_item_requirements(
        self, item: Dict[str, Any], requirements: Dict[str, Any] = None
    ) -> Tuple[bool, List[str]]:
        """
        Check item against specific batch requirements
        Complexity: 3
        """
        errors = []
        requirements = requirements or {}

        # Check size requirements
        if "max_content_size" in requirements:  # +1
            content_size = self._calculate_item_size(item)
            if content_size > requirements["max_content_size"]:
                errors.append(
                    f"Item content size {content_size} exceeds maximum {requirements['max_content_size']}"
                )

        # Check required content fields
        if "required_content_fields" in requirements:  # +1
            content = item.get("content", {})
            for field in requirements["required_content_fields"]:
                if field not in content:
                    errors.append(f"Required content field '{field}' is missing")

        # Check format requirements
        if "allowed_formats" in requirements and "format" in item:  # +1
            if item["format"] not in requirements["allowed_formats"]:
                errors.append(f"Item format '{item['format']}' not in allowed formats")

        return len(errors) == 0, errors

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get validation summary - complexity 1"""
        return {
            "total_errors": len(self.validation_errors),
            "errors": self.validation_errors.copy(),
            "has_errors": len(self.validation_errors) > 0,
        }

    def clear_validation_errors(self) -> int:
        """Clear validation errors - complexity 1"""
        count = len(self.validation_errors)
        self.validation_errors.clear()
        return count

    def set_required_fields(self, fields: List[str]) -> None:
        """Set required fields for validation - complexity 1"""
        self.required_fields = fields.copy() if fields else []

    def _check_required_fields(self, item: Dict[str, Any]) -> bool:
        """Check if all required fields are present - complexity 2"""
        for field in self.required_fields:  # +1
            if field not in item or item[field] is None:
                self.validation_errors.append(f"Required field '{field}' is missing or null")
                return False
        return True

    def _check_item_type(self, item: Dict[str, Any]) -> bool:
        """Check if item type is valid - complexity 2"""
        item_type = item.get("type", "").lower().strip()

        if item_type not in self.valid_item_types:  # +1
            self.validation_errors.append(
                f"Invalid item type '{item_type}'. Allowed types: {', '.join(self.valid_item_types)}"
            )
            return False

        return True

    def _calculate_item_size(self, item: Dict[str, Any]) -> int:
        """Calculate approximate item size - complexity 2"""
        try:
            import sys

            return sys.getsizeof(str(item))
        except Exception:  # +1
            # Fallback calculation
            return len(str(item))

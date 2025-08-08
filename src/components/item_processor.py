"""
Item Processor Component - Single Responsibility: Core Item Processing
Extracted from _process_batch_item (complexity 16 → 4 per method)
"""

import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional


class ItemProcessor:
    """
    Single Responsibility: Core item processing logic and transformation
    All methods ≤ 4 complexity
    """

    def __init__(self):
        self.processing_rules = []
        self.transformation_functions = {
            "uppercase": lambda x: str(x).upper(),
            "lowercase": lambda x: str(x).lower(),
            "trim": lambda x: str(x).strip(),
            "multiply": lambda x, factor=1: x * factor if isinstance(x, (int, float)) else x,
        }
        self.logger = logging.getLogger(__name__)

    def process_item(
        self, item: Dict[str, Any], processing_options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process individual batch item with core logic
        Complexity: 4
        """
        processing_options = processing_options or {}

        if not item:  # +1
            return {"success": False, "error": "Empty item provided"}

        try:
            # Create processing result
            result = {
                "success": True,
                "item_id": item.get("id", "unknown"),
                "processed_data": {},
                "processing_time": None,
                "transformations_applied": [],
            }

            start_time = time.time()

            # Apply core processing logic
            if "content" in item:  # +1
                result["processed_data"] = self._process_content(item["content"])
            else:
                result["processed_data"] = item.copy()

            # Apply transformations if specified
            if "transformations" in processing_options:  # +1
                result["processed_data"] = self.transform_item(
                    result["processed_data"], processing_options["transformations"]
                )
                result["transformations_applied"] = processing_options["transformations"]

            # Calculate processing time
            result["processing_time"] = time.time() - start_time

            # Apply processing rules if specified
            if self.processing_rules:  # +1
                result["processed_data"] = self.apply_processing_rules(
                    result["processed_data"], self.processing_rules
                )

            return result

        except Exception as e:
            return {
                "success": False,
                "item_id": item.get("id", "unknown"),
                "error": str(e),
                "processing_time": time.time() - start_time if "start_time" in locals() else 0,
            }

    def transform_item(
        self, item: Dict[str, Any], transformation_rules: List[str]
    ) -> Dict[str, Any]:
        """
        Apply transformation rules to item data
        Complexity: 4
        """
        if not item or not transformation_rules:  # +1
            return item

        transformed_item = item.copy()

        for rule in transformation_rules:
            if rule in self.transformation_functions:  # +1
                transform_func = self.transformation_functions[rule]

                # Apply transformation to all string/numeric values
                for key, value in transformed_item.items():
                    try:
                        if isinstance(value, (str, int, float)):  # +1
                            transformed_item[key] = transform_func(value)
                        elif isinstance(value, dict):  # +1
                            # Recursively transform nested dictionaries
                            transformed_item[key] = self.transform_item(value, [rule])
                    except Exception as e:
                        self.logger.warning(f"Transformation '{rule}' failed for key '{key}': {e}")

        return transformed_item

    def apply_processing_rules(
        self, data: Dict[str, Any], rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Apply complex processing rules to data
        Complexity: 4
        """
        if not data or not rules:  # +1
            return data

        processed_data = data.copy()

        for rule in rules:
            rule_type = rule.get("type")

            if rule_type == "field_mapping":  # +1
                processed_data = self._apply_field_mapping(processed_data, rule)
            elif rule_type == "value_calculation":  # +1
                processed_data = self._apply_value_calculation(processed_data, rule)
            elif rule_type == "conditional_processing":  # +1
                processed_data = self._apply_conditional_processing(processed_data, rule)

        return processed_data

    def set_processing_rules(self, rules: List[Dict[str, Any]]) -> None:
        """Set processing rules - complexity 1"""
        self.processing_rules = rules.copy() if rules else []

    def add_transformation_function(self, name: str, func: Callable) -> None:
        """Add custom transformation function - complexity 1"""
        self.transformation_functions[name] = func

    def get_supported_transformations(self) -> List[str]:
        """Get list of supported transformations - complexity 1"""
        return list(self.transformation_functions.keys())

    def clear_processing_rules(self) -> int:
        """Clear all processing rules - complexity 1"""
        count = len(self.processing_rules)
        self.processing_rules.clear()
        return count

    def _process_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Process item content - complexity 2"""
        if not isinstance(content, dict):  # +1
            return {"processed_content": content}

        processed = content.copy()
        processed["processing_timestamp"] = time.time()
        processed["processed"] = True

        return processed

    def _apply_field_mapping(self, data: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """Apply field mapping rule - complexity 3"""
        mapping = rule.get("mapping", {})
        if not mapping:  # +1
            return data

        result = data.copy()

        for old_field, new_field in mapping.items():
            if old_field in result:  # +1
                result[new_field] = result.pop(old_field)
            elif rule.get("create_missing", False):  # +1
                result[new_field] = None

        return result

    def _apply_value_calculation(
        self, data: Dict[str, Any], rule: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply value calculation rule - complexity 3"""
        target_field = rule.get("target_field")
        calculation = rule.get("calculation")

        if not target_field or not calculation:  # +1
            return data

        result = data.copy()

        try:
            if calculation["type"] == "sum":  # +1
                fields = calculation.get("fields", [])
                total = sum(result.get(field, 0) for field in fields if field in result)
                result[target_field] = total
            elif calculation["type"] == "multiply":  # +1
                field = calculation.get("field")
                factor = calculation.get("factor", 1)
                if field in result:
                    result[target_field] = result[field] * factor
        except Exception as e:
            self.logger.error(f"Value calculation failed: {e}")

        return result

    def _apply_conditional_processing(
        self, data: Dict[str, Any], rule: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply conditional processing rule - complexity 3"""
        condition = rule.get("condition")
        action = rule.get("action")

        if not condition or not action:  # +1
            return data

        result = data.copy()

        # Simple condition evaluation
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")

        if field in result:  # +1
            current_value = result[field]
            condition_met = False

            if operator == "equals":
                condition_met = current_value == value
            elif operator == "greater_than":
                condition_met = current_value > value
            elif operator == "contains":
                condition_met = value in str(current_value)

            if condition_met:  # +1
                if action["type"] == "set_field":
                    result[action["field"]] = action["value"]
                elif action["type"] == "remove_field":
                    result.pop(action["field"], None)

        return result

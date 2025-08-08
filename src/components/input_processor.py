"""Input Processor - UI Input Processing"""

from typing import Any, Callable, Dict, List, Optional


class InputProcessor:
    """Process user input - complexity ≤ 4"""

    def __init__(self):
        self.processors = {}
        self.processed_count = 0

    def process_input(
        self, input_data: Dict[str, Any], processing_rules: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Process input data - complexity 4"""
        if not input_data:  # +1
            return {"success": False, "error": "No input data"}

        try:
            result = input_data.copy()
            rules = processing_rules or {}

            # Apply transformations
            if "transforms" in rules:  # +1
                for field, transform in rules["transforms"].items():
                    if field in result:  # +1
                        result[field] = self._apply_transform(result[field], transform)

            # Apply filters
            if "filters" in rules:  # +1
                result = {k: v for k, v in result.items() if k in rules["filters"]}

            self.processed_count += 1
            return {"success": True, "data": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _apply_transform(self, value: Any, transform: str) -> Any:
        """Apply transformation - complexity 2"""
        if transform == "uppercase":
            return str(value).upper()
        elif transform == "lowercase":  # +1
            return str(value).lower()
        return value

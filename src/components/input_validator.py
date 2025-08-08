"""Input Validator - UI Input Validation"""

import re
from typing import Any, Dict, List, Optional


class InputValidator:
    """Validate user input - complexity ≤ 3"""

    def __init__(self):
        self.validation_rules = {
            "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "phone": r"^\+?1?-?\d{3}-?\d{3}-?\d{4}$",
            "password": r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d@$!%*?&]{8,}$",
        }
        self.errors = []

    def validate_input(
        self, input_data: Dict[str, Any], validation_schema: Dict[str, Any] = None
    ) -> tuple[bool, List[str]]:
        """Validate user input - complexity 3"""
        self.errors.clear()

        if not input_data:  # +1
            self.errors.append("Empty input data")
            return False, self.errors

        schema = validation_schema or {}

        for field, rules in schema.items():  # +1
            if field in input_data:
                if not self._validate_field(input_data[field], rules):  # +1
                    return False, self.errors

        return True, []

    def sanitize_input(self, input_value: str) -> str:
        """Sanitize input value - complexity 2"""
        if not isinstance(input_value, str):  # +1
            return str(input_value)
        return input_value.strip().replace("<", "&lt;").replace(">", "&gt;")

    def _validate_field(self, value: Any, rules: Dict[str, Any]) -> bool:
        """Validate individual field - complexity 2"""
        if rules.get("required") and not value:  # +1
            self.errors.append(f"Field is required")
            return False
        return True

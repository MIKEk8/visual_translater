"""
Config Value Validator Component - Single Responsibility: Value Validation
Extracted from validate_configuration (complexity 15 → 4 per method)
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Union


class ConfigValueValidator:
    """
    Single Responsibility: Validate configuration values and constraints
    All methods ≤ 4 complexity
    """

    def __init__(self):
        self.validation_errors = []
        self.constraints = {
            "port": {"min": 1024, "max": 65535},
            "timeout": {"min": 1, "max": 3600},
            "version": {"pattern": r"^\d+\.\d+\.\d+$"},
        }

    def validate_values(
        self, config: Dict[str, Any], constraints: Dict[str, Any] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate configuration values against constraints
        Complexity: 4
        """
        self.validation_errors.clear()
        constraints = constraints or self.constraints

        if not config:  # +1
            self.validation_errors.append("Empty configuration provided")
            return False, self.validation_errors

        # Check numeric constraints
        if not self._validate_numeric_constraints(config, constraints):  # +1
            return False, self.validation_errors

        # Check string patterns
        if not self._validate_string_patterns(config, constraints):  # +1
            return False, self.validation_errors

        # Check custom constraints
        if not self._validate_custom_constraints(config, constraints):  # +1
            return False, self.validation_errors

        return len(self.validation_errors) == 0, self.validation_errors

    def check_constraints(self, value: Any, constraint_def: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check individual value against constraint definition
        Complexity: 4
        """
        # Check minimum value
        if "min" in constraint_def:  # +1
            if isinstance(value, (int, float)) and value < constraint_def["min"]:
                return False, f"Value {value} below minimum {constraint_def['min']}"

        # Check maximum value
        if "max" in constraint_def:  # +1
            if isinstance(value, (int, float)) and value > constraint_def["max"]:
                return False, f"Value {value} above maximum {constraint_def['max']}"

        # Check pattern matching
        if "pattern" in constraint_def:  # +1
            if isinstance(value, str):
                if not re.match(constraint_def["pattern"], value):
                    return (
                        False,
                        f"Value '{value}' does not match pattern {constraint_def['pattern']}",
                    )

        # Check allowed values
        if "allowed_values" in constraint_def:  # +1
            if value not in constraint_def["allowed_values"]:
                return (
                    False,
                    f"Value '{value}' not in allowed values {constraint_def['allowed_values']}",
                )

        return True, ""

    def verify_ranges(
        self,
        config: Dict[str, Any],
        field_name: str,
        min_val: Union[int, float] = None,
        max_val: Union[int, float] = None,
    ) -> bool:
        """
        Verify value ranges for specific field
        Complexity: 4
        """
        if field_name not in config:  # +1
            return True  # Field not present, no range to check

        value = config[field_name]

        if not isinstance(value, (int, float)):  # +1
            self.validation_errors.append(
                f"Field '{field_name}' must be numeric for range checking"
            )
            return False

        if min_val is not None and value < min_val:  # +1
            self.validation_errors.append(
                f"Field '{field_name}' value {value} below minimum {min_val}"
            )
            return False

        if max_val is not None and value > max_val:  # +1
            self.validation_errors.append(
                f"Field '{field_name}' value {value} above maximum {max_val}"
            )
            return False

        return True

    def validate_string_formats(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate string field formats
        Complexity: 3
        """
        format_errors = []

        # Validate version format
        if "version" in config:  # +1
            version = config["version"]
            if isinstance(version, str):
                if not re.match(r"^\d+\.\d+\.\d+$", version):
                    format_errors.append(
                        f"Version '{version}' must follow semantic versioning (e.g., 1.0.0)"
                    )

        # Validate app_name format
        if "app_name" in config:  # +1
            app_name = config["app_name"]
            if isinstance(app_name, str):
                if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", app_name):
                    format_errors.append(
                        f"App name '{app_name}' must start with letter and contain only letters, numbers, underscore, or hyphen"
                    )

        # Validate email format if present
        if "contact_email" in config:  # +1
            email = config["contact_email"]
            if isinstance(email, str):
                if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
                    format_errors.append(f"Contact email '{email}' has invalid format")

        return len(format_errors) == 0, format_errors

    def set_constraints(self, constraints: Dict[str, Any]) -> None:
        """Set validation constraints - complexity 1"""
        self.constraints = constraints.copy() if constraints else {}

    def add_constraint(self, field_name: str, constraint: Dict[str, Any]) -> None:
        """Add constraint for specific field - complexity 1"""
        self.constraints[field_name] = constraint

    def get_validation_errors(self) -> List[str]:
        """Get current validation errors - complexity 1"""
        return self.validation_errors.copy()

    def _validate_numeric_constraints(
        self, config: Dict[str, Any], constraints: Dict[str, Any]
    ) -> bool:
        """Validate numeric constraints - complexity 3"""
        for field_name, constraint in constraints.items():
            if field_name in config and ("min" in constraint or "max" in constraint):  # +1
                value = config[field_name]
                if isinstance(value, (int, float)):  # +1
                    is_valid, error_msg = self.check_constraints(value, constraint)
                    if not is_valid:  # +1
                        self.validation_errors.append(f"Field '{field_name}': {error_msg}")
                        return False
        return True

    def _validate_string_patterns(
        self, config: Dict[str, Any], constraints: Dict[str, Any]
    ) -> bool:
        """Validate string patterns - complexity 3"""
        for field_name, constraint in constraints.items():
            if field_name in config and "pattern" in constraint:  # +1
                value = config[field_name]
                if isinstance(value, str):  # +1
                    is_valid, error_msg = self.check_constraints(value, constraint)
                    if not is_valid:  # +1
                        self.validation_errors.append(f"Field '{field_name}': {error_msg}")
                        return False
        return True

    def _validate_custom_constraints(
        self, config: Dict[str, Any], constraints: Dict[str, Any]
    ) -> bool:
        """Validate custom constraints - complexity 2"""
        for field_name, constraint in constraints.items():
            if field_name in config and "custom_validator" in constraint:  # +1
                value = config[field_name]
                validator_func = constraint["custom_validator"]
                try:
                    if not validator_func(value):
                        self.validation_errors.append(
                            f"Field '{field_name}' failed custom validation"
                        )
                        return False
                except Exception as e:
                    self.validation_errors.append(
                        f"Field '{field_name}' custom validator error: {str(e)}"
                    )
                    return False
        return True

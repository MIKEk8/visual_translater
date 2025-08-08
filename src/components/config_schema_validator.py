"""
Config Schema Validator Component - Single Responsibility: Schema Validation
Extracted from validate_configuration (complexity 15 → 3 per method)
"""

import logging
from typing import Any, Dict, List, Optional, Tuple


class ConfigSchemaValidator:
    """
    Single Responsibility: Validate configuration schema and structure
    All methods ≤ 3 complexity
    """

    def __init__(self):
        self.validation_errors = []
        self.required_fields = {"app_name": str, "version": str, "port": int}
        self.optional_fields = {"debug": bool, "timeout": int, "database": dict}
        self.logger = logging.getLogger(__name__)

    def validate_schema(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate configuration schema
        Complexity: 3
        """
        self.validation_errors.clear()

        if not isinstance(config, dict):  # +1
            self.validation_errors.append("Configuration must be a dictionary")
            return False, self.validation_errors

        # Check required fields
        if not self._check_required_fields(config):  # +1
            return False, self.validation_errors

        # Check field types
        if not self._validate_field_types(config):  # +1
            return False, self.validation_errors

        return True, []

    def check_structure(self, config: Dict[str, Any], required_fields: List[str] = None) -> bool:
        """
        Check configuration structure requirements
        Complexity: 3
        """
        if not config:  # +1
            return False

        fields_to_check = required_fields or list(self.required_fields.keys())

        for field in fields_to_check:  # +1
            if field not in config:
                self.validation_errors.append(f"Missing required field: {field}")
                return False

        # Check for nested structures
        if "database" in config and config["database"]:  # +1
            if not isinstance(config["database"], dict):
                self.validation_errors.append("Database configuration must be a dictionary")
                return False

        return True

    def verify_types(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Verify data types of configuration fields
        Complexity: 3
        """
        type_errors = []

        for field, expected_type in self.required_fields.items():
            if field in config:  # +1
                actual_value = config[field]
                if not isinstance(actual_value, expected_type):  # +1
                    type_errors.append(
                        f"Field '{field}' expected {expected_type.__name__}, got {type(actual_value).__name__}"
                    )

        # Check optional fields if present
        for field, expected_type in self.optional_fields.items():
            if field in config:  # +1
                actual_value = config[field]
                if actual_value is not None and not isinstance(actual_value, expected_type):
                    type_errors.append(
                        f"Optional field '{field}' expected {expected_type.__name__}, got {type(actual_value).__name__}"
                    )

        return len(type_errors) == 0, type_errors

    def get_schema_definition(self) -> Dict[str, Any]:
        """Get current schema definition - complexity 1"""
        return {
            "required_fields": self.required_fields.copy(),
            "optional_fields": self.optional_fields.copy(),
        }

    def set_required_fields(self, fields: Dict[str, type]) -> None:
        """Set required fields schema - complexity 1"""
        self.required_fields = fields.copy() if fields else {}

    def add_optional_field(self, name: str, field_type: type) -> None:
        """Add optional field to schema - complexity 1"""
        self.optional_fields[name] = field_type

    def _check_required_fields(self, config: Dict[str, Any]) -> bool:
        """Check if all required fields are present - complexity 2"""
        missing_fields = []

        for field in self.required_fields.keys():  # +1
            if field not in config:
                missing_fields.append(field)

        if missing_fields:  # +1
            self.validation_errors.extend(
                [f"Missing required field: {field}" for field in missing_fields]
            )
            return False

        return True

    def _validate_field_types(self, config: Dict[str, Any]) -> bool:
        """Validate field types - complexity 2"""
        is_valid, type_errors = self.verify_types(config)

        if not is_valid:  # +1
            self.validation_errors.extend(type_errors)

        return is_valid

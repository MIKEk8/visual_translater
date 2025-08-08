"""Schema Validator - Database Schema Validation"""

import json
import re
from typing import Any, Dict, List, Optional


class SchemaValidator:
    """Validate database schemas - complexity ≤ 3"""

    def __init__(self):
        self.validation_errors = []
        self.required_fields = {"name", "type"}

    def validate_schema(self, schema_def: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate complete schema - complexity 3"""
        self.validation_errors.clear()

        if not schema_def:  # +1
            self.validation_errors.append("Empty schema definition")
            return False, self.validation_errors

        if "tables" not in schema_def:  # +1
            self.validation_errors.append("No tables defined in schema")
            return False, self.validation_errors

        for table_name, table_def in schema_def.get("tables", {}).items():  # +1
            if not self._validate_table(table_name, table_def):
                return False, self.validation_errors

        return True, []

    def validate_table_structure(self, table_def: Dict[str, Any]) -> bool:
        """Validate individual table - complexity 2"""
        if "columns" not in table_def:  # +1
            self.validation_errors.append("Table missing columns definition")
            return False
        return self._check_column_types(table_def["columns"])

    def check_naming_conventions(self, schema_def: Dict[str, Any]) -> List[str]:
        """Check naming conventions - complexity 2"""
        issues = []
        pattern = r"^[a-z][a-z0-9_]*$"

        for table_name in schema_def.get("tables", {}):  # +1
            if not re.match(pattern, table_name):
                issues.append(f"Invalid table name: {table_name}")

        return issues

    def _validate_table(self, name: str, definition: Dict[str, Any]) -> bool:
        """Private table validation - complexity 2"""
        if not isinstance(definition, dict):  # +1
            self.validation_errors.append(f"Invalid table definition for {name}")
            return False
        return self.validate_table_structure(definition)

    def _check_column_types(self, columns: Dict[str, Any]) -> bool:
        """Check column type validity - complexity 2"""
        valid_types = {"INTEGER", "TEXT", "REAL", "BLOB", "BOOLEAN", "TIMESTAMP"}

        for col_name, col_def in columns.items():  # +1
            if col_def.get("type", "").upper() not in valid_types:
                self.validation_errors.append(f"Invalid column type: {col_name}")
                return False
        return True

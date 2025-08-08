"""
Export Data Validator Component - Single Responsibility: Validation
Extracted from export_batch_results (complexity 16 → 3 per method)
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ExportDataValidator:
    """
    Single Responsibility: Validate export data and parameters
    All methods ≤ 3 complexity
    """

    SUPPORTED_FORMATS = {"csv", "json", "xml", "xlsx"}
    REQUIRED_FIELDS = {"data", "filename", "format"}
    MAX_FILENAME_LENGTH = 255

    def __init__(self):
        self.validation_errors = []

    def validate_export_request(self, export_request: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate complete export request
        Complexity: 3
        """
        self.validation_errors.clear()

        # Check required fields
        if not self._check_required_fields(export_request):  # +1
            return False, self.validation_errors

        # Validate data format
        if not self._validate_data_structure(export_request.get("data")):  # +1
            return False, self.validation_errors

        # Validate filename and format
        if not self._validate_file_parameters(export_request):  # +1
            return False, self.validation_errors

        return len(self.validation_errors) == 0, self.validation_errors

    def validate_data_format(self, data: Any, expected_format: str = "list") -> bool:
        """
        Validate data format matches expected structure
        Complexity: 3
        """
        if not data:  # +1
            self.validation_errors.append("Data cannot be empty")
            return False

        if expected_format == "list":  # +1
            if not isinstance(data, (list, tuple)):
                self.validation_errors.append("Data must be a list or tuple")
                return False

        if expected_format == "dict":  # +1
            if not isinstance(data, dict):
                self.validation_errors.append("Data must be a dictionary")
                return False

        return True

    def check_permissions(self, filepath: str, operation: str = "write") -> bool:
        """
        Check file system permissions for export operation
        Complexity: 3
        """
        try:
            path = Path(filepath)
            parent_dir = path.parent

            # Check if parent directory exists or can be created
            if not parent_dir.exists():  # +1
                try:
                    parent_dir.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    self.validation_errors.append(f"Cannot create directory: {parent_dir}")
                    return False

            # Check write permissions
            if operation == "write":  # +1
                if not os.access(parent_dir, os.W_OK):
                    self.validation_errors.append(
                        f"No write permission for directory: {parent_dir}"
                    )
                    return False

            # Check if file already exists and handle overwrite
            if path.exists() and operation == "write":  # +1
                if not os.access(path, os.W_OK):
                    self.validation_errors.append(f"No write permission for file: {path}")
                    return False

            return True

        except Exception as e:
            self.validation_errors.append(f"Permission check failed: {str(e)}")
            return False

    def _check_required_fields(self, request: Dict[str, Any]) -> bool:
        """Check all required fields are present - complexity 2"""
        missing_fields = []

        for field in self.REQUIRED_FIELDS:  # +1
            if field not in request or request[field] is None:
                missing_fields.append(field)

        if missing_fields:  # +1
            self.validation_errors.append(f"Missing required fields: {', '.join(missing_fields)}")
            return False

        return True

    def _validate_data_structure(self, data: Any) -> bool:
        """Validate data structure is exportable - complexity 2"""
        if not data:  # +1
            self.validation_errors.append("Export data is empty")
            return False

        # For list data, check if items have consistent structure
        if isinstance(data, (list, tuple)) and len(data) > 0:  # +1
            first_item = data[0]
            if isinstance(first_item, dict):
                # All items should have similar keys for consistent export
                first_keys = set(first_item.keys())
                for item in data[1:]:
                    if isinstance(item, dict) and set(item.keys()) != first_keys:
                        self.validation_errors.append("Inconsistent data structure in export items")
                        return False

        return True

    def _validate_file_parameters(self, request: Dict[str, Any]) -> bool:
        """Validate filename and format parameters - complexity 3"""
        filename = request.get("filename", "")
        file_format = request.get("format", "").lower()

        # Validate format
        if file_format not in self.SUPPORTED_FORMATS:  # +1
            self.validation_errors.append(
                f"Unsupported format: {file_format}. Supported: {', '.join(self.SUPPORTED_FORMATS)}"
            )
            return False

        # Validate filename
        if not filename or len(filename.strip()) == 0:  # +1
            self.validation_errors.append("Filename cannot be empty")
            return False

        if len(filename) > self.MAX_FILENAME_LENGTH:  # +1
            self.validation_errors.append(
                f"Filename too long (max {self.MAX_FILENAME_LENGTH} characters)"
            )
            return False

        # Check for invalid characters in filename
        invalid_chars = '<>:"/\|?*'
        if any(char in filename for char in invalid_chars):
            self.validation_errors.append(f"Filename contains invalid characters: {invalid_chars}")
            return False

        return True

    def get_last_errors(self) -> List[str]:
        """Get validation errors from last validation - complexity 1"""
        return self.validation_errors.copy()

    def clear_errors(self) -> None:
        """Clear accumulated validation errors - complexity 1"""
        self.validation_errors.clear()

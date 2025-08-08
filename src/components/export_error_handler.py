"""
Export Error Handler Component - Single Responsibility: Error Handling
Extracted from export_batch_results (complexity 16 → 4 per method)
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional


class ErrorSeverity(Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExportError:
    """Export error information"""

    def __init__(
        self, error_type: str, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ):
        self.error_type = error_type
        self.message = message
        self.severity = severity
        self.timestamp = None
        self.context = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "context": self.context,
        }


class ExportErrorHandler:
    """
    Single Responsibility: Handle export errors and recovery
    All methods ≤ 4 complexity
    """

    def __init__(self):
        self.errors = []
        self.error_counts = {}
        self.logger = logging.getLogger(__name__)

    def handle_format_error(
        self, format_type: str, error: Exception, context: Dict[str, Any] = None
    ) -> ExportError:
        """
        Handle format-specific errors
        Complexity: 4
        """
        error_message = f"Format error in {format_type}: {str(error)}"

        # Determine severity based on error type
        if isinstance(error, (FileNotFoundError, PermissionError)):  # +1
            severity = ErrorSeverity.HIGH
            error_message += " - Check file path and permissions"
        elif isinstance(error, (ValueError, TypeError)):  # +1
            severity = ErrorSeverity.MEDIUM
            error_message += " - Check data format compatibility"
        elif isinstance(error, MemoryError):  # +1
            severity = ErrorSeverity.CRITICAL
            error_message += " - Data too large for available memory"
        else:  # +1
            severity = ErrorSeverity.MEDIUM
            error_message += " - Unexpected format error"

        export_error = ExportError("format_error", error_message, severity)
        export_error.context = context or {}
        export_error.context["format_type"] = format_type
        export_error.context["original_error"] = str(error)

        self._log_and_store_error(export_error)
        return export_error

    def handle_file_error(
        self, filepath: str, error: Exception, context: Dict[str, Any] = None
    ) -> ExportError:
        """
        Handle file operation errors
        Complexity: 4
        """
        error_message = f"File error for {filepath}: {str(error)}"

        # Determine severity and provide specific guidance
        if isinstance(error, FileNotFoundError):  # +1
            severity = ErrorSeverity.HIGH
            error_message += " - Directory does not exist"
        elif isinstance(error, PermissionError):  # +1
            severity = ErrorSeverity.HIGH
            error_message += " - Insufficient permissions to write file"
        elif isinstance(error, OSError):  # +1
            severity = ErrorSeverity.MEDIUM
            error_message += " - File system error occurred"
        else:  # +1
            severity = ErrorSeverity.MEDIUM
            error_message += " - Unexpected file error"

        export_error = ExportError("file_error", error_message, severity)
        export_error.context = context or {}
        export_error.context["filepath"] = filepath
        export_error.context["original_error"] = str(error)

        self._log_and_store_error(export_error)
        return export_error

    def create_error_report(self) -> Dict[str, Any]:
        """
        Create comprehensive error report
        Complexity: 3
        """
        if not self.errors:  # +1
            return {"status": "no_errors", "total_errors": 0}

        # Group errors by type and severity
        errors_by_type = {}
        errors_by_severity = {}

        for error in self.errors:
            error_type = error.error_type
            severity = error.severity.value

            if error_type not in errors_by_type:  # +1
                errors_by_type[error_type] = []
            errors_by_type[error_type].append(error.to_dict())

            if severity not in errors_by_severity:  # +1
                errors_by_severity[severity] = 0
            errors_by_severity[severity] += 1

        return {
            "status": "errors_found",
            "total_errors": len(self.errors),
            "errors_by_type": errors_by_type,
            "errors_by_severity": errors_by_severity,
            "has_critical_errors": ErrorSeverity.CRITICAL.value in errors_by_severity,
        }

    def get_recovery_suggestions(self, error: ExportError) -> List[str]:
        """
        Get recovery suggestions for specific error
        Complexity: 4
        """
        suggestions = []

        if error.error_type == "format_error":  # +1
            suggestions.extend(
                [
                    "Verify data structure compatibility with target format",
                    "Check for special characters that may need escaping",
                    "Consider using a different export format",
                ]
            )

        if error.error_type == "file_error":  # +1
            suggestions.extend(
                [
                    "Check file path exists and is accessible",
                    "Verify write permissions for target directory",
                    "Ensure sufficient disk space is available",
                ]
            )

        if error.severity == ErrorSeverity.CRITICAL:  # +1
            suggestions.extend(
                [
                    "Consider breaking large exports into smaller batches",
                    "Free up system memory before retrying",
                    "Contact system administrator if problem persists",
                ]
            )

        if not suggestions:  # +1
            suggestions.append("Review error details and try again")

        return suggestions

    def clear_errors(self) -> int:
        """Clear all stored errors - complexity 1"""
        count = len(self.errors)
        self.errors.clear()
        self.error_counts.clear()
        return count

    def get_error_count(self) -> int:
        """Get total error count - complexity 1"""
        return len(self.errors)

    def has_critical_errors(self) -> bool:
        """Check if any critical errors occurred - complexity 2"""
        for error in self.errors:  # +1
            if error.severity == ErrorSeverity.CRITICAL:
                return True
        return False

    def _log_and_store_error(self, error: ExportError) -> None:
        """Log and store error - complexity 2"""
        import time

        error.timestamp = time.time()

        self.errors.append(error)

        # Log based on severity
        if error.severity == ErrorSeverity.CRITICAL:  # +1
            self.logger.critical(error.message)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(error.message)
        else:
            self.logger.warning(error.message)

        # Update error counts
        self.error_counts[error.error_type] = self.error_counts.get(error.error_type, 0) + 1

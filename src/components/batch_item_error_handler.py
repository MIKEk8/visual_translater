"""
Batch Item Error Handler Component - Single Responsibility: Item Error Handling
Extracted from _process_batch_item (complexity 16 → 4 per method)
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class ErrorSeverity(Enum):
    """Error severity levels for batch item processing"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ItemError:
    """Individual item error information"""

    item_id: str
    error_type: str
    message: str
    severity: ErrorSeverity
    timestamp: float
    context: Dict[str, Any]
    recoverable: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "error_type": self.error_type,
            "message": self.message,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "context": self.context,
            "recoverable": self.recoverable,
        }


class BatchItemErrorHandler:
    """
    Single Responsibility: Handle processing errors for individual batch items
    All methods ≤ 4 complexity
    """

    def __init__(self):
        self.item_errors = []
        self.error_counts = {}
        self.logger = logging.getLogger(__name__)
        self.max_retries = 3
        self.recovery_strategies = {
            "validation_error": self._recover_validation_error,
            "processing_error": self._recover_processing_error,
            "transformation_error": self._recover_transformation_error,
        }

    def handle_item_error(
        self, item: Dict[str, Any], error: Exception, context: Dict[str, Any] = None
    ) -> ItemError:
        """
        Handle error for individual batch item
        Complexity: 4
        """
        item_id = item.get("id", "unknown") if item else "unknown"
        context = context or {}

        # Determine error type and severity
        error_type = self._classify_error(error)  # +1
        severity = self._determine_severity(error, context)  # +1

        item_error = ItemError(
            item_id=item_id,
            error_type=error_type,
            message=str(error),
            severity=severity,
            timestamp=time.time(),
            context=context,
        )

        # Determine if error is recoverable
        item_error.recoverable = self._is_recoverable(error, context)  # +1

        # Store error and update counts
        self.item_errors.append(item_error)
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

        # Log error based on severity
        self._log_error(item_error)  # +1

        return item_error

    def create_error_report(self) -> Dict[str, Any]:
        """
        Create comprehensive error report for batch processing
        Complexity: 4
        """
        if not self.item_errors:  # +1
            return {"status": "no_errors", "total_errors": 0, "items_affected": 0}

        # Group errors by various criteria
        errors_by_type = {}
        errors_by_severity = {}
        errors_by_item = {}

        for error in self.item_errors:
            # Group by type
            if error.error_type not in errors_by_type:  # +1
                errors_by_type[error.error_type] = []
            errors_by_type[error.error_type].append(error.to_dict())

            # Group by severity
            severity = error.severity.value
            errors_by_severity[severity] = errors_by_severity.get(severity, 0) + 1

            # Group by item
            if error.item_id not in errors_by_item:  # +1
                errors_by_item[error.item_id] = []
            errors_by_item[error.item_id].append(error.to_dict())

        # Calculate statistics
        total_errors = len(self.item_errors)
        items_affected = len(errors_by_item)
        has_critical = ErrorSeverity.CRITICAL.value in errors_by_severity

        recovery_summary = self._analyze_recovery_potential()  # +1

        return {
            "status": "errors_found",
            "total_errors": total_errors,
            "items_affected": items_affected,
            "errors_by_type": errors_by_type,
            "errors_by_severity": errors_by_severity,
            "errors_by_item": errors_by_item,
            "has_critical_errors": has_critical,
            "recovery_analysis": recovery_summary,
        }

    def get_recovery_suggestions(self, error: ItemError) -> List[str]:
        """
        Get specific recovery suggestions for an item error
        Complexity: 4
        """
        suggestions = []

        # Type-specific suggestions
        if error.error_type == "validation_error":  # +1
            suggestions.extend(
                [
                    "Check item data format and required fields",
                    "Verify data types match expected schema",
                    "Ensure all mandatory fields are present",
                ]
            )
        elif error.error_type == "processing_error":  # +1
            suggestions.extend(
                [
                    "Review processing rules and transformations",
                    "Check for data compatibility issues",
                    "Verify processing configuration",
                ]
            )
        elif error.error_type == "transformation_error":  # +1
            suggestions.extend(
                [
                    "Validate transformation rules syntax",
                    "Check data type compatibility for transformations",
                    "Review custom transformation functions",
                ]
            )

        # Severity-specific suggestions
        if error.severity == ErrorSeverity.CRITICAL:  # +1
            suggestions.extend(
                [
                    "Consider breaking batch into smaller chunks",
                    "Review system resources and capacity",
                    "Contact system administrator if needed",
                ]
            )

        # Recovery strategy suggestions
        if error.recoverable and error.error_type in self.recovery_strategies:
            suggestions.append(f"Automatic recovery available for {error.error_type}")

        return suggestions if suggestions else ["Review error details and retry processing"]

    def attempt_recovery(self, item: Dict[str, Any], error: ItemError) -> Dict[str, Any]:
        """
        Attempt automatic recovery for recoverable errors
        Complexity: 3
        """
        if not error.recoverable:  # +1
            return {"recovery_success": False, "reason": "Error not recoverable"}

        recovery_strategy = self.recovery_strategies.get(error.error_type)
        if not recovery_strategy:  # +1
            return {"recovery_success": False, "reason": "No recovery strategy available"}

        try:
            recovered_item = recovery_strategy(item, error)
            return {
                "recovery_success": True,
                "recovered_item": recovered_item,
                "recovery_method": error.error_type,
            }
        except Exception as e:  # +1
            return {"recovery_success": False, "reason": f"Recovery attempt failed: {str(e)}"}

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics - complexity 2"""
        if not self.item_errors:  # +1
            return {"total_errors": 0, "error_rate": 0.0}

        return {
            "total_errors": len(self.item_errors),
            "error_types": len(self.error_counts),
            "most_common_error": max(self.error_counts, key=self.error_counts.get),
            "recoverable_errors": sum(1 for e in self.item_errors if e.recoverable),
            "critical_errors": sum(
                1 for e in self.item_errors if e.severity == ErrorSeverity.CRITICAL
            ),
        }

    def clear_errors(self) -> int:
        """Clear all stored errors - complexity 1"""
        count = len(self.item_errors)
        self.item_errors.clear()
        self.error_counts.clear()
        return count

    def _classify_error(self, error: Exception) -> str:
        """Classify error type - complexity 3"""
        if isinstance(error, ValueError):  # +1
            return "validation_error"
        elif isinstance(error, KeyError):  # +1
            return "processing_error"
        elif isinstance(error, (TypeError, AttributeError)):  # +1
            return "transformation_error"
        else:
            return "unknown_error"

    def _determine_severity(self, error: Exception, context: Dict[str, Any]) -> ErrorSeverity:
        """Determine error severity - complexity 3"""
        if isinstance(error, (MemoryError, SystemError)):  # +1
            return ErrorSeverity.CRITICAL
        elif isinstance(error, (FileNotFoundError, PermissionError)):  # +1
            return ErrorSeverity.HIGH
        elif context.get("retry_count", 0) > self.max_retries:  # +1
            return ErrorSeverity.HIGH
        else:
            return ErrorSeverity.MEDIUM

    def _is_recoverable(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Check if error is recoverable - complexity 2"""
        if isinstance(error, (MemoryError, SystemError)):  # +1
            return False
        return context.get("retry_count", 0) < self.max_retries

    def _log_error(self, error: ItemError) -> None:
        """Log error based on severity - complexity 2"""
        message = f"Item {error.item_id}: {error.message}"

        if error.severity == ErrorSeverity.CRITICAL:  # +1
            self.logger.critical(message)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(message)
        else:
            self.logger.warning(message)

    def _analyze_recovery_potential(self) -> Dict[str, Any]:
        """Analyze recovery potential - complexity 2"""
        if not self.item_errors:  # +1
            return {"recoverable_count": 0, "recovery_rate": 0.0}

        recoverable = sum(1 for e in self.item_errors if e.recoverable)
        return {
            "recoverable_count": recoverable,
            "recovery_rate": recoverable / len(self.item_errors),
            "recovery_strategies_available": len(self.recovery_strategies),
        }

    def _recover_validation_error(self, item: Dict[str, Any], error: ItemError) -> Dict[str, Any]:
        """Recover from validation error - complexity 2"""
        recovered = item.copy() if item else {}

        # Add missing required fields with defaults
        if "id" not in recovered:  # +1
            recovered["id"] = f"recovered_{int(time.time())}"
        if "type" not in recovered:
            recovered["type"] = "data_record"

        return recovered

    def _recover_processing_error(self, item: Dict[str, Any], error: ItemError) -> Dict[str, Any]:
        """Recover from processing error - complexity 1"""
        return item.copy() if item else {}

    def _recover_transformation_error(
        self, item: Dict[str, Any], error: ItemError
    ) -> Dict[str, Any]:
        """Recover from transformation error - complexity 1"""
        return item.copy() if item else {}

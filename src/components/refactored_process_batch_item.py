"""
Refactored Process Batch Item - Main Coordinator
Complexity reduced from 16 to 5 using composition of focused components
"""

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from .batch_item_error_handler import BatchItemErrorHandler
from .batch_item_validator import BatchItemValidator
from .batch_progress_manager import BatchProgressManager
from .item_processor import ItemProcessor


class RefactoredProcessBatchItem:
    """
    Main coordinator for batch item processing functionality
    Complexity: 5 (down from 16)
    Single Responsibility: Coordinate batch item processing using composed components
    """

    def __init__(self):
        # Composed components - each with single responsibility
        self.validator = BatchItemValidator()
        self.processor = ItemProcessor()
        self.error_handler = BatchItemErrorHandler()
        self.progress_manager = BatchProgressManager()

        self.logger = logging.getLogger(__name__)

    def process_batch_item(
        self,
        item: Dict[str, Any],
        processing_options: Dict[str, Any] = None,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Process individual batch item with full coordination
        Complexity: 5 (down from 16)
        """
        processing_options = processing_options or {}
        item_id = item.get("id", f"item_{int(time.time())}") if item else "unknown"

        # Initialize progress tracking
        if progress_callback:
            self.progress_manager.add_progress_callback(progress_callback)

        self.progress_manager.update_item_progress(item_id, {"status": "processing"})

        try:
            # Step 1: Validate item
            is_valid, validation_errors = self.validator.validate_item(item)
            if not is_valid:  # +1
                error = Exception(f"Validation failed: {', '.join(validation_errors)}")
                item_error = self.error_handler.handle_item_error(
                    item, error, {"stage": "validation"}
                )

                # Track failure
                self.progress_manager.track_completion(
                    item_id, {"success": False, "error": str(error), "stage": "validation"}
                )

                return {
                    "success": False,
                    "item_id": item_id,
                    "stage": "validation",
                    "errors": validation_errors,
                    "error_details": item_error.to_dict(),
                }

            # Step 2: Preprocess item
            preprocessed_item = self.validator.preprocess_item(item)

            # Step 3: Process item
            processing_result = self.processor.process_item(preprocessed_item, processing_options)

            if not processing_result.get("success", False):  # +1
                error_msg = processing_result.get("error", "Processing failed")
                error = Exception(error_msg)
                item_error = self.error_handler.handle_item_error(
                    item, error, {"stage": "processing"}
                )

                # Attempt recovery if possible
                recovery_result = self.error_handler.attempt_recovery(item, item_error)

                if recovery_result["recovery_success"]:  # +1
                    # Retry processing with recovered item
                    retry_result = self.processor.process_item(
                        recovery_result["recovered_item"], processing_options
                    )
                    if retry_result.get("success", False):
                        processing_result = retry_result
                        processing_result["recovered"] = True
                    else:
                        # Track final failure
                        self.progress_manager.track_completion(
                            item_id,
                            {"success": False, "error": error_msg, "stage": "processing_retry"},
                        )

                        return {
                            "success": False,
                            "item_id": item_id,
                            "stage": "processing",
                            "error": error_msg,
                            "recovery_attempted": True,
                            "error_details": item_error.to_dict(),
                        }
                else:
                    # Track failure without recovery
                    self.progress_manager.track_completion(
                        item_id, {"success": False, "error": error_msg, "stage": "processing"}
                    )

                    return {
                        "success": False,
                        "item_id": item_id,
                        "stage": "processing",
                        "error": error_msg,
                        "error_details": item_error.to_dict(),
                    }

            # Step 4: Track successful completion
            completion_data = {
                "success": True,
                "result": processing_result,
                "duration": processing_result.get("processing_time", 0),
            }

            self.progress_manager.track_completion(item_id, completion_data)

            return {
                "success": True,
                "item_id": item_id,
                "processed_data": processing_result.get("processed_data"),
                "processing_time": processing_result.get("processing_time"),
                "transformations_applied": processing_result.get("transformations_applied", []),
                "recovered": processing_result.get("recovered", False),
                "stage": "completed",
            }

        except Exception as e:  # +1
            # Handle unexpected errors
            item_error = self.error_handler.handle_item_error(item, e, {"stage": "unexpected"})

            self.progress_manager.track_completion(
                item_id, {"success": False, "error": str(e), "stage": "unexpected_error"}
            )

            return {
                "success": False,
                "item_id": item_id,
                "stage": "unexpected_error",
                "error": str(e),
                "error_details": item_error.to_dict(),
                "recovery_suggestions": self.error_handler.get_recovery_suggestions(item_error),
            }

    def coordinate_processing(
        self, items: List[Dict[str, Any]], batch_options: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Coordinate processing of multiple batch items
        Complexity: 3
        """
        batch_options = batch_options or {}
        results = []

        # Start batch tracking
        self.progress_manager.start_batch_tracking(len(items))

        # Process each item
        for item in items:  # +1
            try:
                result = self.process_batch_item(item, batch_options.get("processing_options"))
                results.append(result)
            except Exception as e:  # +1
                # Handle batch-level errors
                error_result = {
                    "success": False,
                    "item_id": item.get("id", "unknown") if item else "unknown",
                    "error": str(e),
                    "stage": "batch_coordination",
                }
                results.append(error_result)

        # Complete batch tracking
        self.progress_manager.complete_batch_tracking()

        return results

    def collect_results(self, processing_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Collect and summarize processing results
        Complexity: 2
        """
        if not processing_results:  # +1
            return {"total_processed": 0, "successful": 0, "failed": 0, "recovery_count": 0}

        successful = sum(1 for r in processing_results if r.get("success", False))
        failed = len(processing_results) - successful
        recovered = sum(1 for r in processing_results if r.get("recovered", False))

        # Get error statistics
        error_stats = self.error_handler.get_error_statistics()
        progress_stats = self.progress_manager.get_progress_stats()

        return {
            "total_processed": len(processing_results),
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / len(processing_results)) * 100,
            "recovery_count": recovered,
            "error_statistics": error_stats,
            "progress_statistics": progress_stats,
            "processing_summary": {
                "total_duration": progress_stats.get("total_duration"),
                "items_per_second": progress_stats.get("items_per_second"),
                "completion_rate": progress_stats.get("completion_rate"),
            },
        }

    def get_component_status(self) -> Dict[str, Any]:
        """Get status of all components - complexity 1"""
        return {
            "validator": {"errors": self.validator.get_validation_summary()},
            "processor": {
                "supported_transformations": self.processor.get_supported_transformations()
            },
            "error_handler": {"statistics": self.error_handler.get_error_statistics()},
            "progress_manager": {"stats": self.progress_manager.get_progress_stats()},
        }

    def reset_components(self) -> None:
        """Reset all components - complexity 1"""
        self.validator.clear_validation_errors()
        self.processor.clear_processing_rules()
        self.error_handler.clear_errors()
        self.progress_manager.reset_progress()

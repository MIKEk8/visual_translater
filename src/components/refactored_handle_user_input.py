"""Refactored Handle User Input - Main Coordinator"""

from typing import Any, Dict, Optional

from .input_error_handler import InputErrorHandler
from .input_event_manager import InputEventManager
from .input_processor import InputProcessor
from .input_validator import InputValidator


class RefactoredHandleUserInput:
    """Main UI input coordinator - complexity ≤ 5"""

    def __init__(self):
        self.validator = InputValidator()
        self.processor = InputProcessor()
        self.event_manager = InputEventManager()
        self.error_handler = InputErrorHandler()

    def handle_user_input(
        self, input_data: Dict[str, Any], options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Handle complete user input - complexity 5"""
        options = options or {}

        try:
            # Step 1: Validate input
            is_valid, validation_errors = self.validator.validate_input(
                input_data, options.get("validation_schema")
            )

            if not is_valid:  # +1
                return {"success": False, "stage": "validation", "errors": validation_errors}

            # Step 2: Process input
            processing_result = self.processor.process_input(
                input_data, options.get("processing_rules")
            )

            if not processing_result["success"]:  # +1
                return {
                    "success": False,
                    "stage": "processing",
                    "error": processing_result["error"],
                }

            # Step 3: Handle events if specified
            if "event_type" in options:  # +1
                event_result = self.event_manager.handle_event(
                    options["event_type"], processing_result["data"]
                )

                if not event_result["success"]:  # +1
                    return {
                        "success": False,
                        "stage": "event_handling",
                        "error": event_result["error"],
                    }

            return {
                "success": True,
                "processed_data": processing_result["data"],
                "stage": "completed",
            }

        except Exception as e:  # +1
            error_info = self.error_handler.handle_input_error(e, {"input": input_data})
            return {
                "success": False,
                "error": str(e),
                "user_message": self.error_handler.get_user_friendly_message(error_info),
                "stage": "error",
            }

"""
Refactored Export Batch Results - Main Coordinator
Complexity reduced from 16 to 5 using composition of focused components
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .export_data_validator import ExportDataValidator
from .export_error_handler import ExportErrorHandler
from .export_progress_tracker import ExportProgressTracker
from .format_exporter import FormatExporter


class RefactoredExportBatchResults:
    """
    Main coordinator for export batch results functionality
    Complexity: 5 (down from 16)
    Single Responsibility: Coordinate export process using composed components
    """

    def __init__(self):
        # Composed components - each with single responsibility
        self.validator = ExportDataValidator()
        self.exporter = FormatExporter()
        self.progress_tracker = ExportProgressTracker()
        self.error_handler = ExportErrorHandler()

    def export_batch_results(
        self,
        data: List[Dict[str, Any]],
        filepath: str,
        format_type: str,
        progress_callback: Optional[Callable] = None,
        **options,
    ) -> Dict[str, Any]:
        """
        Export batch results with proper component coordination
        Complexity: 5 (down from 16)
        """
        # Step 1: Validate export request
        export_request = {"data": data, "filename": Path(filepath).name, "format": format_type}

        is_valid, validation_errors = self.validator.validate_export_request(export_request)
        if not is_valid:  # +1
            return {"success": False, "errors": validation_errors, "stage": "validation"}

        # Step 2: Start progress tracking
        total_items = len(data) if data else 0
        if not self.progress_tracker.start_tracking(total_items, progress_callback):  # +1
            return {
                "success": False,
                "errors": ["Failed to initialize progress tracking"],
                "stage": "progress_init",
            }

        # Step 3: Perform export
        try:
            export_success = self.exporter.export_data(data, filepath, format_type, **options)

            if not export_success:  # +1
                export_info = self.exporter.get_export_info()
                error_msg = export_info.get("error", "Unknown export error")

                # Handle export error
                error = Exception(error_msg)
                self.error_handler.handle_format_error(format_type, error, {"filepath": filepath})

                return {
                    "success": False,
                    "errors": [error_msg],
                    "stage": "export",
                    "error_report": self.error_handler.create_error_report(),
                }

        except Exception as e:
            # Handle unexpected errors
            if "file" in str(e).lower() or "path" in str(e).lower():  # +1
                self.error_handler.handle_file_error(filepath, e)
            else:
                self.error_handler.handle_format_error(format_type, e)

            return {
                "success": False,
                "errors": [str(e)],
                "stage": "export_exception",
                "error_report": self.error_handler.create_error_report(),
                "recovery_suggestions": self.error_handler.get_recovery_suggestions(
                    self.error_handler.errors[-1] if self.error_handler.errors else None
                ),
            }

        # Step 4: Complete tracking and return success
        final_stats = self.progress_tracker.complete_tracking()
        export_info = self.exporter.get_export_info()

        return {
            "success": True,
            "filepath": filepath,
            "format": format_type,
            "records_exported": export_info.get("record_count", 0),
            "export_stats": final_stats,
            "stage": "completed",
        }

    def get_supported_formats(self) -> set:
        """Get supported export formats - complexity 1"""
        return self.exporter.get_supported_formats()

    def validate_export_request(self, request: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate export request - complexity 1"""
        return self.validator.validate_export_request(request)

    def get_last_error_report(self) -> Dict[str, Any]:
        """Get last error report - complexity 1"""
        return self.error_handler.create_error_report()

    def clear_errors(self) -> int:
        """Clear all errors - complexity 1"""
        return self.error_handler.clear_errors()

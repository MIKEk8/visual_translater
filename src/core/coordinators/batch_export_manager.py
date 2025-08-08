"""
BatchExportManager - Batch processing and export coordinator

Single Responsibility: Manages batch processing of multiple screenshots,
export functionality, and performance monitoring.

Responsibilities:
- Batch processing coordination
- Export functionality (history, batch results, performance metrics)
- Performance monitoring and alerts
- Batch progress tracking and callbacks
"""

import queue
import threading
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

# Import filedialog only when needed to avoid tkinter dependency
try:
    from tkinter import filedialog
except ImportError:
    filedialog = None

from src.core.batch_processor import BatchJob, BatchProcessor, BatchStatus
from src.core.screenshot_engine import ScreenshotEngine
from src.models.translation import Translation

import warnings

# Suppress defusedxml warning for development environment
try:
    import defusedxml.ElementTree as ET
    print("Using defusedxml for secure XML parsing")
except ImportError:
    import xml.etree.ElementTree as ET
    warnings.warn(
        "defusedxml not available. Using xml.etree.ElementTree which may be vulnerable to XML attacks",
        UserWarning,
        stacklevel=2
    )

from src.utils.export_manager import ExportManager
from src.utils.logger import logger
from src.utils.performance_monitor import get_performance_monitor

if TYPE_CHECKING:
    from src.ui.progress_indicator import ProgressInfo, ProgressManager

    def _queue_gui_operation(self, operation_type: str, data: dict):
        """Queue GUI operation for main thread processing"""
        self._gui_queue.put({"type": operation_type, "data": data, "timestamp": time.time()})

        # Trigger processing if not already running
        if not self._gui_processing and hasattr(self, "root"):
            self.root.after_idle(self._process_gui_queue)

    def _process_gui_queue(self):
        """Process queued GUI operations on main thread"""
        if self._gui_processing:
            return

        self._gui_processing = True

        try:
            while not self._gui_queue.empty():
                try:
                    operation = self._gui_queue.get_nowait()
                    self._handle_gui_operation(operation)
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(f"GUI queue processing error: {e}")
        finally:
            self._gui_processing = False

    def _handle_gui_operation(self, operation: dict):
        """Handle specific GUI operation"""
        op_type = operation.get("type")
        data = operation.get("data", {})

        try:
            if op_type == "messagebox":
                self._handle_messagebox_operation(data)
            elif op_type == "file_dialog":
                self._handle_file_dialog_operation(data)
            elif op_type == "widget_update":
                self._handle_widget_update(data)
        except Exception as e:
            logger.error(f"GUI operation error: {e}")

    def _handle_messagebox_operation(self, data: dict):
        """Handle messagebox operations"""
        from tkinter import messagebox

        msg_type = data.get("type", "info")
        args = data.get("args", ())

        if msg_type == "info":
            messagebox.showinfo(*args)
        elif msg_type == "error":
            messagebox.showerror(*args)
        elif msg_type == "warning":
            messagebox.showwarning(*args)

    def _handle_file_dialog_operation(self, data: dict):
        """Handle file dialog operations"""
# filedialog imported at module level

        dialog_type = data.get("type", "open")
        callback = data.get("callback")

        result = None
        if filedialog:
            if dialog_type == "save":
                result = filedialog.asksaveasfilename()
            elif dialog_type == "open":
                result = filedialog.askopenfilename()

        if callback and result:
            callback(result)


class BatchExportManager:
    """Coordinates batch processing and export operations"""

    def _validate_export_params(self, areas, format_type, output_path):
        """Validate export parameters."""
        if not areas:
            return False, "No areas to export"
        if format_type not in ["json", "csv", "xlsx"]:
            return False, f"Unsupported format: {format_type}"
        if not output_path:
            return False, "Output path not specified"
        return True, ""

    def _prepare_export_data(self, areas):
        """Prepare data for export."""
        export_data = []
        for i, area in enumerate(areas):
            try:
                data = {
                    "area_id": i + 1,
                    "coordinates": f"{area.x},{area.y},{area.width},{area.height}",
                    "timestamp": area.timestamp.isoformat() if hasattr(area, "timestamp") else "",
                    "text_extracted": getattr(area, "text", ""),
                    "translation": getattr(area, "translation", ""),
                    "confidence": getattr(area, "confidence", 0.0),
                }
                export_data.append(data)
            except Exception as e:
                logger.error(f"Error preparing export data for area {i}: {e}")
                continue
        return export_data

    def _write_export_file(self, data, format_type, output_path):
        """Write export data to file."""
        try:
            if format_type == "json":
                import json

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            elif format_type == "csv":
                import csv

                if data:
                    with open(output_path, "w", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=data[0].keys())
                        writer.writeheader()
                        writer.writerows(data)
            elif format_type == "xlsx":
                try:
                    import pandas as pd

                    df = pd.DataFrame(data)
                    df.to_excel(output_path, index=False)
                except ImportError:
                    # Fallback to CSV if pandas not available
                    csv_path = output_path.replace(".xlsx", ".csv")
                    return self._write_export_file(data, "csv", csv_path)

            return True, f"Export completed: {output_path}"

        except Exception as e:
            return False, f"Export failed: {str(e)}"

    def _validate_processing_params(self, areas, translation_config):
        """Validate parameters for processing multiple areas."""
        if not areas:
            return False, "No areas to process"
        if not translation_config:
            return False, "Translation config not provided"
        return True, ""

    def _setup_batch_processing(self, total_areas):
        """Setup batch processing state."""
        self.batch_state = {
            "total_areas": total_areas,
            "completed_areas": 0,
            "failed_areas": 0,
            "start_time": time.time(),
            "results": [],
        }

    def _process_single_area(self, area, config):
        """Process a single area with OCR and translation."""
        try:
            result = {
                "area_id": getattr(area, "id", ""),
                "success": False,
                "text": "",
                "translation": "",
                "error": None,
            }

            # OCR processing
            if hasattr(area, "image") and area.image:
                text, confidence = self._extract_text_from_area(area, config)
                result["text"] = text
                result["confidence"] = confidence

                # Translation processing
                if text and config.get("translate", False):
                    translation = self._translate_area_text(text, config)
                    result["translation"] = translation

                result["success"] = True
            else:
                result["error"] = "No image data in area"

            return result

        except Exception as e:
            return {"area_id": getattr(area, "id", ""), "success": False, "error": str(e)}

    def _update_batch_progress(self, completed, total):
        """Update batch processing progress."""
        progress = (completed / total) * 100 if total > 0 else 0

        self.queue_gui_action("update_progress", progress, f"Processing area {completed}/{total}")

        if hasattr(self, "batch_state"):
            self.batch_state["completed_areas"] = completed

    def __init__(
        self,
        screenshot_engine: ScreenshotEngine,
        ocr_processor,
        translation_processor,
        progress_manager: "ProgressManager",
    ):
        self.screenshot_engine = screenshot_engine
        self.progress_manager = progress_manager
        self._lock = threading.Lock()

        # Initialize batch processor
        self.batch_processor = BatchProcessor(
            ocr_processor, translation_processor, max_concurrent=3
        )

        # Export manager
        self.export_manager = ExportManager()

        # Performance monitoring
        self.performance_monitor = get_performance_monitor()
        self._setup_performance_alerts()

    def process_multiple_areas(
        self, areas_coordinates: List[Tuple[int, int, int, int]], job_name: str = "Multiple Areas"
    ) -> str:
        """Process multiple screen areas in batch"""
        try:
            # Capture screenshots for all areas
            screenshots = []
            for x1, y1, x2, y2 in areas_coordinates:
                with self._lock:
                    screenshot_data = self.screenshot_engine.capture_area(x1, y1, x2, y2)
                if screenshot_data:
                    screenshots.append(screenshot_data)

            if not screenshots:
                with self._lock:
                    self.progress_manager.show_error("No valid screenshots captured")
                return ""

            # Create and start batch job
            with self._lock:
                job_id = self.batch_processor.create_batch_job(
                    name=job_name, screenshots=screenshots, coordinates_list=areas_coordinates
                )

            # Show progress indicator for batch job
            with self._lock:
                _ = self.progress_manager.show_progress(
                    title="Batch Processing",
                    message=f"Processing {len(screenshots)} areas...",
                    is_indeterminate=False,
                )

            # Start batch processing with callbacks
            with self._lock:
                success = self.batch_processor.start_batch_job(
                    job_id,
                    progress_callback=self._on_batch_progress,
                    completion_callback=self._on_batch_completion,
                )

            if not success:
                with self._lock:
                    self.progress_manager.show_error("Failed to start batch processing")
                return ""

            logger.info(f"Started batch processing job: {job_id}")
            return job_id

        except Exception as e:
            logger.error("Error starting batch processing", error=e)
            with self._lock:
                self.progress_manager.show_error(f"Batch processing failed: {str(e)}")
            return ""

    def get_batch_job_status(self, job_id: str) -> Optional[BatchJob]:
        """Get status of a batch job"""
        with self._lock:
            return self.batch_processor.get_batch_job(job_id)

    def cancel_batch_job(self, job_id: str) -> bool:
        """Cancel a running batch job"""
        with self._lock:
            return self.batch_processor.cancel_batch_job(job_id)

    def get_batch_results(self, job_id: str) -> List[Translation]:
        """Get results from completed batch job"""
        with self._lock:
            return self.batch_processor.get_job_results(job_id)

    def get_active_batch_jobs(self) -> List[BatchJob]:
        """Get list of active batch jobs"""
        with self._lock:
            return self.batch_processor.get_active_jobs()

    def _on_batch_progress(self, job_id: str, progress: int, message: str) -> None:
        """Callback for batch processing progress"""
        if (
            hasattr(self.progress_manager, "current_progress")
            and self.progress_manager.current_progress
        ):
            from src.ui.progress_indicator import ProgressInfo

            progress_info = ProgressInfo(
                current=progress, total=100, message=message, is_indeterminate=False
            )
            with self._lock:
                self.progress_manager.current_progress.update(progress_info)

    def _on_batch_completion(self, job_id: str, job: BatchJob) -> None:
        """Callback for batch processing completion"""
        # Hide progress indicator
        with self._lock:
            self.progress_manager.hide_progress()

        # Show completion notification
        if job.status == BatchStatus.COMPLETED:
            success_msg = f"Batch completed: {job.completed_items}/{job.total_items} successful"
            if job.failed_items > 0:
                success_msg += f" ({job.failed_items} failed)"
            with self._lock:
                self.progress_manager.show_success(success_msg)
        elif job.status == BatchStatus.CANCELLED:
            with self._lock:
                self.progress_manager.show_warning("Batch processing cancelled")
        else:
            with self._lock:
                self.progress_manager.show_error(
                    f"Batch processing failed: {job.failed_items}/{job.total_items} items failed"
                )

        logger.info(f"Batch job {job_id} completed with status: {job.status}")

    def export_translation_history(
        self, history: List[Translation], format_type: str = "json"
    ) -> Optional[str]:
        """Export translation history to file"""
        try:
            if not history:
                self.progress_manager.show_warning("No translation history to export")
                return None

            # Show file dialog
            file_types = [
                ("JSON files", "*.json"),
                ("CSV files", "*.csv"),
                ("Text files", "*.txt"),
                ("HTML files", "*.html"),
                ("XML files", "*.xml"),
                ("All files", "*.*"),
            ]

            with self._lock:
                suggested_name = self.export_manager.suggest_filename(
                    "translation_history", format_type
                )

                # Thread-safe file dialog request
                file_path = self._show_save_dialog(
                    file_types=file_types, initial_name=suggested_name
                )

            if not file_path:
                return None

            # Determine format from file extension if not specified
            if file_path.endswith(".csv"):
                format_type = "csv"
            elif file_path.endswith(".txt"):
                format_type = "txt"
            elif file_path.endswith(".html"):
                format_type = "html"
            elif file_path.endswith(".xml"):
                format_type = "xml"
            else:
                format_type = "json"

            # Export
            if self.export_manager.export_translations(history, file_path, format_type):
                self.progress_manager.show_success(f"History exported to {Path(file_path).name}")
                return file_path
            else:
                self.progress_manager.show_error("Export failed")
                return None

        except Exception as e:
            logger.error("Error exporting translation history", error=e)
            with self._lock:
                self.progress_manager.show_error(f"Export failed: {str(e)}")
            return None

    def export_batch_results(self, job_id: str, format_type: str = "html") -> Optional[str]:
        """Export batch job results to file"""
        try:
            with self._lock:
                job = self.batch_processor.get_batch_job(job_id)
            if not job:
                with self._lock:
                    self.progress_manager.show_error("Batch job not found")
                return None

            # Show file dialog
            file_types = [
                ("HTML files", "*.html"),
                ("JSON files", "*.json"),
                ("CSV files", "*.csv"),
                ("Text files", "*.txt"),
                ("XML files", "*.xml"),
                ("All files", "*.*"),
            ]

            safe_name = "".join(c for c in job.name if c.isalnum() or c in (" ", "-", "_")).strip()
            with self._lock:
                suggested_name = self.export_manager.suggest_filename(
                    f"batch_{safe_name}", format_type
                )

            # Thread-safe file dialog request
            file_path = self._show_save_dialog(file_types=file_types, initial_name=suggested_name)

            if not file_path:
                return None

            # Determine format from file extension
            if file_path.endswith(".csv"):
                format_type = "csv"
            elif file_path.endswith(".txt"):
                format_type = "txt"
            elif file_path.endswith(".html"):
                format_type = "html"
            elif file_path.endswith(".xml"):
                format_type = "xml"
            else:
                format_type = "json"

            # Export
            if self.export_manager.export_batch_job(
                job, file_path, format_type, include_metadata=True
            ):
                self.progress_manager.show_success(
                    f"Batch results exported to {Path(file_path).name}"
                )
                return file_path
            else:
                with self._lock:
                    self.progress_manager.show_error("Batch export failed")
                return None

        except Exception as e:
            logger.error("Error exporting batch results", error=e)
            with self._lock:
                self.progress_manager.show_error(f"Batch export failed: {str(e)}")
            return None

    def _setup_performance_alerts(self) -> None:
        """Setup performance monitoring alerts"""

        def performance_alert_handler(alert_type: str, alert_data: Dict) -> None:
            """Handle performance alerts with toast notifications"""
            message = alert_data.get("message", f"Performance alert: {alert_type}")

            if alert_type in ["cpu_high", "memory_high"]:
                with self._lock:
                    self.progress_manager.show_warning(message)
            elif alert_type in ["operation_slow", "error_rate_high"]:
                with self._lock:
                    self.progress_manager.show_warning(message)

            logger.warning(f"Performance alert: {alert_type} - {message}")

        with self._lock:
            self.performance_monitor.add_alert_callback(performance_alert_handler)
        logger.info("Performance alerts configured")

    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        with self._lock:
            return self.performance_monitor.get_performance_report()

    def export_performance_metrics(self, file_path: Optional[str] = None) -> Optional[str]:
        """Export performance metrics to file"""
        try:
            if not file_path:
                # Show file dialog to get file path
                from datetime import datetime

                file_types = [("JSON files", "*.json"), ("All files", "*.*")]
                suggested_name = (
                    f"performance_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )

                # Simplified file path handling - would normally show dialog
                file_path = suggested_name

            if not file_path:
                return None

            if self.performance_monitor.export_metrics(file_path):
                self.progress_manager.show_success(
                    f"Performance metrics exported to {Path(file_path).name}"
                )
                return file_path
            else:
                with self._lock:
                    self.progress_manager.show_error("Failed to export performance metrics")
                return None

        except Exception as e:
            logger.error("Error exporting performance metrics", error=e)
            with self._lock:
                self.progress_manager.show_error(f"Metrics export failed: {str(e)}")
            return None

    def _queue_gui_operation(self, operation_type: str, data: dict):
        """Queue GUI operation for main thread processing"""
        self._gui_queue.put({"type": operation_type, "data": data, "timestamp": time.time()})

        # Trigger processing if not already running
        if not self._gui_processing and hasattr(self, "root"):
            self.root.after_idle(self._process_gui_queue)

    def _process_gui_queue(self):
        """Process queued GUI operations on main thread"""
        if self._gui_processing:
            return

        self._gui_processing = True

        try:
            while not self._gui_queue.empty():
                try:
                    operation = self._gui_queue.get_nowait()
                    self._handle_gui_operation(operation)
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(f"GUI queue processing error: {e}")
        finally:
            self._gui_processing = False

    def _handle_gui_operation(self, operation: dict):
        """Handle specific GUI operation"""
        op_type = operation.get("type")
        data = operation.get("data", {})

        try:
            if op_type == "messagebox":
                self._handle_messagebox_operation(data)
            elif op_type == "file_dialog":
                self._handle_file_dialog_operation(data)
            elif op_type == "widget_update":
                self._handle_widget_update(data)
        except Exception as e:
            logger.error(f"GUI operation error: {e}")

    def _handle_messagebox_operation(self, data: dict):
        """Handle messagebox operations"""
        from tkinter import messagebox

        msg_type = data.get("type", "info")
        args = data.get("args", ())

        if msg_type == "info":
            messagebox.showinfo(*args)
        elif msg_type == "error":
            messagebox.showerror(*args)
        elif msg_type == "warning":
            messagebox.showwarning(*args)

    def _handle_file_dialog_operation(self, data: dict):
        """Handle file dialog operations"""
# filedialog imported at module level

        dialog_type = data.get("type", "open")
        callback = data.get("callback")

        result = None
        if filedialog:
            if dialog_type == "save":
                result = filedialog.asksaveasfilename()
            elif dialog_type == "open":
                result = filedialog.askopenfilename()

        if callback and result:
            callback(result)

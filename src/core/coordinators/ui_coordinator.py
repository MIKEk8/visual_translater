"""
UICoordinator - User interface management coordinator

Single Responsibility: Manages all UI components, progress indicators,
notifications, dialogs, and settings window coordination.

Responsibilities:
- Settings window lifecycle management
- Progress indicators and toast notifications
- Error and success message handling
- Translation history display
- UI state coordination
"""

import queue
import threading
# Import tkinter modules only when available
try:
    from tkinter import TclError, messagebox
except ImportError:
    # Mock TclError and messagebox for compatibility
    class TclError(Exception):
        pass
    
    class MockMessageBox:
        def showerror(self, *args, **kwargs):
            print(f"Mock messagebox.showerror: {args}")
        def showinfo(self, *args, **kwargs):
            print(f"Mock messagebox.showinfo: {args}")
        def showwarning(self, *args, **kwargs):
            print(f"Mock messagebox.showwarning: {args}")
    
    messagebox = MockMessageBox()
    print("tkinter недоступен в src.core.coordinators.ui_coordinator")
    print("Mock GUI компоненты загружены")
from typing import TYPE_CHECKING, List, Optional

from src.models.translation import Translation
from src.services.config_manager import ConfigManager
from src.ui.progress_indicator import ProgressManager
from src.ui.settings_window import SettingsWindow
from src.utils.exceptions import (
    InvalidAreaError,
    OCRError,
    ScreenshotCaptureError,
    TranslationFailedError,
    TTSError,
)
from src.utils.logger import logger

if TYPE_CHECKING:
    import tkinter as tk

    from src.core.tts_engine import TTSProcessor

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
        from tkinter import filedialog

        dialog_type = data.get("type", "open")
        callback = data.get("callback")

        result = None
        if dialog_type == "save":
            result = filedialog.asksaveasfilename()
        elif dialog_type == "open":
            result = filedialog.askopenfilename()

        if callback and result:
            callback(result)


class UICoordinator:
    """Coordinates user interface components and interactions"""

    def __init__(self, root: "tk.Tk", config_manager: ConfigManager, tts_processor: "TTSProcessor"):
        self.root = root
        self.config_manager = config_manager
        self.tts_processor = tts_processor
        self._lock = threading.Lock()

        # UI components
        self.progress_manager = ProgressManager(self.root)
        self.settings_window = None

    def show_progress(self, title: str, message: str, is_indeterminate: bool = True):
        """Show progress indicator"""
        with self._lock:
            return self.progress_manager.show_progress(
                title=title, message=message, is_indeterminate=is_indeterminate
            )

    def hide_progress(self) -> None:
        """Hide progress indicator"""
        with self._lock:
            self.progress_manager.hide_progress()

    def show_success(self, message: str) -> None:
        """Show success toast notification"""
        with self._lock:
            self.progress_manager.show_success(message)

    def show_warning(self, message: str) -> None:
        """Show warning toast notification"""
        with self._lock:
            self.progress_manager.show_warning(message)

    def show_error(self, message: str) -> None:
        """Show error toast notification"""
        with self._lock:
            self.progress_manager.show_error(message)

    def handle_translation_success(self, translation: Translation) -> None:
        """Handle successful translation with UI feedback"""
        # Hide progress indicator
        self.hide_progress()

        if translation:
            # Show success toast with truncated text
            translated_text = translation.translated_text
            display_text = (
                translated_text[:50] + "..." if len(translated_text) > 50 else translated_text
            )
            self.show_success(f"Translated: {display_text}")

    def handle_translation_error(self, error: Exception) -> None:
        """Handle translation error with appropriate UI feedback"""
        # Hide progress indicator
        self.hide_progress()

        # Show error-specific messages
        if isinstance(error, InvalidAreaError):
            logger.warning(f"Invalid area selected: {error.coordinates}")
            self.show_warning("Please select a larger area with text")
        elif isinstance(error, ScreenshotCaptureError):
            logger.error(f"Screenshot capture failed: {error.reason}")
            self.show_error("Failed to capture screen area")
        elif isinstance(error, TranslationFailedError):
            logger.error(f"Translation failed: {error.reason}")
            self.show_error("Translation service unavailable")
        elif isinstance(error, OCRError):
            logger.error(f"OCR failed: {error}")
            self.show_warning("Could not extract text from image")
        elif isinstance(error, TTSError):
            logger.error(f"TTS failed: {error}")
            self.show_warning("Text-to-speech not available")
        else:
            logger.error(f"Unexpected error: {error}")
            self.show_error(f"Operation failed: {str(error)}")

    def show_translation_history(self, history: List[Translation]) -> None:
        """Show translation history dialog"""
        logger.info("UICoordinator: Showing translation history")

        if not history:
            self._queue_gui_operation(
                "messagebox", {"type": "info", "args": ("История", "История переводов пуста")}
            )
            return

        # Create history display - show last 10 translations
        history_text = "\n\n".join(
            [
                f"[{t.timestamp.strftime('%H:%M:%S')}] {t.target_language.upper()}\n{t.original_text}\n→ {t.translated_text}"
                for t in history[-10:]  # Last 10
            ]
        )

        self._queue_gui_operation(
            "messagebox", {"type": "info", "args": ("История переводов", history_text)}
        )

    def show_batch_history(self, jobs: List) -> None:
        """Show batch processing history dialog"""
        logger.info("UICoordinator: Showing batch history")

        if not jobs:
            self._queue_gui_operation(
                "messagebox", {"type": "info", "args": ("Batch History", "No active batch jobs")}
            )
            return

        # Create batch history display
        history_text = "\n\n".join(
            [
                f"[{job.created_at.strftime('%H:%M:%S')}] {job.name}\n"
                f"Status: {job.status.value.title()}\n"
                f"Progress: {job.progress}% ({job.completed_items}/{job.total_items})\n"
                f"Success Rate: {job.success_rate:.1f}%"
                for job in jobs[-5:]  # Last 5 jobs
            ]
        )

        self._queue_gui_operation(
            "messagebox", {"type": "info", "args": ("Batch Processing History", history_text)}
        )

    def open_settings(self) -> None:
        """Open settings window"""
        logger.info("UICoordinator: Opening settings window")

        # Check if window exists and is valid
        if self.settings_window is None:
            with self._lock:
                self.settings_window = SettingsWindow(self.config_manager, self.tts_processor)
        else:
            try:
                # Check if window still exists
                if not self.settings_window.window.winfo_exists():
                    self.settings_window = SettingsWindow(self.config_manager, self.tts_processor)
            except (AttributeError, TclError):
                # Window was destroyed, create new one
                with self._lock:
                    self.settings_window = SettingsWindow(self.config_manager, self.tts_processor)

        with self._lock:
            self.settings_window.show()

    def show_info_dialog(self, title: str, message: str) -> None:
        """Show information dialog"""
        self._queue_gui_operation("messagebox", {"type": "info", "args": (title, message)})

    def show_error_dialog(self, title: str, message: str) -> None:
        """Show error dialog"""
        self._queue_gui_operation("messagebox", {"type": "error", "args": (title, message)})

    def show_warning_dialog(self, title: str, message: str) -> None:
        """Show warning dialog"""
        self._queue_gui_operation("messagebox", {"type": "warning", "args": (title, message)})

    def ask_yes_no(self, title: str, message: str) -> bool:
        """Show yes/no confirmation dialog"""
        return messagebox.askyesno(title, message)

    def update_progress(self, progress: int, message: str = None) -> None:
        """Update progress indicator"""
        if (
            hasattr(self.progress_manager, "current_progress")
            and self.progress_manager.current_progress
        ):
            from src.ui.progress_indicator import ProgressInfo

            progress_info = ProgressInfo(
                current=progress,
                total=100,
                message=message or "Processing...",
                is_indeterminate=False,
            )
            with self._lock:
                self.progress_manager.current_progress.update(progress_info)

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
        from tkinter import filedialog

        dialog_type = data.get("type", "open")
        callback = data.get("callback")

        result = None
        if dialog_type == "save":
            result = filedialog.asksaveasfilename()
        elif dialog_type == "open":
            result = filedialog.askopenfilename()

        if callback and result:
            callback(result)

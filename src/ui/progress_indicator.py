"""
Progress indicator components for showing operation status
"""

import threading
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Callable, Optional

from src.utils.logger import logger


@dataclass
class ProgressInfo:
    """Information about current progress"""

    current: int = 0
    total: int = 100
    message: str = ""
    is_indeterminate: bool = False


class ProgressIndicator:
    """Simple progress indicator with message"""

    def __init__(self, parent: tk.Widget, title: str = "Processing..."):
        self._lock = threading.Lock()
        self.parent = parent
        self.title = title
        self.window: Optional[tk.Toplevel] = None
        self.progress_var = tk.DoubleVar()
        self.message_var = tk.StringVar()
        self.is_visible = False
        self._update_lock = threading.Lock()

    def show(self, message: str = "", is_indeterminate: bool = True) -> None:
        """Show progress indicator"""
        if self.is_visible:
            return

        self.is_visible = True
        self.window = tk.Toplevel(self.parent)
        self.window.title(self.title)
        self.window.geometry("400x120")
        self.window.resizable(False, False)
        self.window.transient(self.parent)
        self.window.grab_set()

        # Center on parent
        self.window.geometry(
            "+%d+%d" % (self.parent.winfo_rootx() + 50, self.parent.winfo_rooty() + 50)
        )

        # Create widgets
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Message label
        self.message_var.set(message or "Processing...")
        message_label = ttk.Label(
            main_frame, textvariable=self.message_var, font=("TkDefaultFont", 10)
        )
        message_label.pack(pady=(0, 10))

        # Progress bar
        mode = "indeterminate" if is_indeterminate else "determinate"
        self.progress_bar = ttk.Progressbar(
            main_frame, mode=mode, variable=self.progress_var, length=350
        )
        self.progress_bar.pack(pady=(0, 10))

        if is_indeterminate:
            self.progress_bar.start(10)

        # Cancel button placeholder (can be customized)
        self.cancel_button = ttk.Button(main_frame, text="Cancel", state="disabled")
        self.cancel_button.pack()

        self.window.update()
        logger.debug(f"Progress indicator shown: {message}")

    def update(self, progress_info: ProgressInfo) -> None:
        """Update progress indicator"""
        if not self.is_visible or not self.window:
            return

        with self._update_lock:
            try:
                # Update message
                if progress_info.message:
                    self.message_var.set(progress_info.message)

                # Update progress
                if not progress_info.is_indeterminate:
                    self.progress_bar.stop()
                    self.progress_bar.config(mode="determinate")
                    if progress_info.total > 0:
                        value = (progress_info.current / progress_info.total) * 100
                        self.progress_var.set(value)
                else:
                    self.progress_bar.config(mode="indeterminate")
                    if not self.progress_bar.cget("mode") == "indeterminate":
                        self.progress_bar.start(10)

                self.window.update()

            except tk.TclError:
                # Window was destroyed
                self.is_visible = False

    def set_cancel_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for cancel button"""
        if self.window and hasattr(self, "cancel_button"):
            self.cancel_button.config(state="normal", command=callback)

    def hide(self) -> None:
        """Hide progress indicator"""
        if not self.is_visible:
            return

        self.is_visible = False
        if self.window:
            try:
                self.window.grab_release()
                self.window.destroy()
            except tk.TclError:
                pass
            self.window = None

        logger.debug("Progress indicator hidden")


class ToastNotification:
    """Simple toast notification for showing brief messages"""

    def __init__(self, parent: tk.Widget):
        self._lock = threading.Lock()
        self.parent = parent
        self.toasts = []  # Track active toasts

    def show(self, message: str, type_: str = "info", duration: int = 3000) -> None:
        """Show toast notification"""
        toast = tk.Toplevel(self.parent)
        toast.withdraw()  # Hide initially

        # Configure toast window
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)

        # Style based on type
        if type_ == "success":
            bg_color = "#d4edda"
            text_color = "#155724"
            border_color = "#c3e6cb"
        elif type_ == "error":
            bg_color = "#f8d7da"
            text_color = "#721c24"
            border_color = "#f5c6cb"
        elif type_ == "warning":
            bg_color = "#fff3cd"
            text_color = "#856404"
            border_color = "#ffeaa7"
        else:  # info
            bg_color = "#d1ecf1"
            text_color = "#0c5460"
            border_color = "#bee5eb"

        # Create frame with border
        frame = tk.Frame(toast, bg=border_color, bd=1, relief="solid")
        frame.pack(fill=tk.BOTH, expand=True)

        # Inner frame
        inner_frame = tk.Frame(frame, bg=bg_color, padx=15, pady=10)
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # Message label
        label = tk.Label(
            inner_frame,
            text=message,
            bg=bg_color,
            fg=text_color,
            font=("TkDefaultFont", 9),
            wraplength=300,
        )
        label.pack()

        # Position toast
        self._position_toast(toast)

        # Show with animation
        toast.deiconify()
        self.toasts.append(toast)

        # Auto-hide after duration
        def hide_toast():
            try:
                if toast in self.toasts:
                    self.toasts.remove(toast)
                toast.destroy()
                self._reposition_toasts()
            except tk.TclError:
                pass

        toast.after(duration, hide_toast)
        logger.debug(f"Toast shown: {type_} - {message}")

    def _position_toast(self, toast: tk.Toplevel) -> None:
        """Position toast in bottom-right corner"""
        toast.update_idletasks()

        # Get screen dimensions
        screen_width = toast.winfo_screenwidth()
        screen_height = toast.winfo_screenheight()

        # Get toast dimensions
        toast_width = toast.winfo_reqwidth()
        toast_height = toast.winfo_reqheight()

        # Calculate position (bottom-right with margin)
        margin = 20
        x = screen_width - toast_width - margin
        y = screen_height - toast_height - margin - (len(self.toasts) * (toast_height + 10))

        toast.geometry(f"+{x}+{y}")

    def _reposition_toasts(self) -> None:
        """Reposition remaining toasts"""
        for i, toast in enumerate(self.toasts):
            try:
                toast.update_idletasks()
                screen_width = toast.winfo_screenwidth()
                screen_height = toast.winfo_screenheight()
                toast_width = toast.winfo_reqwidth()
                toast_height = toast.winfo_reqheight()

                margin = 20
                x = screen_width - toast_width - margin
                y = screen_height - toast_height - margin - (i * (toast_height + 10))

                toast.geometry(f"+{x}+{y}")
            except tk.TclError:
                if toast in self.toasts:
                    self.toasts.remove(toast)


class ProgressManager:
    """Manages progress indicators and notifications for the application"""

    def __init__(self, parent: tk.Widget):
        self._lock = threading.Lock()
        self.parent = parent
        self.toast = ToastNotification(parent)
        self.current_progress: Optional[ProgressIndicator] = None

    def show_progress(
        self, title: str = "Processing...", message: str = "", is_indeterminate: bool = True
    ) -> ProgressIndicator:
        """Show progress indicator"""
        if self.current_progress:
            self.current_progress.hide()

        self.current_progress = ProgressIndicator(self.parent, title)
        self.current_progress.show(message, is_indeterminate)
        return self.current_progress

    def hide_progress(self) -> None:
        """Hide current progress indicator"""
        if self.current_progress:
            self.current_progress.hide()
            self.current_progress = None

    def show_success(self, message: str, duration: int = 3000) -> None:
        """Show success toast"""
        self.toast.show(message, "success", duration)

    def show_error(self, message: str, duration: int = 5000) -> None:
        """Show error toast"""
        self.toast.show(message, "error", duration)

    def show_warning(self, message: str, duration: int = 4000) -> None:
        """Show warning toast"""
        self.toast.show(message, "warning", duration)

    def show_info(self, message: str, duration: int = 3000) -> None:
        """Show info toast"""
        self.toast.show(message, "info", duration)

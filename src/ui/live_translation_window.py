"""
Live Translation Window for managing continuous translation sessions.

This module provides the UI for controlling and monitoring live translation
with real-time status updates and region management.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, List, Callable, Any
from datetime import datetime

from src.services.live_translation_service import LiveTranslationService, CaptureRegion
from src.utils.logger import logger


class LiveTranslationWindow:
    """Window for live translation controls and monitoring."""

    def __init__(self, parent=None, live_service: Optional[LiveTranslationService] = None):
        """Initialize the live translation window.

        Args:
            parent: Parent window
            live_service: Live translation service instance
        """
        self.parent = parent
        self.live_service = live_service

        # Window and widgets
        self.window: Optional[tk.Toplevel] = None
        self.is_visible = False

        # Status variables
        self.status_var = tk.StringVar(value="Stopped")
        self.fps_var = tk.StringVar(value="0.0")
        self.regions_var = tk.StringVar(value="0")

        # Controls
        self.fps_scale: Optional[tk.Scale] = None
        self.threshold_scale: Optional[tk.Scale] = None

        logger.debug("LiveTranslationWindow initialized")

    def show(self) -> None:
        """Show the live translation window."""
        if not self.window:
            self._create_window()

        if not self.is_visible:
            self.window.deiconify()
            self.is_visible = True
            self._update_status()

    def hide(self) -> None:
        """Hide the live translation window."""
        if self.window and self.is_visible:
            self.window.withdraw()
            self.is_visible = False

    def _create_window(self) -> None:
        """Create the main window."""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Live Translation")
        self.window.geometry("400x500")

        # Create main layout
        self._create_status_panel()
        self._create_controls_panel()
        self._create_regions_panel()

        # Bind close event
        self.window.protocol("WM_DELETE_WINDOW", self.hide)

    def _create_status_panel(self) -> None:
        """Create the status information panel."""
        status_frame = ttk.LabelFrame(self.window, text="Status")
        status_frame.pack(fill="x", padx=10, pady=5)

        # Status row
        ttk.Label(status_frame, text="Status:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(status_frame, textvariable=self.status_var).grid(row=0, column=1, sticky="w", padx=5, pady=2)

        # FPS row
        ttk.Label(status_frame, text="FPS:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(status_frame, textvariable=self.fps_var).grid(row=1, column=1, sticky="w", padx=5, pady=2)

        # Regions row
        ttk.Label(status_frame, text="Regions:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(status_frame, textvariable=self.regions_var).grid(row=2, column=1, sticky="w", padx=5, pady=2)

    def _create_controls_panel(self) -> None:
        """Create the controls panel."""
        controls_frame = ttk.LabelFrame(self.window, text="Controls")
        controls_frame.pack(fill="x", padx=10, pady=5)

        # Start/Stop buttons
        button_frame = ttk.Frame(controls_frame)
        button_frame.pack(fill="x", padx=5, pady=5)

        ttk.Button(button_frame, text="Start", command=self._start_live_translation).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Stop", command=self._stop_live_translation).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Pause", command=self._pause_live_translation).pack(side="left", padx=5)

        # FPS control
        ttk.Label(controls_frame, text="FPS:").pack(anchor="w", padx=5)
        self.fps_scale = tk.Scale(
            controls_frame,
            from_=0.5,
            to=10.0,
            resolution=0.5,
            orient="horizontal"
        )
        self.fps_scale.set(2.0)
        self.fps_scale.pack(fill="x", padx=5, pady=2)

        # Threshold control
        ttk.Label(controls_frame, text="Change Threshold (%):").pack(anchor="w", padx=5)
        self.threshold_scale = tk.Scale(
            controls_frame,
            from_=1.0,
            to=20.0,
            resolution=0.5,
            orient="horizontal"
        )
        self.threshold_scale.set(5.0)
        self.threshold_scale.pack(fill="x", padx=5, pady=2)

    def _create_regions_panel(self) -> None:
        """Create the regions management panel."""
        regions_frame = ttk.LabelFrame(self.window, text="Capture Regions")
        regions_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Regions list
        self.regions_listbox = tk.Listbox(regions_frame)
        self.regions_listbox.pack(fill="both", expand=True, padx=5, pady=5)

        # Region buttons
        region_buttons = ttk.Frame(regions_frame)
        region_buttons.pack(fill="x", padx=5, pady=5)

        ttk.Button(region_buttons, text="Add Region", command=self._add_region).pack(side="left", padx=2)
        ttk.Button(region_buttons, text="Remove", command=self._remove_region).pack(side="left", padx=2)
        ttk.Button(region_buttons, text="Edit", command=self._edit_region).pack(side="left", padx=2)

    def _start_live_translation(self) -> None:
        """Start live translation."""
        if self.live_service:
            # Get current settings
            fps = self.fps_scale.get() if self.fps_scale else 2.0
            threshold = self.threshold_scale.get() if self.threshold_scale else 5.0

            # Update service settings
            self.live_service.set_fps(fps)
            self.live_service.change_detector.threshold = threshold

            # Start the service
            # Note: This would be async in real implementation
            logger.info("Starting live translation")
            self.status_var.set("Starting...")

    def _stop_live_translation(self) -> None:
        """Stop live translation."""
        if self.live_service:
            logger.info("Stopping live translation")
            self.status_var.set("Stopping...")

    def _pause_live_translation(self) -> None:
        """Pause/resume live translation."""
        if self.live_service:
            logger.info("Toggling live translation pause")

    def _add_region(self) -> None:
        """Add a new capture region."""
        # This would open a region selection dialog
        region = CaptureRegion(
            x=100,
            y=100,
            width=400,
            height=300,
            name=f"Region {len(self.regions_listbox.get(0, tk.END)) + 1}"
        )

        self.regions_listbox.insert(tk.END, f"{region.name} ({region.width}x{region.height})")
        self._update_regions_count()

    def _remove_region(self) -> None:
        """Remove selected region."""
        selection = self.regions_listbox.curselection()
        if selection:
            self.regions_listbox.delete(selection[0])
            self._update_regions_count()

    def _edit_region(self) -> None:
        """Edit selected region."""
        selection = self.regions_listbox.curselection()
        if selection:
            # This would open an edit dialog
            logger.debug(f"Editing region {selection[0]}")

    def _update_status(self) -> None:
        """Update status information."""
        if self.live_service:
            status = self.live_service.get_status()

            if status["is_active"]:
                if status["is_paused"]:
                    self.status_var.set("Paused")
                else:
                    self.status_var.set("Running")
            else:
                self.status_var.set("Stopped")

            self.fps_var.set(f"{status['fps_actual']:.1f}")
            self.regions_var.set(str(status['regions_count']))

        # Schedule next update
        if self.window and self.is_visible:
            self.window.after(1000, self._update_status)

    def _update_regions_count(self) -> None:
        """Update the regions count display."""
        count = len(self.regions_listbox.get(0, tk.END))
        self.regions_var.set(str(count))

    def set_live_service(self, service: LiveTranslationService) -> None:
        """Set the live translation service."""
        self.live_service = service

    def get_current_settings(self) -> Dict[str, Any]:
        """Get current window settings."""
        return {
            "fps": self.fps_scale.get() if self.fps_scale else 2.0,
            "threshold": self.threshold_scale.get() if self.threshold_scale else 5.0,
            "regions_count": len(self.regions_listbox.get(0, tk.END)) if hasattr(self, 'regions_listbox') else 0
        }

    def destroy(self) -> None:
        """Destroy the window."""
        if self.window:
            self.window.destroy()
            self.window = None
            self.is_visible = False
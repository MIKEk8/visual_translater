from PIL import ImageGrab

"""
Enhanced capture interface with smart area detection integration.
"""

import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional, Tuple

try:
    import cv2
except ImportError:
    print("OpenCV не доступен в данной среде")
    cv2 = None
import numpy as np
from PIL import Image, ImageTk

from src.ai.smart_area_detection import DetectionConfig, SmartAreaDetector, TextRegion
from src.ui.real_time_overlay import OverlayConfig
from src.utils.logger import logger


class EnhancedCaptureInterface:
    """Enhanced screen capture interface with smart area detection."""

    def __init__(self, parent_app):
        self.parent_app = parent_app

        # Smart detection
        self.smart_detector = SmartAreaDetector()
        self.detected_regions: List[TextRegion] = []
        self.selected_region_index = 0

        # UI components
        self.capture_window: Optional[tk.Toplevel] = None
        self.canvas: Optional[tk.Canvas] = None
        self.preview_image: Optional[ImageTk.PhotoImage] = None

        # Capture state
        self.is_capture_mode = False
        self.current_screenshot: Optional[np.ndarray] = None
        self.manual_selection_active = False

        # Selection state
        self.selection_start: Optional[Tuple[int, int]] = None
        self.selection_rect: Optional[int] = None

        # Callbacks
        self.on_area_selected: Optional[Callable[[Tuple[int, int, int, int]], None]] = None

        logger.info("Enhanced capture interface initialized")

    def start_smart_capture(self) -> None:
        """Start smart capture with area detection."""
        try:
            # Take screenshot
            screenshot = self._take_screenshot()
            if screenshot is None:
                logger.error("Failed to take screenshot")
                return

            self.current_screenshot = screenshot

            # Detect text regions
            self._detect_text_regions()

            # Show capture interface
            self._show_capture_interface()

            logger.info("Smart capture started")

        except Exception as e:
            logger.error(f"Failed to start smart capture: {e}")

    def _take_screenshot(self) -> Optional[np.ndarray]:
        """Take screenshot of entire screen."""
        try:
            # Use PIL to take screenshot

            # Take screenshot
            pil_image = ImageGrab.grab()

            # Convert to OpenCV format
            opencv_image = (cv2.cvtColor if cv2 else None)(
                np.array(pil_image), (cv2.COLOR_RGB2BGR if cv2 else None)
            )

            return opencv_image

        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None

    def _detect_text_regions(self) -> None:
        """Detect text regions in screenshot."""
        if self.current_screenshot is None:
            return

        try:
            # Run detection in separate thread to avoid blocking UI
            detection_thread = threading.Thread(target=self._run_detection, daemon=True)
            detection_thread.start()

        except Exception as e:
            logger.error(f"Text region detection failed: {e}")

    def _run_detection(self) -> None:
        """Run text detection in background thread."""
        try:
            self.detected_regions = self.smart_detector.detect_text_regions(self.current_screenshot)

            # Update UI on main thread
            if self.capture_window:
                self.capture_window.after(0, self._update_detected_regions)

            logger.debug(f"Detected {len(self.detected_regions)} text regions")

        except Exception as e:
            logger.error(f"Background detection failed: {e}")

    def _show_capture_interface(self) -> None:
        """Show enhanced capture interface."""
        # Create capture window
        self.capture_window = tk.Toplevel()
        self.capture_window.title("Smart Area Selection")
        self.capture_window.attributes("-fullscreen", True)
        self.capture_window.attributes("-alpha", 0.95)
        self.capture_window.configure(bg="black")

        # Create main frame
        main_frame = ttk.Frame(self.capture_window)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create canvas for screenshot display
        self.canvas = tk.Canvas(main_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Display screenshot
        self._display_screenshot()

        # Create control panel
        self._create_control_panel()

        # Bind events
        self._bind_capture_events()

        # Start with smart mode enabled
        self.is_capture_mode = True

    def _display_screenshot(self) -> None:
        """Display screenshot on canvas."""
        if self.current_screenshot is None or self.canvas is None:
            return

        try:
            # Convert OpenCV image to PIL
            pil_image = Image.fromarray(
                (cv2.cvtColor if cv2 else None)(
                    self.current_screenshot, (cv2.COLOR_BGR2RGB if cv2 else None)
                )
            )

            # Get canvas size
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width <= 1 or canvas_height <= 1:
                # Canvas not ready, try again later
                self.capture_window.after(100, self._display_screenshot)
                return

            # Resize image to fit canvas while maintaining aspect ratio
            img_width, img_height = pil_image.size
            scale_x = canvas_width / img_width
            scale_y = canvas_height / img_height
            scale = min(scale_x, scale_y)

            new_width = int(img_width * scale)
            new_height = int(img_height * scale)

            resized_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert to PhotoImage
            self.preview_image = ImageTk.PhotoImage(resized_image)

            # Display on canvas
            self.canvas.delete("screenshot")
            self.canvas.create_image(
                canvas_width // 2, canvas_height // 2, image=self.preview_image, tags="screenshot"
            )

            # Store scale factor for coordinate conversion
            self.scale_factor = scale
            self.image_offset_x = (canvas_width - new_width) // 2
            self.image_offset_y = (canvas_height - new_height) // 2

        except Exception as e:
            logger.error(f"Failed to display screenshot: {e}")

    def _create_control_panel(self) -> None:
        """Create control panel with options."""
        # Control frame at the top
        control_frame = tk.Frame(self.capture_window, bg="black", height=80)
        control_frame.pack(side=tk.TOP, fill=tk.X)
        control_frame.pack_propagate(False)

        # Title
        title_label = tk.Label(
            control_frame,
            text="Smart Area Selection - Click on detected regions or draw manual selection",
            fg="white",
            bg="black",
            font=("Arial", 14),
        )
        title_label.pack(pady=10)

        # Button frame
        button_frame = tk.Frame(control_frame, bg="black")
        button_frame.pack()

        # Mode toggle button
        self.mode_button = tk.Button(
            button_frame,
            text="Smart Mode: ON",
            command=self._toggle_capture_mode,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
        )
        self.mode_button.pack(side=tk.LEFT, padx=5)

        # Region navigation buttons
        self.prev_button = tk.Button(
            button_frame,
            text="◀ Previous",
            command=self._select_previous_region,
            bg="#2196F3",
            fg="white",
        )
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.next_button = tk.Button(
            button_frame, text="Next ▶", command=self._select_next_region, bg="#2196F3", fg="white"
        )
        self.next_button.pack(side=tk.LEFT, padx=5)

        # Action buttons
        self.select_button = tk.Button(
            button_frame,
            text="Select Region",
            command=self._select_current_region,
            bg="#FF9800",
            fg="white",
            font=("Arial", 10, "bold"),
        )
        self.select_button.pack(side=tk.LEFT, padx=10)

        self.cancel_button = tk.Button(
            button_frame, text="Cancel", command=self._cancel_capture, bg="#F44336", fg="white"
        )
        self.cancel_button.pack(side=tk.LEFT, padx=5)

        # Region info
        self.info_label = tk.Label(
            control_frame,
            text="Detecting text regions...",
            fg="yellow",
            bg="black",
            font=("Arial", 10),
        )
        self.info_label.pack(pady=5)

    def _bind_capture_events(self) -> None:
        """Bind capture interface events."""
        if not self.canvas:
            return

        # Mouse events
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Motion>", self._on_canvas_motion)

        # Keyboard events
        self.capture_window.bind("<KeyPress>", self._on_key_press)
        self.capture_window.focus_set()

    def _update_detected_regions(self) -> None:
        """Update UI with detected regions."""
        if not self.canvas:
            return

        # Clear previous region highlights
        self.canvas.delete("region")

        # Draw detected regions
        for i, region in enumerate(self.detected_regions):
            # Convert coordinates to canvas coordinates
            canvas_coords = self._image_to_canvas_coords(
                region.x, region.y, region.width, region.height
            )

            if canvas_coords:
                x1, y1, x2, y2 = canvas_coords

                # Choose color based on selection
                color = "#00ff00" if i == self.selected_region_index else "#ffff00"
                width = 3 if i == self.selected_region_index else 2

                # Draw rectangle
                self.canvas.create_rectangle(
                    x1, y1, x2, y2, outline=color, width=width, tags="region"
                )

                # Draw region number
                self.canvas.create_text(
                    x1 + 5,
                    y1 + 5,
                    text=str(i + 1),
                    fill=color,
                    font=("Arial", 12, "bold"),
                    tags="region",
                )

                # Draw confidence indicator
                confidence_text = f"{region.confidence:.2f}"
                self.canvas.create_text(
                    x2 - 5,
                    y1 + 5,
                    text=confidence_text,
                    fill=color,
                    font=("Arial", 10),
                    anchor="ne",
                    tags="region",
                )

        # Update info
        self._update_info_display()

    def _image_to_canvas_coords(
        self, x: int, y: int, width: int, height: int
    ) -> Optional[Tuple[int, int, int, int]]:
        """Convert image coordinates to canvas coordinates."""
        try:
            # Apply scale factor and offset
            canvas_x1 = int(x * self.scale_factor) + self.image_offset_x
            canvas_y1 = int(y * self.scale_factor) + self.image_offset_y
            canvas_x2 = canvas_x1 + int(width * self.scale_factor)
            canvas_y2 = canvas_y1 + int(height * self.scale_factor)

            return (canvas_x1, canvas_y1, canvas_x2, canvas_y2)

        except AttributeError:
            # Scale factor not set yet
            return None

    def _canvas_to_image_coords(self, canvas_x: int, canvas_y: int) -> Tuple[int, int]:
        """Convert canvas coordinates to image coordinates."""
        try:
            image_x = int((canvas_x - self.image_offset_x) / self.scale_factor)
            image_y = int((canvas_y - self.image_offset_y) / self.scale_factor)
            return (image_x, image_y)
        except AttributeError:
            return (canvas_x, canvas_y)

    def _toggle_capture_mode(self) -> None:
        """Toggle between smart and manual capture modes."""
        self.is_capture_mode = not self.is_capture_mode

        if self.is_capture_mode:
            self.mode_button.config(text="Smart Mode: ON", bg="#4CAF50")
            self._update_detected_regions()
        else:
            self.mode_button.config(text="Manual Mode: ON", bg="#FF5722")
            self.canvas.delete("region")

        self._update_info_display()

    def _select_previous_region(self) -> None:
        """Select previous detected region."""
        if not self.detected_regions:
            return

        self.selected_region_index = (self.selected_region_index - 1) % len(self.detected_regions)
        self._update_detected_regions()

    def _select_next_region(self) -> None:
        """Select next detected region."""
        if not self.detected_regions:
            return

        self.selected_region_index = (self.selected_region_index + 1) % len(self.detected_regions)
        self._update_detected_regions()

    def _select_current_region(self) -> None:
        """Select currently highlighted region."""
        if self.is_capture_mode and self.detected_regions:
            # Smart mode: use selected detected region
            region = self.detected_regions[self.selected_region_index]
            coordinates = (region.x, region.y, region.x + region.width, region.y + region.height)
            self._complete_selection(coordinates)
        else:
            # Manual mode: need manual selection
            self.info_label.config(text="Draw a rectangle around the text area", fg="yellow")

    def _cancel_capture(self) -> None:
        """Cancel capture and close interface."""
        if self.capture_window:
            self.capture_window.destroy()
            self.capture_window = None

        self.current_screenshot = None
        self.detected_regions = []
        logger.info("Capture cancelled")

    def _update_info_display(self) -> None:
        """Update information display."""
        if not self.info_label:
            return

        if self.is_capture_mode:
            if self.detected_regions:
                region = self.detected_regions[self.selected_region_index]
                text = (
                    f"Region {self.selected_region_index + 1}/{len(self.detected_regions)} - "
                    f"Size: {region.width}x{region.height}, "
                    f"Confidence: {region.confidence:.2f}"
                )
                self.info_label.config(text=text, fg="lightgreen")
            else:
                self.info_label.config(text="Detecting text regions...", fg="yellow")
        else:
            self.info_label.config(text="Manual mode: Click and drag to select area", fg="orange")

    def _on_canvas_click(self, event) -> None:
        """Handle canvas click."""
        if self.is_capture_mode:
            # Smart mode: check if clicking on a region
            self._handle_smart_click(event.x, event.y)
        else:
            # Manual mode: start selection
            self._start_manual_selection(event.x, event.y)

    def _handle_smart_click(self, canvas_x: int, canvas_y: int) -> None:
        """Handle click in smart mode."""
        # Convert to image coordinates
        image_x, image_y = self._canvas_to_image_coords(canvas_x, canvas_y)

        # Check if click is on any detected region
        for i, region in enumerate(self.detected_regions):
            if region.contains_point(image_x, image_y):
                self.selected_region_index = i
                self._update_detected_regions()
                return

    def _start_manual_selection(self, canvas_x: int, canvas_y: int) -> None:
        """Start manual selection."""
        self.manual_selection_active = True
        self.selection_start = (canvas_x, canvas_y)

        # Clear previous selection
        self.canvas.delete("manual_selection")

    def _on_canvas_drag(self, event) -> None:
        """Handle canvas drag."""
        if not self.manual_selection_active or not self.selection_start:
            return

        # Update selection rectangle
        self.canvas.delete("manual_selection")

        start_x, start_y = self.selection_start
        current_x, current_y = event.x, event.y

        self.selection_rect = self.canvas.create_rectangle(
            start_x,
            start_y,
            current_x,
            current_y,
            outline="#ff0000",
            width=2,
            tags="manual_selection",
        )

    def _on_canvas_release(self, event) -> None:
        """Handle canvas button release."""
        if not self.manual_selection_active or not self.selection_start:
            return

        # Complete manual selection
        start_x, start_y = self.selection_start
        end_x, end_y = event.x, event.y

        # Ensure valid rectangle
        x1, x2 = min(start_x, end_x), max(start_x, end_x)
        y1, y2 = min(start_y, end_y), max(start_y, end_y)

        # Convert to image coordinates
        img_x1, img_y1 = self._canvas_to_image_coords(x1, y1)
        img_x2, img_y2 = self._canvas_to_image_coords(x2, y2)

        # Check minimum size
        if (img_x2 - img_x1) > 20 and (img_y2 - img_y1) > 20:
            coordinates = (img_x1, img_y1, img_x2, img_y2)
            self._complete_selection(coordinates)
        else:
            self.info_label.config(text="Selection too small, try again", fg="red")

        self.manual_selection_active = False
        self.selection_start = None

    def _on_canvas_motion(self, event) -> None:
        """Handle canvas mouse motion."""
        if self.is_capture_mode and self.detected_regions:
            # Highlight region under cursor
            image_x, image_y = self._canvas_to_image_coords(event.x, event.y)

            for i, region in enumerate(self.detected_regions):
                if region.contains_point(image_x, image_y):
                    if i != self.selected_region_index:
                        self.selected_region_index = i
                        self._update_detected_regions()
                    break

    def _on_key_press(self, event) -> None:
        """Handle key press events."""
        if event.keysym == "Escape":
            self._cancel_capture()
        elif event.keysym == "Return" or event.keysym == "space":
            self._select_current_region()
        elif event.keysym == "Left":
            self._select_previous_region()
        elif event.keysym == "Right":
            self._select_next_region()
        elif event.keysym == "Tab":
            self._toggle_capture_mode()

    def _complete_selection(self, coordinates: Tuple[int, int, int, int]) -> None:
        """Complete area selection."""
        if self.on_area_selected:
            self.on_area_selected(coordinates)

        # Close capture interface
        if self.capture_window:
            self.capture_window.destroy()
            self.capture_window = None

        logger.info(f"Area selected: {coordinates}")

    def set_area_selected_callback(
        self, callback: Callable[[Tuple[int, int, int, int]], None]
    ) -> None:
        """Set callback for area selection."""
        self.on_area_selected = callback

    def update_detection_config(self, config: DetectionConfig) -> None:
        """Update smart detection configuration."""
        self.smart_detector.update_config(config)
        logger.info("Detection configuration updated")

    def get_detection_stats(self) -> dict:
        """Get detection performance statistics."""
        return self.smart_detector.get_detection_stats()

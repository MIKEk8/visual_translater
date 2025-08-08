"""
CaptureOrchestrator - Screenshot capture and area selection coordinator

Single Responsibility: Manages all screenshot capture operations, overlay UI,
and area selection functionality. Extracted from the original God Class.

Responsibilities:
- Capture overlay setup and management
- Mouse event handling for area selection
- Screenshot capture coordination
- Quick translate methods (center/bottom areas)
"""

import threading

try:
    import tkinter as tk
except ImportError:
    print(f"tkinter недоступен в {__name__}")
    # Используем заглушку
    from src.utils.mock_gui import tk

from typing import TYPE_CHECKING, Callable, Optional, Tuple

from src.core.events import EventType, publish_event
from src.core.screenshot_engine import ScreenshotEngine
from src.services.task_queue import TaskPriority, get_task_queue
from src.utils.exceptions import ScreenshotCaptureError
from src.utils.logger import logger

if TYPE_CHECKING:
    from src.ui.progress_indicator import ProgressManager


class CaptureOrchestrator:
    """Coordinates screenshot capture and area selection operations"""

    def __init__(
        self,
        root: tk.Tk,
        screenshot_engine: ScreenshotEngine,
        progress_manager: "ProgressManager",
        on_area_captured: Optional[Callable] = None,
        on_capture_error: Optional[Callable] = None,
    ):
        self.root = root
        self.screenshot_engine = screenshot_engine
        self.progress_manager = progress_manager
        self.task_queue = get_task_queue()
        self._lock = threading.Lock()

        # Callbacks for coordination with other components
        self.on_area_captured = on_area_captured
        self.on_capture_error = on_capture_error

        # Overlay state
        self.canvas = None
        self.start_x = 0
        self.start_y = 0
        self.rect = None

        self._setup_capture_overlay()

    def _setup_capture_overlay(self) -> None:
        """Setup screenshot capture overlay"""
        self.root.attributes("-alpha", 0.3)
        self.root.configure(background="black")
        self.root.attributes("-fullscreen", True)
        self.root.overrideredirect(True)

        self.canvas = tk.Canvas(self.root, cursor="cross", bg="grey11")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Bind events
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        self.root.withdraw()
        self.root.protocol("WM_DELETE_WINDOW", self._hide_overlay)

    def _on_press(self, event: tk.Event) -> None:
        """Handle mouse press for area selection"""
        self.start_x = event.x_root
        self.start_y = event.y_root

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        self.rect = self.canvas.create_rectangle(
            canvas_x, canvas_y, canvas_x, canvas_y, outline="red", width=2
        )

    def _on_drag(self, event: tk.Event) -> None:
        """Handle mouse drag for area selection"""
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, canvas_x, canvas_y)

    def _on_release(self, event: tk.Event) -> None:
        """Handle mouse release to complete area selection"""
        self.canvas.delete(self.rect)
        self._hide_overlay()

        x1 = min(self.start_x, event.x_root)
        y1 = min(self.start_y, event.y_root)
        x2 = max(self.start_x, event.x_root)
        y2 = max(self.start_y, event.y_root)

        # Show progress indicator
        with self._lock:
            _ = self.progress_manager.show_progress(
                title="Screen Translation",
                message="Capturing and processing screen area...",
                is_indeterminate=True,
            )

        # Process asynchronously using task queue
        with self._lock:
            task_id = self.task_queue.submit(
                func=self._process_area_capture,
                args=(x1, y1, x2, y2),
                name="process_area_capture",
                priority=TaskPriority.HIGH,
                callback=self._on_capture_success,
                error_callback=self._on_capture_error_callback,
            )
        logger.debug(f"Area capture task queued: {task_id}")

    def _hide_overlay(self) -> None:
        """Hide capture overlay"""
        self.root.withdraw()

    def capture_area(self) -> None:
        """Show area selection overlay"""
        logger.info("CaptureOrchestrator: Starting area selection")
        self.root.deiconify()
        self.root.attributes("-topmost", True)
        self.root.focus_force()

    def quick_translate_center(self) -> None:
        """Translate center area of screen"""
        logger.info("CaptureOrchestrator: Quick translate center")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        with self._lock:
            _ = self.progress_manager.show_progress(
                title="Quick Translation",
                message="Translating center area...",
                is_indeterminate=True,
            )

        with self._lock:
            task_id = self.task_queue.submit(
                func=self._process_center_capture,
                args=(screen_width, screen_height),
                name="quick_translate_center",
                priority=TaskPriority.HIGH,
                callback=self._on_capture_success,
                error_callback=self._on_capture_error_callback,
            )
        logger.debug(f"Center capture task queued: {task_id}")

    def quick_translate_bottom(self) -> None:
        """Translate bottom area of screen"""
        logger.info("CaptureOrchestrator: Quick translate bottom")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        with self._lock:
            _ = self.progress_manager.show_progress(
                title="Quick Translation",
                message="Translating bottom area...",
                is_indeterminate=True,
            )

        with self._lock:
            task_id = self.task_queue.submit(
                func=self._process_bottom_capture,
                args=(screen_width, screen_height),
                name="quick_translate_bottom",
                priority=TaskPriority.HIGH,
                callback=self._on_capture_success,
                error_callback=self._on_capture_error_callback,
            )
        logger.debug(f"Bottom capture task queued: {task_id}")

    def _process_area_capture(self, x1: int, y1: int, x2: int, y2: int):
        """Process screenshot of selected area"""
        try:
            # Publish screenshot request event
            publish_event(
                EventType.SCREENSHOT_REQUESTED,
                data={"coordinates": (x1, y1, x2, y2)},
                source="capture_orchestrator",
            )

            # Capture screenshot
            with self._lock:
                screenshot_data = self.screenshot_engine.capture_area(x1, y1, x2, y2)

            if not screenshot_data:
                publish_event(
                    EventType.SCREENSHOT_FAILED,
                    data={"error": "Failed to capture screenshot", "coordinates": (x1, y1, x2, y2)},
                    source="capture_orchestrator",
                )
                raise ScreenshotCaptureError("Failed to capture screenshot area", (x1, y1, x2, y2))

            # Publish successful screenshot capture event
            publish_event(
                EventType.SCREENSHOT_CAPTURED, data=screenshot_data, source="capture_orchestrator"
            )

            return screenshot_data

        except Exception as e:
            logger.error("Error processing area capture", error=e)
            raise

    def _process_center_capture(self, screen_width: int, screen_height: int):
        """Process center area screenshot"""
        try:
            with self._lock:
                screenshot_data = self.screenshot_engine.capture_center_area(
                    screen_width, screen_height
                )

            if not screenshot_data:
                raise ScreenshotCaptureError("Failed to capture center area", None)

            return screenshot_data

        except Exception as e:
            logger.error("Error processing center capture", error=e)
            raise

    def _process_bottom_capture(self, screen_width: int, screen_height: int):
        """Process bottom area screenshot"""
        try:
            with self._lock:
                screenshot_data = self.screenshot_engine.capture_bottom_area(
                    screen_width, screen_height
                )

            if not screenshot_data:
                raise ScreenshotCaptureError("Failed to capture bottom area", None)

            return screenshot_data

        except Exception as e:
            logger.error("Error processing bottom capture", error=e)
            raise

    def _on_capture_success(self, screenshot_data):
        """Handle successful screenshot capture"""
        if self.on_area_captured:
            self.on_area_captured(screenshot_data)

    def _on_capture_error_callback(self, error: Exception):
        """Handle capture errors"""
        if self.on_capture_error:
            self.on_capture_error(error)

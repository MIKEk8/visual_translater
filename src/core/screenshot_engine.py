import ctypes
import time
from datetime import datetime
from typing import Optional, Tuple

try:
    from PIL import Image, ImageGrab

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    from unittest.mock import Mock

    # Mock objects for when PIL is not available
    class MockImage:
        def open(self, *args, **kwargs):
            return Mock()

    class MockImageGrab:
        def grab(self, *args, **kwargs):
            return None

    Image = MockImage()
    ImageGrab = MockImageGrab()

from src.models.screenshot_data import ScreenshotData
from src.utils.exceptions import InvalidAreaError, ScreenshotCaptureError
from src.utils.logger import logger


class ScreenshotEngine:
    """Handles screen capture functionality"""

    def __init__(self):
        self.dpi_scale = self._get_dpi_scale()
        logger.debug(f"Screenshot engine initialized with DPI scale: {self.dpi_scale}")

    def _get_dpi_scale(self) -> float:
        """Get system DPI scale factor"""
        try:
            return ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
        except Exception as e:
            logger.warning("Could not get DPI scale, using 1.0", error=e)
            return 1.0

    def _validate_coordinates(
        self, x1: int, y1: int, x2: int, y2: int, screen_width: int, screen_height: int
    ) -> Tuple[int, int, int, int]:
        """Validate and adjust coordinates to screen bounds"""
        x1 = max(0, min(x1, screen_width))
        x2 = max(0, min(x2, screen_width))
        y1 = max(0, min(y1, screen_height))
        y2 = max(0, min(y2, screen_height))

        # Ensure we have a valid rectangle
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1

        return x1, y1, x2, y2

    def capture_area(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None,
    ) -> Optional[ScreenshotData]:
        """Capture screenshot of specified area"""
        start_time = time.time()

        try:
            # Get screen dimensions if not provided
            if screen_width is None or screen_height is None:
                screen = ImageGrab.grab()
                screen_width, screen_height = screen.size
                screen.close()

            # Validate coordinates
            x1, y1, x2, y2 = self._validate_coordinates(x1, y1, x2, y2, screen_width, screen_height)

            # Apply DPI scaling
            scaled_coords = (
                int(x1 * self.dpi_scale),
                int(y1 * self.dpi_scale),
                int(x2 * self.dpi_scale),
                int(y2 * self.dpi_scale),
            )

            # Validate area size
            width = x2 - x1
            height = y2 - y1
            if width <= 0 or height <= 0:
                raise InvalidAreaError((x1, y1, x2, y2))

            # Capture screenshot
            screenshot = ImageGrab.grab(bbox=scaled_coords)

            if screenshot is None:
                raise ScreenshotCaptureError((x1, y1, x2, y2), "Screenshot capture returned None")

            duration = time.time() - start_time

            result = ScreenshotData(
                image=screenshot,
                image_data=b"",  # Will be populated by image_bytes property
                coordinates=(x1, y1, x2, y2),
                timestamp=datetime.now(),
                dpi_scale=self.dpi_scale,
            )

            logger.log_screenshot(
                coordinates=(x1, y1, x2, y2), size=(x2 - x1, y2 - y1), duration=duration
            )

            return result

        except (InvalidAreaError, ScreenshotCaptureError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Screenshot capture failed",
                error=e,
                coordinates=(x1, y1, x2, y2),
                duration=duration,
            )
            raise ScreenshotCaptureError((x1, y1, x2, y2), f"Unexpected error: {str(e)}") from e

    def capture_center_area(
        self,
        screen_width: int,
        screen_height: int,
        width_ratio: float = 0.5,
        height_ratio: float = 0.33,
    ) -> Optional[ScreenshotData]:
        """Capture center area of screen (useful for game dialogs)"""
        x1 = int(screen_width * (1 - width_ratio) / 2)
        y1 = int(screen_height * (1 - height_ratio) / 2)
        x2 = int(screen_width * (1 + width_ratio) / 2)
        y2 = int(screen_height * (1 + height_ratio) / 2)

        return self.capture_area(x1, y1, x2, y2, screen_width, screen_height)

    def capture_bottom_area(
        self,
        screen_width: int,
        screen_height: int,
        width_ratio: float = 0.75,
        height_ratio: float = 0.25,
    ) -> Optional[ScreenshotData]:
        """Capture bottom area of screen (useful for subtitles)"""
        x1 = int(screen_width * (1 - width_ratio) / 2)
        y1 = int(screen_height * (1 - height_ratio))
        x2 = int(screen_width * (1 + width_ratio) / 2)
        y2 = screen_height - 50  # Leave some margin from bottom

        return self.capture_area(x1, y1, x2, y2, screen_width, screen_height)

    def save_debug_screenshot(
        self, screenshot_data: ScreenshotData, filename: Optional[str] = None
    ) -> bool:
        """Save screenshot for debugging purposes"""
        try:
            if filename is None:
                timestamp = screenshot_data.timestamp.strftime("%Y%m%d_%H%M%S")
                filename = f"debug_screenshot_{timestamp}.png"

            # Convert bytes back to image and save
            import io

            image = Image.open(io.BytesIO(screenshot_data.image_data))
            image.save(filename)

            logger.debug(f"Debug screenshot saved: {filename}")
            return True

        except Exception as e:
            logger.error("Failed to save debug screenshot", error=e, filename=filename)
            return False

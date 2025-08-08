"""Screenshot-related commands for CQRS pattern."""

from dataclasses import dataclass
from typing import Optional, Tuple

from .base_command import Command


@dataclass
class CaptureAreaCommand(Command):
    """Command to capture a specific area of the screen."""

    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    save_debug: bool = False
    enhance_image: bool = True

    def validate(self) -> bool:
        """Validate capture area coordinates."""
        if self.width <= 0 or self.height <= 0:
            return False

        # Minimum area check (50x50 pixels)
        if self.width < 50 or self.height < 50:
            return False

        return True

    @property
    def area_size(self) -> Tuple[int, int]:
        """Get area dimensions."""
        return (self.width, self.height)

    @property
    def coordinates(self) -> Tuple[int, int, int, int]:
        """Get coordinates as tuple."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    @property
    def area(self) -> int:
        """Get area in pixels."""
        return self.width * self.height


@dataclass
class CaptureScreenCommand(Command):
    """Command to capture predefined screen areas."""

    capture_type: str = "full"  # "center", "bottom", "full"
    screen_width: Optional[int] = None
    screen_height: Optional[int] = None
    save_debug: bool = False

    def validate(self) -> bool:
        """Validate capture screen command."""
        valid_types = ["center", "bottom", "full"]
        if self.capture_type not in valid_types:
            return False

        if self.capture_type in ["center", "bottom"]:
            if not self.screen_width or not self.screen_height:
                return False

            if self.screen_width <= 0 or self.screen_height <= 0:
                return False

        return True

    def get_area_coordinates(self) -> Tuple[int, int, int, int]:
        """Calculate area coordinates based on capture type."""
        if not self.screen_width or not self.screen_height:
            raise ValueError("Screen dimensions required")

        if self.capture_type == "center":
            # Center 400x300 area
            center_x = self.screen_width // 2
            center_y = self.screen_height // 2
            return (center_x - 200, center_y - 150, center_x + 200, center_y + 150)

        elif self.capture_type == "bottom":
            # Bottom 800x200 area
            return (
                (self.screen_width - 800) // 2,
                self.screen_height - 250,
                (self.screen_width + 800) // 2,
                self.screen_height - 50,
            )

        elif self.capture_type == "full":
            # Full screen
            return (0, 0, self.screen_width, self.screen_height)

        else:
            raise ValueError(f"Unknown capture type: {self.capture_type}")


@dataclass
class SaveScreenshotCommand(Command):
    """Command to save screenshot to file."""

    screenshot_data: bytes = b""
    file_path: str = ""
    image_format: str = "PNG"
    quality: int = 95

    def validate(self) -> bool:
        """Validate save screenshot command."""
        if not self.screenshot_data:
            return False

        if not self.file_path:
            return False

        valid_formats = ["PNG", "JPEG", "JPG", "BMP", "TIFF"]
        if self.image_format.upper() not in valid_formats:
            return False

        if not (1 <= self.quality <= 100):
            return False

        return True

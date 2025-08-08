"""
Refactored Screenshot Processor - Low Complexity Components
Extracted from complex screenshot validation and processing
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass
class ScreenBounds:
    """Value object for screen boundaries"""

    x: int
    y: int
    width: int
    height: int

    def is_valid(self) -> bool:
        """Check if bounds are valid - complexity 3"""
        if self.x < 0 or self.y < 0:  # +1
            return False
        if self.width <= 0 or self.height <= 0:  # +1
            return False
        if self.width > 10000 or self.height > 10000:  # +1
            return False
        return True


class BoundsValidator:
    """Single responsibility: Validate screenshot bounds"""

    def validate(self, bounds: ScreenBounds) -> Tuple[bool, str]:
        """Validate bounds - complexity 2"""
        if not bounds.is_valid():  # +1
            return False, "Invalid screen bounds"

        # Check for minimum size
        if bounds.width < 10 or bounds.height < 10:  # +1
            return False, "Screenshot too small (minimum 10x10)"

        return True, ""


class ImageDataValidator:
    """Single responsibility: Validate image data"""

    MIN_SIZE = 100  # bytes
    MAX_SIZE = 50_000_000  # 50MB

    def validate(self, image_data: Optional[bytes]) -> Tuple[bool, str]:
        """Validate image data - complexity 4"""
        if not image_data:  # +1
            return False, "Image data is empty"

        if len(image_data) < self.MIN_SIZE:  # +1
            return False, f"Image too small (min {self.MIN_SIZE} bytes)"

        if len(image_data) > self.MAX_SIZE:  # +1
            return False, f"Image too large (max {self.MAX_SIZE} bytes)"

        # Basic format validation
        if not image_data.startswith((b"\x89PNG", b"\xff\xd8\xff", b"BM")):  # +1
            return False, "Unsupported image format"

        return True, ""


class ScreenshotProcessor:
    """Main processor with low complexity - complexity 5"""

    def __init__(self):
        self.bounds_validator = BoundsValidator()
        self.image_validator = ImageDataValidator()

    def process(self, screenshot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process screenshot - complexity 5"""
        # Step 1: Validate bounds
        if "bounds" not in screenshot_data:  # +1
            return {"success": False, "error": "Missing bounds data"}

        bounds = ScreenBounds(**screenshot_data["bounds"])
        bounds_valid, bounds_error = self.bounds_validator.validate(bounds)
        if not bounds_valid:  # +1
            return {"success": False, "error": bounds_error}

        # Step 2: Validate image if present
        if "image_data" in screenshot_data:  # +1
            image_valid, image_error = self.image_validator.validate(screenshot_data["image_data"])
            if not image_valid:  # +1
                return {"success": False, "error": image_error}

        # Step 3: Create processed result
        result = {
            "success": True,
            "bounds": bounds,
            "size": bounds.width * bounds.height,
            "has_image": "image_data" in screenshot_data,
        }

        return result

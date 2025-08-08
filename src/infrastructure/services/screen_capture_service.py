"""
Screen capture service implementation.
"""

from typing import Optional

try:
    from PIL import Image, ImageGrab

    ImageType = Image.Image
    CAPTURE_AVAILABLE = True
except ImportError:
    from typing import Any

    Image = Any
    ImageGrab = Any
    ImageType = Any
    CAPTURE_AVAILABLE = False

from ...domain.protocols.services import ScreenCaptureService
from ...domain.value_objects.coordinates import ScreenCoordinates
from ...utils.logger import logger


class PILScreenCaptureService(ScreenCaptureService):
    """PIL-based screen capture service."""

    def __init__(self):
        pass

    async def capture_area(self, coordinates: ScreenCoordinates) -> ImageType:
        """Capture screen area."""
        try:
            # PIL ImageGrab uses (left, top, right, bottom) format
            bbox = (coordinates.x1, coordinates.y1, coordinates.x2, coordinates.y2)

            image = ImageGrab.grab(bbox=bbox)

            logger.info(
                f"Screen capture completed",
                coordinates=f"{coordinates.x1},{coordinates.y1},{coordinates.x2},{coordinates.y2}",
                size=f"{image.width}x{image.height}",
            )

            return image

        except Exception as e:
            logger.error(f"Screen capture failed: {e}")
            raise

    async def select_area(self) -> Optional[ScreenCoordinates]:
        """Let user select screen area interactively."""
        # This would typically show an overlay UI for area selection
        # For now, return None to indicate not implemented
        logger.warning("Interactive area selection not implemented")
        return None

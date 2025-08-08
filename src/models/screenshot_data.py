"""
Screenshot data model for Screen Translator v2.0

This module provides the ScreenshotData class for handling screenshot information
including images, coordinates, and metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Tuple
from uuid import uuid4


@dataclass
class ScreenshotData:
    """
    Data container for screenshot information

    Attributes:
        image: PIL Image object containing the screenshot
        image_data: Raw image bytes (for compatibility)
        coordinates: Screen coordinates as (x1, y1, x2, y2) tuple
        timestamp: When the screenshot was taken
        dpi_scale: DPI scaling factor for the screenshot
        metadata: Additional metadata (file path, etc.)
        id: Unique identifier
        image_path: File path where image is stored
    """

    image: Any  # PIL Image object
    image_data: bytes
    coordinates: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: Optional[datetime] = None
    dpi_scale: float = 1.0
    metadata: Optional[dict] = None
    image_path: Optional[str] = None

    def __post_init__(self):
        """Initialize default values after creation"""
        if self.timestamp is None:
            self.timestamp = datetime.now()

        if self.metadata is None:
            self.metadata = {}

    @property
    def size(self) -> Tuple[int, int]:
        """Get size as (width, height) tuple"""
        if self.image:
            width, height = self.image.size
            return (int(width), int(height))

        # Calculate from coordinates if image not available
        x1, y1, x2, y2 = self.coordinates
        return (x2 - x1, y2 - y1)

    @property
    def width(self) -> int:
        """Get screenshot width"""
        return self.size[0]

    @property
    def height(self) -> int:
        """Get screenshot height"""
        return self.size[1]

    @property
    def image_bytes(self) -> bytes:
        """
        Get image as bytes for plugin compatibility

        Returns:
            bytes: PNG-encoded image data
        """
        if self.image_data:
            return self.image_data

        if self.image:
            import io

            buffer = io.BytesIO()
            self.image.save(buffer, format="PNG")
            return buffer.getvalue()

        return b""

    def to_dict(self) -> dict:
        """
        Convert to dictionary representation

        Returns:
            dict: Dictionary containing screenshot data
        """
        return {
            "id": self.id,
            "coordinates": self.coordinates,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "size": self.size,
            "dpi_scale": self.dpi_scale,
            "metadata": self.metadata or {},
            "image_path": self.image_path,
        }

    @classmethod
    def from_dict(cls, data: dict, image=None, image_data=None) -> "ScreenshotData":
        """
        Create ScreenshotData from dictionary

        Args:
            data: Dictionary containing screenshot metadata
            image: PIL Image object (optional)
            image_data: Raw image bytes (optional)

        Returns:
            ScreenshotData: New instance
        """
        timestamp = None
        if data.get("timestamp"):
            timestamp = datetime.fromisoformat(data["timestamp"])

        return cls(
            id=data.get("id", str(uuid4())),
            image=image,
            image_data=image_data or b"",
            coordinates=tuple(data["coordinates"]),
            timestamp=timestamp,
            dpi_scale=data.get("dpi_scale", 1.0),
            metadata=data.get("metadata", {}),
            image_path=data.get("image_path"),
        )

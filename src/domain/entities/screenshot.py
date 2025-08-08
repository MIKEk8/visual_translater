"""
Screenshot entity - represents a captured screen area.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..value_objects.domain_id import DomainId

try:
    from PIL import Image

    ImageType = Image.Image
except ImportError:
    # Fallback for when PIL is not available
    from typing import Any

    Image = Any
    ImageType = Any

from ..value_objects.coordinates import ScreenCoordinates
from ..value_objects.text import Text


@dataclass
class Screenshot:
    """Screenshot entity with business logic."""

    id: DomainId = field(default_factory=DomainId.generate)
    coordinates: Optional[ScreenCoordinates] = None
    image: Optional[ImageType] = None
    extracted_text: Optional[Text] = None
    timestamp: datetime = field(default_factory=datetime.now)
    ocr_confidence: Optional[float] = None

    def __post_init__(self):
        """Validate screenshot entity."""
        if not self.id:
            self.id = DomainId.generate()

    @property
    def has_text(self) -> bool:
        """Check if text was extracted."""
        return self.extracted_text is not None

    @property
    def is_valid(self) -> bool:
        """Check if screenshot is valid."""
        return self.image is not None and self.coordinates is not None

    @property
    def size(self) -> tuple[int, int]:
        """Get image size."""
        if self.image:
            return self.image.size
        elif self.coordinates:
            return (self.coordinates.width, self.coordinates.height)
        return (0, 0)

    def extract_text(self, text: str, confidence: float) -> None:
        """Set extracted text from OCR."""
        self.extracted_text = Text(text)
        self.ocr_confidence = confidence

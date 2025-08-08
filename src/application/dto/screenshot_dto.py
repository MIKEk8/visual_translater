"""Screenshot Data Transfer Objects."""

from dataclasses import dataclass
from typing import List, Optional

from ...domain.entities.screenshot import Screenshot


@dataclass
class ScreenshotRequest:
    """Request for screenshot operations."""

    x1: int
    y1: int
    x2: int
    y2: int
    extract_text: bool = False
    ocr_language: Optional[str] = None


@dataclass
class ScreenshotResponse:
    """Response for screenshot operations."""

    success: bool
    screenshot: Optional[Screenshot] = None
    errors: List[str] = None

    @classmethod
    def success(cls, screenshot: Screenshot) -> "ScreenshotResponse":
        """Create success response."""
        return cls(success=True, screenshot=screenshot)

    @classmethod
    def error(cls, errors: List[str]) -> "ScreenshotResponse":
        """Create error response."""
        return cls(success=False, errors=errors or [])

"""
Screen coordinates value object.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ScreenCoordinates:
    """Immutable screen coordinates."""

    x1: int
    y1: int
    x2: int
    y2: int

    def __post_init__(self):
        """Validate coordinates."""
        if self.x1 < 0 or self.y1 < 0:
            raise ValueError("Coordinates cannot be negative")

        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("Invalid rectangle: x2/y2 must be greater than x1/y1")

    @property
    def width(self) -> int:
        """Get rectangle width."""
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        """Get rectangle height."""
        return self.y2 - self.y1

    @property
    def area(self) -> int:
        """Get rectangle area."""
        return self.width * self.height

    @property
    def center(self) -> Tuple[int, int]:
        """Get rectangle center point."""
        return (self.x1 + self.width // 2, self.y1 + self.height // 2)

    def contains(self, x: int, y: int) -> bool:
        """Check if point is inside rectangle."""
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def intersects(self, other: "ScreenCoordinates") -> bool:
        """Check if rectangles intersect."""
        return not (
            self.x2 <= other.x1 or other.x2 <= self.x1 or self.y2 <= other.y1 or other.y2 <= self.y1
        )

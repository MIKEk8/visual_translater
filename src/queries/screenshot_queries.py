"""
Screenshot-related queries for CQRS pattern.
"""

from dataclasses import dataclass
from typing import Optional

from .base_query import Query


@dataclass
class GetScreenshotHistoryQuery(Query):
    """Query to get screenshot history."""

    limit: int = 100
    include_failed: bool = False
    date_from: Optional[str] = None
    date_to: Optional[str] = None

    def validate(self) -> bool:
        """Validate screenshot history query."""
        if self.limit < 1 or self.limit > 1000:
            return False

        # Validate pagination if present
        if self.pagination and not self.pagination.validate():
            return False

        # Validate sorting if present
        if self.sorting and not self.sorting.validate():
            return False

        # Validate supported sort fields
        if self.sorting:
            valid_sort_fields = ["timestamp", "size", "coordinates", "ocr_duration"]
            if self.sorting.field not in valid_sort_fields:
                return False

        return True


@dataclass
class GetScreenshotByIdQuery(Query):
    """Query to get specific screenshot by ID."""

    screenshot_id: str = ""
    include_metadata: bool = True
    include_image_data: bool = False

    def validate(self) -> bool:
        """Validate get screenshot by ID query."""
        if not self.screenshot_id:
            return False

        return True

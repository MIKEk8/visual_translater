"""
Screenshot repository implementation.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

try:
    from PIL import Image
except ImportError:
    from typing import Any

    Image = Any

from ...domain.entities.screenshot import Screenshot
from ...domain.protocols.repositories import ScreenshotRepository
from ...domain.value_objects.coordinates import ScreenCoordinates
from ...domain.value_objects.text import Text
from .base_repository import BaseRepository


class FileScreenshotRepository(BaseRepository, ScreenshotRepository):
    """File-based screenshot repository."""

    def __init__(self, storage_path: Optional[Path] = None):
        super().__init__(storage_path)
        self._screenshots_file = "screenshots.json"
        self._images_dir = self.storage_path / "images"
        self._images_dir.mkdir(exist_ok=True)

    async def save(self, screenshot: Screenshot) -> None:
        """Save screenshot to storage."""
        screenshots = self._load_screenshots()

        # Save image file if present
        image_filename = None
        if screenshot.image:
            image_filename = f"{screenshot.id}.png"
            image_path = self._images_dir / image_filename
            screenshot.image.save(image_path, "PNG")

        # Convert to dict for storage
        screenshot_dict = {
            "id": screenshot.id,
            "coordinates": (
                {
                    "x1": screenshot.coordinates.x1,
                    "y1": screenshot.coordinates.y1,
                    "x2": screenshot.coordinates.x2,
                    "y2": screenshot.coordinates.y2,
                }
                if screenshot.coordinates
                else None
            ),
            "image_filename": image_filename,
            "extracted_text": (
                screenshot.extracted_text.content if screenshot.extracted_text else None
            ),
            "timestamp": screenshot.timestamp.isoformat(),
            "ocr_confidence": screenshot.ocr_confidence,
        }

        # Update existing or add new
        existing_index = None
        for i, existing in enumerate(screenshots):
            if existing.get("id") == screenshot.id:
                existing_index = i
                break

        if existing_index is not None:
            screenshots[existing_index] = screenshot_dict
        else:
            screenshots.append(screenshot_dict)

        # Keep only last 100 screenshots
        if len(screenshots) > 100:
            old_screenshots = screenshots[:-100]
            screenshots = screenshots[-100:]

            # Clean up old image files
            for old_screenshot in old_screenshots:
                if old_screenshot.get("image_filename"):
                    old_image_path = self._images_dir / old_screenshot["image_filename"]
                    if old_image_path.exists():
                        old_image_path.unlink()

        self._save_to_json(self._screenshots_file, screenshots)

    async def get_by_id(self, screenshot_id: str) -> Optional[Screenshot]:
        """Get screenshot by ID."""
        screenshots = self._load_screenshots()

        for screenshot_dict in screenshots:
            if screenshot_dict.get("id") == screenshot_id:
                return self._dict_to_screenshot(screenshot_dict)

        return None

    async def get_recent(self, limit: int = 50) -> List[Screenshot]:
        """Get recent screenshots."""
        screenshots = self._load_screenshots()

        # Sort by timestamp (most recent first)
        sorted_screenshots = sorted(screenshots, key=lambda x: x.get("timestamp", ""), reverse=True)

        # Convert to entities
        result = []
        for screenshot_dict in sorted_screenshots[:limit]:
            try:
                screenshot = self._dict_to_screenshot(screenshot_dict)
                if screenshot:
                    result.append(screenshot)
            except Exception:
                continue  # Skip corrupted entries

        return result

    async def delete_old(self, days: int = 7) -> int:
        """Delete old screenshots."""
        screenshots = self._load_screenshots()
        cutoff_date = datetime.now() - timedelta(days=days)

        old_screenshots = []
        new_screenshots = []

        for screenshot_dict in screenshots:
            timestamp_str = screenshot_dict.get("timestamp")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp < cutoff_date:
                        old_screenshots.append(screenshot_dict)
                    else:
                        new_screenshots.append(screenshot_dict)
                except Exception:
                    new_screenshots.append(screenshot_dict)  # Keep if can't parse
            else:
                new_screenshots.append(screenshot_dict)

        # Delete old image files
        for old_screenshot in old_screenshots:
            if old_screenshot.get("image_filename"):
                old_image_path = self._images_dir / old_screenshot["image_filename"]
                if old_image_path.exists():
                    old_image_path.unlink()

        # Save updated list
        self._save_to_json(self._screenshots_file, new_screenshots)

        return len(old_screenshots)

    def _load_screenshots(self) -> List[dict]:
        """Load screenshots from storage."""
        return self._load_from_json(self._screenshots_file)

    def _dict_to_screenshot(self, screenshot_dict: dict) -> Optional[Screenshot]:
        """Convert dictionary to Screenshot entity."""
        try:
            # Parse timestamp
            timestamp_str = screenshot_dict.get("timestamp")
            timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.now()

            # Load coordinates
            coordinates = None
            coord_dict = screenshot_dict.get("coordinates")
            if coord_dict:
                coordinates = ScreenCoordinates(
                    coord_dict["x1"], coord_dict["y1"], coord_dict["x2"], coord_dict["y2"]
                )

            # Load image
            image = None
            image_filename = screenshot_dict.get("image_filename")
            if image_filename:
                image_path = self._images_dir / image_filename
                if image_path.exists():
                    image = Image.open(image_path)

            # Load extracted text
            extracted_text = None
            text_content = screenshot_dict.get("extracted_text")
            if text_content:
                extracted_text = Text(text_content)

            # Create screenshot
            screenshot = Screenshot(
                id=screenshot_dict["id"],
                coordinates=coordinates,
                image=image,
                extracted_text=extracted_text,
                timestamp=timestamp,
                ocr_confidence=screenshot_dict.get("ocr_confidence"),
            )

            return screenshot

        except Exception as e:
            print(f"Error converting dict to Screenshot: {e}")
            return None

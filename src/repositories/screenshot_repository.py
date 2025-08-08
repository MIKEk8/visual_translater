"""
Screenshot repository implementations.

This module provides repository implementations for screenshot data persistence.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.models.screenshot_data import ScreenshotData
from src.repositories.base_repository import BaseRepository
from src.utils.logger import logger


class ScreenshotRepository(BaseRepository[ScreenshotData]):
    """Abstract repository for screenshot data."""

    async def find_by_coordinates(self, coordinates: tuple) -> Optional[ScreenshotData]:
        """Find screenshot by coordinates."""
        criteria = {"coordinates": coordinates}
        results = await self.search(criteria)
        return results[0] if results else None

    async def find_recent(self, limit: int = 50) -> List[ScreenshotData]:
        """Find recent screenshots ordered by timestamp."""
        all_screenshots = await self.find_all()
        # Sort by timestamp descending
        sorted_screenshots = sorted(all_screenshots, key=lambda s: s.timestamp, reverse=True)
        return sorted_screenshots[:limit]

    async def find_by_size_range(self, min_size: int, max_size: int) -> List[ScreenshotData]:
        """Find screenshots within size range."""
        criteria = {"size_min": min_size, "size_max": max_size}
        return await self.search(criteria)


class FileScreenshotRepository(ScreenshotRepository):
    """File-based implementation of screenshot repository."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.screenshots_file = self.data_dir / "screenshots.json"
        self.images_dir = self.data_dir / "images"
        self.images_dir.mkdir(exist_ok=True)
        self._cache: Dict[str, ScreenshotData] = {}
        self._load_data()

    def _load_data(self) -> None:
        """Load screenshots from file into cache."""
        try:
            if self.screenshots_file.exists():
                with open(self.screenshots_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for item in data.get("screenshots", []):
                    try:
                        screenshot = self._dict_to_screenshot(item)
                        self._cache[screenshot.id] = screenshot
                    except Exception as e:
                        logger.warning(f"Failed to load screenshot: {e}")

                logger.info(f"Loaded {len(self._cache)} screenshots from file")
            else:
                logger.info("No existing screenshots file found, starting fresh")

        except Exception as e:
            logger.error(f"Failed to load screenshots: {e}")
            self._cache = {}

    def _save_data(self) -> None:
        """Save screenshots from cache to file."""
        try:
            data = {
                "version": "2.0",
                "exported_at": datetime.now().isoformat(),
                "screenshots": [
                    self._screenshot_to_dict(screenshot) for screenshot in self._cache.values()
                ],
            }

            # Write to temp file first, then rename (atomic operation)
            temp_file = self.screenshots_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            temp_file.replace(self.screenshots_file)
            logger.debug(f"Saved {len(self._cache)} screenshots to file")

        except Exception as e:
            logger.error(f"Failed to save screenshots: {e}")

    def _screenshot_to_dict(self, screenshot: ScreenshotData) -> Dict[str, Any]:
        """Convert ScreenshotData object to dictionary."""
        return {
            "id": screenshot.id,
            "coordinates": screenshot.coordinates,
            "timestamp": screenshot.timestamp.isoformat(),
            "image_path": screenshot.image_path,
            "size_bytes": len(screenshot.image_bytes) if screenshot.image_bytes else 0,
            "metadata": screenshot.metadata or {},
        }

    def _dict_to_screenshot(self, data: Dict[str, Any]) -> ScreenshotData:
        """Convert dictionary to ScreenshotData object."""
        # Load image bytes from file if path exists
        image_bytes = None
        image_path = data.get("image_path")
        if image_path:
            full_path = self.images_dir / image_path
            if full_path.exists():
                try:
                    with open(full_path, "rb") as f:
                        image_bytes = f.read()
                except Exception as e:
                    logger.warning(f"Failed to load image {image_path}: {e}")

        return ScreenshotData(
            id=data.get("id", str(uuid4())),
            coordinates=tuple(data["coordinates"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            image_path=image_path,
            image_bytes=image_bytes,
            metadata=data.get("metadata", {}),
        )

    def _save_image(self, screenshot: ScreenshotData) -> Optional[str]:
        """Save image bytes to file and return relative path."""
        if not screenshot.image_bytes:
            return None

        try:
            # Generate unique filename
            timestamp = screenshot.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}_{screenshot.id[:8]}.png"
            file_path = self.images_dir / filename

            # Save image bytes
            with open(file_path, "wb") as f:
                f.write(screenshot.image_bytes)

            logger.debug(f"Saved screenshot image: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Failed to save screenshot image: {e}")
            return None

    async def save(self, screenshot: ScreenshotData) -> str:
        """Save a screenshot."""
        if not screenshot.id:
            screenshot.id = str(uuid4())

        # Save image bytes to file
        if screenshot.image_bytes and not screenshot.image_path:
            screenshot.image_path = self._save_image(screenshot)

        self._cache[screenshot.id] = screenshot
        self._save_data()

        logger.debug(f"Saved screenshot: {screenshot.id}")
        return screenshot.id

    async def find_by_id(self, screenshot_id: str) -> Optional[ScreenshotData]:
        """Find screenshot by ID."""
        return self._cache.get(screenshot_id)

    async def find_all(self, limit: Optional[int] = None, offset: int = 0) -> List[ScreenshotData]:
        """Find all screenshots with pagination."""
        screenshots = list(self._cache.values())

        # Sort by timestamp descending
        screenshots.sort(key=lambda s: s.timestamp, reverse=True)

        # Apply pagination
        start = offset
        end = start + limit if limit else None
        return screenshots[start:end]

    async def delete(self, screenshot_id: str) -> bool:
        """Delete a screenshot."""
        if screenshot_id in self._cache:
            screenshot = self._cache[screenshot_id]

            # Delete image file if exists
            if screenshot.image_path:
                image_file = self.images_dir / screenshot.image_path
                try:
                    if image_file.exists():
                        image_file.unlink()
                        logger.debug(f"Deleted image file: {screenshot.image_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete image file {screenshot.image_path}: {e}")

            del self._cache[screenshot_id]
            self._save_data()
            logger.debug(f"Deleted screenshot: {screenshot_id}")
            return True
        return False

    async def exists(self, screenshot_id: str) -> bool:
        """Check if screenshot exists."""
        return screenshot_id in self._cache

    async def count(self) -> int:
        """Count total screenshots."""
        return len(self._cache)

    async def search(self, criteria: Dict[str, Any]) -> List[ScreenshotData]:
        """Search screenshots by criteria."""
        results = []

        for screenshot in self._cache.values():
            if self._matches_criteria(screenshot, criteria):
                results.append(screenshot)

        # Sort by timestamp descending
        results.sort(key=lambda s: s.timestamp, reverse=True)
        return results

    def _matches_criteria(self, screenshot: ScreenshotData, criteria: Dict[str, Any]) -> bool:
        """Check if screenshot matches search criteria."""
        for key, value in criteria.items():
            if not self._check_field_match(screenshot, key, value):
                return False
        return True

    def _check_field_match(self, screenshot: ScreenshotData, field: str, value: Any) -> bool:
        """Check if a specific field matches the criteria value."""
        field_checkers = {
            "coordinates": lambda s, v: s.coordinates == tuple(v),
            "size_min": lambda s, v: self._get_image_size(s) >= v,
            "size_max": lambda s, v: self._get_image_size(s) <= v,
            "date_from": lambda s, v: s.timestamp >= v,
            "date_to": lambda s, v: s.timestamp <= v,
        }

        checker = field_checkers.get(field)
        if checker:
            return checker(screenshot, value)

        # For unknown fields, try direct attribute comparison
        return getattr(screenshot, field, None) == value

    def _get_image_size(self, screenshot: ScreenshotData) -> int:
        """Get the size of the screenshot image data."""
        return len(screenshot.image_bytes) if screenshot.image_bytes else 0

    async def clear_all(self) -> int:
        """Clear all screenshots."""
        count = len(self._cache)

        # Delete all image files
        for screenshot in self._cache.values():
            if screenshot.image_path:
                image_file = self.images_dir / screenshot.image_path
                try:
                    if image_file.exists():
                        image_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete image file {screenshot.image_path}: {e}")

        self._cache.clear()
        self._save_data()
        logger.info(f"Cleared {count} screenshots")
        return count

    async def get_statistics(self) -> Dict[str, Any]:
        """Get repository statistics."""
        if not self._cache:
            return {"total": 0}

        screenshots = list(self._cache.values())

        # Size statistics
        sizes = [len(s.image_bytes) if s.image_bytes else 0 for s in screenshots]
        total_size = sum(sizes)
        avg_size = total_size / len(sizes) if sizes else 0

        # Time-based statistics
        now = datetime.now()
        recent_count = len([s for s in screenshots if (now - s.timestamp).days <= 7])

        # Coordinate statistics
        unique_coordinates = len(set(s.coordinates for s in screenshots))

        return {
            "total": len(screenshots),
            "recent_week": recent_count,
            "total_size_bytes": total_size,
            "average_size_bytes": int(avg_size),
            "unique_coordinates": unique_coordinates,
            "oldest": min(s.timestamp for s in screenshots),
            "newest": max(s.timestamp for s in screenshots),
        }

"""
Tests for Screenshot entity.
"""

from datetime import datetime
from uuid import UUID

import pytest

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from src.domain.entities.screenshot import Screenshot
from src.domain.value_objects.coordinates import ScreenCoordinates
from src.domain.value_objects.text import Text


class TestScreenshot:
    """Test Screenshot entity."""

    def test_screenshot_creation_minimal(self):
        """Test creating screenshot with minimal data."""
        screenshot = Screenshot()

        assert screenshot.id is not None
        assert len(screenshot.id) > 0
        UUID(screenshot.id)  # Should not raise - valid UUID
        assert isinstance(screenshot.timestamp, datetime)
        assert screenshot.coordinates is None
        assert screenshot.image is None
        assert screenshot.extracted_text is None
        assert screenshot.ocr_confidence is None

    def test_screenshot_creation_full(self):
        """Test creating screenshot with all data."""
        coords = ScreenCoordinates(10, 20, 100, 150)
        text = Text("Extracted text")

        screenshot = Screenshot(coordinates=coords, extracted_text=text, ocr_confidence=0.88)

        assert screenshot.coordinates == coords
        assert screenshot.extracted_text == text
        assert screenshot.ocr_confidence == 0.88

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
    def test_screenshot_with_image(self):
        """Test screenshot with PIL image."""
        # Create a small test image
        image = Image.new("RGB", (100, 50), color="white")
        coords = ScreenCoordinates(0, 0, 100, 50)

        screenshot = Screenshot(coordinates=coords, image=image)

        assert screenshot.image == image
        assert screenshot.size == (100, 50)
        assert screenshot.is_valid is True

    def test_screenshot_properties(self):
        """Test screenshot computed properties."""
        coords = ScreenCoordinates(10, 20, 100, 150)
        text = Text("Found text")

        screenshot = Screenshot(coordinates=coords, extracted_text=text)

        assert screenshot.has_text is True
        assert screenshot.is_valid is False  # No image
        assert screenshot.size == (90, 130)  # From coordinates

    def test_screenshot_no_text(self):
        """Test screenshot without extracted text."""
        coords = ScreenCoordinates(10, 20, 100, 150)

        screenshot = Screenshot(coordinates=coords)

        assert screenshot.has_text is False
        assert screenshot.extracted_text is None

    def test_screenshot_extract_text(self):
        """Test extracting text from screenshot."""
        screenshot = Screenshot()

        screenshot.extract_text("Extracted text", 0.75)

        assert screenshot.extracted_text is not None
        assert screenshot.extracted_text.content == "Extracted text"
        assert screenshot.ocr_confidence == 0.75
        assert screenshot.has_text is True

    def test_screenshot_size_no_image_no_coords(self):
        """Test size calculation with no image or coordinates."""
        screenshot = Screenshot()
        assert screenshot.size == (0, 0)

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
    def test_screenshot_size_with_image(self):
        """Test size calculation with image."""
        image = Image.new("RGB", (200, 100), color="blue")
        screenshot = Screenshot(image=image)
        assert screenshot.size == (200, 100)

    def test_screenshot_size_with_coordinates(self):
        """Test size calculation with coordinates only."""
        coords = ScreenCoordinates(5, 10, 105, 210)
        screenshot = Screenshot(coordinates=coords)
        assert screenshot.size == (100, 200)

    def test_screenshot_id_uniqueness(self):
        """Test that screenshot IDs are unique."""
        screenshot1 = Screenshot()
        screenshot2 = Screenshot()

        assert screenshot1.id != screenshot2.id

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
    def test_screenshot_is_valid_with_image_and_coords(self):
        """Test screenshot validity with image and coordinates."""
        image = Image.new("RGB", (50, 50), color="red")
        coords = ScreenCoordinates(0, 0, 50, 50)

        screenshot = Screenshot(coordinates=coords, image=image)
        assert screenshot.is_valid is True

    def test_screenshot_is_valid_missing_components(self):
        """Test screenshot validity with missing components."""
        # Only coordinates
        screenshot1 = Screenshot(coordinates=ScreenCoordinates(0, 0, 50, 50))
        assert screenshot1.is_valid is False

        # Neither image nor coordinates
        screenshot2 = Screenshot()
        assert screenshot2.is_valid is False

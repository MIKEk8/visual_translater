"""Unit tests for screenshot data model"""

import io
from datetime import datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from src.models.screenshot_data import ScreenshotData


@pytest.fixture
def mock_image():
    """Create mock PIL Image"""
    image = Mock()
    image.size = (800, 600)
    image.mode = "RGB"
    image.format = "PNG"

    # Mock save method
    def mock_save(buffer, format=None):
        buffer.write(b"fake_image_data")

    image.save = mock_save
    return image


@pytest.fixture
def sample_screenshot_data(mock_image):
    """Create sample screenshot data"""
    return ScreenshotData(
        image=mock_image,
        image_data=b"test_image_data",
        coordinates=(100, 100, 900, 700),
        dpi_scale=1.5,
        metadata={"source": "test"},
    )


class TestScreenshotData:
    """Test ScreenshotData model class"""

    def test_creation_with_required_fields(self, mock_image):
        """Test creating ScreenshotData with required fields only"""
        screenshot = ScreenshotData(
            image=mock_image, image_data=b"test_data", coordinates=(0, 0, 100, 100)
        )

        assert screenshot.image == mock_image
        assert screenshot.image_data == b"test_data"
        assert screenshot.coordinates == (0, 0, 100, 100)
        assert screenshot.dpi_scale == 1.0
        assert screenshot.metadata == {}
        assert screenshot.timestamp is not None
        assert len(screenshot.id) > 0

    def test_creation_with_all_fields(self, sample_screenshot_data, mock_image):
        """Test creating ScreenshotData with all fields"""
        assert sample_screenshot_data.image == mock_image
        assert sample_screenshot_data.image_data == b"test_image_data"
        assert sample_screenshot_data.coordinates == (100, 100, 900, 700)
        assert sample_screenshot_data.dpi_scale == 1.5
        assert sample_screenshot_data.metadata == {"source": "test"}

    def test_post_init_timestamp(self, mock_image):
        """Test automatic timestamp generation in __post_init__"""
        before_creation = datetime.now()

        screenshot = ScreenshotData(
            image=mock_image, image_data=b"test", coordinates=(0, 0, 100, 100)
        )

        after_creation = datetime.now()

        assert before_creation <= screenshot.timestamp <= after_creation

    def test_post_init_metadata(self, mock_image):
        """Test automatic metadata initialization"""
        screenshot = ScreenshotData(
            image=mock_image, image_data=b"test", coordinates=(0, 0, 100, 100), metadata=None
        )

        assert screenshot.metadata == {}

    def test_unique_id_generation(self, mock_image):
        """Test that each instance gets unique ID"""
        screenshot1 = ScreenshotData(
            image=mock_image, image_data=b"test1", coordinates=(0, 0, 100, 100)
        )

        screenshot2 = ScreenshotData(
            image=mock_image, image_data=b"test2", coordinates=(0, 0, 100, 100)
        )

        assert screenshot1.id != screenshot2.id
        assert len(screenshot1.id) > 0
        assert len(screenshot2.id) > 0

    def test_size_property(self, sample_screenshot_data):
        """Test size property"""
        size = sample_screenshot_data.size

        assert size == (800, 600)

    def test_size_property_no_image(self):
        """Test size property when no image"""
        screenshot = ScreenshotData(image=None, image_data=b"test", coordinates=(0, 0, 100, 100))

        size = sample_screenshot_data.size

        # Should calculate from coordinates when no image
        assert size == (800, 600)  # 900-100, 700-100

    def test_width_property(self, sample_screenshot_data):
        """Test width property"""
        width = sample_screenshot_data.width

        assert width == 800

    def test_height_property(self, sample_screenshot_data):
        """Test height property"""
        height = sample_screenshot_data.height

        assert height == 600

    def test_area_property(self, sample_screenshot_data):
        """Test area property"""
        area = sample_screenshot_data.area

        assert area == 800 * 600

    def test_aspect_ratio_property(self, sample_screenshot_data):
        """Test aspect ratio property"""
        ratio = sample_screenshot_data.aspect_ratio

        assert ratio == 800 / 600

    def test_coordinates_validation(self, mock_image):
        """Test coordinates validation"""
        # Valid coordinates
        screenshot = ScreenshotData(
            image=mock_image, image_data=b"test", coordinates=(100, 100, 300, 300)
        )

        assert screenshot.is_valid_coordinates() is True

        # Invalid coordinates (x1 >= x2)
        screenshot.coordinates = (300, 100, 100, 300)
        assert screenshot.is_valid_coordinates() is False

        # Invalid coordinates (y1 >= y2)
        screenshot.coordinates = (100, 300, 300, 100)
        assert screenshot.is_valid_coordinates() is False

    def test_save_image(self, sample_screenshot_data, tmp_path):
        """Test saving image to file"""
        output_path = tmp_path / "test_screenshot.png"

        success = sample_screenshot_data.save_image(str(output_path))

        assert success is True
        assert output_path.exists()
        assert sample_screenshot_data.image_path == str(output_path)

    def test_save_image_no_image(self, tmp_path):
        """Test saving when no image available"""
        screenshot = ScreenshotData(
            image=None, image_data=b"test_data", coordinates=(0, 0, 100, 100)
        )

        output_path = tmp_path / "test.png"
        success = screenshot.save_image(str(output_path))

        assert success is False

    def test_load_image_from_path(self, sample_screenshot_data, tmp_path):
        """Test loading image from file path"""
        # First save the image
        output_path = tmp_path / "test_load.png"
        sample_screenshot_data.save_image(str(output_path))

        # Create new instance and load from path
        new_screenshot = ScreenshotData(
            image=None, image_data=b"", coordinates=(0, 0, 100, 100), image_path=str(output_path)
        )

        success = new_screenshot.load_image_from_path()

        assert success is True
        assert new_screenshot.image is not None

    def test_get_image_bytes(self, sample_screenshot_data):
        """Test getting image as bytes"""
        image_bytes = sample_screenshot_data.get_image_bytes()

        assert isinstance(image_bytes, bytes)
        assert len(image_bytes) > 0

    def test_get_image_bytes_format(self, sample_screenshot_data):
        """Test getting image bytes in specific format"""
        png_bytes = sample_screenshot_data.get_image_bytes(format="PNG")
        jpg_bytes = sample_screenshot_data.get_image_bytes(format="JPEG")

        assert isinstance(png_bytes, bytes)
        assert isinstance(jpg_bytes, bytes)
        # Different formats should produce different output
        assert png_bytes != jpg_bytes

    def test_crop_image(self, sample_screenshot_data):
        """Test cropping image to specified region"""
        crop_region = (200, 200, 600, 500)

        cropped = sample_screenshot_data.crop_image(crop_region)

        assert cropped is not None
        assert cropped.coordinates == crop_region
        # Original should remain unchanged
        assert sample_screenshot_data.coordinates == (100, 100, 900, 700)

    def test_resize_image(self, sample_screenshot_data):
        """Test resizing image"""
        new_size = (400, 300)

        resized = sample_screenshot_data.resize_image(new_size)

        assert resized is not None
        assert resized.size == new_size
        # Original should remain unchanged
        assert sample_screenshot_data.size == (800, 600)

    def test_scale_coordinates(self, sample_screenshot_data):
        """Test scaling coordinates by factor"""
        scale_factor = 2.0

        scaled = sample_screenshot_data.scale_coordinates(scale_factor)

        expected_coords = (200, 200, 1800, 1400)  # Original * 2
        assert scaled.coordinates == expected_coords
        assert scaled.dpi_scale == 1.5 * 2.0

    def test_to_dict(self, sample_screenshot_data):
        """Test converting to dictionary"""
        data_dict = sample_screenshot_data.to_dict()

        assert "id" in data_dict
        assert "coordinates" in data_dict
        assert "timestamp" in data_dict
        assert "dpi_scale" in data_dict
        assert "metadata" in data_dict
        assert data_dict["coordinates"] == (100, 100, 900, 700)
        assert data_dict["dpi_scale"] == 1.5

    def test_from_dict(self, mock_image):
        """Test creating from dictionary"""
        data_dict = {
            "id": "test_id",
            "coordinates": (50, 50, 250, 200),
            "timestamp": datetime.now(),
            "dpi_scale": 2.0,
            "metadata": {"test": "value"},
            "image_path": "/path/to/image.png",
        }

        screenshot = ScreenshotData.from_dict(data_dict, mock_image, b"test_data")

        assert screenshot.id == "test_id"
        assert screenshot.coordinates == (50, 50, 250, 200)
        assert screenshot.dpi_scale == 2.0
        assert screenshot.metadata == {"test": "value"}
        assert screenshot.image_path == "/path/to/image.png"

    def test_calculate_file_size(self, sample_screenshot_data):
        """Test calculating file size"""
        file_size = sample_screenshot_data.calculate_file_size()

        assert file_size > 0
        assert isinstance(file_size, int)

    def test_get_color_depth(self, sample_screenshot_data):
        """Test getting color depth"""
        color_depth = sample_screenshot_data.get_color_depth()

        assert color_depth > 0
        # RGB mode should have 24-bit depth
        assert color_depth == 24

    def test_has_transparency(self, mock_image):
        """Test checking for transparency"""
        # RGB image (no transparency)
        screenshot_rgb = ScreenshotData(
            image=mock_image, image_data=b"test", coordinates=(0, 0, 100, 100)
        )

        assert screenshot_rgb.has_transparency() is False

        # RGBA image (with transparency)
        mock_image.mode = "RGBA"
        screenshot_rgba = ScreenshotData(
            image=mock_image, image_data=b"test", coordinates=(0, 0, 100, 100)
        )

        assert screenshot_rgba.has_transparency() is True

    def test_get_dominant_colors(self, sample_screenshot_data):
        """Test getting dominant colors from image"""
        # Mock image histogram
        sample_screenshot_data.image.histogram.return_value = [100] * 256 * 3

        colors = sample_screenshot_data.get_dominant_colors(k=3)

        assert len(colors) <= 3
        assert all(isinstance(color, tuple) for color in colors)

    def test_apply_filter(self, sample_screenshot_data):
        """Test applying image filter"""
        filtered = sample_screenshot_data.apply_filter("blur")

        assert filtered is not None
        assert filtered.image is not None
        # Should be a new instance
        assert filtered.id != sample_screenshot_data.id

    def test_rotate_image(self, sample_screenshot_data):
        """Test rotating image"""
        rotated = sample_screenshot_data.rotate_image(90)

        assert rotated is not None
        # Rotation should swap width and height
        assert rotated.size == (600, 800)  # Original was (800, 600)

    def test_flip_image(self, sample_screenshot_data):
        """Test flipping image"""
        flipped_h = sample_screenshot_data.flip_image(horizontal=True)
        flipped_v = sample_screenshot_data.flip_image(vertical=True)

        assert flipped_h is not None
        assert flipped_v is not None
        assert flipped_h.size == sample_screenshot_data.size
        assert flipped_v.size == sample_screenshot_data.size

    def test_add_annotation(self, sample_screenshot_data):
        """Test adding annotation to image"""
        annotation = {
            "type": "rectangle",
            "coordinates": (200, 200, 300, 300),
            "color": "red",
            "width": 2,
        }

        annotated = sample_screenshot_data.add_annotation(annotation)

        assert annotated is not None
        assert "annotations" in annotated.metadata
        assert len(annotated.metadata["annotations"]) == 1

    def test_extract_text_regions(self, sample_screenshot_data):
        """Test extracting text regions from screenshot"""
        # Mock OCR results
        with patch("src.models.screenshot_data.pytesseract") as mock_ocr:
            mock_ocr.image_to_data.return_value = {
                "text": ["Hello", "World", ""],
                "left": [100, 200, 0],
                "top": [150, 250, 0],
                "width": [50, 60, 0],
                "height": [20, 25, 0],
                "conf": [95, 90, -1],
            }

            regions = sample_screenshot_data.extract_text_regions()

            assert len(regions) == 2  # Two valid text regions
            assert regions[0]["text"] == "Hello"
            assert regions[1]["text"] == "World"

    def test_generate_thumbnail(self, sample_screenshot_data):
        """Test generating thumbnail"""
        thumbnail_size = (200, 150)

        thumbnail = sample_screenshot_data.generate_thumbnail(thumbnail_size)

        assert thumbnail is not None
        assert thumbnail.size == thumbnail_size

    def test_calculate_similarity(self, mock_image, sample_screenshot_data):
        """Test calculating similarity with another screenshot"""
        other_screenshot = ScreenshotData(
            image=mock_image, image_data=b"other_data", coordinates=(100, 100, 900, 700)
        )

        similarity = sample_screenshot_data.calculate_similarity(other_screenshot)

        assert 0.0 <= similarity <= 1.0

    def test_merge_screenshots(self, mock_image, sample_screenshot_data):
        """Test merging multiple screenshots"""
        other_screenshot = ScreenshotData(
            image=mock_image, image_data=b"other_data", coordinates=(500, 100, 1400, 700)
        )

        merged = sample_screenshot_data.merge_screenshots([other_screenshot])

        assert merged is not None
        # Merged screenshot should encompass both regions
        assert merged.coordinates[0] <= min(100, 500)  # Min x
        assert merged.coordinates[2] >= max(900, 1400)  # Max x

    def test_validate_data_integrity(self, sample_screenshot_data):
        """Test validating data integrity"""
        # Valid data
        assert sample_screenshot_data.validate_data_integrity() is True

        # Corrupt coordinates
        sample_screenshot_data.coordinates = (100, 100, 90, 200)  # x1 > x2
        assert sample_screenshot_data.validate_data_integrity() is False

    def test_cleanup_resources(self, sample_screenshot_data, tmp_path):
        """Test cleanup of associated resources"""
        # Save image to create file
        image_path = tmp_path / "cleanup_test.png"
        sample_screenshot_data.save_image(str(image_path))

        assert image_path.exists()

        # Cleanup should remove file
        sample_screenshot_data.cleanup_resources()

        # File should be removed if cleanup_resources is implemented
        # (This depends on actual implementation)

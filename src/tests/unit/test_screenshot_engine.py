import io
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    # Create mock Image for tests
    Image = Mock()

from src.core.screenshot_engine import ScreenshotEngine
from src.models.screenshot_data import ScreenshotData
from src.tests.test_utils import requires_windows, skip_on_windows, skip_without_display
from src.utils.exceptions import InvalidAreaError, ScreenshotCaptureError


@unittest.skipUnless(PIL_AVAILABLE, "PIL not available")
class TestScreenshotEngine(unittest.TestCase):
    """Test ScreenshotEngine functionality"""

    def setUp(self):
        """Setup test environment"""
        self.engine = ScreenshotEngine()

    @skip_without_display
    @patch("src.core.screenshot_engine.ImageGrab")
    def test_capture_area(self, mock_grab):
        """Test area capture"""
        # Mock full screen capture for dimension detection
        mock_screen = Mock(spec=Image.Image)
        mock_screen.size = (1920, 1080)  # Full screen size

        # Mock area capture
        mock_area = Mock(spec=Image.Image)
        mock_area.size = (100, 100)  # Area size

        # Configure grab to return screen first, then area
        mock_grab.grab.side_effect = [mock_screen, mock_area]

        # Capture area within screen bounds
        result = self.engine.capture_area(10, 10, 110, 110)

        # Verify
        self.assertIsInstance(result, ScreenshotData)
        self.assertEqual(result.coordinates, (10, 10, 110, 110))
        self.assertEqual(result.size, (100, 100))
        # Should be called twice: once for screen size, once for area
        self.assertEqual(mock_grab.grab.call_count, 2)

    @skip_without_display
    @patch("src.core.screenshot_engine.ImageGrab")
    def test_capture_invalid_area(self, mock_grab):
        """Test invalid area capture"""
        # Mock screen for dimension detection
        mock_screen = Mock(spec=Image.Image)
        mock_screen.size = (1920, 1080)
        mock_grab.grab.return_value = mock_screen

        # Test zero-size area should raise InvalidAreaError
        from src.utils.exceptions import InvalidAreaError

        with self.assertRaises(InvalidAreaError):
            self.engine.capture_area(10, 10, 10, 10)

        # Test negative area (coordinates will be swapped automatically)
        result = self.engine.capture_area(110, 110, 10, 10, screen_width=1920, screen_height=1080)
        # This should work because coordinates get swapped and area becomes valid
        self.assertIsNotNone(result)

        # Grab should be called for screen dimensions and valid area capture
        self.assertGreaterEqual(mock_grab.grab.call_count, 1)

    @skip_without_display
    @patch("src.core.screenshot_engine.ImageGrab")
    def test_capture_center_area(self, mock_grab):
        """Test center area capture"""
        # Mock screen for dimension detection
        mock_screen = Mock(spec=Image.Image)
        mock_screen.size = (1920, 1080)

        # Mock captured area
        mock_area = Mock(spec=Image.Image)
        mock_area.size = (960, 357)  # 50% width, 33% height of 1920x1080

        mock_grab.grab.side_effect = [mock_screen, mock_area]

        # Capture center area with default ratios (0.5 width, 0.33 height)
        result = self.engine.capture_center_area(1920, 1080)

        # Verify result
        self.assertIsInstance(result, ScreenshotData)
        # Center area calculation: x1=480, y1=361, x2=1440, y2=718
        expected_coords = (480, 361, 1440, 718)
        self.assertEqual(result.coordinates, expected_coords)

    @skip_without_display
    @patch("src.core.screenshot_engine.ImageGrab")
    def test_capture_bottom_area(self, mock_grab):
        """Test bottom area capture"""
        # Mock screen for dimension detection
        mock_screen = Mock(spec=Image.Image)
        mock_screen.size = (1920, 1080)

        # Mock captured area
        mock_area = Mock(spec=Image.Image)
        mock_area.size = (1440, 270)  # 75% width, 25% height of 1920x1080

        mock_grab.grab.side_effect = [mock_screen, mock_area]

        # Capture bottom area with default ratios (0.75 width, 0.25 height)
        result = self.engine.capture_bottom_area(1920, 1080)

        # Verify result
        self.assertIsInstance(result, ScreenshotData)
        # Bottom area calculation: x1=240, y1=810, x2=1680, y2=1030 (1080-50)
        expected_coords = (240, 810, 1680, 1030)
        self.assertEqual(result.coordinates, expected_coords)

    @requires_windows
    def test_dpi_awareness_windows(self):
        """Test DPI awareness detection on Windows"""
        # Test that engine initializes without error
        engine = ScreenshotEngine()

        # On Windows, DPI scale should be detected properly
        self.assertIsInstance(engine.dpi_scale, float)
        self.assertGreater(engine.dpi_scale, 0.0)

    @skip_on_windows
    def test_dpi_awareness_non_windows(self):
        """Test DPI awareness on non-Windows systems"""
        engine = ScreenshotEngine()
        # On non-Windows systems, DPI scale should be 1.0
        self.assertEqual(engine.dpi_scale, 1.0)

    def test_save_debug_screenshot(self):
        """Test debug screenshot saving"""
        # Create test image and convert to bytes
        test_image = Image.new("RGB", (100, 100), color="red")
        import io

        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format="PNG")
        img_bytes = img_bytes.getvalue()

        from datetime import datetime

        screenshot_data = ScreenshotData(
            image=test_image,
            image_data=img_bytes,
            coordinates=(0, 0, 100, 100),
            timestamp=datetime.now(),
        )

        # Mock image operations
        with patch("src.core.screenshot_engine.Image.open") as mock_open:
            mock_image = Mock()
            mock_open.return_value = mock_image

            result = self.engine.save_debug_screenshot(screenshot_data)

            # Verify result
            self.assertTrue(result)
            mock_open.assert_called_once()
            mock_image.save.assert_called_once()

    def test_validate_coordinates(self):
        """Test coordinate validation"""
        # Valid coordinates should return adjusted coordinates
        result = self.engine._validate_coordinates(0, 0, 100, 100, 1920, 1080)
        self.assertEqual(result, (0, 0, 100, 100))

        # Swapped coordinates should be corrected
        result = self.engine._validate_coordinates(100, 100, 0, 0, 1920, 1080)
        self.assertEqual(result, (0, 0, 100, 100))

        # Out of bounds coordinates should be clipped
        result = self.engine._validate_coordinates(-10, -10, 2000, 2000, 1920, 1080)
        self.assertEqual(result, (0, 0, 1920, 1080))

    def test_dpi_scale_fallback(self):
        """Test DPI scale fallback on error"""
        with patch("src.core.screenshot_engine.ctypes") as mock_ctypes:
            # Simulate Windows API not available (Linux environment)
            mock_ctypes.windll.shcore.GetScaleFactorForDevice.side_effect = Exception("DPI Error")
            engine = ScreenshotEngine()
            self.assertEqual(engine.dpi_scale, 1.0)

    @patch("src.core.screenshot_engine.ImageGrab")
    def test_capture_area_with_screen_dimensions(self, mock_grab):
        """Test capture area when screen dimensions are provided"""
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (100, 100)
        mock_grab.grab.return_value = mock_image

        result = self.engine.capture_area(10, 10, 110, 110, screen_width=1920, screen_height=1080)

        self.assertIsInstance(result, ScreenshotData)
        # Should only call grab once (no need to get screen dimensions)
        self.assertEqual(mock_grab.grab.call_count, 1)

    @patch("src.core.screenshot_engine.ImageGrab")
    def test_capture_area_none_result(self, mock_grab):
        """Test handling when ImageGrab returns None"""
        mock_grab.grab.return_value = None

        with self.assertRaises(ScreenshotCaptureError):
            self.engine.capture_area(10, 10, 110, 110, screen_width=1920, screen_height=1080)

    @patch("src.core.screenshot_engine.ImageGrab")
    def test_capture_area_with_exception(self, mock_grab):
        """Test handling unexpected exceptions during capture"""
        mock_grab.grab.side_effect = RuntimeError("Unexpected error")

        with self.assertRaises(ScreenshotCaptureError) as context:
            self.engine.capture_area(10, 10, 110, 110, screen_width=1920, screen_height=1080)

        self.assertIn("Unexpected error", str(context.exception))

    def test_capture_area_zero_width(self):
        """Test capture area with zero width"""
        with self.assertRaises(InvalidAreaError):
            self.engine.capture_area(10, 10, 10, 20, screen_width=1920, screen_height=1080)

    def test_capture_area_zero_height(self):
        """Test capture area with zero height"""
        with self.assertRaises(InvalidAreaError):
            self.engine.capture_area(10, 10, 20, 10, screen_width=1920, screen_height=1080)

    @patch("src.core.screenshot_engine.ImageGrab")
    def test_capture_center_area_custom_ratios(self, mock_grab):
        """Test center area capture with custom ratios"""
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (600, 400)  # 60% width, 40% height
        mock_grab.grab.return_value = mock_image

        result = self.engine.capture_center_area(1000, 1000, width_ratio=0.6, height_ratio=0.4)

        self.assertIsInstance(result, ScreenshotData)
        # Center area with 60% width, 40% height: x1=200, y1=300, x2=800, y2=700
        expected_coords = (200, 300, 800, 700)
        self.assertEqual(result.coordinates, expected_coords)

    @patch("src.core.screenshot_engine.ImageGrab")
    def test_capture_bottom_area_custom_ratios(self, mock_grab):
        """Test bottom area capture with custom ratios"""
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (800, 200)  # Custom size
        mock_grab.grab.return_value = mock_image

        result = self.engine.capture_bottom_area(1000, 1000, width_ratio=0.8, height_ratio=0.2)

        self.assertIsInstance(result, ScreenshotData)
        # Bottom area: x1=99, y1=800, x2=900, y2=950 (1000-50) - due to int() rounding
        expected_coords = (99, 800, 900, 950)
        self.assertEqual(result.coordinates, expected_coords)

    def test_save_debug_screenshot_with_filename(self):
        """Test debug screenshot saving with custom filename"""
        test_image = Image.new("RGB", (100, 100), color="blue")
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format="PNG")
        img_bytes = img_bytes.getvalue()

        screenshot_data = ScreenshotData(
            image=test_image,
            image_data=img_bytes,
            coordinates=(0, 0, 100, 100),
            timestamp=datetime.now(),
        )

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            temp_filename = tmp_file.name

        try:
            result = self.engine.save_debug_screenshot(screenshot_data, temp_filename)
            self.assertTrue(result)
            self.assertTrue(os.path.exists(temp_filename))
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def test_save_debug_screenshot_failure(self):
        """Test debug screenshot saving failure"""
        test_image = Image.new("RGB", (100, 100), color="green")

        screenshot_data = ScreenshotData(
            image=test_image,
            image_data=b"invalid_image_data",  # Invalid data
            coordinates=(0, 0, 100, 100),
            timestamp=datetime.now(),
        )

        result = self.engine.save_debug_screenshot(screenshot_data)
        self.assertFalse(result)

    @patch("src.core.screenshot_engine.logger")
    def test_logging_operations(self, mock_logger):
        """Test that operations are properly logged"""
        # Test initialization logging
        engine = ScreenshotEngine()
        mock_logger.debug.assert_called()

        # Test successful capture logging
        with patch("src.core.screenshot_engine.ImageGrab") as mock_grab:
            mock_image = Mock(spec=Image.Image)
            mock_image.size = (100, 100)
            mock_grab.grab.return_value = mock_image

            engine.capture_area(10, 10, 110, 110, screen_width=1920, screen_height=1080)

            # Should have called log_screenshot
            mock_logger.log_screenshot.assert_called()

    @patch("src.core.screenshot_engine.ImageGrab")
    def test_dpi_scaling_applied(self, mock_grab):
        """Test that DPI scaling is applied to coordinates"""
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (200, 200)  # Scaled size
        mock_grab.grab.return_value = mock_image

        # Set custom DPI scale
        self.engine.dpi_scale = 2.0

        self.engine.capture_area(10, 10, 110, 110, screen_width=1920, screen_height=1080)

        # Verify that grab was called with scaled coordinates
        expected_scaled_coords = (20, 20, 220, 220)  # 2x scale
        mock_grab.grab.assert_called_with(bbox=expected_scaled_coords)

    def test_coordinate_boundary_edge_cases(self):
        """Test edge cases in coordinate validation"""
        # Test coordinates at exact screen boundaries
        result = self.engine._validate_coordinates(0, 0, 1920, 1080, 1920, 1080)
        self.assertEqual(result, (0, 0, 1920, 1080))

        # Test single pixel area at boundary
        result = self.engine._validate_coordinates(1919, 1079, 1920, 1080, 1920, 1080)
        self.assertEqual(result, (1919, 1079, 1920, 1080))

        # Test extreme negative coordinates
        result = self.engine._validate_coordinates(-9999, -9999, 100, 100, 1920, 1080)
        self.assertEqual(result, (0, 0, 100, 100))

        # Test extreme positive coordinates
        result = self.engine._validate_coordinates(100, 100, 99999, 99999, 1920, 1080)
        self.assertEqual(result, (100, 100, 1920, 1080))

    @patch("src.core.screenshot_engine.ImageGrab")
    def test_screenshot_data_fields(self, mock_grab):
        """Test that ScreenshotData contains all expected fields"""
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (100, 100)
        mock_grab.grab.return_value = mock_image

        result = self.engine.capture_area(10, 10, 110, 110, screen_width=1920, screen_height=1080)

        # Verify all fields are present
        self.assertIsNotNone(result.image)
        self.assertEqual(result.coordinates, (10, 10, 110, 110))
        self.assertEqual(result.size, (100, 100))
        self.assertIsInstance(result.timestamp, datetime)
        self.assertEqual(result.dpi_scale, self.engine.dpi_scale)

    def test_multiple_capture_independence(self):
        """Test that multiple captures are independent"""
        with patch("src.core.screenshot_engine.ImageGrab") as mock_grab:
            mock_image1 = Mock(spec=Image.Image)
            mock_image1.size = (100, 100)
            mock_image2 = Mock(spec=Image.Image)
            mock_image2.size = (200, 200)

            mock_grab.grab.side_effect = [mock_image1, mock_image2]

            result1 = self.engine.capture_area(
                10, 10, 110, 110, screen_width=1920, screen_height=1080
            )
            result2 = self.engine.capture_area(
                20, 20, 220, 220, screen_width=1920, screen_height=1080
            )

            # Results should be different
            self.assertNotEqual(result1.coordinates, result2.coordinates)
            self.assertNotEqual(result1.size, result2.size)
            self.assertNotEqual(result1.image, result2.image)

    @patch("src.core.screenshot_engine.ImageGrab")
    def test_capture_performance_timing(self, mock_grab):
        """Test that capture performance is logged"""
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (100, 100)
        mock_grab.grab.return_value = mock_image

        with patch("src.core.screenshot_engine.logger") as mock_logger:
            self.engine.capture_area(10, 10, 110, 110, screen_width=1920, screen_height=1080)

            # Verify log_screenshot was called with duration
            args, kwargs = mock_logger.log_screenshot.call_args
            self.assertIn("duration", kwargs)
            self.assertIsInstance(kwargs["duration"], float)
            self.assertGreater(kwargs["duration"], 0)

    def test_integration_center_bottom_areas(self):
        """Test integration between center and bottom area methods"""
        with patch("src.core.screenshot_engine.ImageGrab") as mock_grab:
            mock_image = Mock(spec=Image.Image)
            mock_image.size = (400, 200)
            mock_grab.grab.return_value = mock_image

            # Test that both methods work with same screen dimensions
            center_result = self.engine.capture_center_area(800, 600)
            bottom_result = self.engine.capture_bottom_area(800, 600)

            self.assertIsInstance(center_result, ScreenshotData)
            self.assertIsInstance(bottom_result, ScreenshotData)

            # Areas should be different
            self.assertNotEqual(center_result.coordinates, bottom_result.coordinates)


if __name__ == "__main__":
    unittest.main()

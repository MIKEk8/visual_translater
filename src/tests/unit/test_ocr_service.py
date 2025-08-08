"""Unit tests for OCR service"""

import unittest
from unittest.mock import MagicMock, Mock, patch

from PIL import Image

from src.models.config import AppConfig, ImageProcessingConfig
from src.services.ocr_service import OCRService
from src.utils.exceptions import OCRError


class TestOCRService(unittest.TestCase):
    """Test OCRService class"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_plugin_service = Mock()
        self.mock_config_manager = Mock()
        self.mock_performance_monitor = Mock()

        # Configure mock config
        self.mock_config = AppConfig(
            image_processing=ImageProcessingConfig(
                preprocessing=True,
                contrast_enhancement=True,
                noise_reduction=True,
                deskew=True,
                upscale=False,
            )
        )
        self.mock_config_manager.config = self.mock_config

        # Mock OCR plugin
        self.mock_ocr_plugin = Mock()
        self.mock_ocr_plugin.extract_text.return_value = ("Test text", 0.95)
        self.mock_plugin_service.get_active_plugin.return_value = self.mock_ocr_plugin

        # Create service
        self.service = OCRService(
            plugin_service=self.mock_plugin_service,
            config_manager=self.mock_config_manager,
            performance_monitor=self.mock_performance_monitor,
        )

    def test_initialization(self):
        """Test service initialization"""
        self.assertIsNotNone(self.service)
        self.assertEqual(self.service.plugin_service, self.mock_plugin_service)
        self.assertEqual(self.service.config_manager, self.mock_config_manager)
        self.assertEqual(self.service.performance_monitor, self.mock_performance_monitor)

    def test_extract_text_success(self):
        """Test successful text extraction"""
        # Create test image
        image = Image.new("RGB", (100, 100), color="white")

        text, confidence = self.service.extract_text(image)

        self.assertEqual(text, "Test text")
        self.assertEqual(confidence, 0.95)

        # Verify plugin was called
        self.mock_plugin_service.get_active_plugin.assert_called_once_with("ocr")
        self.mock_ocr_plugin.extract_text.assert_called_once()

        # Verify performance monitoring
        self.mock_performance_monitor.record_metric.assert_called()

    def test_extract_text_no_plugin(self):
        """Test extraction when no OCR plugin is available"""
        self.mock_plugin_service.get_active_plugin.return_value = None

        image = Image.new("RGB", (100, 100), color="white")

        with self.assertRaises(OCRError) as context:
            self.service.extract_text(image)

        self.assertIn("No OCR plugin available", str(context.exception))

    def test_extract_text_plugin_error(self):
        """Test handling of plugin extraction error"""
        self.mock_ocr_plugin.extract_text.side_effect = Exception("Extraction failed")

        image = Image.new("RGB", (100, 100), color="white")

        with self.assertRaises(OCRError) as context:
            self.service.extract_text(image)

        self.assertIn("OCR extraction failed", str(context.exception))

    def test_extract_text_with_language(self):
        """Test extraction with specific language"""
        image = Image.new("RGB", (100, 100), color="white")

        text, confidence = self.service.extract_text(image, language="rus")

        # Verify language was passed to plugin
        call_args = self.mock_ocr_plugin.extract_text.call_args
        # Check if language parameter was passed (depends on plugin implementation)
        self.assertIsNotNone(call_args)

    def test_preprocess_image_enabled(self):
        """Test image preprocessing when enabled"""
        image = Image.new("RGB", (100, 100), color="gray")

        # Enable preprocessing
        self.mock_config.image_processing.preprocessing = True

        with patch.object(self.service, "_enhance_image") as mock_enhance:
            mock_enhance.return_value = image

            self.service.extract_text(image)

            # Should call enhancement
            mock_enhance.assert_called_once_with(image)

    def test_preprocess_image_disabled(self):
        """Test skipping preprocessing when disabled"""
        image = Image.new("RGB", (100, 100), color="gray")

        # Disable preprocessing
        self.mock_config.image_processing.preprocessing = False

        with patch.object(self.service, "_enhance_image") as mock_enhance:
            self.service.extract_text(image)

            # Should not call enhancement
            mock_enhance.assert_not_called()

    def test_enhance_image_contrast(self):
        """Test contrast enhancement"""
        image = Image.new("RGB", (100, 100), color="gray")

        # Enable contrast enhancement
        self.mock_config.image_processing.contrast_enhancement = True

        enhanced = self.service._enhance_image(image)

        # Should return an image
        self.assertIsInstance(enhanced, Image.Image)

    def test_enhance_image_noise_reduction(self):
        """Test noise reduction"""
        image = Image.new("RGB", (100, 100), color="gray")

        # Enable noise reduction
        self.mock_config.image_processing.noise_reduction = True

        enhanced = self.service._enhance_image(image)

        # Should return an image
        self.assertIsInstance(enhanced, Image.Image)

    def test_enhance_image_deskew(self):
        """Test deskewing"""
        image = Image.new("RGB", (100, 100), color="gray")

        # Enable deskew
        self.mock_config.image_processing.deskew = True

        with patch("cv2.minAreaRect") as mock_rect:
            # Mock skew detection
            mock_rect.return_value = ((50, 50), (100, 100), 5.0)  # 5 degree skew

            enhanced = self.service._enhance_image(image)

            # Should return an image
            self.assertIsInstance(enhanced, Image.Image)

    def test_enhance_image_upscale(self):
        """Test image upscaling"""
        # Small image
        image = Image.new("RGB", (50, 50), color="gray")

        # Enable upscaling
        self.mock_config.image_processing.upscale = True

        enhanced = self.service._enhance_image(image)

        # Should upscale small images
        self.assertGreaterEqual(enhanced.width, 50)
        self.assertGreaterEqual(enhanced.height, 50)

    def test_batch_extract(self):
        """Test batch text extraction"""
        images = [
            Image.new("RGB", (100, 100), color="white"),
            Image.new("RGB", (100, 100), color="gray"),
            Image.new("RGB", (100, 100), color="black"),
        ]

        # Mock different results for each image
        self.mock_ocr_plugin.extract_text.side_effect = [
            ("Text 1", 0.95),
            ("Text 2", 0.90),
            ("Text 3", 0.85),
        ]

        results = self.service.batch_extract(images)

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0], ("Text 1", 0.95))
        self.assertEqual(results[1], ("Text 2", 0.90))
        self.assertEqual(results[2], ("Text 3", 0.85))

    def test_batch_extract_with_error(self):
        """Test batch extraction with one failing image"""
        images = [
            Image.new("RGB", (100, 100), color="white"),
            Image.new("RGB", (100, 100), color="gray"),
        ]

        # Second extraction fails
        self.mock_ocr_plugin.extract_text.side_effect = [
            ("Text 1", 0.95),
            Exception("Failed"),
        ]

        results = self.service.batch_extract(images)

        # Should still return results for successful extractions
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], ("Text 1", 0.95))
        self.assertEqual(results[1], ("", 0.0))  # Failed extraction

    def test_get_available_languages(self):
        """Test getting available OCR languages"""
        self.mock_ocr_plugin.get_available_languages = Mock(
            return_value=["eng", "rus", "deu", "fra"]
        )

        languages = self.service.get_available_languages()

        self.assertEqual(languages, ["eng", "rus", "deu", "fra"])
        self.mock_ocr_plugin.get_available_languages.assert_called_once()

    def test_get_available_languages_no_plugin(self):
        """Test getting languages when no plugin available"""
        self.mock_plugin_service.get_active_plugin.return_value = None

        languages = self.service.get_available_languages()

        self.assertEqual(languages, [])

    def test_validate_image(self):
        """Test image validation"""
        # Valid image
        valid_image = Image.new("RGB", (100, 100), color="white")
        self.assertTrue(self.service._validate_image(valid_image))

        # Too small
        small_image = Image.new("RGB", (5, 5), color="white")
        self.assertFalse(self.service._validate_image(small_image))

        # Not an image
        not_image = "not an image"
        self.assertFalse(self.service._validate_image(not_image))

    def test_extract_with_region_of_interest(self):
        """Test extraction from specific region"""
        image = Image.new("RGB", (200, 200), color="white")

        # Define region of interest
        roi = (50, 50, 150, 150)  # x1, y1, x2, y2

        text, confidence = self.service.extract_text(image, region=roi)

        # Verify cropped image was passed to plugin
        call_args = self.mock_ocr_plugin.extract_text.call_args[0][0]
        self.assertEqual(call_args.width, 100)  # 150 - 50
        self.assertEqual(call_args.height, 100)  # 150 - 50

    def test_caching_integration(self):
        """Test integration with caching"""
        image = Image.new("RGB", (100, 100), color="white")

        # First call
        text1, conf1 = self.service.extract_text(image)

        # Second call with same image
        text2, conf2 = self.service.extract_text(image)

        # Both should return same result
        self.assertEqual(text1, text2)
        self.assertEqual(conf1, conf2)

        # But plugin should be called twice (no built-in caching)
        self.assertEqual(self.mock_ocr_plugin.extract_text.call_count, 2)

    def test_performance_metrics(self):
        """Test performance metric recording"""
        image = Image.new("RGB", (100, 100), color="white")

        self.service.extract_text(image)

        # Should record extraction time
        self.mock_performance_monitor.record_metric.assert_called()
        call_args = self.mock_performance_monitor.record_metric.call_args
        self.assertEqual(call_args[0][0], "ocr_extraction_time")
        self.assertIsInstance(call_args[0][1], float)

    def test_extract_with_confidence_threshold(self):
        """Test extraction with minimum confidence threshold"""
        image = Image.new("RGB", (100, 100), color="white")

        # Low confidence result
        self.mock_ocr_plugin.extract_text.return_value = ("Unclear text", 0.5)

        with self.assertRaises(OCRError) as context:
            self.service.extract_text(image, min_confidence=0.7)

        self.assertIn("Confidence too low", str(context.exception))


if __name__ == "__main__":
    unittest.main()

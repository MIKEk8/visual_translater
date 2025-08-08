import asyncio
import io
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = Mock()

from src.core.ocr_engine import OCREngine, OCRProcessor, TesseractOCR
from src.models.config import ImageProcessingConfig
from src.models.screenshot_data import ScreenshotData
from src.services.circuit_breaker import CircuitBreakerError


@unittest.skipUnless(PIL_AVAILABLE, "PIL not available")
class TestTesseractOCR(unittest.TestCase):
    """Test TesseractOCR engine"""

    def setUp(self):
        """Setup test environment"""
        self.engine = TesseractOCR()

    def test_find_tesseract_executable(self):
        """Test finding Tesseract executable"""
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True

            path = self.engine._find_tesseract()
            # Should find first available path
            self.assertIsNotNone(path)
            mock_exists.assert_called()

    def test_find_tesseract_not_found(self):
        """Test Tesseract not found"""
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = False

            path = self.engine._find_tesseract()
            # Should still find 'tesseract' as fallback
            self.assertEqual(path, "tesseract")

    @patch("src.core.ocr_engine.TesseractOCR._find_tesseract")
    @patch("importlib.util.find_spec")
    def test_is_available_true(self, mock_find_spec, mock_find_tesseract):
        """Test availability when Tesseract is available"""
        mock_find_spec.return_value = Mock()  # pytesseract available
        mock_find_tesseract.return_value = "/usr/bin/tesseract"

        # Mock pytesseract module
        with patch.dict("sys.modules", {"pytesseract": MagicMock()}):
            self.assertTrue(self.engine.is_available())

    @patch("src.core.ocr_engine.TesseractOCR._find_tesseract")
    def test_is_available_false(self, mock_find_tesseract):
        """Test availability when Tesseract is not available"""
        mock_find_tesseract.return_value = None  # tesseract executable not found

        # Create a new engine instance to test the initialization with None tesseract_cmd
        engine = TesseractOCR()
        self.assertFalse(engine.is_available())

    def test_extract_text_success(self):
        """Test successful text extraction"""
        # Mock pytesseract module
        mock_pytesseract = MagicMock()
        mock_pytesseract.image_to_string.return_value = "  Hello World  "
        mock_pytesseract.image_to_data.return_value = {
            "conf": ["95", "90", "88", "92", "0", "-1"],  # Mixed confidence values
        }
        mock_pytesseract.Output.DICT = "dict"

        with patch.dict("sys.modules", {"pytesseract": mock_pytesseract}):
            # Create test image
            test_image = Image.new("RGB", (100, 50), color="white")

            text, confidence = self.engine.extract_text(test_image, "eng")

            self.assertEqual(text, "Hello World")  # Should be stripped
            self.assertIsNotNone(confidence)
            self.assertGreater(confidence, 0)

            mock_pytesseract.image_to_string.assert_called_once_with(test_image, lang="eng")

    def test_extract_text_confidence_calculation(self):
        """Test confidence calculation"""
        mock_pytesseract = MagicMock()
        mock_pytesseract.image_to_string.return_value = "Test"
        mock_pytesseract.image_to_data.return_value = {
            "conf": ["95", "90", "85", "0", "-1"],  # Should average 95, 90, 85 = 90
        }
        mock_pytesseract.Output.DICT = "dict"

        with patch.dict("sys.modules", {"pytesseract": mock_pytesseract}):
            test_image = Image.new("RGB", (100, 50), color="white")
            text, confidence = self.engine.extract_text(test_image)

            expected_confidence = (95 + 90 + 85) / 3
            self.assertAlmostEqual(confidence, expected_confidence, places=1)

    def test_extract_text_no_confidence(self):
        """Test extraction when confidence data is not available"""
        # Create an engine instance first
        engine = TesseractOCR()

        # Mock the methods directly on the engine
        with patch("pytesseract.image_to_string", return_value="Test"):
            with patch("pytesseract.image_to_data", side_effect=Exception("No confidence data")):
                test_image = Image.new("RGB", (100, 50), color="white")
                text, confidence = engine.extract_text(test_image)

                self.assertEqual(text, "Test")
                self.assertIsNone(confidence)

    def test_extract_text_failure(self):
        """Test extraction failure"""
        mock_pytesseract = MagicMock()
        mock_pytesseract.image_to_string.side_effect = Exception("OCR failed")

        with patch.dict("sys.modules", {"pytesseract": mock_pytesseract}):
            test_image = Image.new("RGB", (100, 50), color="white")
            text, confidence = self.engine.extract_text(test_image)

            self.assertEqual(text, "")
            self.assertIsNone(confidence)


@unittest.skipUnless(PIL_AVAILABLE, "PIL not available")
class TestOCRProcessor(unittest.TestCase):
    """Test OCRProcessor functionality"""

    def setUp(self):
        """Setup test environment"""
        self.config = ImageProcessingConfig(
            upscale_factor=2.0,
            contrast_enhance=1.5,
            sharpness_enhance=2.0,
            ocr_confidence_threshold=0.7,
            enable_preprocessing=True,
            noise_reduction=True,
        )

        # Mock the engine to be available
        with patch("src.core.ocr_engine.TesseractOCR.is_available", return_value=True):
            self.processor = OCRProcessor(self.config)

    def test_initialization_with_available_engine(self):
        """Test processor initialization with available engine"""
        with patch("src.core.ocr_engine.TesseractOCR.is_available", return_value=True):
            processor = OCRProcessor(self.config)
            self.assertIsNotNone(processor.active_engine)

    def test_initialization_no_engines(self):
        """Test processor initialization with no available engines"""
        with patch("src.core.ocr_engine.TesseractOCR.is_available", return_value=False):
            processor = OCRProcessor(self.config)
            self.assertIsNone(processor.active_engine)

    def test_enhance_image_basic(self):
        """Test basic image enhancement"""
        # Create test image
        test_image = Image.new("RGB", (100, 100), color="white")

        enhanced = self.processor.enhance_image(test_image)

        # Should be enhanced
        self.assertIsInstance(enhanced, Image.Image)
        # Should be upscaled
        self.assertEqual(enhanced.size, (200, 200))  # 2x upscale

    def test_enhance_image_disabled(self):
        """Test image enhancement when disabled"""
        config = ImageProcessingConfig(enable_preprocessing=False)
        processor = OCRProcessor(config)

        test_image = Image.new("RGB", (100, 100), color="white")
        enhanced = processor.enhance_image(test_image)

        # Should return original image unchanged
        self.assertEqual(enhanced.size, test_image.size)

    def test_enhance_image_mode_conversion(self):
        """Test image mode conversion"""
        # Create RGBA image
        test_image = Image.new("RGBA", (100, 100), color=(255, 255, 255, 128))

        enhanced = self.processor.enhance_image(test_image)

        # Should be converted to RGB
        self.assertEqual(enhanced.mode, "RGB")

    def test_noise_reduction(self):
        """Test noise reduction filters"""
        test_image = Image.new("RGB", (100, 100), color="white")

        # Mock the _apply_noise_reduction method to verify it gets called
        with patch.object(self.processor, "_apply_noise_reduction") as mock_noise_reduction:
            mock_noise_reduction.return_value = test_image.copy()

            self.processor.enhance_image(test_image)

            # Should call noise reduction when enabled
            mock_noise_reduction.assert_called_once_with(test_image)

    def test_noise_reduction_disabled(self):
        """Test when noise reduction is disabled"""
        config = ImageProcessingConfig(noise_reduction=False)
        with patch("src.core.ocr_engine.TesseractOCR.is_available", return_value=True):
            processor = OCRProcessor(config)

        test_image = Image.new("RGB", (100, 100), color="white")

        with patch("PIL.ImageFilter") as mock_filter:
            processor.enhance_image(test_image)

            # Should not apply noise reduction filters
            mock_filter.GaussianBlur.assert_not_called()

    def test_noise_reduction_import_error(self):
        """Test noise reduction with import error"""
        test_image = Image.new("RGB", (100, 100), color="white")

        with patch("src.core.ocr_engine.logger") as mock_logger:
            with patch("PIL.ImageFilter", side_effect=ImportError("No ImageFilter")):
                enhanced = self.processor._apply_noise_reduction(test_image)

                # Should return original image and log debug message
                self.assertEqual(enhanced, test_image)
                mock_logger.debug.assert_called()

    def test_process_screenshot_success(self):
        """Test successful screenshot processing"""
        # Create test screenshot data
        test_image = Image.new("RGB", (100, 100), color="white")
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format="PNG")

        screenshot_data = ScreenshotData(
            image=test_image,
            image_data=img_bytes.getvalue(),
            coordinates=(0, 0, 100, 100),
            timestamp=datetime.now(),
        )

        # Mock the OCR engine
        with patch.object(self.processor.active_engine, "extract_text") as mock_extract:
            mock_extract.return_value = ("Hello World", 0.95)

            text, confidence = self.processor.process_screenshot(screenshot_data, "eng")

            self.assertEqual(text, "Hello World")
            self.assertEqual(confidence, 0.95)
            mock_extract.assert_called_once()

    def test_process_screenshot_low_confidence(self):
        """Test processing with low confidence"""
        test_image = Image.new("RGB", (100, 100), color="white")
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format="PNG")

        screenshot_data = ScreenshotData(
            image=test_image,
            image_data=img_bytes.getvalue(),
            coordinates=(0, 0, 100, 100),
            timestamp=datetime.now(),
        )

        # Mock low confidence result
        with patch.object(self.processor.active_engine, "extract_text") as mock_extract:
            with patch("src.core.ocr_engine.logger") as mock_logger:
                mock_extract.return_value = ("Uncertain text", 0.5)  # Below 0.7 threshold

                text, confidence = self.processor.process_screenshot(screenshot_data)

                # Should still return text but log warning
                self.assertEqual(text, "Uncertain text")
                self.assertEqual(confidence, 0.5)
                mock_logger.warning.assert_called()

                # Warning should mention confidence threshold
                warning_call = mock_logger.warning.call_args[0][0]
                self.assertIn("confidence", warning_call.lower())
                self.assertIn("threshold", warning_call.lower())

    def test_process_screenshot_no_engine(self):
        """Test processing with no available engine"""
        # Create processor with no engines
        with patch("src.core.ocr_engine.TesseractOCR.is_available", return_value=False):
            processor = OCRProcessor(self.config)

        screenshot_data = ScreenshotData(
            image=Image.new("RGB", (100, 100)),
            image_data=b"fake_data",
            coordinates=(0, 0, 100, 100),
            timestamp=datetime.now(),
        )

        text, confidence = processor.process_screenshot(screenshot_data)

        self.assertEqual(text, "")
        self.assertIsNone(confidence)

    def test_process_screenshot_exception(self):
        """Test processing with exception"""
        screenshot_data = ScreenshotData(
            image=Image.new("RGB", (100, 100)),
            image_data=b"invalid_image_data",  # Invalid data
            coordinates=(0, 0, 100, 100),
            timestamp=datetime.now(),
        )

        # Should handle exception gracefully
        text, confidence = self.processor.process_screenshot(screenshot_data)

        self.assertEqual(text, "")
        self.assertIsNone(confidence)

    def test_clean_text(self):
        """Test text cleaning functionality"""
        # Test various text cleaning scenarios
        test_cases = [
            ("  Hello World  ", "Hello World"),
            ("Hello\n\nWorld", "Hello World"),
            ("Hello\t\tWorld", "Hello World"),
            ("Hello\r\nWorld", "Hello World"),
            ("", ""),
            ("   \n\t   ", ""),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                cleaned = self.processor._clean_text(input_text)
                self.assertEqual(cleaned, expected)

    def test_extract_text_from_image_direct(self):
        """Test direct image extraction method"""
        # Create test screenshot data
        test_image = Image.new("RGB", (100, 100), color="white")
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format="PNG")

        screenshot_data = ScreenshotData(
            image=test_image,
            image_data=img_bytes.getvalue(),
            coordinates=(0, 0, 100, 100),
            timestamp=datetime.now(),
        )

        # Mock the OCR engine directly
        with patch.object(self.processor.active_engine, "extract_text") as mock_extract:
            mock_extract.return_value = ("Direct extraction", 0.9)

            text, confidence = self.processor.process_screenshot(screenshot_data, "eng")

            self.assertEqual(text, "Direct extraction")
            self.assertEqual(confidence, 0.9)
            mock_extract.assert_called_once()


@unittest.skipUnless(PIL_AVAILABLE, "PIL not available")
class TestImageProcessingConfig(unittest.TestCase):
    """Test ImageProcessingConfig updates"""

    def setUp(self):
        """Setup test environment"""
        self.config = ImageProcessingConfig(
            upscale_factor=2.0,
            contrast_enhance=1.5,
            sharpness_enhance=2.0,
            ocr_confidence_threshold=0.7,
            enable_preprocessing=True,
            noise_reduction=True,
        )

        # Mock the engine to be available
        with patch("src.core.ocr_engine.TesseractOCR.is_available", return_value=True):
            self.processor = OCRProcessor(self.config)

    def test_new_config_fields(self):
        """Test new configuration fields"""
        config = ImageProcessingConfig()

        # Test new fields with defaults
        self.assertEqual(config.ocr_confidence_threshold, 0.7)
        self.assertTrue(config.enable_preprocessing)
        self.assertTrue(config.noise_reduction)

    def test_config_customization(self):
        """Test configuration customization"""
        config = ImageProcessingConfig(
            ocr_confidence_threshold=0.8, enable_preprocessing=False, noise_reduction=False
        )

        self.assertEqual(config.ocr_confidence_threshold, 0.8)
        self.assertFalse(config.enable_preprocessing)
        self.assertFalse(config.noise_reduction)

    def test_get_engine_info(self):
        """Test getting engine information"""
        info = self.processor.get_engine_info()

        self.assertIn("engine", info)
        self.assertIn("available", info)

        if self.processor.active_engine:
            self.assertTrue(info["available"])
            self.assertEqual(info["engine"], "TesseractOCR")
        else:
            self.assertFalse(info["available"])
            self.assertEqual(info["engine"], "None")

    def test_get_engine_info_no_engine(self):
        """Test getting engine info when no engine available"""
        with patch("src.core.ocr_engine.TesseractOCR.is_available", return_value=False):
            processor = OCRProcessor(self.config)

            info = processor.get_engine_info()

            self.assertEqual(info["engine"], "None")
            self.assertFalse(info["available"])

    def test_multiple_engines_availability(self):
        """Test processor with multiple engines"""
        # Mock multiple engines
        mock_engine1 = Mock(spec=OCREngine)
        mock_engine1.is_available.return_value = False

        mock_engine2 = Mock(spec=OCREngine)
        mock_engine2.is_available.return_value = True

        processor = OCRProcessor(self.config)
        processor.engines = [mock_engine1, mock_engine2]

        # Should select second engine
        active_engine = processor._get_available_engine()
        self.assertEqual(active_engine, mock_engine2)

    def test_image_enhancement_error_handling(self):
        """Test image enhancement with errors"""
        test_image = Image.new("RGB", (100, 100), color="white")

        with patch("PIL.ImageEnhance.Contrast") as mock_contrast:
            mock_contrast.side_effect = Exception("Enhancement failed")

            # Should return original image on error
            enhanced = self.processor.enhance_image(test_image)
            self.assertEqual(enhanced, test_image)

    def test_text_cleaning_edge_cases(self):
        """Test text cleaning with edge cases"""
        test_cases = [
            ("Hello\x00World", "Hello World"),  # Null character
            ("Test\u200bText", "Test Text"),  # Zero-width space
            ("Multiple\n\n\nLines", "Multiple Lines"),
            ("Tab\t\tSeparated\t\tText", "Tab Separated Text"),
            ("Mixed\r\n\t  Whitespace", "Mixed Whitespace"),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=repr(input_text)):
                cleaned = self.processor._clean_text(input_text)
                self.assertEqual(cleaned, expected)

    @patch("src.core.ocr_engine.logger")
    def test_processor_logging(self, mock_logger):
        """Test that processor operations are logged"""
        # Test initialization logging
        with patch("src.core.ocr_engine.TesseractOCR.is_available", return_value=True):
            processor = OCRProcessor(self.config)
            mock_logger.info.assert_called()

        # Reset mock for processing test
        mock_logger.reset_mock()

        # Test processing logging
        test_image = Image.new("RGB", (100, 100), color="white")
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format="PNG")

        screenshot_data = ScreenshotData(
            image=test_image,
            image_data=img_bytes.getvalue(),
            coordinates=(0, 0, 100, 100),
            timestamp=datetime.now(),
        )

        with patch.object(processor.active_engine, "extract_text") as mock_extract:
            mock_extract.return_value = ("Test", 0.9)

            processor.process_screenshot(screenshot_data)

            # Should call log_ocr
            mock_logger.log_ocr.assert_called_once()

    def test_is_available_method(self):
        """Test processor availability check"""
        # With available engine
        self.assertTrue(self.processor.is_available())

        # Without available engine
        with patch("src.core.ocr_engine.TesseractOCR.is_available", return_value=False):
            processor = OCRProcessor(self.config)
            self.assertFalse(processor.is_available())


@unittest.skipUnless(PIL_AVAILABLE, "PIL not available")
class TestTesseractOCRCircuitBreaker(unittest.TestCase):
    """Test TesseractOCR circuit breaker functionality"""

    def setUp(self):
        """Setup test environment"""
        with patch("src.core.ocr_engine.get_circuit_breaker_manager") as mock_manager:
            self.mock_circuit_breaker = Mock()
            mock_manager.return_value.create_circuit_breaker.return_value = (
                self.mock_circuit_breaker
            )

            with patch("src.core.ocr_engine.TesseractOCR.is_available", return_value=True):
                self.engine = TesseractOCR()

    def test_circuit_breaker_initialization(self):
        """Test circuit breaker is properly initialized"""
        self.assertIsNotNone(self.engine.circuit_breaker)

    def test_extract_text_with_circuit_breaker_success(self):
        """Test successful text extraction through circuit breaker"""
        test_image = Image.new("RGB", (100, 50), color="white")

        # Mock successful circuit breaker call
        async def mock_call(func):
            return await func()

        self.mock_circuit_breaker.call = AsyncMock(side_effect=mock_call)

        with patch("pytesseract.image_to_string", return_value="Test Text"):
            with patch("pytesseract.image_to_data", return_value={"conf": ["95", "90", "85"]}):
                text, confidence = self.engine.extract_text(test_image)

                self.assertEqual(text, "Test Text")
                self.assertIsNotNone(confidence)

    def test_extract_text_circuit_breaker_error(self):
        """Test circuit breaker error handling"""
        test_image = Image.new("RGB", (100, 50), color="white")

        # Mock circuit breaker error
        from src.services.circuit_breaker import CircuitState

        self.mock_circuit_breaker.call = AsyncMock(
            side_effect=CircuitBreakerError("Circuit open", CircuitState.OPEN)
        )

        text, confidence = self.engine.extract_text(test_image)

        self.assertEqual(text, "")
        self.assertIsNone(confidence)

    def test_tesseract_setup_without_import(self):
        """Test Tesseract setup when pytesseract is not available"""
        with patch("importlib.util.find_spec", return_value=None):  # Simulate no pytesseract
            with patch("src.core.ocr_engine.logger") as mock_logger:
                engine = TesseractOCR()
                engine._setup_tesseract()

                # Should log error about unavailable pytesseract
                mock_logger.error.assert_called()

    def test_tesseract_availability_test_failure(self):
        """Test availability when Tesseract test fails"""
        with patch("pytesseract.image_to_string", side_effect=Exception("Tesseract not working")):
            engine = TesseractOCR()
            self.assertFalse(engine.is_available())


@unittest.skipUnless(PIL_AVAILABLE, "PIL not available")
class TestOCREngineAbstract(unittest.TestCase):
    """Test OCR engine abstract base class"""

    def test_abstract_methods_required(self):
        """Test that abstract methods must be implemented"""
        with self.assertRaises(TypeError):
            OCREngine()

    def test_concrete_implementation(self):
        """Test that concrete implementation works"""

        class TestOCREngine(OCREngine):
            def extract_text(self, image, languages="eng"):
                return "test", 0.95

            def is_available(self):
                return True

        engine = TestOCREngine()
        text, confidence = engine.extract_text(Image.new("RGB", (100, 100)))

        self.assertEqual(text, "test")
        self.assertEqual(confidence, 0.95)
        self.assertTrue(engine.is_available())


@unittest.skipUnless(PIL_AVAILABLE, "PIL not available")
class TestOCRProcessorAdvanced(unittest.TestCase):
    """Advanced OCR processor tests"""

    def setUp(self):
        """Setup test environment"""
        self.config = ImageProcessingConfig(
            upscale_factor=1.5,
            contrast_enhance=1.2,
            sharpness_enhance=1.1,
            ocr_confidence_threshold=0.8,
            enable_preprocessing=True,
            noise_reduction=True,
        )

        with patch("src.core.ocr_engine.TesseractOCR.is_available", return_value=True):
            self.processor = OCRProcessor(self.config)

    def test_complex_image_enhancement_pipeline(self):
        """Test complete image enhancement pipeline"""
        # Create RGBA test image
        test_image = Image.new("RGBA", (100, 100), color=(255, 255, 255, 128))

        with patch("PIL.ImageFilter.GaussianBlur") as mock_blur:
            with patch("PIL.ImageFilter.UnsharpMask") as mock_unsharp:
                mock_blur.return_value = test_image
                mock_unsharp.return_value = test_image

                enhanced = self.processor.enhance_image(test_image)

                # Should be converted to RGB
                self.assertEqual(enhanced.mode, "RGB")

                # Should be upscaled
                expected_size = (int(100 * 1.5), int(100 * 1.5))
                self.assertEqual(enhanced.size, expected_size)

    def test_performance_timing(self):
        """Test that processing time is measured"""
        test_image = Image.new("RGB", (100, 100), color="white")
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format="PNG")

        screenshot_data = ScreenshotData(
            image=test_image,
            image_data=img_bytes.getvalue(),
            coordinates=(0, 0, 100, 100),
            timestamp=datetime.now(),
        )

        with patch.object(self.processor.active_engine, "extract_text") as mock_extract:
            with patch("src.core.ocr_engine.logger") as mock_logger:
                mock_extract.return_value = ("Test", 0.9)

                self.processor.process_screenshot(screenshot_data)

                # Should log duration
                args, kwargs = mock_logger.log_ocr.call_args
                self.assertIn("duration", kwargs)
                self.assertIsInstance(kwargs["duration"], float)
                self.assertGreater(kwargs["duration"], 0)


if __name__ == "__main__":
    unittest.main()

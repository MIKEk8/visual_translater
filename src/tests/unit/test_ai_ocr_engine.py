"""Unit tests for AI-enhanced OCR engine"""

import unittest
from unittest.mock import MagicMock, Mock, patch

import numpy as np
from PIL import Image

from src.core.ai_ocr_engine import (
    AIEnhancedOCRPlugin,
    ImageEnhancer,
    TextDetector,
    TextRegion,
)


class TestTextRegion(unittest.TestCase):
    """Test TextRegion data class"""

    def test_text_region_creation(self):
        """Test creating a TextRegion instance"""
        region = TextRegion(
            x=100,
            y=200,
            width=300,
            height=400,
            confidence=0.95,
            text="Sample text",
        )

        self.assertEqual(region.x, 100)
        self.assertEqual(region.y, 200)
        self.assertEqual(region.width, 300)
        self.assertEqual(region.height, 400)
        self.assertEqual(region.confidence, 0.95)
        self.assertEqual(region.text, "Sample text")

    def test_text_region_area(self):
        """Test area calculation"""
        region = TextRegion(x=0, y=0, width=100, height=50, confidence=0.9)
        self.assertEqual(region.area, 5000)

    def test_text_region_center(self):
        """Test center point calculation"""
        region = TextRegion(x=100, y=200, width=100, height=100, confidence=0.9)
        center_x, center_y = region.center
        self.assertEqual(center_x, 150)
        self.assertEqual(center_y, 250)

    def test_text_region_to_dict(self):
        """Test conversion to dictionary"""
        region = TextRegion(x=10, y=20, width=30, height=40, confidence=0.85, text="Test")
        result = region.to_dict()

        self.assertEqual(result["x"], 10)
        self.assertEqual(result["y"], 20)
        self.assertEqual(result["width"], 30)
        self.assertEqual(result["height"], 40)
        self.assertEqual(result["confidence"], 0.85)
        self.assertEqual(result["text"], "Test")


class TestTextDetector(unittest.TestCase):
    """Test TextDetector class"""

    def setUp(self):
        """Set up test fixtures"""
        self.detector = TextDetector()

    @patch("cv2.dnn.readNet")
    def test_initialization(self, mock_readnet):
        """Test TextDetector initialization"""
        detector = TextDetector()
        self.assertIsNotNone(detector)
        # Should attempt to load model
        mock_readnet.assert_called()

    def test_detect_text_regions_no_model(self):
        """Test detection when model is not available"""
        self.detector.net = None
        image = np.zeros((100, 100, 3), dtype=np.uint8)

        regions = self.detector.detect_text_regions(image)
        self.assertEqual(len(regions), 0)

    @patch("cv2.dnn.NMSBoxes")
    @patch("cv2.dnn.blobFromImage")
    def test_detect_text_regions_with_model(self, mock_blob, mock_nms):
        """Test text detection with loaded model"""
        # Mock model
        mock_net = Mock()
        mock_net.forward.return_value = [
            np.array([[[[0.9]]]], dtype=np.float32),  # scores
            np.array(
                [[[[0.1, 0.2, 0.3, 0.4]]]],  # geometry
                dtype=np.float32,
            ),
        ]
        self.detector.net = mock_net

        # Mock NMS
        mock_nms.return_value = ([0], [0.9])

        # Test image
        image = np.zeros((320, 320, 3), dtype=np.uint8)

        regions = self.detector.detect_text_regions(image)

        # Should call blob creation
        mock_blob.assert_called_once()
        # Should call forward pass
        mock_net.forward.assert_called_once()

    def test_group_regions_by_line_empty(self):
        """Test grouping empty regions"""
        result = self.detector.group_regions_by_line([])
        self.assertEqual(len(result), 0)

    def test_group_regions_by_line_single(self):
        """Test grouping single region"""
        region = TextRegion(x=0, y=0, width=100, height=50, confidence=0.9)
        result = self.detector.group_regions_by_line([region])
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]), 1)

    def test_group_regions_by_line_multiple_lines(self):
        """Test grouping regions on different lines"""
        region1 = TextRegion(x=0, y=0, width=100, height=30, confidence=0.9)
        region2 = TextRegion(x=0, y=100, width=100, height=30, confidence=0.9)

        result = self.detector.group_regions_by_line([region1, region2])
        self.assertEqual(len(result), 2)

    def test_group_regions_by_line_same_line(self):
        """Test grouping regions on same line"""
        region1 = TextRegion(x=0, y=10, width=100, height=30, confidence=0.9)
        region2 = TextRegion(x=110, y=15, width=100, height=30, confidence=0.9)

        result = self.detector.group_regions_by_line([region1, region2])
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]), 2)

    def test_merge_line_regions(self):
        """Test merging regions in a line"""
        region1 = TextRegion(x=0, y=10, width=100, height=30, confidence=0.9, text="Hello")
        region2 = TextRegion(x=110, y=10, width=100, height=30, confidence=0.8, text="World")

        merged = self.detector.merge_line_regions([region1, region2])

        self.assertEqual(merged.x, 0)
        self.assertEqual(merged.y, 10)
        self.assertEqual(merged.width, 210)
        self.assertEqual(merged.text, "Hello World")
        self.assertAlmostEqual(merged.confidence, 0.85)


class TestImageEnhancer(unittest.TestCase):
    """Test ImageEnhancer class"""

    def setUp(self):
        """Set up test fixtures"""
        self.enhancer = ImageEnhancer()

    def test_enhance_for_ocr(self):
        """Test OCR enhancement pipeline"""
        # Create test image
        image = np.ones((100, 100, 3), dtype=np.uint8) * 128

        enhanced = self.enhancer.enhance_for_ocr(image)

        self.assertIsNotNone(enhanced)
        self.assertEqual(enhanced.shape[:2], (100, 100))

    def test_auto_adjust_contrast(self):
        """Test automatic contrast adjustment"""
        # Low contrast image
        image = np.ones((100, 100), dtype=np.uint8) * 128

        adjusted = self.enhancer.auto_adjust_contrast(image)

        # Should increase contrast
        self.assertGreater(np.std(adjusted), np.std(image))

    def test_remove_noise(self):
        """Test noise removal"""
        # Create noisy image
        image = np.random.randint(0, 255, (100, 100), dtype=np.uint8)

        denoised = self.enhancer.remove_noise(image)

        self.assertIsNotNone(denoised)
        self.assertEqual(denoised.shape, image.shape)

    def test_adaptive_threshold(self):
        """Test adaptive thresholding"""
        image = np.ones((100, 100), dtype=np.uint8) * 128

        binary = self.enhancer.adaptive_threshold(image)

        # Should be binary
        unique = np.unique(binary)
        self.assertTrue(all(v in [0, 255] for v in unique))

    def test_deskew_straight_image(self):
        """Test deskewing already straight image"""
        image = np.ones((100, 100), dtype=np.uint8) * 255
        # Add some lines
        image[50, :] = 0

        deskewed = self.enhancer.deskew(image)

        self.assertEqual(deskewed.shape, image.shape)

    def test_sharpen_image(self):
        """Test image sharpening"""
        image = np.ones((100, 100), dtype=np.uint8) * 128

        sharpened = self.enhancer.sharpen(image)

        self.assertIsNotNone(sharpened)
        self.assertEqual(sharpened.shape, image.shape)

    def test_enhance_low_contrast(self):
        """Test enhancement of low contrast image"""
        # Very low contrast image
        image = np.ones((100, 100, 3), dtype=np.uint8) * 127
        image[40:60, 40:60] = 129

        enhanced = self.enhancer.enhance_for_ocr(image, enhance_contrast=True)

        # Should increase contrast
        self.assertIsNotNone(enhanced)

    def test_enhance_dark_image(self):
        """Test enhancement of dark image"""
        # Dark image
        image = np.ones((100, 100, 3), dtype=np.uint8) * 30

        enhanced = self.enhancer.enhance_for_ocr(image, adaptive_thresh=True)

        # Should brighten
        self.assertGreater(np.mean(enhanced), np.mean(image[:, :, 0]))


class TestAIEnhancedOCRPlugin(unittest.TestCase):
    """Test AIEnhancedOCRPlugin"""

    def setUp(self):
        """Set up test fixtures"""
        self.plugin = AIEnhancedOCRPlugin()

    @patch("src.core.ai_ocr_engine.TesseractOCR")
    def test_initialization(self, mock_tesseract):
        """Test plugin initialization"""
        plugin = AIEnhancedOCRPlugin()
        self.assertIsNotNone(plugin.text_detector)
        self.assertIsNotNone(plugin.enhancer)
        self.assertIsNotNone(plugin.base_ocr)

    def test_info(self):
        """Test plugin info"""
        info = self.plugin.info()
        self.assertEqual(info["name"], "AI-Enhanced OCR")
        self.assertIn("version", info)
        self.assertIn("description", info)

    @patch("pytesseract.pytesseract.tesseract_cmd", "tesseract")
    def test_is_available(self):
        """Test availability check"""
        with patch("importlib.util.find_spec") as mock_spec:
            mock_spec.side_effect = lambda x: Mock() if x != "easyocr" else None

            available = self.plugin.is_available()
            # Should be available if dependencies are met
            self.assertIsInstance(available, bool)

    def test_extract_text_with_regions(self):
        """Test text extraction with detected regions"""
        # Mock image
        image = Image.new("RGB", (100, 100), color="white")

        # Mock text detection
        mock_region = TextRegion(x=10, y=10, width=80, height=30, confidence=0.9, text="Test text")
        self.plugin.text_detector.detect_text_regions = Mock(return_value=[mock_region])

        # Mock OCR
        self.plugin.base_ocr.extract_text = Mock(return_value=("Test text", 0.95))

        text, confidence = self.plugin.extract_text(image)

        self.assertEqual(text, "Test text")
        self.assertGreater(confidence, 0)

    def test_extract_text_no_regions(self):
        """Test text extraction when no regions detected"""
        # Mock image
        image = Image.new("RGB", (100, 100), color="white")

        # No regions detected
        self.plugin.text_detector.detect_text_regions = Mock(return_value=[])

        # Fallback to base OCR
        self.plugin.base_ocr.extract_text = Mock(return_value=("Fallback text", 0.85))

        text, confidence = self.plugin.extract_text(image)

        self.assertEqual(text, "Fallback text")
        self.assertEqual(confidence, 0.85)

    def test_extract_text_error_handling(self):
        """Test error handling during extraction"""
        image = Image.new("RGB", (100, 100), color="white")

        # Simulate error in text detection
        self.plugin.text_detector.detect_text_regions = Mock(
            side_effect=Exception("Detection failed")
        )

        # Should fall back to base OCR
        self.plugin.base_ocr.extract_text = Mock(return_value=("Fallback", 0.8))

        text, confidence = self.plugin.extract_text(image)

        self.assertEqual(text, "Fallback")
        self.assertEqual(confidence, 0.8)

    def test_process_single_region(self):
        """Test processing a single region"""
        # Create test image array
        image_array = np.ones((100, 100, 3), dtype=np.uint8) * 255

        region = TextRegion(x=10, y=10, width=50, height=30, confidence=0.9)

        # Mock base OCR
        self.plugin.base_ocr.extract_text = Mock(return_value=("Region text", 0.92))

        text, conf = self.plugin._process_single_region(image_array, region)

        self.assertEqual(text, "Region text")
        self.assertGreater(conf, 0)

    def test_enhance_options(self):
        """Test different enhancement options"""
        image = Image.new("RGB", (100, 100), color="gray")

        # Mock to test enhancement options
        self.plugin.enhancer.enhance_for_ocr = Mock(
            return_value=np.ones((100, 100), dtype=np.uint8)
        )
        self.plugin.text_detector.detect_text_regions = Mock(return_value=[])
        self.plugin.base_ocr.extract_text = Mock(return_value=("Text", 0.9))

        # Test with enhancement
        self.plugin.enable_enhancement = True
        self.plugin.extract_text(image)

        # Verify enhancement was called
        self.plugin.enhancer.enhance_for_ocr.assert_called()

    def test_confidence_aggregation(self):
        """Test confidence score aggregation"""
        regions = [
            TextRegion(x=0, y=0, width=100, height=30, confidence=0.9, text="Hello"),
            TextRegion(x=0, y=40, width=100, height=30, confidence=0.8, text="World"),
            TextRegion(x=0, y=80, width=100, height=30, confidence=0.95, text="!"),
        ]

        # Mock processing
        self.plugin._process_single_region = Mock(
            side_effect=[("Hello", 0.9), ("World", 0.8), ("!", 0.95)]
        )

        # Mock text detection
        self.plugin.text_detector.detect_text_regions = Mock(return_value=regions)

        image = Image.new("RGB", (100, 100), color="white")
        text, confidence = self.plugin.extract_text(image)

        # Should aggregate text and average confidence
        self.assertIn("Hello", text)
        self.assertIn("World", text)
        self.assertAlmostEqual(confidence, 0.88, places=1)


if __name__ == "__main__":
    unittest.main()

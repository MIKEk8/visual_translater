"""Unit tests for lightweight AI-enhanced OCR engine"""

import unittest
from unittest.mock import MagicMock, Mock, patch

import numpy as np
from PIL import Image

from src.core.ai_ocr_engine_lite import (
    AIEnhancedOCRPluginLite,
    ImageEnhancerLite,
    TextDetectorLite,
    TextRegion,
)


class TestTextDetectorLite(unittest.TestCase):
    """Test TextDetectorLite class"""

    def setUp(self):
        """Set up test fixtures"""
        self.detector = TextDetectorLite()

    def test_detect_text_regions_empty_image(self):
        """Test detection on empty image"""
        # Black image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        regions = self.detector.detect_text_regions(image)
        self.assertEqual(len(regions), 0)

    def test_detect_text_regions_with_contours(self):
        """Test detection with text-like contours"""
        # Create image with white rectangle (simulating text)
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[30:60, 20:80] = 255

        regions = self.detector.detect_text_regions(image)

        # Should detect at least one region
        self.assertGreater(len(regions), 0)

        # Check region properties
        if regions:
            region = regions[0]
            self.assertGreater(region.width, 0)
            self.assertGreater(region.height, 0)
            self.assertGreater(region.confidence, 0)

    def test_detect_small_regions_filtered(self):
        """Test that very small regions are filtered out"""
        # Create image with tiny white dot
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[50:52, 50:52] = 255  # 2x2 pixel region

        regions = self.detector.detect_text_regions(image)

        # Should filter out tiny regions
        self.assertEqual(len(regions), 0)

    def test_detect_multiple_regions(self):
        """Test detection of multiple text regions"""
        # Create image with multiple rectangles
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        image[20:50, 20:80] = 255  # First "text" block
        image[70:100, 20:80] = 255  # Second "text" block
        image[120:150, 20:80] = 255  # Third "text" block

        regions = self.detector.detect_text_regions(image)

        # Should detect multiple regions
        self.assertGreater(len(regions), 1)

    def test_merge_nearby_regions(self):
        """Test merging of nearby regions"""
        regions = [
            TextRegion(x=10, y=10, width=50, height=20, confidence=0.8),
            TextRegion(x=65, y=12, width=50, height=20, confidence=0.8),  # Close horizontally
            TextRegion(x=10, y=100, width=50, height=20, confidence=0.8),  # Far vertically
        ]

        merged = self.detector._merge_nearby_regions(regions)

        # Should merge first two but not the third
        self.assertEqual(len(merged), 2)

    def test_calculate_confidence(self):
        """Test confidence calculation based on aspect ratio"""
        # Good aspect ratio for text
        conf1 = self.detector._calculate_confidence(100, 30, area=3000)

        # Very tall region (unlikely to be text)
        conf2 = self.detector._calculate_confidence(30, 100, area=3000)

        # Very small area
        conf3 = self.detector._calculate_confidence(100, 30, area=100)

        # Good aspect ratio should have higher confidence
        self.assertGreater(conf1, conf2)
        self.assertGreater(conf1, conf3)


class TestImageEnhancerLite(unittest.TestCase):
    """Test ImageEnhancerLite class"""

    def setUp(self):
        """Set up test fixtures"""
        self.enhancer = ImageEnhancerLite()

    def test_preprocess_dark_image(self):
        """Test preprocessing of dark image"""
        # Create dark image
        image = np.ones((100, 100, 3), dtype=np.uint8) * 30

        processed = self.enhancer.preprocess(image)

        # Should be grayscale
        self.assertEqual(len(processed.shape), 2)
        # Should brighten image
        self.assertGreater(np.mean(processed), 30)

    def test_preprocess_bright_image(self):
        """Test preprocessing of bright image"""
        # Create bright image
        image = np.ones((100, 100, 3), dtype=np.uint8) * 250

        processed = self.enhancer.preprocess(image)

        # Should handle bright images properly
        self.assertIsNotNone(processed)
        self.assertEqual(processed.shape[:2], (100, 100))

    def test_preprocess_normal_image(self):
        """Test preprocessing of normal image"""
        # Create normal contrast image
        image = np.ones((100, 100, 3), dtype=np.uint8) * 128
        image[40:60, 40:60] = 200  # Add some contrast

        processed = self.enhancer.preprocess(image)

        # Should maintain reasonable contrast
        self.assertIsNotNone(processed)
        self.assertGreater(np.std(processed), 0)

    def test_preprocess_grayscale_input(self):
        """Test preprocessing of already grayscale image"""
        # Grayscale image
        image = np.ones((100, 100), dtype=np.uint8) * 128

        processed = self.enhancer.preprocess(image)

        # Should handle gracefully
        self.assertEqual(processed.shape, image.shape)

    def test_apply_clahe(self):
        """Test CLAHE contrast enhancement"""
        # Low contrast image
        image = np.ones((100, 100), dtype=np.uint8) * 128
        image[45:55, 45:55] = 135  # Very subtle contrast

        enhanced = self.enhancer._apply_clahe(image)

        # Should increase contrast
        self.assertGreaterEqual(np.std(enhanced), np.std(image))

    def test_denoise(self):
        """Test noise reduction"""
        # Create noisy image
        image = np.random.randint(100, 150, (100, 100), dtype=np.uint8)

        denoised = self.enhancer._denoise(image)

        # Should reduce noise (lower std deviation)
        self.assertLess(np.std(denoised), np.std(image))

    def test_binarize_adaptive(self):
        """Test adaptive binarization"""
        # Create image with varying illumination
        image = np.ones((100, 100), dtype=np.uint8) * 128
        # Add gradient
        for i in range(100):
            image[i, :] = 100 + i // 2

        binary = self.enhancer._binarize(image)

        # Should be binary
        unique = np.unique(binary)
        self.assertTrue(all(v in [0, 255] for v in unique))


class TestAIEnhancedOCRPluginLite(unittest.TestCase):
    """Test AIEnhancedOCRPluginLite"""

    def setUp(self):
        """Set up test fixtures"""
        self.plugin = AIEnhancedOCRPluginLite()

    def test_info(self):
        """Test plugin info"""
        info = self.plugin.info()
        self.assertEqual(info["name"], "AI-Enhanced OCR Lite")
        self.assertIn("version", info)
        self.assertIn("description", info)
        self.assertIn("lightweight", info["description"].lower())

    @patch("pytesseract.pytesseract.tesseract_cmd", "tesseract")
    def test_is_available(self):
        """Test availability check"""
        with patch("importlib.util.find_spec") as mock_spec:
            # All required packages available
            mock_spec.return_value = Mock()

            available = self.plugin.is_available()
            self.assertTrue(available)

        with patch("importlib.util.find_spec") as mock_spec:
            # Missing cv2
            mock_spec.side_effect = lambda x: None if x == "cv2" else Mock()

            available = self.plugin.is_available()
            self.assertFalse(available)

    def test_extract_text_with_enhancement(self):
        """Test text extraction with enhancement enabled"""
        # Create test image
        image = Image.new("RGB", (100, 100), color="white")

        # Draw black text-like rectangle
        from PIL import ImageDraw

        draw = ImageDraw.Draw(image)
        draw.rectangle([20, 40, 80, 60], fill="black")

        # Mock base OCR
        self.plugin.base_ocr.extract_text = Mock(return_value=("Enhanced text", 0.9))

        # Enable enhancement
        self.plugin.enable_enhancement = True

        text, confidence = self.plugin.extract_text(image)

        self.assertEqual(text, "Enhanced text")
        self.assertEqual(confidence, 0.9)

    def test_extract_text_without_enhancement(self):
        """Test text extraction without enhancement"""
        image = Image.new("RGB", (100, 100), color="white")

        # Mock base OCR
        self.plugin.base_ocr.extract_text = Mock(return_value=("Direct text", 0.85))

        # Disable enhancement
        self.plugin.enable_enhancement = False

        text, confidence = self.plugin.extract_text(image)

        self.assertEqual(text, "Direct text")
        self.assertEqual(confidence, 0.85)

    def test_extract_text_with_regions(self):
        """Test extraction with detected regions"""
        image = Image.new("RGB", (200, 100), color="white")

        # Mock region detection
        regions = [
            TextRegion(x=10, y=10, width=80, height=30, confidence=0.8),
            TextRegion(x=10, y=50, width=80, height=30, confidence=0.85),
        ]
        self.plugin.detector.detect_text_regions = Mock(return_value=regions)

        # Mock OCR for each region
        self.plugin.base_ocr.extract_text = Mock(
            side_effect=[("First line", 0.9), ("Second line", 0.88)]
        )

        text, confidence = self.plugin.extract_text(image)

        # Should combine both lines
        self.assertIn("First line", text)
        self.assertIn("Second line", text)
        # Confidence should be average
        self.assertAlmostEqual(confidence, 0.89, places=2)

    def test_extract_text_error_handling(self):
        """Test error handling during extraction"""
        image = Image.new("RGB", (100, 100), color="white")

        # Simulate error in enhancement
        self.plugin.enhancer.preprocess = Mock(side_effect=Exception("Enhancement failed"))

        # Base OCR should still work
        self.plugin.base_ocr.extract_text = Mock(return_value=("Fallback text", 0.7))

        self.plugin.enable_enhancement = True
        text, confidence = self.plugin.extract_text(image)

        # Should fall back gracefully
        self.assertEqual(text, "Fallback text")
        self.assertEqual(confidence, 0.7)

    def test_process_multiple_regions_ordering(self):
        """Test that regions are processed in correct order"""
        image_array = np.ones((200, 100, 3), dtype=np.uint8) * 255

        # Create regions in mixed order
        regions = [
            TextRegion(x=10, y=100, width=80, height=30, confidence=0.8),  # Bottom
            TextRegion(x=10, y=10, width=80, height=30, confidence=0.8),  # Top
            TextRegion(x=10, y=55, width=80, height=30, confidence=0.8),  # Middle
        ]

        # Mock OCR
        self.plugin.base_ocr.extract_text = Mock(
            side_effect=[("Bottom", 0.9), ("Top", 0.9), ("Middle", 0.9)]
        )

        texts = []
        for region in sorted(regions, key=lambda r: r.y):
            text, _ = self.plugin._process_region(image_array, region)
            texts.append(text)

        # Should be in top-to-bottom order
        self.assertEqual(texts, ["Top", "Middle", "Bottom"])

    def test_extract_from_region(self):
        """Test extracting text from a specific region"""
        image_array = np.ones((100, 100, 3), dtype=np.uint8) * 255

        region = TextRegion(x=20, y=20, width=60, height=30, confidence=0.85)

        # Mock base OCR
        self.plugin.base_ocr.extract_text = Mock(return_value=("Region text", 0.92))

        text, conf = self.plugin._process_region(image_array, region)

        # Should extract from the cropped region
        self.assertEqual(text, "Region text")
        self.assertEqual(conf, 0.92)

        # Verify OCR was called with cropped image
        call_args = self.plugin.base_ocr.extract_text.call_args[0][0]
        # Should be PIL Image
        self.assertIsInstance(call_args, Image.Image)

    def test_empty_regions_handling(self):
        """Test handling when no regions are detected"""
        image = Image.new("RGB", (100, 100), color="white")

        # No regions detected
        self.plugin.detector.detect_text_regions = Mock(return_value=[])

        # Should fall back to full image OCR
        self.plugin.base_ocr.extract_text = Mock(return_value=("Full image text", 0.8))

        text, confidence = self.plugin.extract_text(image)

        self.assertEqual(text, "Full image text")
        self.assertEqual(confidence, 0.8)

    def test_confidence_boosting(self):
        """Test confidence boosting for lite version"""
        image = Image.new("RGB", (100, 100), color="white")

        # Mock low confidence from base OCR
        self.plugin.base_ocr.extract_text = Mock(return_value=("Text", 0.6))

        # Disable enhancement to test base confidence
        self.plugin.enable_enhancement = False

        text, confidence = self.plugin.extract_text(image)

        # Lite version might adjust confidence
        self.assertGreaterEqual(confidence, 0.6)


if __name__ == "__main__":
    unittest.main()

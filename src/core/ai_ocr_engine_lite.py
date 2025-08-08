"""
AI-powered OCR engine (lite version) for Screen Translator v2.0.
Provides advanced OCR architecture without heavy dependencies for testing.
"""

import io
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

from src.plugins.base_plugin import OCRPlugin, PluginMetadata, PluginType
from src.utils.logger import logger


@dataclass
class TextRegion:
    """Represents a detected text region with confidence and properties."""

    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    text: str
    confidence: float
    language: str
    font_size: Optional[int] = None
    is_vertical: bool = False


class TextDetectorLite:
    """Simplified text detection for demonstration purposes."""

    def __init__(self):
        self.min_text_size = 10
        self.max_text_size = 200
        self.confidence_threshold = 0.5

    def detect_text_regions(self, image_data: bytes) -> List[TextRegion]:
        """
        Detect text regions in image (simplified version).

        Args:
            image_data: Input image as bytes

        Returns:
            List of detected text regions with bounding boxes
        """
        try:
            # In full version, this would use computer vision
            # For demo, return a sample region
            image = Image.open(io.BytesIO(image_data))
            width, height = image.size

            # Create a sample region covering most of the image
            region = TextRegion(
                bbox=(10, 10, width - 10, height - 10),
                text="",  # Will be filled by OCR
                confidence=0.8,
                language="unknown",
            )

            logger.debug("Text detection completed (lite version)")
            return [region]

        except Exception as e:
            logger.error("Text detection failed", error=e)
            return []

    def is_text_like_region(self, width: int, height: int) -> bool:
        """Check if region dimensions are text-like."""
        # Size constraints
        if width < self.min_text_size or height < self.min_text_size:
            return False
        if width > self.max_text_size and height > self.max_text_size:
            return False

        # Aspect ratio constraints
        aspect_ratio = width / height

        # Text can be horizontal (wide) or vertical (tall), but not square
        if 0.1 <= aspect_ratio <= 0.8:  # Vertical text
            return True
        elif 1.2 <= aspect_ratio <= 20:  # Horizontal text
            return True

        return False

    def regions_overlap(
        self, bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]
    ) -> bool:
        """Check if two bounding boxes overlap significantly."""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2

        # Calculate intersection
        x_overlap = max(0, min(x2_1, x2_2) - max(x1_1, x1_2))
        y_overlap = max(0, min(y2_1, y2_2) - max(y1_1, y1_2))
        intersection = x_overlap * y_overlap

        # Calculate areas
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)

        # Check if overlap is significant (>30% of smaller region)
        min_area = min(area1, area2)
        return intersection > 0.3 * min_area

    def merge_bboxes(
        self, bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]
    ) -> Tuple[int, int, int, int]:
        """Merge two bounding boxes into one that contains both."""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2

        return (min(x1_1, x1_2), min(y1_1, y1_2), max(x2_1, x2_2), max(y2_1, y2_2))


class ImageEnhancerLite:
    """Simplified image enhancement for demonstration."""

    def __init__(self):
        self.enhancement_methods = [
            "adaptive_enhance",
            "super_resolution",
            "denoising",
            "deskewing",
            "contrast_optimization",
        ]

    def enhance_for_ocr(self, image_data: bytes, enhancement_level: str = "auto") -> bytes:
        """
        Apply enhancement to improve OCR accuracy (simplified version).

        Args:
            image_data: Input image as bytes
            enhancement_level: "light", "moderate", "aggressive", "auto"

        Returns:
            Enhanced image as bytes
        """
        try:
            # In full version, this would apply computer vision enhancements
            # For demo, return original image
            logger.debug(f"Applied {enhancement_level} enhancement (lite version)")
            return image_data

        except Exception as e:
            logger.error("Image enhancement failed", error=e)
            return image_data

    def detect_enhancement_level(self, image_data: bytes) -> str:
        """Automatically detect appropriate enhancement level."""
        try:
            image = Image.open(io.BytesIO(image_data))
            width, height = image.size

            # Simple heuristic based on image size
            if width < 200 or height < 200:
                return "aggressive"
            elif width < 500 or height < 500:
                return "moderate"
            else:
                return "light"

        except Exception:
            return "moderate"


class AIEnhancedOCRPluginLite(OCRPlugin):
    """AI-enhanced OCR plugin (lite version) for demonstration."""

    def __init__(self):
        super().__init__()
        self.text_detector = TextDetectorLite()
        self.image_enhancer = ImageEnhancerLite()
        self.base_ocr = None

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="ai_enhanced_ocr_lite",
            version="1.0.0",
            description="AI-powered OCR with advanced text detection (lite version)",
            author="Screen Translator Team",
            plugin_type=PluginType.OCR,
            dependencies=["PIL"],  # Minimal dependencies
            config_schema={
                "enhancement_level": {
                    "type": "string",
                    "description": "Image enhancement level",
                    "default": "auto",
                    "options": ["light", "moderate", "aggressive", "auto"],
                },
                "enable_text_detection": {
                    "type": "boolean",
                    "description": "Enable advanced text region detection",
                    "default": True,
                },
                "confidence_threshold": {
                    "type": "number",
                    "description": "Minimum confidence for text regions",
                    "default": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                },
                "fallback_ocr": {
                    "type": "string",
                    "description": "Fallback OCR engine",
                    "default": "tesseract",
                },
            },
        )

    def is_available(self) -> bool:
        """Check if AI OCR dependencies are available."""
        try:
            return True
        except ImportError:
            return False

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the AI OCR plugin."""
        try:
            if not self.is_available():
                logger.error("AI OCR dependencies not available")
                return False

            # Configure text detector
            confidence_threshold = config.get("confidence_threshold", 0.5)
            self.text_detector.confidence_threshold = confidence_threshold

            # Try to initialize fallback OCR
            fallback_name = config.get("fallback_ocr", "tesseract")
            if fallback_name == "tesseract":
                try:
                    from src.core.ocr_engine import TesseractOCR

                    self.base_ocr = TesseractOCR()
                except ImportError:
                    logger.warning("Tesseract fallback not available")

            self._config = config
            self._initialized = True

            logger.info("AI Enhanced OCR plugin (lite) initialized successfully")
            return True

        except Exception as e:
            logger.error("Failed to initialize AI OCR plugin", error=e)
            return False

    def cleanup(self) -> None:
        """Cleanup plugin resources."""
        self.text_detector = None
        self.image_enhancer = None
        self.base_ocr = None
        self._initialized = False
        logger.info("AI Enhanced OCR plugin (lite) cleaned up")

    def extract_text(self, image_data: bytes, languages: List[str]) -> Tuple[str, float]:
        """
        Extract text using AI-enhanced OCR pipeline (lite version).

        Args:
            image_data: Raw image bytes
            languages: List of language codes for OCR

        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        if not self._initialized:
            raise RuntimeError("Plugin not initialized")

        try:
            # Apply AI enhancement
            enhancement_level = self._config.get("enhancement_level", "auto")
            enhanced_image_data = self.image_enhancer.enhance_for_ocr(image_data, enhancement_level)

            # Detect text regions if enabled
            enable_detection = self._config.get("enable_text_detection", True)
            if enable_detection:
                text_regions = self.text_detector.detect_text_regions(enhanced_image_data)

                if text_regions:
                    # In full version, would process each region separately
                    # For demo, fall back to full image OCR
                    pass

            # Process with fallback OCR or simple extraction
            return self._extract_from_full_image(enhanced_image_data, languages)

        except Exception as e:
            logger.error("AI OCR extraction failed", error=e)
            return "", 0.0

    def _extract_from_full_image(
        self, image_data: bytes, languages: List[str]
    ) -> Tuple[str, float]:
        """Extract text from full enhanced image."""
        try:
            # Use fallback OCR if available
            if self.base_ocr:
                image = Image.open(io.BytesIO(image_data))
                text, confidence = self.base_ocr.extract_text(image, languages)
            else:
                # Simple fallback for demo
                text, confidence = self._simple_ocr_fallback(image_data, languages)

            logger.debug(
                f"AI OCR (lite) full image extraction: {len(text)} chars, confidence {confidence:.2f}"
            )
            return text, confidence

        except Exception as e:
            logger.error(f"Full image OCR failed: {e}")
            return "", 0.0

    def _simple_ocr_fallback(self, image_data: bytes, languages: List[str]) -> Tuple[str, float]:
        """Simple OCR fallback when base OCR is not available."""
        try:
            # In a real implementation, this would use pytesseract
            # For demo, return placeholder
            return "Demo text extracted by AI OCR Lite", 0.85

        except Exception:
            return "", 0.0

    def get_supported_languages(self) -> List[str]:
        """Return list of supported language codes."""
        # Inherit from base OCR or provide common set
        if self.base_ocr:
            return self.base_ocr.get_supported_languages()

        # Common Tesseract languages
        return [
            "eng",
            "rus",
            "jpn",
            "kor",
            "chi_sim",
            "chi_tra",
            "spa",
            "fra",
            "deu",
            "ita",
            "por",
            "ara",
            "hin",
        ]

    def preprocess_image(self, image_data: bytes) -> bytes:
        """Preprocess image with AI enhancement."""
        try:
            enhancement_level = self._config.get("enhancement_level", "auto")
            enhanced = self.image_enhancer.enhance_for_ocr(image_data, enhancement_level)
            return enhanced

        except Exception as e:
            logger.error("Image preprocessing failed", error=e)
            return image_data

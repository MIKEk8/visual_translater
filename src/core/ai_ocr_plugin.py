"""AI-enhanced OCR plugin using modular components.

Refactored from the original 812-line God Class for better maintainability.
"""

import io
from typing import Any, Dict, List, Optional

import pytesseract
import numpy as np
from PIL import Image

from src.core.text_detection import TextDetector, TextRegion
from src.core.image_enhancement import ImageEnhancer
from src.core.ocr_engine import TesseractOCR
from src.plugins.base_plugin import OCRPlugin, PluginMetadata, PluginType
from src.utils.logger import logger


class AIEnhancedOCRPlugin(OCRPlugin):
    """AI-enhanced OCR plugin with advanced text detection and image processing."""

    def __init__(self):
        super().__init__()
        self.text_detector = TextDetector()
        self.image_enhancer = ImageEnhancer()
        self.base_ocr = None  # Will be set to fallback OCR engine

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="ai_enhanced_ocr",
            version="1.0.0",
            description="AI-powered OCR with advanced text detection and image enhancement",
            author="Screen Translator Team",
            plugin_type=PluginType.OCR,
            dependencies=["opencv-python", "numpy", "pytesseract", "PIL"],
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
            # Check core dependencies
            import cv2
            import numpy
            import pytesseract
            from PIL import Image

            # Test pytesseract availability
            pytesseract.get_tesseract_version()
            return True

        except ImportError as e:
            logger.warning(f"AI OCR dependencies not available: {e}")
            return False
        except Exception as e:
            logger.warning(f"AI OCR not available: {e}")
            return False

    def extract_text(self, image_data: bytes, config: Optional[Dict[str, Any]] = None) -> str:
        """
        Extract text from image using AI-enhanced OCR.

        Args:
            image_data: Image data as bytes
            config: Optional configuration parameters

        Returns:
            Extracted text string
        """
        try:
            # Parse configuration
            config = config or {}
            enhancement_level = config.get("enhancement_level", "auto")
            enable_text_detection = config.get("enable_text_detection", True)
            confidence_threshold = config.get("confidence_threshold", 0.5)

            # Convert image data to PIL Image
            image = Image.open(io.BytesIO(image_data))

            # Convert PIL Image to numpy array
            img_array = np.array(image)

            # Apply image enhancement
            enhanced_image = self.image_enhancer.enhance_for_ocr(img_array, enhancement_level)

            # Extract text using different strategies
            if enable_text_detection:
                text = self._extract_with_text_detection(enhanced_image, confidence_threshold, config)
            else:
                text = self._extract_with_basic_ocr(enhanced_image, config)

            logger.debug(f"AI OCR extracted {len(text)} characters")
            return text

        except Exception as e:
            logger.error("AI OCR text extraction failed", error=e)
            return self._fallback_extraction(image_data, config)

    def _extract_with_text_detection(self, image: np.ndarray, confidence_threshold: float, config: Dict[str, Any]) -> str:
        """Extract text using advanced text region detection."""
        try:
            # Update text detector confidence threshold
            self.text_detector.confidence_threshold = confidence_threshold

            # Detect text regions
            text_regions = self.text_detector.detect_text_regions(image)

            if not text_regions:
                logger.debug("No text regions detected, using fallback")
                return self._extract_with_basic_ocr(image, config)

            # Extract text from each region
            extracted_texts = []
            for region in text_regions:
                try:
                    # Crop region from image
                    x1, y1, x2, y2 = region.bbox
                    cropped = image[y1:y2, x1:x2]

                    if cropped.size == 0:
                        continue

                    # Convert numpy array back to PIL Image for pytesseract
                    pil_image = Image.fromarray(cropped)

                    # Extract text from region
                    region_text = self._extract_text_from_region(pil_image, config)

                    if region_text.strip():
                        extracted_texts.append(region_text.strip())

                except Exception as e:
                    logger.warning(f"Failed to extract text from region {region.bbox}: {e}")
                    continue

            # Combine texts with appropriate spacing
            combined_text = self._combine_region_texts(extracted_texts, text_regions)

            if combined_text.strip():
                return combined_text
            else:
                # If no text from regions, fallback to full image OCR
                return self._extract_with_basic_ocr(image, config)

        except Exception as e:
            logger.error("Text detection extraction failed", error=e)
            return self._extract_with_basic_ocr(image, config)

    def _extract_with_basic_ocr(self, image: np.ndarray, config: Dict[str, Any]) -> str:
        """Extract text using basic OCR on the full image."""
        try:
            # Convert numpy array to PIL Image
            pil_image = Image.fromarray(image)

            # Use pytesseract for OCR
            return self._extract_text_from_region(pil_image, config)

        except Exception as e:
            logger.error("Basic OCR extraction failed", error=e)
            return ""

    def _extract_text_from_region(self, image: Image.Image, config: Dict[str, Any]) -> str:
        """Extract text from a single image region using pytesseract."""
        try:
            # Configure pytesseract options
            custom_config = r'--oem 3 --psm 6'  # Default config

            # Add language configuration if specified
            lang = config.get("language", "eng")
            if lang != "eng":
                custom_config = f"-l {lang} " + custom_config

            # Extract text
            text = pytesseract.image_to_string(image, config=custom_config)
            return text

        except Exception as e:
            logger.warning(f"Pytesseract extraction failed: {e}")
            return ""

    def _combine_region_texts(self, texts: List[str], regions: List[TextRegion]) -> str:
        """Combine texts from multiple regions with appropriate spacing."""
        if not texts:
            return ""

        if len(texts) == 1:
            return texts[0]

        # Sort texts by vertical position (top to bottom, then left to right)
        text_region_pairs = list(zip(texts, regions))
        text_region_pairs.sort(key=lambda x: (x[1].bbox[1], x[1].bbox[0]))  # Sort by y, then x

        # Combine with appropriate line breaks
        combined_lines = []
        current_line_texts = []
        current_y = None

        for text, region in text_region_pairs:
            x1, y1, x2, y2 = region.bbox

            # Check if this region is on a new line (significant vertical difference)
            if current_y is not None and abs(y1 - current_y) > 20:
                # New line detected
                if current_line_texts:
                    combined_lines.append(" ".join(current_line_texts))
                current_line_texts = [text]
            else:
                # Same line
                current_line_texts.append(text)

            current_y = y1

        # Add the last line
        if current_line_texts:
            combined_lines.append(" ".join(current_line_texts))

        return "\n".join(combined_lines)

    def _fallback_extraction(self, image_data: bytes, config: Dict[str, Any]) -> str:
        """Fallback extraction using basic OCR engine."""
        try:
            if self.base_ocr is None:
                self.base_ocr = TesseractOCR()

            if self.base_ocr.is_available():
                return self.base_ocr.extract_text(image_data)
            else:
                logger.warning("No fallback OCR available")
                return ""

        except Exception as e:
            logger.error("Fallback OCR failed", error=e)
            return ""

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the AI OCR plugin."""
        try:
            # Update text detector settings
            if "confidence_threshold" in config:
                self.text_detector.confidence_threshold = config["confidence_threshold"]

            # Update image enhancer settings
            # (Enhancement level is passed per-call, not stored)

            logger.debug("AI OCR plugin configured")

        except Exception as e:
            logger.error("AI OCR configuration failed", error=e)

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        try:
            # Get languages from pytesseract
            langs = pytesseract.get_languages(config='')
            return langs if langs else ["eng"]

        except Exception as e:
            logger.warning(f"Could not get supported languages: {e}")
            return ["eng", "rus", "deu", "fra", "spa", "ita", "por"]  # Common defaults

    def get_version_info(self) -> Dict[str, str]:
        """Get version information for the OCR components."""
        try:
            info = {
                "plugin_version": self.metadata.version,
                "tesseract_version": pytesseract.get_tesseract_version(),
            }

            try:
                import cv2
                info["opencv_version"] = cv2.__version__
            except ImportError:
                info["opencv_version"] = "Not available"

            return info

        except Exception as e:
            logger.warning(f"Could not get version info: {e}")
            return {"plugin_version": self.metadata.version}


# For backward compatibility
AIEnhancedOCR = AIEnhancedOCRPlugin
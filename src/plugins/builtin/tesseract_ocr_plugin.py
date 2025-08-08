"""
Built-in Tesseract OCR plugin for Screen Translator v2.0.
Wraps the existing TesseractOCR engine as a plugin.
"""

from typing import Any, Dict, List, Tuple

from src.plugins.base_plugin import OCRPlugin, PluginMetadata, PluginType
from src.utils.logger import logger


class TesseractOCRPlugin(OCRPlugin):
    """Plugin wrapper for Tesseract OCR engine."""

    def __init__(self):
        super().__init__()
        self._tesseract_engine = None

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="tesseract_ocr",
            version="1.0.0",
            description="Tesseract OCR engine plugin for text extraction",
            author="Screen Translator Team",
            plugin_type=PluginType.OCR,
            dependencies=["pytesseract", "PIL"],
            config_schema={
                "tesseract_cmd": {
                    "type": "string",
                    "description": "Path to tesseract executable",
                    "default": "tesseract",
                },
                "config_options": {
                    "type": "string",
                    "description": "Tesseract configuration options",
                    "default": "--psm 6",
                },
            },
        )

    def is_available(self) -> bool:
        """Check if Tesseract dependencies are available."""
        try:
            return True
        except ImportError:
            return False

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the Tesseract OCR plugin."""
        try:
            if not self.is_available():
                logger.error("Tesseract OCR dependencies not available")
                return False

            # Import here to avoid import errors if dependencies missing
            from src.core.ocr_engine import TesseractOCR

            # Create OCR engine instance
            self._tesseract_engine = TesseractOCR()

            # Configure tesseract path if provided
            tesseract_cmd = config.get("tesseract_cmd")
            if tesseract_cmd:
                import pytesseract

                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

            self._config = config
            self._initialized = True

            logger.info("Tesseract OCR plugin initialized successfully")
            return True

        except Exception as e:
            logger.error("Failed to initialize Tesseract OCR plugin", error=e)
            return False

    def cleanup(self) -> None:
        """Cleanup plugin resources."""
        self._tesseract_engine = None
        self._initialized = False
        logger.info("Tesseract OCR plugin cleaned up")

    def extract_text(self, image_data: bytes, languages: List[str]) -> Tuple[str, float]:
        """
        Extract text from image using Tesseract.

        Args:
            image_data: Raw image bytes
            languages: List of language codes for OCR

        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        if not self._initialized or not self._tesseract_engine:
            raise RuntimeError("Plugin not initialized")

        try:
            import io

            from PIL import Image

            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))

            # Use the existing OCR engine
            text, confidence = self._tesseract_engine.extract_text(image, languages)

            logger.debug(
                f"Tesseract OCR extracted {len(text)} characters with confidence {confidence:.2f}"
            )
            return text, confidence

        except Exception as e:
            logger.error("Tesseract OCR extraction failed", error=e)
            return "", 0.0

    def get_supported_languages(self) -> List[str]:
        """Return list of supported language codes."""
        # Common Tesseract language codes
        return [
            "eng",  # English
            "rus",  # Russian
            "jpn",  # Japanese
            "kor",  # Korean
            "chi_sim",  # Chinese Simplified
            "chi_tra",  # Chinese Traditional
            "spa",  # Spanish
            "fra",  # French
            "deu",  # German
            "ita",  # Italian
            "por",  # Portuguese
            "ara",  # Arabic
            "hin",  # Hindi
        ]

    def preprocess_image(self, image_data: bytes) -> bytes:
        """Preprocess image for better OCR results."""
        if not self._tesseract_engine:
            return image_data

        try:
            import io

            from PIL import Image

            # Convert to PIL Image
            image = Image.open(io.BytesIO(image_data))

            # Use existing image enhancement from OCR engine
            enhanced_image = self._tesseract_engine._enhance_image(image)

            # Convert back to bytes
            output = io.BytesIO()
            enhanced_image.save(output, format="PNG")
            return output.getvalue()

        except Exception as e:
            logger.error("Image preprocessing failed", error=e)
            return image_data

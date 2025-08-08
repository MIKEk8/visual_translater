import asyncio
import io
import os
import time
from abc import ABC, abstractmethod
from typing import Optional, Tuple

try:
    from PIL import Image, ImageEnhance

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    from unittest.mock import Mock

    Image = Mock()
    ImageEnhance = Mock()

from src.models.config import ImageProcessingConfig
from src.models.screenshot_data import ScreenshotData
from src.services.circuit_breaker import (
    OCR_SERVICE_CONFIG,
    CircuitBreakerError,
    get_circuit_breaker_manager,
)
from src.utils.logger import logger


class OCREngine(ABC):
    """Abstract base class for OCR engines"""

    @abstractmethod
    def extract_text(
        self, image: Image.Image, languages: str = "eng"
    ) -> Tuple[str, Optional[float]]:
        """Extract text from image, return (text, confidence)"""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if OCR engine is available"""


class TesseractOCR(OCREngine):
    """Tesseract OCR implementation with circuit breaker protection"""

    def __init__(self):
        self.tesseract_cmd = self._find_tesseract()
        self._setup_tesseract()

        # Initialize circuit breaker
        manager = get_circuit_breaker_manager()
        self.circuit_breaker = manager.create_circuit_breaker("tesseract_ocr", OCR_SERVICE_CONFIG)

        if self.is_available():
            logger.info(
                f"Tesseract OCR initialized with circuit breaker protection: {self.tesseract_cmd}"
            )
        else:
            logger.error("Tesseract OCR not available")

    def _find_tesseract(self) -> Optional[str]:
        """Find Tesseract executable"""
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            "tesseract",  # If in PATH
        ]

        for path in possible_paths:
            if os.path.exists(path) or path == "tesseract":
                return path

        return None

    def _setup_tesseract(self):
        """Setup Tesseract configuration"""
        if self.tesseract_cmd and self.tesseract_cmd != "tesseract":
            try:
                import pytesseract

                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            except ImportError:
                logger.error("pytesseract module not available")

    def is_available(self) -> bool:
        """Check if Tesseract is available"""
        if not self.tesseract_cmd:
            return False

        try:
            import pytesseract

            # Try a simple test
            test_img = Image.new("RGB", (100, 30), color="white")
            pytesseract.image_to_string(test_img)
            return True
        except (ImportError, Exception):
            return False

    def extract_text(
        self, image: Image.Image, languages: str = "eng"
    ) -> Tuple[str, Optional[float]]:
        """Extract text using Tesseract with circuit breaker protection"""
        try:
            # Use circuit breaker to protect OCR operation
            async def _extract_text():
                import pytesseract

                # Extract text
                text = pytesseract.image_to_string(image, lang=languages).strip()

                # Try to get confidence (Tesseract 4.0+)
                confidence = None
                try:
                    data = pytesseract.image_to_data(
                        image, lang=languages, output_type=pytesseract.Output.DICT
                    )
                    confidences = [int(conf) for conf in data["conf"] if int(conf) > 0]
                    if confidences:
                        confidence = sum(confidences) / len(confidences)
                except Exception as e:
                    logger.debug(f"Could not calculate OCR confidence: {e}")
                    # Confidence not available, using default

                return text, confidence

            # Run the protected OCR operation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.circuit_breaker.call(_extract_text))
            finally:
                loop.close()

        except CircuitBreakerError as e:
            logger.warning(f"OCR circuit breaker triggered: {e}")
            return "", None
        except Exception as e:
            logger.error("Tesseract OCR failed", error=e)
            return "", None


class OCRProcessor:
    """Main OCR processing class with image enhancement"""

    def __init__(self, config: ImageProcessingConfig):
        self.config = config
        self.engines = [TesseractOCR()]  # Can add more engines later
        self.active_engine = self._get_available_engine()

        if self.active_engine:
            logger.info(f"OCR processor initialized with {type(self.active_engine).__name__}")
        else:
            logger.error("No OCR engines available")

    def _get_available_engine(self) -> Optional[OCREngine]:
        """Get first available OCR engine"""
        for engine in self.engines:
            if engine.is_available():
                return engine
        return None

    def enhance_image(self, image: Image.Image) -> Image.Image:
        """Enhance image for better OCR accuracy"""
        try:
            # Skip enhancement if disabled
            if not self.config.enable_preprocessing:
                return image

            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Apply noise reduction
            if self.config.noise_reduction:
                image = self._apply_noise_reduction(image)

            # Upscale image
            if self.config.upscale_factor != 1.0:
                width, height = image.size
                new_size = (
                    int(width * self.config.upscale_factor),
                    int(height * self.config.upscale_factor),
                )
                image = image.resize(new_size, Image.LANCZOS)

            # Enhance contrast
            if self.config.contrast_enhance != 1.0:
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(self.config.contrast_enhance)

            # Enhance sharpness
            if self.config.sharpness_enhance != 1.0:
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(self.config.sharpness_enhance)

            return image

        except Exception as e:
            logger.error("Image enhancement failed", error=e)
            return image  # Return original if enhancement fails

    def _apply_noise_reduction(self, image: Image.Image) -> Image.Image:
        """Apply basic noise reduction filters"""
        try:
            from PIL import ImageFilter

            # Apply Gaussian blur for noise reduction
            image = image.filter(ImageFilter.GaussianBlur(radius=0.5))

            # Apply unsharp mask to restore sharpness
            image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))

            return image
        except (ImportError, Exception) as e:
            logger.debug(f"Noise reduction not available: {e}")
            return image

    def process_screenshot(
        self, screenshot_data: ScreenshotData, languages: str = "eng"
    ) -> Tuple[str, Optional[float]]:
        """Process screenshot and extract text"""
        if not self.active_engine:
            logger.error("No OCR engine available")
            return "", None

        start_time = time.time()

        try:
            # Convert bytes to image
            image = Image.open(io.BytesIO(screenshot_data.image_data))

            # Enhance image
            enhanced_image = self.enhance_image(image)

            # Extract text
            text, confidence = self.active_engine.extract_text(enhanced_image, languages)

            # Check confidence threshold
            if confidence is not None and confidence < (self.config.ocr_confidence_threshold * 100):
                logger.warning(
                    f"OCR confidence {confidence:.1f}% below threshold {self.config.ocr_confidence_threshold * 100}%"
                )
                # Still return the text but log the low confidence
                # In the future, could try alternative engines or image preprocessing

            # Clean up text
            text = self._clean_text(text)

            duration = time.time() - start_time

            logger.log_ocr(text_length=len(text), confidence=confidence, duration=duration)

            return text, confidence

        except Exception as e:
            duration = time.time() - start_time
            logger.error("OCR processing failed", error=e, duration=duration)
            return "", None

    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""

        # Common OCR error corrections
        replacements = {
            "1": "I",  # Common OCR mistake
            "0": "O",  # Common OCR mistake
            "\n": " ",
            "\r": " ",
            "\t": " ",
            "_": " ",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # Normalize whitespace
        text = " ".join(text.split())

        return text.strip()

    def is_available(self) -> bool:
        """Check if OCR processing is available"""
        return self.active_engine is not None

    def get_engine_info(self) -> dict:
        """Get information about active OCR engine"""
        if not self.active_engine:
            return {"engine": "None", "available": False}

        return {
            "engine": type(self.active_engine).__name__,
            "available": True,
            "tesseract_cmd": getattr(self.active_engine, "tesseract_cmd", None),
        }

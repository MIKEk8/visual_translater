"""
OCR service implementation.
"""

from typing import Tuple

try:
    import pytesseract
    from PIL import Image

    ImageType = Image.Image
    OCR_AVAILABLE = True
except ImportError:
    from typing import Any

    Image = Any
    pytesseract = Any
    ImageType = Any
    OCR_AVAILABLE = False

from ...domain.protocols.services import OCRService
from ...domain.value_objects.language import Language
from ...utils.logger import logger


class TesseractOCRService(OCRService):
    """Tesseract OCR service implementation."""

    def __init__(self):
        self._language_mapping = {
            "ru": "rus",
            "en": "eng",
            "ja": "jpn",
            "de": "deu",
            "fr": "fra",
            "es": "spa",
            "it": "ita",
            "pt": "por",
            "zh": "chi_sim",
            "ko": "kor",
            "ar": "ara",
            "hi": "hin",
            "th": "tha",
            "vi": "vie",
            "pl": "pol",
            "nl": "nld",
        }

    async def extract_text(self, image: ImageType, language: Language) -> Tuple[str, float]:
        """Extract text from image with confidence score."""
        try:
            # Map language code to Tesseract format
            tesseract_lang = self._language_mapping.get(language.code, "eng")

            # Configure Tesseract
            config = r"--oem 3 --psm 6"

            # Extract text
            text = pytesseract.image_to_string(image, lang=tesseract_lang, config=config).strip()

            # Get confidence (rough estimation)
            try:
                data = pytesseract.image_to_data(
                    image, lang=tesseract_lang, config=config, output_type=pytesseract.Output.DICT
                )

                confidences = [int(conf) for conf in data["conf"] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                confidence = avg_confidence / 100.0  # Convert to 0-1 range

            except Exception:
                confidence = 0.5  # Default confidence

            logger.info(
                f"OCR extraction completed",
                text_length=len(text),
                confidence=confidence,
                language=language.code,
            )

            return text, confidence

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return "", 0.0

    def is_available(self) -> bool:
        """Check if OCR service is available."""
        try:
            # Test with a simple image
            test_image = Image.new("RGB", (100, 30), color="white")
            pytesseract.image_to_string(test_image, config="--oem 3 --psm 6")
            return True
        except Exception:
            return False

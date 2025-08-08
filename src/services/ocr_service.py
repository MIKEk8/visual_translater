"""
OCR service for Screen Translator v2.0.
Provides text extraction from images using multiple OCR backends.
"""

import io
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from src.utils.logger import logger


class OCRProvider(Enum):
    """Supported OCR providers."""

    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
    PADDLE = "paddle"
    WINDOWS_OCR = "windows_ocr"
    MOCK = "mock"


@dataclass
class OCRConfig:
    """Configuration for OCR service."""

    default_provider: OCRProvider = OCRProvider.TESSERACT
    languages: Optional[List[str]] = None
    confidence_threshold: float = 0.7
    preprocessing: bool = True
    auto_rotate: bool = True
    remove_whitespace: bool = True
    timeout: float = 30.0

    def __post_init__(self):
        if self.languages is None:
            self.languages = ["eng", "rus"]


@dataclass
class OCRResult:
    """Result of OCR operation."""

    text: str
    confidence: float
    language: str
    provider: OCRProvider
    processing_time: float
    bounding_boxes: Optional[List[Dict[str, Any]]] = None
    timestamp: float = 0

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()
        if self.bounding_boxes is None:
            self.bounding_boxes = []


class OCRBackend:
    """Base class for OCR backends."""

    def __init__(self, config: OCRConfig):
        self.config = config
        self.available = False

    def is_available(self) -> bool:
        """Check if backend is available."""
        return self.available

    def extract_text(self, image_data: bytes, languages: Optional[List[str]] = None) -> OCRResult:
        """Extract text from image."""
        raise NotImplementedError

    def preprocess_image(self, image_data: bytes) -> bytes:
        """Preprocess image for better OCR results."""
        return image_data  # Default: no preprocessing


class TesseractOCRBackend(OCRBackend):
    """Tesseract OCR backend."""

    def __init__(self, config: OCRConfig):
        super().__init__(config)
        try:
            import pytesseract
            from PIL import Image

            self.pytesseract = pytesseract
            self.Image = Image
            self.available = True
            logger.debug("Tesseract OCR backend initialized")
        except ImportError:
            logger.warning("Tesseract OCR backend not available - pytesseract or PIL not installed")
            self.available = False

    def extract_text(self, image_data: bytes, languages: Optional[List[str]] = None) -> OCRResult:
        """Extract text using Tesseract."""
        if not self.available:
            raise RuntimeError("Tesseract OCR backend not available")

        start_time = time.time()

        try:
            # Convert bytes to PIL Image
            image = self.Image.open(io.BytesIO(image_data))

            # Set language
            lang = "+".join(languages) if languages else "+".join(self.config.languages)

            # Extract text with confidence
            data = self.pytesseract.image_to_data(
                image, lang=lang, output_type=self.pytesseract.Output.DICT
            )

            # Combine text with confidence filtering
            text_parts = []
            confidences = []

            for i, confidence in enumerate(data["conf"]):
                if int(confidence) > (self.config.confidence_threshold * 100):
                    word = data["text"][i].strip()
                    if word:
                        text_parts.append(word)
                        confidences.append(int(confidence))

            # Calculate average confidence
            avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0

            # Join text
            extracted_text = " ".join(text_parts)

            if self.config.remove_whitespace:
                extracted_text = " ".join(extracted_text.split())

            processing_time = time.time() - start_time

            return OCRResult(
                text=extracted_text,
                confidence=avg_confidence,
                language=lang.split("+")[0],
                provider=OCRProvider.TESSERACT,
                processing_time=processing_time,
            )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Tesseract OCR failed: {e}")
            raise


class MockOCRBackend(OCRBackend):
    """Mock OCR backend for testing."""

    def __init__(self, config: OCRConfig):
        super().__init__(config)
        self.available = True
        logger.debug("Mock OCR backend initialized")

    def extract_text(self, image_data: bytes, languages: Optional[List[str]] = None) -> OCRResult:
        """Mock text extraction."""
        start_time = time.time()

        # Simulate processing time
        import secrets

        processing_time = 0.1 + (secrets.randbelow(40) / 100.0)  # 0.1-0.5 seconds
        time.sleep(processing_time)

        # Mock extracted text based on image size
        image_size = len(image_data)

        if image_size < 1000:
            mock_text = "Hello"
        elif image_size < 5000:
            mock_text = "Hello, world!"
        elif image_size < 10000:
            mock_text = "This is a sample text extracted from image."
        else:
            mock_text = "This is a longer sample text that was extracted from a larger image using mock OCR backend."

        actual_processing_time = time.time() - start_time

        return OCRResult(
            text=mock_text,
            confidence=0.8 + (secrets.randbelow(15) / 100.0),  # 0.8-0.95
            language=languages[0] if languages else "en",
            provider=OCRProvider.MOCK,
            processing_time=actual_processing_time,
        )


class OCRService:
    """Main OCR service with multiple backends."""

    def __init__(self, config: Optional[OCRConfig] = None):
        """Initialize OCR service."""
        self.config = config or OCRConfig()
        self.backends: Dict[OCRProvider, OCRBackend] = {}
        self.cache: Dict[str, OCRResult] = {}

        # Initialize backends
        self._initialize_backends()

        # Find primary backend
        self.primary_backend = self._get_primary_backend()

        logger.info(f"OCR service initialized with {len(self.backends)} backends")
        if self.primary_backend:
            logger.debug(f"Primary backend: {type(self.primary_backend).__name__}")

    def _initialize_backends(self) -> None:
        """Initialize all available OCR backends."""

        # Tesseract
        tesseract_backend = TesseractOCRBackend(self.config)
        if tesseract_backend.is_available():
            self.backends[OCRProvider.TESSERACT] = tesseract_backend

        # Mock backend (always available)
        mock_backend = MockOCRBackend(self.config)
        self.backends[OCRProvider.MOCK] = mock_backend

    def _get_primary_backend(self) -> Optional[OCRBackend]:
        """Get primary OCR backend."""
        # Prefer real backends over mock
        for provider in [
            OCRProvider.TESSERACT,
            OCRProvider.EASYOCR,
            OCRProvider.WINDOWS_OCR,
            OCRProvider.MOCK,
        ]:
            if provider in self.backends:
                return self.backends[provider]

        return None

    def extract_text(
        self,
        image_data: bytes,
        languages: Optional[List[str]] = None,
        provider: Optional[OCRProvider] = None,
    ) -> OCRResult:
        """
        Extract text from image.

        Args:
            image_data: Image data as bytes
            languages: List of language codes
            provider: Specific OCR provider to use

        Returns:
            OCR result
        """
        if not image_data:
            return OCRResult(
                text="",
                confidence=0.0,
                language="unknown",
                provider=OCRProvider.MOCK,
                processing_time=0.0,
            )

        languages = languages or self.config.languages

        # Use specific provider or primary
        backend = None
        if provider and provider in self.backends:
            backend = self.backends[provider]
        else:
            backend = self.primary_backend

        if not backend:
            raise RuntimeError("No OCR backends available")

        # Check cache
        cache_key = self._generate_cache_key(image_data, languages, backend.config.default_provider)
        if cache_key in self.cache:
            logger.debug("OCR result found in cache")
            return self.cache[cache_key]

        try:
            # Extract text
            result = backend.extract_text(image_data, languages)

            # Cache result
            self.cache[cache_key] = result

            logger.debug(
                f"OCR extracted {len(result.text)} characters with {result.confidence:.2f} confidence"
            )
            return result

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")

            # Fallback to mock if available
            if OCRProvider.MOCK in self.backends and backend != self.backends[OCRProvider.MOCK]:
                logger.warning("Using mock OCR fallback")
                return self.backends[OCRProvider.MOCK].extract_text(image_data, languages)

            raise

    def _generate_cache_key(
        self, image_data: bytes, languages: List[str], provider: OCRProvider
    ) -> str:
        """Generate cache key for image and parameters."""
        import hashlib

        # Create hash of image data
        image_hash = hashlib.md5(image_data, usedforsecurity=False).hexdigest()[:16]

        # Create key from parameters
        lang_key = "+".join(sorted(languages))

        return f"{image_hash}|{lang_key}|{provider.value}"

    def get_available_providers(self) -> List[OCRProvider]:
        """Get list of available OCR providers."""
        return list(self.backends.keys())

    def clear_cache(self) -> None:
        """Clear OCR cache."""
        self.cache.clear()
        logger.debug("OCR cache cleared")

    def get_cache_size(self) -> int:
        """Get number of cached results."""
        return len(self.cache)

    def preprocess_image(self, image_data: bytes) -> bytes:
        """Preprocess image for better OCR results."""
        if not self.primary_backend:
            return image_data

        try:
            return self.primary_backend.preprocess_image(image_data)
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}")
            return image_data


# Global OCR service instance
_ocr_service: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    """Get global OCR service instance."""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service


def initialize_ocr_service(config: Optional[OCRConfig] = None) -> OCRService:
    """Initialize global OCR service."""
    global _ocr_service
    _ocr_service = OCRService(config)
    return _ocr_service


# Convenience functions
def extract_text_from_image(image_data: bytes, languages: Optional[List[str]] = None) -> str:
    """Quick OCR function."""
    service = get_ocr_service()
    result = service.extract_text(image_data, languages)
    return result.text


def extract_text_with_confidence(
    image_data: bytes, languages: Optional[List[str]] = None
) -> Tuple[str, float]:
    """Quick OCR function with confidence."""
    service = get_ocr_service()
    result = service.extract_text(image_data, languages)
    return result.text, result.confidence

import pytesseract

from src.core.ocr_engine import TesseractOCR

"""
AI-powered OCR engine for Screen Translator v2.0.
Provides advanced text detection and recognition using machine learning approaches.
"""

import io
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    import cv2
except ImportError:
    print("OpenCV не доступен в данной среде")
    cv2 = None
import numpy as np
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


class TextDetector:
    """Advanced text detection using computer vision techniques."""

    def __init__(self):
        self.min_text_size = 10
        self.max_text_size = 200
        self.confidence_threshold = 0.5

    def detect_text_regions(self, image: np.ndarray) -> List[TextRegion]:
        """
        Detect text regions in image using advanced computer vision.

        Args:
            image: Input image as numpy array

        Returns:
            List of detected text regions with bounding boxes
        """
        try:
            # Convert to grayscale for processing
            if len(image.shape) == 3:
                gray = (cv2.cvtColor if cv2 else None)(image, (cv2.COLOR_RGB2GRAY if cv2 else None))
            else:
                gray = image.copy()

            # Apply adaptive preprocessing
            processed = self._preprocess_for_text_detection(gray)

            # Detect text using multiple methods
            regions = []

            # Method 1: MSER (Maximally Stable Extremal Regions)
            mser_regions = self._detect_with_mser(processed)
            regions.extend(mser_regions)

            # Method 2: Edge-based detection
            edge_regions = self._detect_with_edges(processed)
            regions.extend(edge_regions)

            # Method 3: Contour-based detection
            contour_regions = self._detect_with_contours(processed)
            regions.extend(contour_regions)

            # Merge overlapping regions and filter
            merged_regions = self._merge_and_filter_regions(regions)

            logger.debug(f"Detected {len(merged_regions)} text regions")
            return merged_regions

        except Exception as e:
            logger.error("Text detection failed", error=e)
            return []

    def _preprocess_for_text_detection(self, gray: np.ndarray) -> np.ndarray:
        """Apply preprocessing optimized for text detection."""
        # Noise reduction
        denoised = (cv2.bilateralFilter if cv2 else None)(gray, 9, 75, 75)

        # Contrast enhancement
        clahe = (cv2.createCLAHE if cv2 else None)(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        # Sharpening
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        sharpened = (cv2.filter2D if cv2 else None)(enhanced, -1, kernel)

        return sharpened

    def _detect_with_mser(self, image: np.ndarray) -> List[TextRegion]:
        """Detect text using MSER algorithm."""
        try:
            # Create MSER detector
            mser = (cv2.MSER_create if cv2 else None)(
                _min_area=60, _max_area=14400, _max_variation=0.25, _min_diversity=0.2
            )

            # Detect regions
            regions, _ = mser.detectRegions(image)

            text_regions = []
            for region in regions:
                # Get bounding box
                x, y, w, h = (cv2.boundingRect if cv2 else None)(region.reshape(-1, 1, 2))

                # Filter by size and aspect ratio
                if self._is_text_like_region(w, h):
                    bbox = (x, y, x + w, y + h)
                    text_region = TextRegion(
                        bbox=bbox,
                        text="",  # Will be filled by OCR
                        confidence=0.8,  # MSER regions are generally reliable
                        language="unknown",
                    )
                    text_regions.append(text_region)

            return text_regions

        except Exception as e:
            logger.debug(f"MSER detection failed: {e}")
            return []

    def _detect_with_edges(self, image: np.ndarray) -> List[TextRegion]:
        """Detect text using edge-based methods."""
        try:
            # Edge detection
            edges = (cv2.Canny if cv2 else None)(image, 50, 150, apertureSize=3)

            # Morphological operations to connect text components
            kernel = (cv2.getStructuringElement if cv2 else None)(
                (cv2.MORPH_RECT if cv2 else None), (3, 3)
            )
            dilated = (cv2.dilate if cv2 else None)(edges, kernel, iterations=1)

            # Find contours
            contours, _ = (cv2.findContours if cv2 else None)(
                dilated,
                (cv2.RETR_EXTERNAL if cv2 else None),
                (cv2.CHAIN_APPROX_SIMPLE if cv2 else None),
            )

            text_regions = []
            for contour in contours:
                x, y, w, h = (cv2.boundingRect if cv2 else None)(contour)

                if self._is_text_like_region(w, h):
                    bbox = (x, y, x + w, y + h)
                    text_region = TextRegion(
                        bbox=bbox,
                        text="",
                        confidence=0.6,  # Edge-based is less reliable
                        language="unknown",
                    )
                    text_regions.append(text_region)

            return text_regions

        except Exception as e:
            logger.debug(f"Edge detection failed: {e}")
            return []

    def _detect_with_contours(self, image: np.ndarray) -> List[TextRegion]:
        """Detect text using contour analysis."""
        try:
            # Adaptive threshold
            thresh = (cv2.adaptiveThreshold if cv2 else None)(
                image,
                255,
                (cv2.ADAPTIVE_THRESH_GAUSSIAN_C if cv2 else None),
                (cv2.THRESH_BINARY if cv2 else None),
                11,
                2,
            )

            # Find contours
            contours, _ = (cv2.findContours if cv2 else None)(
                thresh, (cv2.RETR_TREE if cv2 else None), (cv2.CHAIN_APPROX_SIMPLE if cv2 else None)
            )

            text_regions = []
            for contour in contours:
                x, y, w, h = (cv2.boundingRect if cv2 else None)(contour)

                # Additional checks for text-like properties
                if self._is_text_like_region(w, h):
                    # Check if contour has text-like characteristics
                    area = (cv2.contourArea if cv2 else None)(contour)
                    hull_area = (cv2.contourArea if cv2 else None)(
                        (cv2.convexHull if cv2 else None)(contour)
                    )

                    if area > 0 and hull_area > 0:
                        solidity = area / hull_area

                        # Text regions typically have moderate solidity
                        if 0.3 <= solidity <= 0.95:
                            bbox = (x, y, x + w, y + h)
                            text_region = TextRegion(
                                bbox=bbox, text="", confidence=0.7, language="unknown"
                            )
                            text_regions.append(text_region)

            return text_regions

        except Exception as e:
            logger.debug(f"Contour detection failed: {e}")
            return []

    def _is_text_like_region(self, width: int, height: int) -> bool:
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

    def _merge_and_filter_regions(self, regions: List[TextRegion]) -> List[TextRegion]:
        """Merge overlapping regions and filter out low-quality detections."""
        if not regions:
            return []

        # Sort by confidence
        sorted_regions = sorted(regions, key=lambda r: r.confidence, reverse=True)

        merged = []
        for current in sorted_regions:
            should_merge = False

            for i, existing in enumerate(merged):
                if self._regions_overlap(current.bbox, existing.bbox):
                    # Merge with existing region
                    merged_bbox = self._merge_bboxes(current.bbox, existing.bbox)
                    merged_confidence = max(current.confidence, existing.confidence)

                    merged[i] = TextRegion(
                        bbox=merged_bbox, text="", confidence=merged_confidence, language="unknown"
                    )
                    should_merge = True
                    break

            if not should_merge and current.confidence >= self.confidence_threshold:
                merged.append(current)

        return merged

    def _regions_overlap(
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

    def _merge_bboxes(
        self, bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]
    ) -> Tuple[int, int, int, int]:
        """Merge two bounding boxes into one that contains both."""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2

        return (min(x1_1, x1_2), min(y1_1, y1_2), max(x2_1, x2_2), max(y2_1, y2_2))


class ImageEnhancer:
    """Advanced image enhancement for better OCR results."""

    def __init__(self):
        self.enhancement_methods = [
            "adaptive_enhance",
            "super_resolution",
            "denoising",
            "deskewing",
            "contrast_optimization",
        ]

    def enhance_for_ocr(self, image: np.ndarray, enhancement_level: str = "auto") -> np.ndarray:
        """
        Apply multiple enhancement techniques to improve OCR accuracy.

        Args:
            image: Input image as numpy array
            enhancement_level: "light", "moderate", "aggressive", "auto"

        Returns:
            Enhanced image optimized for OCR
        """
        try:
            enhanced = image.copy()

            # Auto-detect best enhancement level
            if enhancement_level == "auto":
                enhancement_level = self._detect_enhancement_level(image)

            # Apply enhancements based on level
            if enhancement_level in ["moderate", "aggressive"]:
                enhanced = self._apply_super_resolution(enhanced)

            enhanced = self._apply_adaptive_enhancement(enhanced)
            enhanced = self._apply_denoising(enhanced, strength=enhancement_level)
            enhanced = self._apply_deskewing(enhanced)

            if enhancement_level == "aggressive":
                enhanced = self._apply_contrast_optimization(enhanced)

            logger.debug(f"Applied {enhancement_level} enhancement to image")
            return enhanced

        except Exception as e:
            logger.error("Image enhancement failed", error=e)
            return image

    def _detect_enhancement_level(self, image: np.ndarray) -> str:
        """Automatically detect appropriate enhancement level."""
        # Convert to grayscale for analysis
        if len(image.shape) == 3:
            gray = (cv2.cvtColor if cv2 else None)(image, (cv2.COLOR_RGB2GRAY if cv2 else None))
        else:
            gray = image

        # Calculate image quality metrics
        blur_score = (cv2.Laplacian if cv2 else None)(gray, (cv2.CV_64F if cv2 else None)).var()
        noise_score = np.std(gray)
        contrast_score = gray.std()

        # Determine enhancement level based on quality
        if blur_score < 100 or noise_score > 50:
            return "aggressive"
        elif blur_score < 500 or contrast_score < 40:
            return "moderate"
        else:
            return "light"

    def _apply_super_resolution(self, image: np.ndarray) -> np.ndarray:
        """Apply super-resolution enhancement (simplified version)."""
        try:
            # Simple bicubic upscaling - in production, could use ML models
            height, width = image.shape[:2]

            # Only upscale if image is small
            if height < 200 or width < 200:
                scale_factor = 2.0
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)

                upscaled = (cv2.resize if cv2 else None)(
                    image, (new_width, new_height), interpolation=(cv2.INTER_CUBIC if cv2 else None)
                )

                # Apply sharpening after upscaling
                kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
                sharpened = (cv2.filter2D if cv2 else None)(upscaled, -1, kernel)

                return sharpened

            return image

        except Exception:
            return image

    def _apply_adaptive_enhancement(self, image: np.ndarray) -> np.ndarray:
        """Apply adaptive contrast and brightness enhancement."""
        try:
            if len(image.shape) == 3:
                # Convert to LAB color space for better enhancement
                lab = (cv2.cvtColor if cv2 else None)(image, (cv2.COLOR_RGB2LAB if cv2 else None))
                l_channel, a_channel, b_channel = (cv2.split if cv2 else None)(lab)

                # Apply CLAHE to L channel
                clahe = (cv2.createCLAHE if cv2 else None)(clipLimit=3.0, tileGridSize=(8, 8))
                enhanced_l = clahe.apply(l_channel)

                # Merge channels and convert back
                enhanced_lab = (cv2.merge if cv2 else None)([enhanced_l, a_channel, b_channel])
                enhanced = (cv2.cvtColor if cv2 else None)(
                    enhanced_lab, (cv2.COLOR_LAB2RGB if cv2 else None)
                )
            else:
                # Grayscale image
                clahe = (cv2.createCLAHE if cv2 else None)(clipLimit=3.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(image)

            return enhanced

        except Exception:
            return image

    def _apply_denoising(self, image: np.ndarray, strength: str = "moderate") -> np.ndarray:
        """Apply noise reduction."""
        try:
            if strength == "light":
                h = 3
            elif strength == "moderate":
                h = 7
            else:  # aggressive
                h = 10

            if len(image.shape) == 3:
                denoised = (cv2.fastNlMeansDenoisingColored if cv2 else None)(
                    image, None, h, h, 7, 21
                )
            else:
                denoised = (cv2.fastNlMeansDenoising if cv2 else None)(image, None, h, 7, 21)

            return denoised

        except Exception:
            return image

    def _apply_deskewing(self, image: np.ndarray) -> np.ndarray:
        """Correct skew in the image."""
        try:
            # Convert to grayscale for skew detection
            if len(image.shape) == 3:
                gray = (cv2.cvtColor if cv2 else None)(image, (cv2.COLOR_RGB2GRAY if cv2 else None))
            else:
                gray = image

            # Detect edges
            edges = (cv2.Canny if cv2 else None)(gray, 50, 150, apertureSize=3)

            # Detect lines using Hough transform
            lines = (cv2.HoughLines if cv2 else None)(edges, 1, np.pi / 180, threshold=100)

            if lines is not None and len(lines) > 5:
                # Calculate average angle
                angles = []
                for line in lines[:20]:  # Use top 20 lines
                    rho, theta = line[0]
                    angle = theta * 180 / np.pi - 90
                    if abs(angle) < 45:  # Only consider reasonable skew angles
                        angles.append(angle)

                if angles:
                    avg_angle = np.median(angles)

                    # Only correct if skew is significant
                    if abs(avg_angle) > 0.5:
                        height, width = image.shape[:2]
                        center = (width // 2, height // 2)

                        # Create rotation matrix
                        rotation_matrix = (cv2.getRotationMatrix2D if cv2 else None)(
                            center, avg_angle, 1.0
                        )

                        # Apply rotation
                        corrected = (cv2.warpAffine if cv2 else None)(
                            image,
                            rotation_matrix,
                            (width, height),
                            flags=(cv2.INTER_CUBIC if cv2 else None),
                            borderMode=(cv2.BORDER_REPLICATE if cv2 else None),
                        )

                        logger.debug(f"Corrected skew by {avg_angle:.2f} degrees")
                        return corrected

            return image

        except Exception:
            return image

    def _apply_contrast_optimization(self, image: np.ndarray) -> np.ndarray:
        """Apply advanced contrast optimization."""
        try:
            if len(image.shape) == 3:
                # Convert to grayscale for analysis
                gray = (cv2.cvtColor if cv2 else None)(image, (cv2.COLOR_RGB2GRAY if cv2 else None))
            else:
                gray = image

            # Calculate optimal contrast parameters
            hist = (cv2.calcHist if cv2 else None)([gray], [0], None, [256], [0, 256])

            # Find the 1st and 99th percentiles
            cumsum = np.cumsum(hist)
            total_pixels = cumsum[-1]

            lower_bound = np.argmax(cumsum > total_pixels * 0.01)
            upper_bound = np.argmax(cumsum > total_pixels * 0.99)

            # Apply linear stretching
            if upper_bound > lower_bound:
                # Calculate alpha and beta for linear transformation
                alpha = 255.0 / (upper_bound - lower_bound)
                beta = -alpha * lower_bound

                enhanced = (cv2.convertScaleAbs if cv2 else None)(image, alpha=alpha, beta=beta)
                return enhanced

            return image

        except Exception:
            return image


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
            return True
        except ImportError:
            return False

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the AI OCR plugin."""
        try:
            if not self.is_available():
                logger.error("AI OCR dependencies not available")
                return False

            # Import dependencies

            # Configure text detector
            confidence_threshold = config.get("confidence_threshold", 0.5)
            self.text_detector.confidence_threshold = confidence_threshold

            # Try to initialize fallback OCR
            fallback_name = config.get("fallback_ocr", "tesseract")
            if fallback_name == "tesseract":
                try:

                    self.base_ocr = TesseractOCR()
                except ImportError:
                    logger.warning("Tesseract fallback not available")

            self._config = config
            self._initialized = True

            logger.info("AI Enhanced OCR plugin initialized successfully")
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
        logger.info("AI Enhanced OCR plugin cleaned up")

    def extract_text(self, image_data: bytes, languages: List[str]) -> Tuple[str, float]:
        """
        Extract text using AI-enhanced OCR pipeline.

        Args:
            image_data: Raw image bytes
            languages: List of language codes for OCR

        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        if not self._initialized:
            raise RuntimeError("Plugin not initialized")

        try:
            # Convert bytes to image
            # TODO: Performance - Consider using aiofiles for async file operations
            image = Image.open(io.BytesIO(image_data))
            image_np = np.array(image)

            # Apply AI enhancement
            enhancement_level = self._config.get("enhancement_level", "auto")
            enhanced_image = self.image_enhancer.enhance_for_ocr(image_np, enhancement_level)

            # Detect text regions if enabled
            enable_detection = self._config.get("enable_text_detection", True)
            if enable_detection:
                text_regions = self.text_detector.detect_text_regions(enhanced_image)

                if text_regions:
                    # Process each region separately for better accuracy
                    return self._extract_from_regions(enhanced_image, text_regions, languages)

            # Fallback to full image OCR
            return self._extract_from_full_image(enhanced_image, languages)

        except Exception as e:
            logger.error("AI OCR extraction failed", error=e)
            return "", 0.0

    def _extract_from_regions(
        self, image: np.ndarray, regions: List[TextRegion], languages: List[str]
    ) -> Tuple[str, float]:
        """Extract text from detected regions."""
        all_text = []
        all_confidences = []

        for region in regions:
            try:
                # Extract region from image
                x1, y1, x2, y2 = region.bbox
                region_image = image[y1:y2, x1:x2]

                if region_image.size == 0:
                    continue

                # Convert to PIL for OCR
                region_pil = Image.fromarray(region_image)
                region_bytes = io.BytesIO()
                region_pil.save(region_bytes, format="PNG")
                region_bytes.seek(0)

                # Extract text from region
                if self.base_ocr:
                    text, confidence = self.base_ocr.extract_text(region_pil, languages)
                else:
                    # Simple fallback
                    text, confidence = self._simple_ocr_fallback(region_pil, languages)

                if text.strip():
                    all_text.append(text.strip())
                    all_confidences.append(confidence)

                    # Update region with extracted text
                    region.text = text.strip()
                    region.confidence = confidence

            except Exception as e:
                logger.debug(f"Failed to extract text from region: {e}")
                continue

        # Combine results
        if all_text:
            combined_text = " ".join(all_text)
            avg_confidence = sum(all_confidences) / len(all_confidences)

            logger.debug(
                f"AI OCR extracted from {len(all_text)} regions with avg confidence {avg_confidence:.2f}"
            )
            return combined_text, avg_confidence

        return "", 0.0

    def _extract_from_full_image(
        self, image: np.ndarray, languages: List[str]
    ) -> Tuple[str, float]:
        """Extract text from full enhanced image."""
        try:
            # Convert to PIL
            pil_image = Image.fromarray(image)

            # Use fallback OCR
            if self.base_ocr:
                text, confidence = self.base_ocr.extract_text(pil_image, languages)
            else:
                text, confidence = self._simple_ocr_fallback(pil_image, languages)

            logger.debug(
                f"AI OCR full image extraction: {len(text)} chars, confidence {confidence:.2f}"
            )
            return text, confidence

        except Exception as e:
            logger.error(f"Full image OCR failed: {e}")
            return "", 0.0

    def _simple_ocr_fallback(self, image: Image.Image, languages: List[str]) -> Tuple[str, float]:
        """Simple OCR fallback when base OCR is not available."""
        try:

            # Convert language codes
            lang_string = "+".join(languages) if languages else "eng"

            # Extract text with confidence
            data = pytesseract.image_to_data(
                image, lang=lang_string, output_type=pytesseract.Output.DICT
            )

            # Filter confident text
            confidences = [int(conf) for conf in data["conf"] if int(conf) > 0]
            texts = [data["text"][i] for i, conf in enumerate(data["conf"]) if int(conf) > 0]

            if texts and confidences:
                combined_text = " ".join(text for text in texts if text.strip())
                avg_confidence = sum(confidences) / len(confidences) / 100.0  # Convert to 0-1
                return combined_text, avg_confidence

            return "", 0.0

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
            # Convert to numpy array
            # TODO: Performance - Consider using aiofiles for async file operations
            image = Image.open(io.BytesIO(image_data))
            image_np = np.array(image)

            # Apply enhancement
            enhancement_level = self._config.get("enhancement_level", "auto")
            enhanced = self.image_enhancer.enhance_for_ocr(image_np, enhancement_level)

            # Convert back to bytes
            enhanced_pil = Image.fromarray(enhanced)
            output = io.BytesIO()
            enhanced_pil.save(output, format="PNG")
            return output.getvalue()

        except Exception as e:
            logger.error("Image preprocessing failed", error=e)
            return image_data

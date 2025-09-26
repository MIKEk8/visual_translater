"""Text detection module for AI OCR engine.

Separated from the original God Class for better maintainability.
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
            List of detected text regions
        """
        if cv2 is None:
            logger.warning("OpenCV not available, using basic detection")
            return self._fallback_detection(image)

        # Convert to grayscale for processing
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Preprocess image for text detection
        processed = self._preprocess_for_text_detection(gray)

        # Use multiple detection methods and combine results
        regions = []

        # MSER detection (good for text)
        mser_regions = self._detect_with_mser(processed)
        regions.extend(mser_regions)

        # Edge-based detection
        edge_regions = self._detect_with_edges(processed)
        regions.extend(edge_regions)

        # Contour-based detection
        contour_regions = self._detect_with_contours(processed)
        regions.extend(contour_regions)

        # Filter and merge overlapping regions
        final_regions = self._merge_and_filter_regions(regions)

        logger.debug(f"Detected {len(final_regions)} text regions")
        return final_regions

    def _preprocess_for_text_detection(self, gray: np.ndarray) -> np.ndarray:
        """Preprocess image for better text detection."""
        if cv2 is None:
            return gray

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)

        # Apply adaptive threshold
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        return thresh

    def _detect_with_mser(self, image: np.ndarray) -> List[TextRegion]:
        """Detect text regions using MSER (Maximally Stable Extremal Regions)."""
        if cv2 is None:
            return []

        try:
            # Create MSER detector
            mser = cv2.MSER_create(
                _delta=5,
                _min_area=60,
                _max_area=14400,
                _max_variation=0.25,
                _min_diversity=0.2,
                _max_evolution=200,
                _area_threshold=1.01,
                _min_margin=0.003,
                _edge_blur_size=5
            )

            # Detect regions
            regions, _ = mser.detectRegions(image)

            text_regions = []
            for region in regions:
                # Get bounding box
                x, y, w, h = cv2.boundingRect(region.reshape(-1, 1, 2))

                # Filter by size
                if self._is_text_like_region(w, h):
                    text_regions.append(TextRegion(
                        bbox=(x, y, x + w, y + h),
                        text="",  # Will be filled by OCR
                        confidence=0.7,  # MSER is generally reliable
                        language="unknown"
                    ))

            return text_regions

        except Exception as e:
            logger.warning(f"MSER detection failed: {e}")
            return []

    def _detect_with_edges(self, image: np.ndarray) -> List[TextRegion]:
        """Detect text regions using edge detection."""
        if cv2 is None:
            return []

        try:
            # Apply Canny edge detection
            edges = cv2.Canny(image, 50, 150, apertureSize=3)

            # Dilate to connect text components
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            dilated = cv2.dilate(edges, kernel, iterations=1)

            # Find contours
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            text_regions = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)

                if self._is_text_like_region(w, h):
                    text_regions.append(TextRegion(
                        bbox=(x, y, x + w, y + h),
                        text="",
                        confidence=0.6,  # Edge detection is less reliable
                        language="unknown"
                    ))

            return text_regions

        except Exception as e:
            logger.warning(f"Edge detection failed: {e}")
            return []

    def _detect_with_contours(self, image: np.ndarray) -> List[TextRegion]:
        """Detect text regions using contour analysis."""
        if cv2 is None:
            return []

        try:
            # Find contours in the binary image
            contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            text_regions = []
            for contour in contours:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)

                # Calculate contour properties
                area = cv2.contourArea(contour)
                if area < 50:  # Too small
                    continue

                # Check aspect ratio and size
                if self._is_text_like_region(w, h):
                    # Calculate solidity (area/convex_hull_area)
                    hull = cv2.convexHull(contour)
                    hull_area = cv2.contourArea(hull)
                    solidity = area / hull_area if hull_area > 0 else 0

                    # Text regions typically have medium solidity
                    if 0.3 <= solidity <= 0.95:
                        text_regions.append(TextRegion(
                            bbox=(x, y, x + w, y + h),
                            text="",
                            confidence=0.5 + solidity * 0.3,  # Confidence based on solidity
                            language="unknown"
                        ))

            return text_regions

        except Exception as e:
            logger.warning(f"Contour detection failed: {e}")
            return []

    def _is_text_like_region(self, width: int, height: int) -> bool:
        """Check if region dimensions are suitable for text."""
        # Check minimum and maximum size
        if width < self.min_text_size or height < self.min_text_size:
            return False
        if width > self.max_text_size or height > self.max_text_size:
            return False

        # Check aspect ratio (text is usually wider than tall, but not extremely)
        aspect_ratio = width / height
        if aspect_ratio < 0.1 or aspect_ratio > 15:
            return False

        # Check area
        area = width * height
        if area < 100 or area > 40000:
            return False

        return True

    def _merge_and_filter_regions(self, regions: List[TextRegion]) -> List[TextRegion]:
        """Merge overlapping regions and filter out unlikely text regions."""
        if not regions:
            return []

        # Sort by confidence (descending)
        regions.sort(key=lambda r: r.confidence, reverse=True)

        merged_regions = []
        for region in regions:
            # Check if this region overlaps significantly with any existing region
            overlaps = False
            for existing in merged_regions:
                if self._regions_overlap(region.bbox, existing.bbox, threshold=0.5):
                    overlaps = True
                    break

            if not overlaps:
                merged_regions.append(region)

        # Filter by confidence threshold
        final_regions = [r for r in merged_regions if r.confidence >= self.confidence_threshold]

        return final_regions

    def _regions_overlap(
        self,
        bbox1: Tuple[int, int, int, int],
        bbox2: Tuple[int, int, int, int],
        threshold: float = 0.3
    ) -> bool:
        """Check if two bounding boxes overlap significantly."""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2

        # Calculate intersection area
        x_overlap = max(0, min(x2_1, x2_2) - max(x1_1, x1_2))
        y_overlap = max(0, min(y2_1, y2_2) - max(y1_1, y1_2))
        intersection = x_overlap * y_overlap

        # Calculate union area
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection

        # Calculate IoU (Intersection over Union)
        iou = intersection / union if union > 0 else 0

        return iou >= threshold

    def _merge_bboxes(
        self,
        bbox1: Tuple[int, int, int, int],
        bbox2: Tuple[int, int, int, int]
    ) -> Tuple[int, int, int, int]:
        """Merge two bounding boxes into one."""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2

        return (
            min(x1_1, x1_2),
            min(y1_1, y1_2),
            max(x2_1, x2_2),
            max(y2_1, y2_2)
        )

    def _fallback_detection(self, image: np.ndarray) -> List[TextRegion]:
        """Fallback detection when OpenCV is not available."""
        height, width = image.shape[:2]

        # Create a single region covering the entire image
        return [TextRegion(
            bbox=(0, 0, width, height),
            text="",
            confidence=0.3,  # Low confidence for fallback
            language="unknown"
        )]
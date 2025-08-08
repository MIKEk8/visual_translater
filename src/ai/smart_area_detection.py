"""Smart area detection using AI/ML for automatic text region identification."""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    import cv2
except ImportError:
    print("OpenCV не доступен в данной среде")
    cv2 = None
import numpy as np

from src.utils.logger import logger


class DetectionMethod(Enum):
    """Available detection methods."""

    CONTOUR_BASED = "contour_based"
    EDGE_DETECTION = "edge_detection"
    TEXT_DETECTION = "text_detection"
    ML_BASED = "ml_based"
    HYBRID = "hybrid"


@dataclass
class TextRegion:
    """Detected text region information."""

    x: int
    y: int
    width: int
    height: int
    confidence: float
    text_density: float
    method_used: DetectionMethod

    @property
    def area(self) -> int:
        """Get region area."""
        return self.width * self.height

    @property
    def aspect_ratio(self) -> float:
        """Get region aspect ratio."""
        return self.width / self.height if self.height > 0 else 0

    @property
    def coordinates(self) -> Tuple[int, int, int, int]:
        """Get region coordinates as (x1, y1, x2, y2)."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    def contains_point(self, x: int, y: int) -> bool:
        """Check if point is inside region."""
        return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height

    def overlaps_with(self, other: "TextRegion", threshold: float = 0.3) -> bool:
        """Check if region overlaps with another region."""
        x1, y1, x2, y2 = self.coordinates
        ox1, oy1, ox2, oy2 = other.coordinates

        # Calculate intersection
        ix1 = max(x1, ox1)
        iy1 = max(y1, oy1)
        ix2 = min(x2, ox2)
        iy2 = min(y2, oy2)

        if ix1 >= ix2 or iy1 >= iy2:
            return False

        intersection_area = (ix2 - ix1) * (iy2 - iy1)
        union_area = self.area + other.area - intersection_area

        overlap_ratio = intersection_area / union_area if union_area > 0 else 0
        return overlap_ratio >= threshold


@dataclass
class DetectionConfig:
    """Configuration for smart area detection."""

    # Method selection
    primary_method: DetectionMethod = DetectionMethod.HYBRID
    fallback_methods: Optional[List[DetectionMethod]] = None

    # Image preprocessing
    resize_factor: float = 1.0
    blur_kernel_size: int = 3
    apply_noise_reduction: bool = True

    # Contour detection
    contour_min_area: int = 100
    contour_max_area: int = 50000
    contour_aspect_ratio_min: float = 0.1
    contour_aspect_ratio_max: float = 10.0

    # Edge detection
    canny_low_threshold: int = 50
    canny_high_threshold: int = 150
    edge_dilation_iterations: int = 2

    # Text detection
    text_confidence_threshold: float = 0.5
    text_nms_threshold: float = 0.4

    # Region filtering
    min_region_size: int = 400  # Minimum region area
    max_regions: int = 10
    merge_overlapping: bool = True
    overlap_threshold: float = 0.3

    # Performance
    max_processing_time: float = 2.0  # seconds
    enable_caching: bool = True

    def __post_init__(self):
        """Set default fallback methods."""
        if self.fallback_methods is None:
            self.fallback_methods = [DetectionMethod.CONTOUR_BASED, DetectionMethod.EDGE_DETECTION]


class SmartAreaDetector:
    """Smart area detection system using multiple algorithms."""

    def __init__(self, config: Optional[DetectionConfig] = None):
        self.config = config or DetectionConfig()

        # Detection cache
        self.detection_cache: Dict[str, List[TextRegion]] = {}
        self.cache_timestamps: Dict[str, float] = {}
        self.cache_max_age = 30.0  # seconds

        # Performance metrics
        self.detection_times: List[float] = []
        self.detection_counts: Dict[DetectionMethod, int] = {
            method: 0 for method in DetectionMethod
        }

        # Try to load advanced detection models
        self.text_detector = None
        self._initialize_text_detector()

        logger.info("Smart area detector initialized")

    def _initialize_text_detector(self) -> None:
        """Initialize advanced text detection model."""
        try:
            # Try to load EAST text detector or similar
            # This would require additional model files
            logger.debug("Advanced text detection models not available, using OpenCV methods")
        except Exception as e:
            logger.debug(f"Could not load advanced text detector: {e}")

    def detect_text_regions(
        self, image: np.ndarray, method: Optional[DetectionMethod] = None
    ) -> List[TextRegion]:
        """
        Detect text regions in image.

        Args:
            image: Input image as numpy array
            method: Detection method to use (None for config default)

        Returns:
            List of detected text regions
        """
        start_time = time.time()

        try:
            # Check cache if enabled
            cache_key = self._generate_cache_key(image)
            if self.config.enable_caching and cache_key in self.detection_cache:
                if time.time() - self.cache_timestamps[cache_key] < self.cache_max_age:
                    logger.debug("Using cached detection results")
                    return self.detection_cache[cache_key]

            # Use specified method or config default
            detection_method = method or self.config.primary_method

            # Preprocess image
            processed_image = self._preprocess_image(image)

            # Detect regions using primary method
            regions = self._detect_with_method(processed_image, detection_method)

            # If primary method fails or returns few results, try fallback methods
            if len(regions) < 2 and detection_method != DetectionMethod.HYBRID:
                for fallback_method in self.config.fallback_methods:
                    if fallback_method != detection_method:
                        fallback_regions = self._detect_with_method(
                            processed_image, fallback_method
                        )
                        regions.extend(fallback_regions)
                        if len(regions) >= 3:  # Enough regions found
                            break

            # Post-process regions
            regions = self._post_process_regions(regions)

            # Cache results
            if self.config.enable_caching:
                self.detection_cache[cache_key] = regions
                self.cache_timestamps[cache_key] = time.time()
                self._cleanup_cache()

            # Update metrics
            detection_time = time.time() - start_time
            self.detection_times.append(detection_time)
            self.detection_counts[detection_method] += 1

            logger.debug(
                f"Detected {len(regions)} text regions in {detection_time:.2f}s using {detection_method.value}"
            )
            return regions

        except Exception as e:
            logger.error(f"Text region detection failed: {e}")
            return []

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for better detection."""
        processed = image.copy()

        # Resize if needed
        if self.config.resize_factor != 1.0:
            height, width = processed.shape[:2]
            new_height = int(height * self.config.resize_factor)
            new_width = int(width * self.config.resize_factor)
            processed = (cv2.resize if cv2 else None)(processed, (new_width, new_height))

        # Convert to grayscale if needed
        if len(processed.shape) == 3:
            processed = (cv2.cvtColor if cv2 else None)(
                processed, (cv2.COLOR_BGR2GRAY if cv2 else None)
            )

        # Apply noise reduction
        if self.config.apply_noise_reduction:
            processed = (cv2.medianBlur if cv2 else None)(processed, self.config.blur_kernel_size)

        return processed

    def _detect_with_method(self, image: np.ndarray, method: DetectionMethod) -> List[TextRegion]:
        """Detect regions using specific method."""
        if method == DetectionMethod.CONTOUR_BASED:
            return self._detect_contour_based(image)
        elif method == DetectionMethod.EDGE_DETECTION:
            return self._detect_edge_based(image)
        elif method == DetectionMethod.TEXT_DETECTION:
            return self._detect_text_based(image)
        elif method == DetectionMethod.ML_BASED:
            return self._detect_ml_based(image)
        elif method == DetectionMethod.HYBRID:
            return self._detect_hybrid(image)
        else:
            logger.warning(f"Unknown detection method: {method}")
            return []

    def _detect_contour_based(self, image: np.ndarray) -> List[TextRegion]:
        """Detect text regions using contour analysis."""
        regions = []

        try:
            # Apply threshold to get binary image
            _, binary = (cv2.threshold if cv2 else None)(
                image,
                0,
                255,
                (cv2.THRESH_BINARY if cv2 else None) + (cv2.THRESH_OTSU if cv2 else None),
            )

            # Find contours
            contours, _ = (cv2.findContours if cv2 else None)(
                binary,
                (cv2.RETR_EXTERNAL if cv2 else None),
                (cv2.CHAIN_APPROX_SIMPLE if cv2 else None),
            )

            for contour in contours:
                # Get bounding rectangle
                x, y, w, h = (cv2.boundingRect if cv2 else None)(contour)
                area = w * h
                aspect_ratio = w / h if h > 0 else 0

                # Filter by size and aspect ratio
                if (
                    self.config.contour_min_area <= area <= self.config.contour_max_area
                    and self.config.contour_aspect_ratio_min
                    <= aspect_ratio
                    <= self.config.contour_aspect_ratio_max
                ):

                    # Calculate text density (simplified)
                    roi = binary[y : y + h, x : x + w]
                    text_density = np.sum(roi == 0) / (w * h) if w * h > 0 else 0

                    # Create region
                    region = TextRegion(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        confidence=min(text_density * 2, 1.0),  # Rough confidence
                        text_density=text_density,
                        method_used=DetectionMethod.CONTOUR_BASED,
                    )
                    regions.append(region)

        except Exception as e:
            logger.error(f"Contour-based detection failed: {e}")

        return regions

    def _detect_edge_based(self, image: np.ndarray) -> List[TextRegion]:
        """Detect text regions using edge detection."""
        regions = []

        try:
            # Apply Canny edge detection
            edges = (cv2.Canny if cv2 else None)(
                image, self.config.canny_low_threshold, self.config.canny_high_threshold
            )

            # Dilate edges to connect nearby text
            kernel = np.ones((3, 3), np.uint8)
            edges = (cv2.dilate if cv2 else None)(
                edges, kernel, iterations=self.config.edge_dilation_iterations
            )

            # Find contours in edge image
            contours, _ = (cv2.findContours if cv2 else None)(
                edges,
                (cv2.RETR_EXTERNAL if cv2 else None),
                (cv2.CHAIN_APPROX_SIMPLE if cv2 else None),
            )

            for contour in contours:
                x, y, w, h = (cv2.boundingRect if cv2 else None)(contour)
                area = w * h

                if area >= self.config.min_region_size:
                    # Calculate edge density
                    roi_edges = edges[y : y + h, x : x + w]
                    edge_density = np.sum(roi_edges > 0) / (w * h) if w * h > 0 else 0

                    region = TextRegion(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        confidence=min(edge_density * 3, 1.0),
                        text_density=edge_density,
                        method_used=DetectionMethod.EDGE_DETECTION,
                    )
                    regions.append(region)

        except Exception as e:
            logger.error(f"Edge-based detection failed: {e}")

        return regions

    def _detect_text_based(self, image: np.ndarray) -> List[TextRegion]:
        """Detect text regions using text-specific algorithms."""
        regions = []

        try:
            # Use MSER (Maximally Stable Extremal Regions) for text detection
            mser = (cv2.MSER_create if cv2 else None)()
            regions_mser, _ = mser.detectRegions(image)

            for region_points in regions_mser:
                # Get bounding rectangle
                x, y, w, h = (cv2.boundingRect if cv2 else None)(region_points)
                area = w * h

                if area >= self.config.min_region_size:
                    # Simple confidence based on region stability
                    confidence = min(len(region_points) / 1000, 1.0)

                    region = TextRegion(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        confidence=confidence,
                        text_density=0.5,  # Default value
                        method_used=DetectionMethod.TEXT_DETECTION,
                    )
                    regions.append(region)

        except Exception as e:
            logger.error(f"Text-based detection failed: {e}")

        return regions

    def _detect_ml_based(self, image: np.ndarray) -> List[TextRegion]:
        """Detect text regions using ML models (placeholder)."""
        regions = []

        # This would use trained ML models like EAST, CRAFT, etc.
        # For now, return empty list as models are not available
        logger.debug("ML-based detection not implemented (requires trained models)")

        return regions

    def _detect_hybrid(self, image: np.ndarray) -> List[TextRegion]:
        """Detect text regions using multiple methods combined."""
        all_regions = []

        # Try multiple methods
        methods = [
            DetectionMethod.CONTOUR_BASED,
            DetectionMethod.EDGE_DETECTION,
            DetectionMethod.TEXT_DETECTION,
        ]

        for method in methods:
            method_regions = self._detect_with_method(image, method)
            all_regions.extend(method_regions)

        # Merge and deduplicate regions
        merged_regions = self._merge_similar_regions(all_regions)

        return merged_regions

    def _post_process_regions(self, regions: List[TextRegion]) -> List[TextRegion]:
        """Post-process detected regions."""
        if not regions:
            return regions

        # Filter by minimum size
        filtered_regions = [r for r in regions if r.area >= self.config.min_region_size]

        # Merge overlapping regions if enabled
        if self.config.merge_overlapping:
            filtered_regions = self._merge_overlapping_regions(filtered_regions)

        # Sort by confidence and limit count
        filtered_regions.sort(key=lambda r: r.confidence, reverse=True)
        filtered_regions = filtered_regions[: self.config.max_regions]

        return filtered_regions

    def _merge_overlapping_regions(self, regions: List[TextRegion]) -> List[TextRegion]:
        """Merge overlapping regions."""
        if len(regions) <= 1:
            return regions

        merged = []
        used = set()

        for i, region1 in enumerate(regions):
            if i in used:
                continue

            merged_region = region1
            merged_with = [i]

            for j, region2 in enumerate(regions[i + 1 :], i + 1):
                if j in used:
                    continue

                if region1.overlaps_with(region2, self.config.overlap_threshold):
                    # Merge regions
                    x1 = min(merged_region.x, region2.x)
                    y1 = min(merged_region.y, region2.y)
                    x2 = max(merged_region.x + merged_region.width, region2.x + region2.width)
                    y2 = max(merged_region.y + merged_region.height, region2.y + region2.height)

                    merged_region = TextRegion(
                        x=x1,
                        y=y1,
                        width=x2 - x1,
                        height=y2 - y1,
                        confidence=max(merged_region.confidence, region2.confidence),
                        text_density=(merged_region.text_density + region2.text_density) / 2,
                        method_used=DetectionMethod.HYBRID,
                    )
                    merged_with.append(j)

            for idx in merged_with:
                used.add(idx)

            merged.append(merged_region)

        return merged

    def _merge_similar_regions(self, regions: List[TextRegion]) -> List[TextRegion]:
        """Merge similar regions from different detection methods."""
        if len(regions) <= 1:
            return regions

        # Group similar regions
        groups = []
        used = set()

        for i, region1 in enumerate(regions):
            if i in used:
                continue

            group = [region1]
            used.add(i)

            for j, region2 in enumerate(regions[i + 1 :], i + 1):
                if j in used:
                    continue

                # Check if regions are similar (overlapping or very close)
                if self._are_regions_similar(region1, region2):
                    group.append(region2)
                    used.add(j)

            groups.append(group)

        # Merge each group into single region
        merged_regions = []
        for group in groups:
            if len(group) == 1:
                merged_regions.append(group[0])
            else:
                # Create merged region from group
                min_x = min(r.x for r in group)
                min_y = min(r.y for r in group)
                max_x = max(r.x + r.width for r in group)
                max_y = max(r.y + r.height for r in group)

                avg_confidence = sum(r.confidence for r in group) / len(group)
                avg_text_density = sum(r.text_density for r in group) / len(group)

                merged_region = TextRegion(
                    x=min_x,
                    y=min_y,
                    width=max_x - min_x,
                    height=max_y - min_y,
                    confidence=avg_confidence,
                    text_density=avg_text_density,
                    method_used=DetectionMethod.HYBRID,
                )
                merged_regions.append(merged_region)

        return merged_regions

    def _are_regions_similar(
        self, region1: TextRegion, region2: TextRegion, threshold: float = 0.2
    ) -> bool:
        """Check if two regions are similar enough to merge."""
        # Calculate overlap
        if region1.overlaps_with(region2, threshold):
            return True

        # Calculate distance between centers
        center1_x = region1.x + region1.width // 2
        center1_y = region1.y + region1.height // 2
        center2_x = region2.x + region2.width // 2
        center2_y = region2.y + region2.height // 2

        distance = np.sqrt((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2)
        max_dimension = max(region1.width, region1.height, region2.width, region2.height)

        # Regions are similar if they're close and similar size
        return distance < max_dimension * 0.5

    def _generate_cache_key(self, image: np.ndarray) -> str:
        """Generate cache key for image."""
        # Use image hash for caching (SHA256 is more secure than MD5)
        import hashlib

        image_bytes = image.tobytes()
        return hashlib.sha256(image_bytes, usedforsecurity=False).hexdigest()[:16]

    def _cleanup_cache(self) -> None:
        """Clean up old cache entries."""
        current_time = time.time()
        expired_keys = []

        for key, timestamp in self.cache_timestamps.items():
            if current_time - timestamp > self.cache_max_age:
                expired_keys.append(key)

        for key in expired_keys:
            del self.detection_cache[key]
            del self.cache_timestamps[key]

    def get_best_region(self, regions: List[TextRegion]) -> Optional[TextRegion]:
        """Get the best text region based on confidence and size."""
        if not regions:
            return None

        # Score regions based on confidence, size, and text density
        def score_region(region: TextRegion) -> float:
            size_score = min(region.area / 10000, 1.0)  # Normalize by reasonable text area
            return region.confidence * 0.5 + size_score * 0.3 + region.text_density * 0.2

        return max(regions, key=score_region)

    def filter_regions_by_size(
        self, regions: List[TextRegion], min_area: int, max_area: Optional[int] = None
    ) -> List[TextRegion]:
        """Filter regions by area size."""
        filtered = [r for r in regions if r.area >= min_area]
        if max_area:
            filtered = [r for r in filtered if r.area <= max_area]
        return filtered

    def get_detection_stats(self) -> Dict[str, Any]:
        """Get detection performance statistics."""
        avg_time = (
            sum(self.detection_times) / len(self.detection_times) if self.detection_times else 0
        )

        return {
            "total_detections": len(self.detection_times),
            "average_time_seconds": avg_time,
            "method_usage": dict(self.detection_counts),
            "cache_size": len(self.detection_cache),
            "config": {
                "primary_method": self.config.primary_method.value,
                "min_region_size": self.config.min_region_size,
                "max_regions": self.config.max_regions,
            },
        }

    def clear_cache(self) -> None:
        """Clear detection cache."""
        self.detection_cache.clear()
        self.cache_timestamps.clear()
        logger.info("Detection cache cleared")

    def update_config(self, config: DetectionConfig) -> None:
        """Update detection configuration."""
        self.config = config
        self.clear_cache()  # Clear cache as detection parameters changed
        logger.info("Detection configuration updated")

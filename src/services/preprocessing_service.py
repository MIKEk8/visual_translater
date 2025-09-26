"""
Preprocessing Service for image preparation and enhancement.

This service handles image preprocessing tasks such as denoising,
contrast adjustment, and OCR optimization.
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum

from src.utils.logger import logger


class PreprocessingMethod(Enum):
    """Available preprocessing methods."""
    DENOISE = "denoise"
    SHARPEN = "sharpen"
    CONTRAST = "contrast"
    BRIGHTNESS = "brightness"
    THRESHOLD = "threshold"
    GAUSSIAN_BLUR = "gaussian_blur"
    HISTOGRAM_EQ = "histogram_eq"


@dataclass
class PreprocessingConfig:
    """Configuration for image preprocessing."""

    methods: List[PreprocessingMethod]
    denoise_strength: float = 0.1
    sharpen_strength: float = 0.5
    contrast_factor: float = 1.0
    brightness_offset: int = 0
    threshold_value: int = 128
    blur_kernel_size: int = 3
    apply_histogram_eq: bool = False


class PreprocessingService:
    """Service for preprocessing images before OCR."""

    def __init__(self):
        """Initialize the preprocessing service."""
        self.default_config = PreprocessingConfig(
            methods=[PreprocessingMethod.CONTRAST, PreprocessingMethod.DENOISE]
        )
        logger.debug("PreprocessingService initialized")

    def preprocess_image(
        self,
        image: Union[np.ndarray, bytes],
        config: Optional[PreprocessingConfig] = None
    ) -> np.ndarray:
        """Preprocess an image for better OCR results.

        Args:
            image: Input image as numpy array or bytes
            config: Preprocessing configuration

        Returns:
            Preprocessed image as numpy array
        """
        if config is None:
            config = self.default_config

        try:
            # Convert bytes to numpy array if needed
            if isinstance(image, bytes):
                nparr = np.frombuffer(image, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            else:
                img = image.copy()

            # Apply preprocessing methods in order
            for method in config.methods:
                img = self._apply_method(img, method, config)

            logger.debug(f"Applied {len(config.methods)} preprocessing methods")
            return img

        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            # Return original image if preprocessing fails
            if isinstance(image, bytes):
                nparr = np.frombuffer(image, np.uint8)
                return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return image

    def _apply_method(
        self,
        image: np.ndarray,
        method: PreprocessingMethod,
        config: PreprocessingConfig
    ) -> np.ndarray:
        """Apply a specific preprocessing method."""
        try:
            if method == PreprocessingMethod.DENOISE:
                return cv2.fastNlMeansDenoising(
                    image, None, config.denoise_strength * 30, 7, 21
                )

            elif method == PreprocessingMethod.SHARPEN:
                kernel = np.array([[-1,-1,-1],
                                 [-1, 9,-1],
                                 [-1,-1,-1]]) * config.sharpen_strength
                return cv2.filter2D(image, -1, kernel)

            elif method == PreprocessingMethod.CONTRAST:
                return cv2.convertScaleAbs(image, alpha=config.contrast_factor, beta=0)

            elif method == PreprocessingMethod.BRIGHTNESS:
                return cv2.convertScaleAbs(image, alpha=1.0, beta=config.brightness_offset)

            elif method == PreprocessingMethod.THRESHOLD:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, config.threshold_value, 255, cv2.THRESH_BINARY)
                return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)

            elif method == PreprocessingMethod.GAUSSIAN_BLUR:
                kernel_size = config.blur_kernel_size
                if kernel_size % 2 == 0:  # Ensure odd kernel size
                    kernel_size += 1
                return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)

            elif method == PreprocessingMethod.HISTOGRAM_EQ:
                if len(image.shape) == 3:
                    # Convert to LAB color space for better histogram equalization
                    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
                    lab[:, :, 0] = cv2.equalizeHist(lab[:, :, 0])
                    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
                else:
                    return cv2.equalizeHist(image)

            else:
                logger.warning(f"Unknown preprocessing method: {method}")
                return image

        except Exception as e:
            logger.error(f"Failed to apply {method}: {e}")
            return image

    def create_config(
        self,
        methods: Optional[List[str]] = None,
        **kwargs
    ) -> PreprocessingConfig:
        """Create a preprocessing configuration.

        Args:
            methods: List of method names as strings
            **kwargs: Additional configuration parameters

        Returns:
            PreprocessingConfig object
        """
        if methods is None:
            methods = ["contrast", "denoise"]

        # Convert string method names to enum values
        method_enums = []
        for method_name in methods:
            try:
                method_enum = PreprocessingMethod(method_name.lower())
                method_enums.append(method_enum)
            except ValueError:
                logger.warning(f"Unknown preprocessing method: {method_name}")

        return PreprocessingConfig(
            methods=method_enums,
            **kwargs
        )

    def get_available_methods(self) -> List[str]:
        """Get list of available preprocessing methods."""
        return [method.value for method in PreprocessingMethod]

    def get_default_config(self) -> PreprocessingConfig:
        """Get the default preprocessing configuration."""
        return self.default_config

    def validate_image(self, image: Union[np.ndarray, bytes]) -> bool:
        """Validate that the input is a valid image."""
        try:
            if isinstance(image, bytes):
                nparr = np.frombuffer(image, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                return img is not None
            elif isinstance(image, np.ndarray):
                return len(image.shape) >= 2  # At least 2D array
            else:
                return False
        except Exception:
            return False
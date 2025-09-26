"""
Image Preprocessing Pipeline for improving OCR accuracy.

This module provides a comprehensive image preprocessing pipeline using OpenCV
to enhance image quality before OCR processing.
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import asyncio

from PIL import Image
from src.services.circuit_breaker import get_circuit_breaker_manager
from src.utils.logger import logger


class PreprocessingStep(Enum):
    """Available preprocessing steps."""
    CONVERT_TO_GRAYSCALE = "convert_to_grayscale"
    DENOISE = "denoise"
    ENHANCE_CONTRAST = "enhance_contrast"
    BINARIZE = "binarize"
    DESKEW = "deskew"
    REMOVE_NOISE = "remove_noise"
    RESIZE = "resize"
    SHARPEN = "sharpen"


@dataclass
class ImageQualityMetrics:
    """Metrics for assessing image quality after preprocessing."""

    sharpness_score: float = 0.0
    contrast_score: float = 0.0
    brightness_score: float = 0.0
    noise_level: float = 0.0
    text_clarity: float = 0.0
    overall_score: float = 0.0


@dataclass
class PreprocessingConfig:
    """Configuration for image preprocessing pipeline."""

    # Enabled steps
    enabled_steps: List[PreprocessingStep] = field(default_factory=lambda: [
        PreprocessingStep.CONVERT_TO_GRAYSCALE,
        PreprocessingStep.DENOISE,
        PreprocessingStep.ENHANCE_CONTRAST,
        PreprocessingStep.BINARIZE
    ])

    # Step-specific parameters
    denoise_strength: int = 3  # 1-10
    contrast_alpha: float = 1.2  # 1.0-3.0
    contrast_beta: int = 10  # 0-100
    binary_threshold: int = 0  # 0 for automatic
    binary_method: str = "otsu"  # "otsu", "adaptive"
    resize_factor: float = 2.0  # Scale factor for upsampling
    sharpen_strength: float = 1.0  # 0.5-2.0

    # Performance settings
    max_image_size: Tuple[int, int] = (2048, 2048)
    preserve_aspect_ratio: bool = True

    def is_enabled(self, step: PreprocessingStep) -> bool:
        """Check if a preprocessing step is enabled."""
        return step in self.enabled_steps

    def is_enabled_by_name(self, step_name: str) -> bool:
        """Check if a preprocessing step is enabled by name."""
        try:
            step = PreprocessingStep(step_name)
            return step in self.enabled_steps
        except ValueError:
            return False


class ImagePreprocessor:
    """Image preprocessing pipeline for OCR enhancement."""

    def __init__(self, config: Optional[PreprocessingConfig] = None):
        """Initialize the image preprocessor.

        Args:
            config: Optional preprocessing configuration
        """
        self.config = config or PreprocessingConfig()
        self.circuit_breaker = get_circuit_breaker_manager().create_circuit_breaker("image_preprocessing")

        # Initialize step functions mapping
        self.pipeline_steps: Dict[PreprocessingStep, Callable] = {
            PreprocessingStep.CONVERT_TO_GRAYSCALE: self.convert_to_grayscale,
            PreprocessingStep.DENOISE: self.denoise,
            PreprocessingStep.ENHANCE_CONTRAST: self.enhance_contrast,
            PreprocessingStep.BINARIZE: self.binarize,
            PreprocessingStep.DESKEW: self.deskew,
            PreprocessingStep.REMOVE_NOISE: self.remove_noise,
            PreprocessingStep.RESIZE: self.resize,
            PreprocessingStep.SHARPEN: self.sharpen,
        }

        # Performance metrics
        self.processing_times: Dict[str, List[float]] = {}

        logger.info(f"ImagePreprocessor initialized with {len(self.config.enabled_steps)} enabled steps")

    async def preprocess(self, image: Image.Image, config: Optional[PreprocessingConfig] = None) -> Image.Image:
        """Preprocess an image through the configured pipeline.

        Args:
            image: Input PIL Image
            config: Optional configuration override

        Returns:
            Preprocessed PIL Image

        Raises:
            ValueError: If image is invalid
            RuntimeError: If preprocessing fails
        """
        if image is None:
            raise ValueError("Input image cannot be None")

        config = config or self.config
        start_time = asyncio.get_event_loop().time()

        try:
            # Convert PIL to OpenCV format
            processed = await self._pil_to_opencv(image)

            # Apply enabled preprocessing steps
            for step in config.enabled_steps:
                if step in self.pipeline_steps:
                    step_start = asyncio.get_event_loop().time()

                    processed = await self.circuit_breaker.call(
                        self.pipeline_steps[step],
                        processed,
                        config
                    )

                    step_time = asyncio.get_event_loop().time() - step_start
                    self._record_step_time(step.value, step_time)

                    logger.debug(f"Applied {step.value} in {step_time:.3f}s")
                else:
                    logger.warning(f"Unknown preprocessing step: {step}")

            # Convert back to PIL
            result_image = await self._opencv_to_pil(processed)

            total_time = asyncio.get_event_loop().time() - start_time
            logger.debug(f"Image preprocessing completed in {total_time:.3f}s")

            return result_image

        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            # Return original image on failure
            return image

    async def preprocess_batch(
        self,
        images: List[Image.Image],
        config: Optional[PreprocessingConfig] = None
    ) -> List[Image.Image]:
        """Preprocess a batch of images concurrently.

        Args:
            images: List of PIL Images
            config: Optional configuration override

        Returns:
            List of preprocessed PIL Images
        """
        if not images:
            return []

        logger.info(f"Processing batch of {len(images)} images")

        # Process images concurrently
        tasks = [self.preprocess(image, config) for image in images]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle results and exceptions
        processed_images = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process image {i}: {result}")
                processed_images.append(images[i])  # Return original on error
            else:
                processed_images.append(result)

        return processed_images

    async def convert_to_grayscale(self, image: np.ndarray, config: PreprocessingConfig) -> np.ndarray:
        """Convert image to grayscale."""
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image

    async def denoise(self, image: np.ndarray, config: PreprocessingConfig) -> np.ndarray:
        """Apply denoising to reduce image noise."""
        if len(image.shape) == 3:
            # Color image denoising
            return cv2.fastNlMeansDenoisingColored(
                image, None, config.denoise_strength, config.denoise_strength, 7, 21
            )
        else:
            # Grayscale denoising
            return cv2.fastNlMeansDenoising(
                image, None, config.denoise_strength, 7, 21
            )

    async def enhance_contrast(self, image: np.ndarray, config: PreprocessingConfig) -> np.ndarray:
        """Enhance image contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
        if len(image.shape) == 3:
            # Convert to LAB color space for better contrast enhancement
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)

            # Apply CLAHE to L channel
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced_l = clahe.apply(l_channel)

            # Merge channels back
            enhanced_lab = cv2.merge([enhanced_l, a_channel, b_channel])
            return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        else:
            # Grayscale CLAHE
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(image)

    async def binarize(self, image: np.ndarray, config: PreprocessingConfig) -> np.ndarray:
        """Convert image to binary (black and white)."""
        # Ensure grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        if config.binary_method == "otsu":
            # Otsu's thresholding
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif config.binary_method == "adaptive":
            # Adaptive thresholding
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
        else:
            # Manual threshold
            threshold = config.binary_threshold if config.binary_threshold > 0 else 127
            _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)

        return binary

    async def deskew(self, image: np.ndarray, config: PreprocessingConfig) -> np.ndarray:
        """Correct skewed text by detecting and rotating the image."""
        try:
            # Ensure grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            # Create binary image for line detection
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            # Detect lines using HoughLines
            lines = cv2.HoughLines(binary, 1, np.pi / 180, threshold=100)

            if lines is not None and len(lines) > 0:
                # Calculate average angle
                angles = []
                for line in lines[:20]:  # Use first 20 lines
                    rho, theta = line[0]
                    angle = (theta - np.pi / 2) * 180 / np.pi
                    angles.append(angle)

                # Get median angle to avoid outliers
                median_angle = np.median(angles)

                # Only rotate if angle is significant
                if abs(median_angle) > 0.5:
                    height, width = image.shape[:2]
                    rotation_matrix = cv2.getRotationMatrix2D((width / 2, height / 2), median_angle, 1)
                    return cv2.warpAffine(image, rotation_matrix, (width, height), flags=cv2.INTER_CUBIC)

            return image

        except Exception as e:
            logger.debug(f"Deskewing failed: {e}")
            return image

    async def remove_noise(self, image: np.ndarray, config: PreprocessingConfig) -> np.ndarray:
        """Remove small noise artifacts using morphological operations."""
        # Use morphological opening to remove small noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

        if len(image.shape) == 3:
            # Apply to each channel
            result = np.zeros_like(image)
            for i in range(image.shape[2]):
                result[:, :, i] = cv2.morphologyEx(image[:, :, i], cv2.MORPH_OPENING, kernel)
            return result
        else:
            return cv2.morphologyEx(image, cv2.MORPH_OPENING, kernel)

    async def resize(self, image: np.ndarray, config: PreprocessingConfig) -> np.ndarray:
        """Resize image to improve OCR accuracy."""
        height, width = image.shape[:2]

        # Check if resize is needed
        max_height, max_width = config.max_image_size

        if width <= max_width and height <= max_height:
            # Upscale small images
            if width < 300 or height < 300:
                scale_factor = config.resize_factor
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)

                return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)

        else:
            # Downscale large images
            if config.preserve_aspect_ratio:
                scale = min(max_width / width, max_height / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
            else:
                new_width = max_width
                new_height = max_height

            return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)

        return image

    async def sharpen(self, image: np.ndarray, config: PreprocessingConfig) -> np.ndarray:
        """Apply sharpening filter to enhance text edges."""
        # Create sharpening kernel
        strength = config.sharpen_strength
        kernel = np.array([
            [-1, -1, -1],
            [-1, 8 + strength, -1],
            [-1, -1, -1]
        ])

        return cv2.filter2D(image, -1, kernel)

    async def _pil_to_opencv(self, pil_image: Image.Image) -> np.ndarray:
        """Convert PIL Image to OpenCV format."""
        # Convert to RGB if necessary
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')

        # Convert to numpy array
        numpy_image = np.array(pil_image)

        # Convert RGB to BGR (OpenCV format)
        return cv2.cvtColor(numpy_image, cv2.COLOR_RGB2BGR)

    async def _opencv_to_pil(self, opencv_image: np.ndarray) -> Image.Image:
        """Convert OpenCV format to PIL Image."""
        if len(opencv_image.shape) == 3:
            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2RGB)
        else:
            # Grayscale
            rgb_image = opencv_image

        return Image.fromarray(rgb_image)

    def _record_step_time(self, step_name: str, time_taken: float) -> None:
        """Record processing time for a step."""
        if step_name not in self.processing_times:
            self.processing_times[step_name] = []

        self.processing_times[step_name].append(time_taken)

        # Keep only last 100 measurements
        if len(self.processing_times[step_name]) > 100:
            self.processing_times[step_name].pop(0)

    def get_performance_stats(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics for preprocessing steps."""
        stats = {}

        for step_name, times in self.processing_times.items():
            if times:
                stats[step_name] = {
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "total_runs": len(times)
                }

        return stats

    async def test_preprocessing_quality(
        self,
        image: Image.Image,
        configs: List[PreprocessingConfig]
    ) -> Dict[str, Any]:
        """Test different preprocessing configurations and return quality metrics.

        Args:
            image: Test image
            configs: List of configurations to test

        Returns:
            Dictionary with quality metrics for each configuration
        """
        results = {}

        for i, config in enumerate(configs):
            config_name = f"config_{i}"

            try:
                start_time = asyncio.get_event_loop().time()
                processed_image = await self.preprocess(image, config)
                processing_time = asyncio.get_event_loop().time() - start_time

                # Calculate basic quality metrics
                opencv_processed = await self._pil_to_opencv(processed_image)
                opencv_original = await self._pil_to_opencv(image)

                # Sharpness metric (Laplacian variance)
                if len(opencv_processed.shape) == 3:
                    gray_processed = cv2.cvtColor(opencv_processed, cv2.COLOR_BGR2GRAY)
                    gray_original = cv2.cvtColor(opencv_original, cv2.COLOR_BGR2GRAY)
                else:
                    gray_processed = opencv_processed
                    gray_original = opencv_original

                sharpness_processed = cv2.Laplacian(gray_processed, cv2.CV_64F).var()
                sharpness_original = cv2.Laplacian(gray_original, cv2.CV_64F).var()

                results[config_name] = {
                    "processing_time": processing_time,
                    "sharpness_score": sharpness_processed,
                    "sharpness_improvement": sharpness_processed / max(sharpness_original, 1),
                    "enabled_steps": [step.value for step in config.enabled_steps],
                    "image_size": processed_image.size
                }

            except Exception as e:
                results[config_name] = {
                    "error": str(e),
                    "processing_time": 0,
                    "sharpness_score": 0,
                    "enabled_steps": [step.value for step in config.enabled_steps]
                }

        return results

    def create_optimized_config(self, image_type: str = "text") -> PreprocessingConfig:
        """Create an optimized configuration for specific image types.

        Args:
            image_type: Type of image ("text", "screenshot", "document", "photo")

        Returns:
            Optimized PreprocessingConfig
        """
        if image_type == "text":
            return PreprocessingConfig(
                enabled_steps=[
                    PreprocessingStep.CONVERT_TO_GRAYSCALE,
                    PreprocessingStep.DENOISE,
                    PreprocessingStep.ENHANCE_CONTRAST,
                    PreprocessingStep.BINARIZE,
                    PreprocessingStep.SHARPEN
                ],
                denoise_strength=2,
                contrast_alpha=1.3,
                binary_method="otsu",
                sharpen_strength=0.8
            )

        elif image_type == "screenshot":
            return PreprocessingConfig(
                enabled_steps=[
                    PreprocessingStep.RESIZE,
                    PreprocessingStep.ENHANCE_CONTRAST,
                    PreprocessingStep.SHARPEN
                ],
                resize_factor=1.5,
                contrast_alpha=1.1,
                sharpen_strength=0.6
            )

        elif image_type == "document":
            return PreprocessingConfig(
                enabled_steps=[
                    PreprocessingStep.CONVERT_TO_GRAYSCALE,
                    PreprocessingStep.DESKEW,
                    PreprocessingStep.ENHANCE_CONTRAST,
                    PreprocessingStep.BINARIZE,
                    PreprocessingStep.REMOVE_NOISE
                ],
                binary_method="adaptive",
                contrast_alpha=1.4
            )

        else:
            # Default for photos and other types
            return PreprocessingConfig(
                enabled_steps=[
                    PreprocessingStep.DENOISE,
                    PreprocessingStep.ENHANCE_CONTRAST,
                    PreprocessingStep.RESIZE
                ],
                denoise_strength=3,
                resize_factor=1.2
            )
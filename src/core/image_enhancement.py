"""Image enhancement module for AI OCR engine.

Separated from the original God Class for better maintainability.
"""

try:
    import cv2
except ImportError:
    print("OpenCV не доступен в данной среде")
    cv2 = None
import numpy as np
from PIL import Image

from src.utils.logger import logger


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
        """Automatically detect the best enhancement level for the image."""
        if cv2 is None:
            return "light"

        try:
            # Convert to grayscale for analysis
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            # Calculate image quality metrics
            # 1. Variance (sharpness indicator)
            variance = cv2.Laplacian(gray, cv2.CV_64F).var()

            # 2. Mean brightness
            mean_brightness = np.mean(gray)

            # 3. Contrast (standard deviation)
            contrast = np.std(gray)

            # Determine enhancement level based on metrics
            if variance < 100 and contrast < 30:
                return "aggressive"  # Very blurry/low contrast
            elif variance < 300 or contrast < 50:
                return "moderate"   # Somewhat blurry/low contrast
            else:
                return "light"      # Good quality

        except Exception as e:
            logger.warning(f"Enhancement level detection failed: {e}")
            return "moderate"

    def _apply_super_resolution(self, image: np.ndarray) -> np.ndarray:
        """Apply super-resolution to increase image resolution."""
        if cv2 is None:
            return image

        try:
            # Simple upscaling with bicubic interpolation
            # In a real implementation, you might use deep learning models like ESRGAN
            height, width = image.shape[:2]

            # Only upscale if image is small
            if width < 400 or height < 400:
                scale_factor = 2
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)

                upscaled = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)

                # Apply sharpening after upscaling
                kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
                sharpened = cv2.filter2D(upscaled, -1, kernel)

                return sharpened

            return image

        except Exception as e:
            logger.warning(f"Super-resolution failed: {e}")
            return image

    def _apply_adaptive_enhancement(self, image: np.ndarray) -> np.ndarray:
        """Apply adaptive enhancement based on local image properties."""
        if cv2 is None:
            return image

        try:
            if len(image.shape) == 3:
                # Convert to LAB color space for better enhancement
                lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)

                # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to L channel
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                l = clahe.apply(l)

                # Merge channels and convert back
                enhanced = cv2.merge([l, a, b])
                enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
            else:
                # Grayscale image
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(image)

            return enhanced

        except Exception as e:
            logger.warning(f"Adaptive enhancement failed: {e}")
            return image

    def _apply_denoising(self, image: np.ndarray, strength: str = "moderate") -> np.ndarray:
        """Apply denoising based on the specified strength."""
        if cv2 is None:
            return image

        try:
            strength_map = {
                "light": (3, 3, 7, 21),
                "moderate": (5, 5, 7, 21),
                "aggressive": (10, 10, 7, 21)
            }

            h, h_color, template_window, search_window = strength_map.get(strength, strength_map["moderate"])

            if len(image.shape) == 3:
                # Color image denoising
                denoised = cv2.fastNlMeansDenoisingColored(
                    image, None, h, h_color, template_window, search_window
                )
            else:
                # Grayscale image denoising
                denoised = cv2.fastNlMeansDenoising(
                    image, None, h, template_window, search_window
                )

            return denoised

        except Exception as e:
            logger.warning(f"Denoising failed: {e}")
            return image

    def _apply_deskewing(self, image: np.ndarray) -> np.ndarray:
        """Detect and correct skew in the image."""
        if cv2 is None:
            return image

        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            # Apply binary threshold
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            # Detect lines using HoughLines
            edges = cv2.Canny(binary, 50, 150, apertureSize=3)
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)

            if lines is not None:
                # Calculate angles
                angles = []
                for rho, theta in lines[:20]:  # Use first 20 lines
                    angle = theta * 180 / np.pi
                    # Convert to angle relative to horizontal
                    if angle > 90:
                        angle = angle - 180
                    angles.append(angle)

                # Find median angle (more robust than mean)
                if angles:
                    median_angle = np.median(angles)

                    # Only correct if skew is significant (> 0.5 degrees)
                    if abs(median_angle) > 0.5:
                        # Rotate image to correct skew
                        height, width = image.shape[:2]
                        center = (width // 2, height // 2)
                        rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)

                        # Calculate new image size to prevent cropping
                        cos_angle = abs(rotation_matrix[0, 0])
                        sin_angle = abs(rotation_matrix[0, 1])
                        new_width = int((height * sin_angle) + (width * cos_angle))
                        new_height = int((height * cos_angle) + (width * sin_angle))

                        # Adjust translation
                        rotation_matrix[0, 2] += (new_width - width) / 2
                        rotation_matrix[1, 2] += (new_height - height) / 2

                        # Apply rotation
                        deskewed = cv2.warpAffine(image, rotation_matrix, (new_width, new_height),
                                                flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

                        logger.debug(f"Corrected skew angle: {median_angle:.2f} degrees")
                        return deskewed

            return image

        except Exception as e:
            logger.warning(f"Deskewing failed: {e}")
            return image

    def _apply_contrast_optimization(self, image: np.ndarray) -> np.ndarray:
        """Optimize contrast for better text recognition."""
        if cv2 is None:
            return image

        try:
            if len(image.shape) == 3:
                # Convert to YUV color space
                yuv = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
                y, u, v = cv2.split(yuv)

                # Apply histogram equalization to Y channel
                y_eq = cv2.equalizeHist(y)

                # Apply gamma correction for mid-tone enhancement
                gamma = 1.2
                y_gamma = np.power(y_eq / 255.0, gamma) * 255.0
                y_gamma = np.clip(y_gamma, 0, 255).astype(np.uint8)

                # Merge channels and convert back
                yuv_enhanced = cv2.merge([y_gamma, u, v])
                enhanced = cv2.cvtColor(yuv_enhanced, cv2.COLOR_YUV2BGR)
            else:
                # Grayscale image
                eq = cv2.equalizeHist(image)

                # Apply gamma correction
                gamma = 1.2
                enhanced = np.power(eq / 255.0, gamma) * 255.0
                enhanced = np.clip(enhanced, 0, 255).astype(np.uint8)

            return enhanced

        except Exception as e:
            logger.warning(f"Contrast optimization failed: {e}")
            return image
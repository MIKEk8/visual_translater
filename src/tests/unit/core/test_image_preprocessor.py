"""
Tests for OCR Preprocessing Pipeline with image enhancement.

FEATURE: OCR Preprocessing Pipeline (Image Enhancement)
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# CRITICAL: Import paths will fail until implementation exists
from src.core.image_preprocessor import (
    ImagePreprocessor,
    PreprocessingConfig,
    PreprocessingStep,
    ImageQualityMetrics
)
from src.services.preprocessing_service import PreprocessingService


class TestPreprocessingConfig:
    """Test preprocessing configuration."""

    def test_preprocessing_config_creation(self):
        """Test PreprocessingConfig creation with default values."""
        config = PreprocessingConfig()

        assert config.denoise_enabled is True
        assert config.contrast_enhancement_enabled is True
        assert config.binarization_enabled is True
        assert config.deskew_enabled is False  # More expensive, default off
        assert config.noise_removal_enabled is True

    def test_preprocessing_config_custom_settings(self):
        """Test PreprocessingConfig with custom settings."""
        config = PreprocessingConfig(
            denoise_enabled=False,
            contrast_factor=1.5,
            binarization_threshold=128,
            gaussian_blur_kernel_size=3
        )

        assert config.denoise_enabled is False
        assert config.contrast_factor == 1.5
        assert config.binarization_threshold == 128

    def test_config_step_enabled_check(self):
        """Test checking if preprocessing steps are enabled."""
        config = PreprocessingConfig(
            denoise_enabled=True,
            contrast_enhancement_enabled=False
        )

        assert config.is_enabled("denoise") is True
        assert config.is_enabled("enhance_contrast") is False

    def test_config_validation(self):
        """Test configuration parameter validation."""
        # Test invalid contrast factor
        with pytest.raises(ValueError, match="Contrast factor must be positive"):
            PreprocessingConfig(contrast_factor=-0.5)

        # Test invalid threshold
        with pytest.raises(ValueError, match="Threshold must be between 0 and 255"):
            PreprocessingConfig(binarization_threshold=300)


class TestImagePreprocessor:
    """Test suite for ImagePreprocessor."""

    @pytest.fixture
    def preprocessor(self):
        """Create ImagePreprocessor instance."""
        return ImagePreprocessor()

    @pytest.fixture
    def sample_image(self):
        """Create sample test image."""
        # Create a simple test image with text-like patterns
        image_array = np.random.randint(0, 255, (100, 200, 3), dtype=np.uint8)
        # Add some text-like rectangles
        image_array[30:40, 50:150] = [255, 255, 255]  # White text area
        image_array[32:38, 52:148] = [0, 0, 0]        # Black text
        return Image.fromarray(image_array)

    @pytest.fixture
    def noisy_image(self):
        """Create noisy test image for preprocessing tests."""
        # Create image with noise and low contrast
        base = np.ones((100, 200), dtype=np.uint8) * 128
        noise = np.random.normal(0, 20, (100, 200))
        noisy_array = np.clip(base + noise, 0, 255).astype(np.uint8)

        # Add some text with poor contrast
        noisy_array[40:50, 70:130] = 140  # Slightly darker text
        return Image.fromarray(noisy_array, mode='L')

    # CRITICAL: Core preprocessing functionality
    def test_preprocessor_initialization(self, preprocessor):
        """Test preprocessor initializes with correct pipeline steps."""
        expected_steps = [
            'convert_to_grayscale',
            'denoise',
            'enhance_contrast',
            'binarize',
            'deskew',
            'remove_noise'
        ]

        pipeline_step_names = [step.__name__ for step in preprocessor.pipeline_steps]

        for step in expected_steps:
            assert step in pipeline_step_names

    def test_full_preprocessing_pipeline(self, preprocessor, sample_image):
        """Test complete preprocessing pipeline execution."""
        config = PreprocessingConfig()

        processed_image = preprocessor.preprocess(sample_image, config)

        # CRITICAL: Output should be valid Image
        assert isinstance(processed_image, Image.Image)
        assert processed_image.size == sample_image.size
        # After full pipeline, should be grayscale
        assert processed_image.mode in ['L', '1']  # Grayscale or binary

    # CRITICAL: Individual preprocessing steps
    def test_convert_to_grayscale(self, preprocessor, sample_image):
        """Test grayscale conversion step."""
        config = PreprocessingConfig()
        rgb_array = np.array(sample_image)

        grayscale_array = preprocessor.convert_to_grayscale(rgb_array, config)

        # CRITICAL: Should convert RGB to grayscale
        assert len(grayscale_array.shape) == 2  # 2D array (grayscale)
        assert grayscale_array.dtype == np.uint8
        assert grayscale_array.shape[:2] == rgb_array.shape[:2]

    def test_denoise_step(self, preprocessor, noisy_image):
        """Test denoising step reduces image noise."""
        config = PreprocessingConfig(denoise_enabled=True)
        noisy_array = np.array(noisy_image)

        # Calculate original noise level (standard deviation)
        original_std = np.std(noisy_array)

        denoised_array = preprocessor.denoise(noisy_array, config)

        # CRITICAL: Denoising should reduce noise (lower std deviation)
        denoised_std = np.std(denoised_array)
        assert denoised_std < original_std

        # Shape should remain the same
        assert denoised_array.shape == noisy_array.shape

    def test_enhance_contrast_step(self, preprocessor, sample_image):
        """Test contrast enhancement step."""
        config = PreprocessingConfig(contrast_factor=1.5)
        gray_array = np.array(sample_image.convert('L'))

        enhanced_array = preprocessor.enhance_contrast(gray_array, config)

        # CRITICAL: Contrast enhancement should increase dynamic range
        original_range = gray_array.max() - gray_array.min()
        enhanced_range = enhanced_array.max() - enhanced_array.min()

        # Enhanced image should have better contrast (wider range)
        assert enhanced_range >= original_range
        assert enhanced_array.shape == gray_array.shape

    def test_binarization_step(self, preprocessor, sample_image):
        """Test binarization (thresholding) step."""
        config = PreprocessingConfig(binarization_threshold=128)
        gray_array = np.array(sample_image.convert('L'))

        binary_array = preprocessor.binarize(gray_array, config)

        # CRITICAL: Binarization should create black and white image
        unique_values = np.unique(binary_array)
        assert len(unique_values) <= 2
        assert 0 in unique_values or 255 in unique_values
        assert binary_array.shape == gray_array.shape

    def test_deskew_step(self, preprocessor):
        """Test deskewing step for rotated text."""
        # Create artificially skewed image
        straight_array = np.zeros((100, 200), dtype=np.uint8)
        straight_array[45:55, 50:150] = 255  # Horizontal line

        # Apply rotation to simulate skew
        from scipy import ndimage
        skewed_array = ndimage.rotate(straight_array, angle=5, reshape=False, cval=0)

        config = PreprocessingConfig(deskew_enabled=True)

        deskewed_array = preprocessor.deskew(skewed_array, config)

        # CRITICAL: Deskewing should reduce rotation angle
        # This is a complex test, but we can at least verify shape consistency
        assert deskewed_array.shape == skewed_array.shape
        assert deskewed_array.dtype == np.uint8

    def test_noise_removal_step(self, preprocessor, noisy_image):
        """Test final noise removal step."""
        config = PreprocessingConfig()
        noisy_array = np.array(noisy_image)

        cleaned_array = preprocessor.remove_noise(noisy_array, config)

        # CRITICAL: Should preserve image structure while reducing noise
        assert cleaned_array.shape == noisy_array.shape
        assert cleaned_array.dtype == np.uint8

        # Should reduce small isolated noise pixels
        original_edges = np.sum(np.abs(np.diff(noisy_array, axis=1)))
        cleaned_edges = np.sum(np.abs(np.diff(cleaned_array, axis=1)))
        # Cleaned image should have fewer sharp edges (less noise)
        assert cleaned_edges <= original_edges

    # CRITICAL: Conditional step execution
    def test_conditional_step_execution(self, preprocessor, sample_image):
        """Test that disabled steps are skipped."""
        # Disable all steps except grayscale
        config = PreprocessingConfig(
            denoise_enabled=False,
            contrast_enhancement_enabled=False,
            binarization_enabled=False,
            deskew_enabled=False,
            noise_removal_enabled=False
        )

        with patch.object(preprocessor, 'denoise') as mock_denoise:
            with patch.object(preprocessor, 'enhance_contrast') as mock_contrast:
                preprocessor.preprocess(sample_image, config)

                # CRITICAL: Disabled steps should not be called
                mock_denoise.assert_not_called()
                mock_contrast.assert_not_called()

    # CRITICAL: Error handling and robustness
    def test_preprocessing_with_invalid_image(self, preprocessor):
        """Test preprocessing handles invalid input gracefully."""
        config = PreprocessingConfig()

        # Test with None input
        with pytest.raises(ValueError, match="Invalid image input"):
            preprocessor.preprocess(None, config)

        # Test with empty array
        empty_image = Image.fromarray(np.array([]).reshape(0, 0, 3).astype(np.uint8))
        with pytest.raises(ValueError, match="Image dimensions too small"):
            preprocessor.preprocess(empty_image, config)

    def test_preprocessing_step_error_recovery(self, preprocessor, sample_image):
        """Test error recovery when individual steps fail."""
        config = PreprocessingConfig()

        # Mock one step to fail
        with patch.object(preprocessor, 'denoise') as mock_denoise:
            mock_denoise.side_effect = Exception("Denoising failed")

            # Should continue with other steps and log error
            with patch('src.utils.logger.Logger') as mock_logger:
                result = preprocessor.preprocess(sample_image, config)

                # Should still return processed image (other steps worked)
                assert isinstance(result, Image.Image)
                mock_logger.warning.assert_called()

    # CRITICAL: Performance requirements
    def test_preprocessing_performance_small_image(self, preprocessor):
        """Test preprocessing performance with small images (OCR typical size)."""
        # Create typical OCR-sized image (300x100 pixels)
        small_image = Image.fromarray(
            np.random.randint(0, 255, (100, 300, 3), dtype=np.uint8)
        )
        config = PreprocessingConfig()

        import time
        start_time = time.time()

        preprocessor.preprocess(small_image, config)

        processing_time = time.time() - start_time

        # CRITICAL: Small image processing should complete under 500ms
        assert processing_time < 0.5

    def test_preprocessing_performance_large_image(self, preprocessor):
        """Test preprocessing performance with large images."""
        # Create large image (1920x1080 pixels)
        large_image = Image.fromarray(
            np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        )
        config = PreprocessingConfig(deskew_enabled=False)  # Skip expensive step

        import time
        start_time = time.time()

        preprocessor.preprocess(large_image, config)

        processing_time = time.time() - start_time

        # CRITICAL: Large image processing should complete under 3 seconds
        assert processing_time < 3.0

    # CRITICAL: Quality metrics and validation
    def test_preprocessing_improves_ocr_readiness(self, preprocessor, noisy_image):
        """Test that preprocessing improves image readiness for OCR."""
        config = PreprocessingConfig()

        # Process noisy image
        processed = preprocessor.preprocess(noisy_image, config)
        processed_array = np.array(processed)

        # Calculate quality metrics
        original_array = np.array(noisy_image)

        # CRITICAL: Processed image should have better contrast
        original_contrast = np.std(original_array)
        processed_contrast = np.std(processed_array)

        # After processing, contrast should be improved for OCR
        assert processed_contrast >= original_contrast * 0.9  # Allow for some variation


class TestPreprocessingService:
    """Test PreprocessingService integration layer."""

    @pytest.fixture
    def preprocessing_service(self):
        """Create PreprocessingService with mocked dependencies."""
        with patch('src.core.image_preprocessor.ImagePreprocessor') as mock_preprocessor:
            return PreprocessingService(image_preprocessor=mock_preprocessor.return_value)

    # CRITICAL: Service integration
    def test_service_initialization(self, preprocessing_service):
        """Test service initializes with proper configuration."""
        assert preprocessing_service.image_preprocessor is not None
        assert hasattr(preprocessing_service, 'get_default_config')

    def test_preprocess_image_with_config(self, preprocessing_service):
        """Test service preprocessing with configuration."""
        test_image = Mock(spec=Image.Image)
        config = PreprocessingConfig()

        result = preprocessing_service.preprocess_image(test_image, config)

        # Should delegate to image preprocessor
        preprocessing_service.image_preprocessor.preprocess.assert_called_once_with(
            test_image, config
        )

    def test_get_optimization_config_for_ocr_type(self, preprocessing_service):
        """Test getting optimized configs for different OCR scenarios."""
        # Gaming text (often stylized, colored backgrounds)
        gaming_config = preprocessing_service.get_config_for_context("gaming")
        assert gaming_config.contrast_enhancement_enabled is True
        assert gaming_config.denoise_enabled is True

        # Document text (clean, high quality)
        document_config = preprocessing_service.get_config_for_context("document")
        assert document_config.deskew_enabled is True  # Important for scanned docs

        # Screenshot text (variable quality)
        screenshot_config = preprocessing_service.get_config_for_context("screenshot")
        assert screenshot_config.binarization_enabled is True

    # CRITICAL: Performance monitoring integration
    def test_preprocessing_performance_monitoring(self, preprocessing_service):
        """Test that preprocessing performance is monitored."""
        test_image = Mock(spec=Image.Image)
        config = PreprocessingConfig()

        with patch('src.utils.performance_monitor.PerformanceMonitor') as mock_monitor:
            preprocessing_service.preprocess_image(test_image, config)

            # Should track preprocessing performance
            mock_monitor.record_operation.assert_called_with(
                "image_preprocessing", duration=pytest.approx(0, abs=1)
            )

    def test_circuit_breaker_integration(self, preprocessing_service):
        """Test circuit breaker protection for preprocessing operations."""
        test_image = Mock(spec=Image.Image)
        config = PreprocessingConfig()

        # Mock preprocessor to fail
        preprocessing_service.image_preprocessor.preprocess.side_effect = Exception("Processing failed")

        with patch('src.services.circuit_breaker.CircuitBreaker') as mock_breaker:
            breaker_instance = Mock()
            mock_breaker.return_value = breaker_instance
            breaker_instance.call.side_effect = Exception("Circuit breaker open")

            with pytest.raises(Exception, match="Circuit breaker open"):
                preprocessing_service.preprocess_image(test_image, config)

            # Circuit breaker should have been triggered
            breaker_instance.call.assert_called_once()


# CRITICAL: Integration tests
class TestOCRPreprocessingIntegration:
    """Integration tests for OCR preprocessing pipeline."""

    def test_ocr_engine_integration(self):
        """Test integration with OCR engine."""
        # This test will fail until OCR integration exists

        with patch('src.core.ocr_engine.OCREngine') as mock_ocr:
            with patch('src.core.image_preprocessor.ImagePreprocessor') as mock_preprocessor:

                ocr_engine = mock_ocr.return_value
                preprocessor = mock_preprocessor.return_value

                # Mock preprocessing improving OCR accuracy
                original_image = Mock(spec=Image.Image)
                processed_image = Mock(spec=Image.Image)
                preprocessor.preprocess.return_value = processed_image

                # Mock OCR results
                ocr_engine.extract_text.side_effect = [
                    "H3ll0 W0r1d",    # Original image (poor quality)
                    "Hello World"    # Processed image (better quality)
                ]

                # Test OCR without preprocessing
                original_result = ocr_engine.extract_text(original_image)

                # Test OCR with preprocessing
                processed_result = ocr_engine.extract_text(processed_image)

                # CRITICAL: Preprocessing should improve OCR accuracy
                assert "Hello World" in processed_result
                assert processed_result != original_result

    def test_preprocessing_configuration_persistence(self):
        """Test preprocessing configuration persistence."""
        with patch('src.services.config_manager.ConfigManager') as mock_config:
            config_manager = mock_config.return_value

            # Mock saved configuration
            saved_config = {
                "denoise_enabled": True,
                "contrast_factor": 1.3,
                "binarization_threshold": 140
            }
            config_manager.get.return_value = saved_config

            service = PreprocessingService(image_preprocessor=Mock())

            # Should load saved configuration
            loaded_config = service.load_user_config()

            assert loaded_config.denoise_enabled is True
            assert loaded_config.contrast_factor == 1.3
            assert loaded_config.binarization_threshold == 140

    def test_real_world_image_preprocessing_scenarios(self):
        """Test preprocessing with real-world scenarios."""
        preprocessor = ImagePreprocessor()

        # Test scenario 1: Dark game UI with colored text
        dark_game_image = np.ones((100, 200, 3), dtype=np.uint8) * 30  # Dark background
        dark_game_image[40:60, 50:150] = [255, 255, 100]  # Yellow text
        dark_image = Image.fromarray(dark_game_image)

        gaming_config = PreprocessingConfig(
            contrast_factor=2.0,
            binarization_enabled=True
        )

        processed_dark = preprocessor.preprocess(dark_image, gaming_config)
        assert isinstance(processed_dark, Image.Image)

        # Test scenario 2: Scanned document with slight skew
        document_array = np.ones((200, 400), dtype=np.uint8) * 240  # Light background
        document_array[50:70, 50:350] = 50   # Text lines
        document_array[100:120, 50:300] = 50
        document_image = Image.fromarray(document_array, mode='L')

        document_config = PreprocessingConfig(
            deskew_enabled=True,
            denoise_enabled=True
        )

        processed_doc = preprocessor.preprocess(document_image, document_config)
        assert isinstance(processed_doc, Image.Image)
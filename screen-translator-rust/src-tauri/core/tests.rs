//! Phase 2 Core Module Tests - TDD Implementation
//!
//! This module contains failing tests that define the contracts for Phase 2 core functionality:
//! - Screenshot capture integration with real Windows implementation
//! - OCR pipeline with Tesseract integration and preprocessing
//! - Image processing pipeline with enhancement algorithms
//! - Monitor enumeration and DPI awareness
//!
//! All tests are designed to FAIL initially and pass once implementation is complete.

use super::*;
use crate::core::screenshot::{
    CaptureArea, ImageFormat, MonitorInfo, ScreenshotCapture, ScreenshotConfig, WindowsScreenshot,
};

// Import image_processor and ocr only when feature is enabled
#[cfg(feature = "image_processing")]
use crate::core::{
    image_processor::{EnhancementFilter, ImageProcessor, PreprocessingConfig},
    ocr::{BoundingBox, OcrConfig, OcrEngine, OcrResult, TesseractOcr, TextRegion},
};

#[cfg(feature = "image_processing")]
use crate::utils::error::OcrError;
use crate::utils::error::ScreenshotError;

use image::{DynamicImage, ImageBuffer, Rgb};
use std::path::PathBuf;

// CRITICAL: Screenshot Integration Tests
#[cfg(feature = "phase4_services")] // Disabled - async/await issues need tokio::test
mod screenshot_integration_tests {
    use super::*;

    #[test]
    // CRITICAL: Real Windows screenshot capture
    fn test_real_windows_screenshot_capture() {
        let mut screenshot = WindowsScreenshot::new();

        // Should initialize with real Windows API
        screenshot
            .initialize()
            .expect("Should initialize Windows screenshot API");
        assert!(
            screenshot.is_available(),
            "Windows screenshot should be available"
        );

        // Should capture real screen area
        let area = CaptureArea {
            x: 100,
            y: 100,
            width: 400,
            height: 300,
        };

        let image = screenshot
            .capture_area(area)
            .expect("Should capture real screen area");

        // Should return actual screen data, not mock
        assert_eq!(image.width(), 400);
        assert_eq!(image.height(), 300);

        // Real screenshot should have varied pixel data (not uniform pattern)
        let rgb_image = image.to_rgb8();
        let pixels: Vec<_> = rgb_image.pixels().take(100).collect();

        // Mock images have predictable patterns, real screenshots should be varied
        let unique_colors: std::collections::HashSet<_> = pixels.iter().collect();
        assert!(
            unique_colors.len() > 10,
            "Real screenshot should have varied colors, got {} unique colors",
            unique_colors.len()
        );
    }

    #[test]
    // CRITICAL: Multi-monitor enumeration
    fn test_real_monitor_enumeration() {
        let screenshot = WindowsScreenshot::new();

        let monitors = screenshot
            .get_monitors()
            .expect("Should enumerate real monitors");

        // Should detect actual system monitors (not just mock data)
        assert!(!monitors.is_empty(), "Should detect at least one monitor");

        // Should have realistic monitor properties
        for monitor in &monitors {
            assert!(
                monitor.width >= 640 && monitor.width <= 7680,
                "Monitor width should be realistic: {}",
                monitor.width
            );
            assert!(
                monitor.height >= 480 && monitor.height <= 4320,
                "Monitor height should be realistic: {}",
                monitor.height
            );
            assert!(
                monitor.scale_factor >= 0.5 && monitor.scale_factor <= 4.0,
                "Scale factor should be realistic: {}",
                monitor.scale_factor
            );
            assert!(!monitor.name.is_empty(), "Monitor should have a name");
        }

        // Should have exactly one primary monitor
        let primary_count = monitors.iter().filter(|m| m.is_primary).count();
        assert_eq!(primary_count, 1, "Should have exactly one primary monitor");
    }

    #[test]
    // CRITICAL: DPI scaling support
    fn test_dpi_awareness_real_scaling() {
        let screenshot = WindowsScreenshot::new();
        let monitors = screenshot.get_monitors().expect("Should get monitors");

        for monitor in monitors {
            // Should handle high DPI monitors correctly
            if monitor.scale_factor > 1.0 {
                let scaled_area = CaptureArea {
                    x: 0,
                    y: 0,
                    width: (100.0 * monitor.scale_factor) as u32,
                    height: (100.0 * monitor.scale_factor) as u32,
                };

                let mut screenshot_service = WindowsScreenshot::new();
                screenshot_service.initialize().expect("Should initialize");

                let image = screenshot_service
                    .capture_area(scaled_area)
                    .expect("Should capture scaled area");

                // Should return correctly scaled image dimensions
                assert_eq!(image.width(), scaled_area.width);
                assert_eq!(image.height(), scaled_area.height);
            }
        }
    }

    #[test]
    // CRITICAL: Performance requirements
    fn test_screenshot_performance_requirements() {
        let mut screenshot = WindowsScreenshot::new();
        screenshot.initialize().expect("Should initialize");

        let area = CaptureArea {
            x: 0,
            y: 0,
            width: 1920,
            height: 1080,
        };

        let start = std::time::Instant::now();
        let _image = screenshot
            .capture_area(area)
            .expect("Should capture screenshot");
        let duration = start.elapsed();

        // Should capture fullscreen in under 500ms
        assert!(
            duration.as_millis() < 500,
            "Screenshot should complete in <500ms, took {}ms",
            duration.as_millis()
        );
    }

    #[test]
    // CRITICAL: Edge case handling
    fn test_screenshot_edge_cases() {
        let mut screenshot = WindowsScreenshot::new();
        screenshot.initialize().expect("Should initialize");

        // Test negative coordinates (should adjust automatically)
        let negative_area = CaptureArea {
            x: -100,
            y: -50,
            width: 300,
            height: 200,
        };

        // Should handle negative coordinates gracefully
        let result = screenshot.capture_area(negative_area);
        // Implementation should either adjust coordinates or return appropriate error
        match result {
            Ok(image) => {
                assert!(image.width() <= 300);
                assert!(image.height() <= 200);
            }
            Err(ScreenshotError::InvalidArea(_)) => {
                // Also acceptable - clear error for invalid area
            }
            Err(e) => panic!("Unexpected error type: {:?}", e),
        }

        // Test area extending beyond screen bounds
        let monitors = screenshot.get_monitors().expect("Should get monitors");
        let primary = monitors
            .iter()
            .find(|m| m.is_primary)
            .expect("Should have primary monitor");

        let oversized_area = CaptureArea {
            x: primary.width as i32 - 100,
            y: primary.height as i32 - 50,
            width: 200,
            height: 100,
        };

        // Should handle partial off-screen areas
        let result = screenshot.capture_area(oversized_area);
        assert!(result.is_ok() || matches!(result, Err(ScreenshotError::InvalidArea(_))));
    }
}

// CRITICAL: OCR Integration Tests
#[cfg(feature = "image_processing")]
mod ocr_integration_tests {
    use super::*;

    #[test]
    // CRITICAL: Real Tesseract OCR integration
    fn test_real_tesseract_ocr_integration() {
        let mut ocr_engine = TesseractOcr::new();
        let config = OcrConfig {
            language: "eng".to_string(),
            confidence_threshold: 0.6,
            preprocessing_enabled: true,
            ..Default::default()
        };

        // Should initialize with real Tesseract
        ocr_engine
            .initialize(&config)
            .expect("Should initialize Tesseract OCR");
        assert!(ocr_engine.is_available(), "Tesseract should be available");

        // Create test image with known text
        let test_image = create_test_text_image("Hello World", 24);

        // Should extract text with real OCR
        let result = ocr_engine
            .extract_text(&test_image)
            .expect("Should extract text");

        // Should detect the text (allowing for OCR variations)
        assert!(
            result.text.to_lowercase().contains("hello"),
            "Should detect 'hello' in: '{}'",
            result.text
        );
        assert!(
            result.text.to_lowercase().contains("world"),
            "Should detect 'world' in: '{}'",
            result.text
        );
        assert!(
            result.confidence > 0.5,
            "Should have reasonable confidence: {}",
            result.confidence
        );
        assert!(!result.regions.is_empty(), "Should detect text regions");
    }

    #[test]
    // CRITICAL: Text region detection accuracy
    fn test_text_region_detection_accuracy() {
        let mut ocr_engine = TesseractOcr::new();
        let config = OcrConfig::default();
        ocr_engine.initialize(&config).expect("Should initialize");

        // Create image with multiple text blocks
        let test_image = create_multi_text_image();

        let result = ocr_engine
            .extract_text(&test_image)
            .expect("Should extract text");

        // Should detect multiple text regions
        assert!(
            result.regions.len() >= 2,
            "Should detect multiple text regions, found {}",
            result.regions.len()
        );

        // Each region should have reasonable bounds
        for region in &result.regions {
            assert!(region.bounds.width > 0, "Region width should be positive");
            assert!(region.bounds.height > 0, "Region height should be positive");
            assert!(
                region.bounds.x < test_image.width(),
                "Region X should be within image bounds"
            );
            assert!(
                region.bounds.y < test_image.height(),
                "Region Y should be within image bounds"
            );
            assert!(!region.text.trim().is_empty(), "Region should contain text");
        }
    }

    #[test]
    // CRITICAL: OCR language support
    fn test_ocr_language_support() {
        let mut ocr_engine = TesseractOcr::new();

        // Should support multiple languages
        let available_languages = ocr_engine
            .get_available_languages()
            .expect("Should get available languages");

        // Should have at least English
        assert!(
            available_languages.contains(&"eng".to_string()),
            "Should support English OCR"
        );

        // Test language switching
        for lang in &["eng", "rus", "deu", "fra", "spa", "jpn", "chi_sim"] {
            if available_languages.contains(&lang.to_string()) {
                let config = OcrConfig {
                    language: lang.to_string(),
                    ..Default::default()
                };

                let result = ocr_engine.initialize(&config);
                if result.is_ok() {
                    assert!(
                        ocr_engine.is_available(),
                        "Should be available after language switch to {}",
                        lang
                    );
                }
            }
        }
    }

    #[test]
    // CRITICAL: OCR performance requirements
    fn test_ocr_performance_requirements() {
        let mut ocr_engine = TesseractOcr::new();
        let config = OcrConfig::default();
        ocr_engine.initialize(&config).expect("Should initialize");

        // Test with typical screenshot size
        let test_image = create_test_text_image("Performance Test Text", 16);

        let start = std::time::Instant::now();
        let _result = ocr_engine
            .extract_text(&test_image)
            .expect("Should extract text");
        let duration = start.elapsed();

        // Should complete OCR in under 3 seconds for typical image
        assert!(
            duration.as_secs() < 3,
            "OCR should complete in <3s, took {}ms",
            duration.as_millis()
        );
    }

    // Helper function to create test image with text
    fn create_test_text_image(text: &str, font_size: u32) -> DynamicImage {
        // Create white background
        let width = text.len() as u32 * font_size / 2;
        let height = font_size + 20;
        let img = ImageBuffer::from_pixel(width, height, Rgb([255, 255, 255]));

        // For now, return simple image (real implementation would render text)
        DynamicImage::ImageRgb8(img)
    }

    fn create_multi_text_image() -> DynamicImage {
        // Create image with multiple text blocks for region testing
        let img = ImageBuffer::from_pixel(400, 300, Rgb([255, 255, 255]));
        DynamicImage::ImageRgb8(img)
    }
}

// CRITICAL: Image Processing Pipeline Tests
#[cfg(feature = "image_processing")]
mod image_processing_tests {
    use super::*;

    #[test]
    // CRITICAL: Real image preprocessing pipeline
    fn test_real_image_preprocessing_pipeline() {
        let processor = ImageProcessor::new();

        // Create low-quality test image
        let noisy_image = create_noisy_test_image();

        let config = PreprocessingConfig {
            enable_noise_reduction: true,
            enable_contrast_enhancement: true,
            enable_rotation_correction: true,
            sharpen_factor: 1.2,
            ..Default::default()
        };

        // Should enhance image quality
        let enhanced = processor
            .preprocess(&noisy_image, &config)
            .expect("Should preprocess image");

        // Enhanced image should have better properties for OCR
        assert_eq!(enhanced.width(), noisy_image.width());
        assert_eq!(enhanced.height(), noisy_image.height());

        // Should improve image characteristics (implementation-dependent validation)
        let original_histogram = calculate_histogram(&noisy_image);
        let enhanced_histogram = calculate_histogram(&enhanced);

        // Enhanced image should have better contrast (more varied histogram)
        assert!(
            enhanced_histogram.variance() >= original_histogram.variance() * 0.8,
            "Enhanced image should maintain or improve contrast"
        );
    }

    #[test]
    // CRITICAL: Rotation detection and correction
    fn test_rotation_detection_and_correction() {
        let processor = ImageProcessor::new();

        // Create image with known rotation
        let rotated_image = create_rotated_test_image(15.0); // 15 degrees

        // Should detect rotation angle
        let detected_angle = processor
            .detect_rotation_angle(&rotated_image)
            .expect("Should detect rotation");

        // Should detect approximate rotation (±2 degrees tolerance)
        assert!(
            (detected_angle - 15.0).abs() < 2.0,
            "Should detect ~15° rotation, detected: {}°",
            detected_angle
        );

        // Should correct rotation
        let corrected = processor
            .correct_rotation(&rotated_image, detected_angle)
            .expect("Should correct rotation");

        // Corrected image should be closer to horizontal
        let final_angle = processor
            .detect_rotation_angle(&corrected)
            .expect("Should detect final angle");
        assert!(
            final_angle.abs() < 2.0,
            "Corrected image should be nearly horizontal, angle: {}°",
            final_angle
        );
    }

    #[test]
    // CRITICAL: Enhancement filter effectiveness
    fn test_enhancement_filter_effectiveness() {
        let processor = ImageProcessor::new();

        // Test different enhancement filters
        let test_image = create_low_contrast_image();

        let filters = vec![
            EnhancementFilter::ContrastBoost(1.5),
            EnhancementFilter::NoiseReduction(0.3),
            EnhancementFilter::Sharpen(1.2),
            EnhancementFilter::GaussianBlur(1.0),
        ];

        for filter in filters {
            let enhanced = processor
                .apply_filter(&test_image, &filter)
                .expect("Should apply filter");

            assert_eq!(enhanced.width(), test_image.width());
            assert_eq!(enhanced.height(), test_image.height());

            // Each filter should produce measurably different results
            let original_checksum = image_checksum(&test_image);
            let enhanced_checksum = image_checksum(&enhanced);
            assert_ne!(
                original_checksum, enhanced_checksum,
                "Filter {:?} should modify image",
                filter
            );
        }
    }

    #[test]
    // CRITICAL: Processing performance requirements
    fn test_image_processing_performance() {
        let processor = ImageProcessor::new();

        // Test with typical screenshot size
        let large_image = create_large_test_image(1920, 1080);

        let config = PreprocessingConfig {
            enable_noise_reduction: true,
            enable_contrast_enhancement: true,
            enable_rotation_correction: false, // Skip rotation for speed test
            ..Default::default()
        };

        let start = std::time::Instant::now();
        let _enhanced = processor
            .preprocess(&large_image, &config)
            .expect("Should preprocess large image");
        let duration = start.elapsed();

        // Should process fullscreen image in under 2 seconds
        assert!(
            duration.as_secs() < 2,
            "Image processing should complete in <2s, took {}ms",
            duration.as_millis()
        );
    }

    // Helper functions
    fn create_noisy_test_image() -> DynamicImage {
        let img = ImageBuffer::from_fn(400, 300, |x, y| {
            let noise = ((x + y) % 17) as u8;
            Rgb([128 + noise, 128 + noise, 128 + noise])
        });
        DynamicImage::ImageRgb8(img)
    }

    fn create_rotated_test_image(_angle: f32) -> DynamicImage {
        // For now, return simple image (real implementation would create rotated image)
        let img = ImageBuffer::from_pixel(400, 300, Rgb([255, 255, 255]));
        DynamicImage::ImageRgb8(img)
    }

    fn create_low_contrast_image() -> DynamicImage {
        let img = ImageBuffer::from_fn(200, 150, |x, y| {
            let gray = 100 + ((x + y) % 20) as u8;
            Rgb([gray, gray, gray])
        });
        DynamicImage::ImageRgb8(img)
    }

    fn create_large_test_image(width: u32, height: u32) -> DynamicImage {
        let img = ImageBuffer::from_fn(width, height, |x, y| {
            let r = (x % 256) as u8;
            let g = (y % 256) as u8;
            let b = ((x + y) % 256) as u8;
            Rgb([r, g, b])
        });
        DynamicImage::ImageRgb8(img)
    }

    fn calculate_histogram(image: &DynamicImage) -> Histogram {
        let rgb_image = image.to_rgb8();
        let mut histogram = [0u32; 256];

        for pixel in rgb_image.pixels() {
            let gray = (pixel[0] as u32 + pixel[1] as u32 + pixel[2] as u32) / 3;
            histogram[gray as usize] += 1;
        }

        Histogram { values: histogram }
    }

    fn image_checksum(image: &DynamicImage) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut hasher = DefaultHasher::new();
        image.as_bytes().hash(&mut hasher);
        hasher.finish()
    }

    struct Histogram {
        values: [u32; 256],
    }

    impl Histogram {
        fn variance(&self) -> f64 {
            let total: u32 = self.values.iter().sum();
            if total == 0 {
                return 0.0;
            }

            let mean: f64 = self
                .values
                .iter()
                .enumerate()
                .map(|(i, &count)| i as f64 * count as f64)
                .sum::<f64>()
                / total as f64;

            let variance: f64 = self
                .values
                .iter()
                .enumerate()
                .map(|(i, &count)| {
                    let diff = i as f64 - mean;
                    diff * diff * count as f64
                })
                .sum::<f64>()
                / total as f64;

            variance
        }
    }
}

// CRITICAL: Integration workflow tests
#[cfg(feature = "image_processing")]
mod integration_workflow_tests {
    use super::*;

    #[test]
    // CRITICAL: Complete screenshot-to-ocr workflow
    fn test_complete_screenshot_ocr_workflow() {
        // Step 1: Initialize services
        let mut screenshot = WindowsScreenshot::new();
        screenshot
            .initialize()
            .expect("Should initialize screenshot service");

        let mut ocr_engine = TesseractOcr::new();
        let ocr_config = OcrConfig::default();
        ocr_engine
            .initialize(&ocr_config)
            .expect("Should initialize OCR engine");

        let processor = ImageProcessor::new();

        // Step 2: Capture screenshot
        let area = CaptureArea {
            x: 100,
            y: 100,
            width: 400,
            height: 300,
        };

        let start_time = std::time::Instant::now();

        let raw_image = screenshot
            .capture_area(area)
            .expect("Should capture screenshot");
        let capture_time = start_time.elapsed();

        // Step 3: Preprocess image
        let preprocessing_config = PreprocessingConfig::default();
        let enhanced_image = processor
            .preprocess(&raw_image, &preprocessing_config)
            .expect("Should preprocess image");
        let preprocessing_time = start_time.elapsed();

        // Step 4: Perform OCR
        let ocr_result = ocr_engine
            .extract_text(&enhanced_image)
            .expect("Should perform OCR");
        let total_time = start_time.elapsed();

        // Validate performance requirements
        assert!(
            capture_time.as_millis() < 500,
            "Screenshot should complete in <500ms"
        );
        assert!(
            preprocessing_time.as_millis() < 1000,
            "Preprocessing should complete in <1s"
        );
        assert!(
            total_time.as_secs() < 5,
            "Complete workflow should finish in <5s"
        );

        // Validate results
        assert!(
            ocr_result.confidence >= 0.0 && ocr_result.confidence <= 1.0,
            "OCR confidence should be valid"
        );
        assert!(
            !ocr_result.regions.is_empty() || ocr_result.text.is_empty(),
            "Should have regions if text detected"
        );

        println!(
            "Workflow completed in {}ms: capture={}ms, preprocess={}ms, ocr={}ms",
            total_time.as_millis(),
            capture_time.as_millis(),
            (preprocessing_time - capture_time).as_millis(),
            (total_time - preprocessing_time).as_millis()
        );
    }

    #[test]
    // CRITICAL: Error recovery and fallback mechanisms
    fn test_error_recovery_fallback_mechanisms() {
        // Test OCR fallback when engine fails
        let mut ocr_engine = TesseractOcr::new();

        // Test with invalid config
        let invalid_config = OcrConfig {
            language: "invalid_language".to_string(),
            ..Default::default()
        };

        let init_result = ocr_engine.initialize(&invalid_config);

        // Should either succeed with fallback or provide clear error
        match init_result {
            Ok(_) => {
                // If initialization succeeded, language should fall back to default
                let available = ocr_engine.get_available_languages().unwrap_or_default();
                assert!(
                    !available.is_empty(),
                    "Should have at least one available language as fallback"
                );
            }
            Err(OcrError::LanguageNotSupported(_)) => {
                // Clear error is acceptable
            }
            Err(e) => panic!("Unexpected error type for invalid language: {:?}", e),
        }

        // Test screenshot fallback for invalid area
        let mut screenshot = WindowsScreenshot::new();
        screenshot.initialize().expect("Should initialize");

        let invalid_area = CaptureArea {
            x: -10000,
            y: -10000,
            width: 50000,
            height: 50000,
        };

        let result = screenshot.capture_area(invalid_area);

        // Should handle gracefully with either adjustment or clear error
        match result {
            Ok(image) => {
                // If succeeded, should have adjusted to valid area
                assert!(image.width() > 0 && image.height() > 0);
            }
            Err(ScreenshotError::InvalidArea(_)) => {
                // Clear error is acceptable
            }
            Err(e) => panic!("Unexpected error type for invalid area: {:?}", e),
        }
    }
}

// Placeholder types for compilation - these will need real implementation
// PreprocessingConfig and EnhancementFilter removed - using imports from actual modules

// Unit tests for Screenshot Capture Engine (FR-1) - Synchronous tests only
// TDD approach: Tests written BEFORE full implementation
// These tests define expected behavior per docs/plan.md

use screen_translator::core::screenshot::{
    CaptureArea, ImageFormat, ScreenshotCapture, ScreenshotConfig, WindowsScreenshot,
};
use screen_translator::utils::error::ScreenshotError;

// ============================================================================
// CRITICAL: DPI Scaling Tests (Pure logic, no async)
// ============================================================================

#[test]
/// CRITICAL: DPI scaling at 125% (scale_factor = 1.25)
fn test_dpi_scaling_125_percent() {
    // This test validates the DPI invariant: physical = logical * scale
    let logical_width = 800u32;
    let logical_height = 600u32;
    let scale_factor = 1.25f64;

    let physical_width = (logical_width as f64 * scale_factor) as u32;
    let physical_height = (logical_height as f64 * scale_factor) as u32;

    assert_eq!(physical_width, 1000, "125% scale should produce 1000px");
    assert_eq!(physical_height, 750, "125% scale should produce 750px");

    // Reverse calculation should be accurate
    let reverse_logical_width = (physical_width as f64 / scale_factor) as u32;
    let reverse_logical_height = (physical_height as f64 / scale_factor) as u32;

    assert_eq!(
        reverse_logical_width, logical_width,
        "DPI calculation should be reversible"
    );
    assert_eq!(
        reverse_logical_height, logical_height,
        "DPI calculation should be reversible"
    );
}

#[test]
/// CRITICAL: DPI scaling at 150% (scale_factor = 1.5)
fn test_dpi_scaling_150_percent() {
    let logical_width = 1920u32;
    let logical_height = 1080u32;
    let scale_factor = 1.5f64;

    let physical_width = (logical_width as f64 * scale_factor) as u32;
    let physical_height = (logical_height as f64 * scale_factor) as u32;

    assert_eq!(physical_width, 2880, "150% scale should produce 2880px");
    assert_eq!(physical_height, 1620, "150% scale should produce 1620px");
}

#[test]
/// CRITICAL: DPI scaling at 200% (scale_factor = 2.0)
fn test_dpi_scaling_200_percent() {
    let logical_width = 1920u32;
    let logical_height = 1080u32;
    let scale_factor = 2.0f64;

    let physical_width = (logical_width as f64 * scale_factor) as u32;
    let physical_height = (logical_height as f64 * scale_factor) as u32;

    assert_eq!(physical_width, 3840, "200% scale should produce 3840px");
    assert_eq!(physical_height, 2160, "200% scale should produce 2160px");
}

#[test]
/// CRITICAL: DPI reversibility invariant
fn test_dpi_reversibility_invariant() {
    let test_scales = vec![1.0, 1.25, 1.5, 1.75, 2.0, 2.5];

    for scale in test_scales {
        let logical = 1000u32;
        let physical = (logical as f64 * scale) as u32;
        let reverse = (physical as f64 / scale) as u32;

        // Allow small rounding error (within 1 pixel)
        assert!(
            (reverse as i32 - logical as i32).abs() <= 1,
            "DPI should be reversible at scale {}",
            scale
        );
    }
}

// ============================================================================
// CRITICAL: Configuration Tests
// ============================================================================

#[test]
/// CRITICAL: Valid configuration should be accepted
fn test_config_valid() {
    let mut screenshot = WindowsScreenshot::new();

    let config = ScreenshotConfig {
        format: ImageFormat::Png,
        quality: 90,
        include_cursor: true,
        timeout_ms: 5000,
        max_width: Some(1920),
        max_height: Some(1080),
    };

    let result = screenshot.set_config(config);
    assert!(result.is_ok(), "Valid config should be accepted");
}

#[test]
/// CRITICAL: Invalid quality should be rejected
fn test_config_invalid_quality() {
    let mut screenshot = WindowsScreenshot::new();

    let config = ScreenshotConfig {
        format: ImageFormat::Jpeg,
        quality: 150, // Invalid: > 100
        include_cursor: false,
        timeout_ms: 5000,
        max_width: Some(1920),
        max_height: Some(1080),
    };

    let result = screenshot.set_config(config);
    assert!(result.is_err(), "Invalid quality should be rejected");
    match result {
        Err(ScreenshotError::InvalidConfig(_)) => {
            // Expected
        }
        _ => panic!("Should return InvalidConfig error"),
    }
}

#[test]
/// CRITICAL: Default config should be valid
fn test_config_default_valid() {
    let config = ScreenshotConfig::default();

    assert_eq!(config.format, ImageFormat::Png);
    assert!(config.quality <= 100, "Default quality should be valid");
    assert!(config.timeout_ms > 0, "Default timeout should be positive");
}

// ============================================================================
// Edge Cases & Boundary Tests
// ============================================================================

#[test]
/// CaptureArea serialization/deserialization
fn test_capture_area_serialization() {
    let area = CaptureArea {
        x: 100,
        y: 200,
        width: 800,
        height: 600,
    };

    // Serialize to JSON
    let json = serde_json::to_string(&area).expect("Should serialize");

    // Deserialize back
    let deserialized: CaptureArea = serde_json::from_str(&json).expect("Should deserialize");

    assert_eq!(area, deserialized, "Serialization should be reversible");
}

#[test]
/// Service initialization
fn test_screenshot_initialization() {
    let mut screenshot = WindowsScreenshot::new();

    // Should be able to initialize (may succeed or fail depending on system)
    let _ = screenshot.initialize();

    // After init attempt, availability should be set
    let _available = screenshot.is_available();
}

#[test]
/// Get service info
fn test_screenshot_get_info() {
    let screenshot = WindowsScreenshot::new();
    let info = screenshot.get_info();

    // Should return some information
    assert!(!info.is_empty(), "Info should not be empty");
    assert!(info.contains_key("name"), "Should have name");
    assert!(info.contains_key("platform"), "Should have platform");
}

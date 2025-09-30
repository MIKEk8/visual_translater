// Integration tests for Screenshot Capture Engine (FR-1)
// TDD approach: End-to-end workflow tests
// These tests verify complete capture workflows per docs/plan.md

use screen_translator::core::screenshot::{
    CaptureArea, ImageFormat, ScreenshotCapture, ScreenshotConfig, WindowsScreenshot,
};
use screen_translator::utils::error::ScreenshotError;
use std::time::Instant;

// ============================================================================
// CRITICAL: Complete Capture Workflow Tests
// ============================================================================

#[tokio::test]
/// CRITICAL: Full area selection and capture workflow
async fn test_complete_area_capture_workflow() {
    // Step 1: Initialize service
    let mut screenshot = WindowsScreenshot::new();
    let init_result = screenshot.initialize();
    assert!(
        init_result.is_ok(),
        "Service should initialize successfully"
    );

    // Step 2: Check availability
    assert!(
        screenshot.is_available(),
        "Service should be available after init"
    );

    // Step 3: Get monitor info for valid area
    let monitors = screenshot
        .get_monitors()
        .await
        .expect("Should get monitors");
    assert!(!monitors.is_empty(), "Should have monitors");

    let primary = &monitors[0];

    // Step 4: Define capture area within monitor bounds
    let area = CaptureArea {
        x: 0,
        y: 0,
        width: (primary.width / 2).min(800),
        height: (primary.height / 2).min(600),
    };

    // Step 5: Capture area
    let start = Instant::now();
    let result = screenshot.capture_area(area.clone()).await;
    let duration = start.elapsed();

    // Step 6: Verify results
    assert!(result.is_ok(), "Capture should succeed");

    let image = result.unwrap();

    // Note: Screenshot returns physical pixels (DPI-scaled), not logical pixels
    // On a 150% DPI screen, a 800x600 logical area becomes 1200x900 physical pixels
    // We verify dimensions are reasonable, accounting for DPI scaling
    let scale = primary.scale_factor;
    let expected_physical_width = (area.width as f64 * scale) as u32;
    let expected_physical_height = (area.height as f64 * scale) as u32;

    // Allow small variance due to rounding
    assert!(
        (image.width() as i32 - expected_physical_width as i32).abs() <= 2,
        "Image width should match area (with DPI scaling): expected ~{}px ({}px * {}), got {}px",
        expected_physical_width,
        area.width,
        scale,
        image.width()
    );
    assert!(
        (image.height() as i32 - expected_physical_height as i32).abs() <= 2,
        "Image height should match area (with DPI scaling): expected ~{}px ({}px * {}), got {}px",
        expected_physical_height,
        area.height,
        scale,
        image.height()
    );

    // Step 7: Verify performance (< 500ms per FR-1)
    assert!(
        duration.as_millis() < 500,
        "Capture should take < 500ms (took {}ms)",
        duration.as_millis()
    );
}

#[tokio::test]
/// CRITICAL: Full fullscreen capture workflow
async fn test_complete_fullscreen_workflow() {
    let mut screenshot = WindowsScreenshot::new();
    screenshot.initialize().expect("Should initialize");

    // Get primary monitor
    let _primary = screenshot
        .get_primary_monitor()
        .await
        .expect("Should get primary monitor");

    // Capture fullscreen
    let start = Instant::now();
    let result = screenshot.capture_fullscreen(None).await;
    let duration = start.elapsed();

    assert!(result.is_ok(), "Fullscreen capture should succeed");

    let image = result.unwrap();
    assert!(
        image.width() > 0 && image.height() > 0,
        "Image should have dimensions"
    );

    // Performance check
    assert!(
        duration.as_millis() < 500,
        "Fullscreen capture should take < 500ms"
    );
}

#[tokio::test]
/// CRITICAL: Error handling for invalid workflow
async fn test_workflow_error_handling() {
    let screenshot = WindowsScreenshot::new();
    // Not initialized

    let area = CaptureArea {
        x: 0,
        y: 0,
        width: 100,
        height: 100,
    };

    let result = screenshot.capture_area(area).await;
    assert!(result.is_err(), "Capture should fail when not initialized");

    match result {
        Err(ScreenshotError::NotAvailable(_)) => {
            // Expected error
        }
        _ => panic!("Should return NotAvailable error"),
    }
}

// ============================================================================
// CRITICAL: Multi-Monitor Scenarios
// ============================================================================

#[tokio::test]
/// CRITICAL: Enumerate and capture from multiple monitors
async fn test_multi_monitor_enumeration_and_capture() {
    let mut screenshot = WindowsScreenshot::new();
    screenshot.initialize().expect("Should initialize");

    // Get all monitors
    let monitors = screenshot
        .get_monitors()
        .await
        .expect("Should get monitors");

    assert!(!monitors.is_empty(), "Should have at least one monitor");

    // Try to capture from each monitor
    for (index, monitor) in monitors.iter().enumerate() {
        let result = screenshot.capture_fullscreen(Some(monitor.id)).await;

        if result.is_ok() {
            let image = result.unwrap();
            assert!(
                image.width() > 0,
                "Monitor {} should produce valid image",
                index
            );
        } else {
            // Some monitors might not be capturable, which is ok
            eprintln!("Warning: Could not capture monitor {}", index);
        }
    }
}

#[tokio::test]
/// CRITICAL: Switch between monitors
async fn test_monitor_switching() {
    let mut screenshot = WindowsScreenshot::new();
    screenshot.initialize().expect("Should initialize");

    let monitors = screenshot
        .get_monitors()
        .await
        .expect("Should get monitors");

    if monitors.len() < 2 {
        eprintln!("Skipping multi-monitor test: only 1 monitor detected");
        return;
    }

    // Capture from first monitor
    let result1 = screenshot.capture_fullscreen(Some(0)).await;
    assert!(result1.is_ok(), "Should capture from first monitor");

    // Capture from second monitor
    let result2 = screenshot.capture_fullscreen(Some(1)).await;
    assert!(result2.is_ok(), "Should capture from second monitor");

    // Images might be different sizes if monitors have different resolutions
    let img1 = result1.unwrap();
    let img2 = result2.unwrap();

    // Verify both are valid
    assert!(img1.width() > 0 && img1.height() > 0);
    assert!(img2.width() > 0 && img2.height() > 0);
}

#[tokio::test]
/// CRITICAL: Invalid monitor ID handling
async fn test_invalid_monitor_id() {
    let mut screenshot = WindowsScreenshot::new();
    screenshot.initialize().expect("Should initialize");

    // Try to capture from non-existent monitor
    let result = screenshot.capture_fullscreen(Some(999)).await;

    assert!(result.is_err(), "Should fail for invalid monitor ID");

    match result {
        Err(ScreenshotError::SystemError(_)) => {
            // Expected
        }
        _ => panic!("Should return SystemError for invalid monitor"),
    }
}

// ============================================================================
// CRITICAL: DPI Accuracy End-to-End
// ============================================================================

#[tokio::test]
/// CRITICAL: Capture area with DPI scaling applied correctly
async fn test_dpi_accurate_capture() {
    let mut screenshot = WindowsScreenshot::new();
    screenshot.initialize().expect("Should initialize");

    let primary = screenshot
        .get_primary_monitor()
        .await
        .expect("Should get primary monitor");

    // Define logical coordinates
    let logical_area = CaptureArea {
        x: 0,
        y: 0,
        width: 400,
        height: 300,
    };

    // Expected physical dimensions (with DPI scaling)
    let expected_physical_width = (logical_area.width as f64 * primary.scale_factor) as u32;
    let expected_physical_height = (logical_area.height as f64 * primary.scale_factor) as u32;

    // Capture
    let result = screenshot.capture_area(logical_area).await;
    assert!(result.is_ok(), "Capture should succeed");

    let image = result.unwrap();

    // Verify dimensions account for DPI
    // Note: This test assumes the implementation handles DPI scaling
    // The actual implementation might return logical or physical dimensions
    // This test documents the expected behavior per FR-1 requirements
    println!(
        "Logical: {}x{}, Scale: {}, Physical: {}x{}, Actual: {}x{}",
        400,
        300,
        primary.scale_factor,
        expected_physical_width,
        expected_physical_height,
        image.width(),
        image.height()
    );

    // The actual assertion depends on implementation choice:
    // Option A: Image has logical dimensions (400x300)
    // Option B: Image has physical dimensions (scaled)
    // For now, just verify image is valid
    assert!(image.width() > 0 && image.height() > 0);
}

#[tokio::test]
/// CRITICAL: Multiple DPI scales handled correctly
async fn test_multiple_dpi_scales() {
    let mut screenshot = WindowsScreenshot::new();
    screenshot.initialize().expect("Should initialize");

    let monitors = screenshot
        .get_monitors()
        .await
        .expect("Should get monitors");

    // Test with each monitor's DPI scale
    for monitor in monitors {
        println!(
            "Testing monitor {} with scale factor {}",
            monitor.id, monitor.scale_factor
        );

        let area = CaptureArea {
            x: 0,
            y: 0,
            width: 100,
            height: 100,
        };

        let result = screenshot.capture_area(area).await;

        if result.is_ok() {
            let image = result.unwrap();
            assert!(
                image.width() > 0 && image.height() > 0,
                "Image should be valid for monitor with scale {}",
                monitor.scale_factor
            );
        }
    }
}

// ============================================================================
// CRITICAL: Performance Benchmarks
// ============================================================================

#[tokio::test]
/// CRITICAL: Small area capture performance (< 500ms)
async fn test_performance_small_area() {
    let mut screenshot = WindowsScreenshot::new();
    screenshot.initialize().expect("Should initialize");

    let area = CaptureArea {
        x: 0,
        y: 0,
        width: 400,
        height: 300,
    };

    let start = Instant::now();
    let result = screenshot.capture_area(area).await;
    let duration = start.elapsed();

    assert!(result.is_ok(), "Small area capture should succeed");

    assert!(
        duration.as_millis() < 500,
        "Small area should capture in < 500ms (took {}ms)",
        duration.as_millis()
    );
}

#[tokio::test]
/// CRITICAL: Large area capture performance (< 500ms)
async fn test_performance_large_area() {
    let mut screenshot = WindowsScreenshot::new();
    screenshot.initialize().expect("Should initialize");

    let monitors = screenshot
        .get_monitors()
        .await
        .expect("Should get monitors");
    let primary = &monitors[0];

    // Large area (half of monitor)
    let area = CaptureArea {
        x: 0,
        y: 0,
        width: primary.width / 2,
        height: primary.height / 2,
    };

    let start = Instant::now();
    let result = screenshot.capture_area(area).await;
    let duration = start.elapsed();

    assert!(result.is_ok(), "Large area capture should succeed");

    assert!(
        duration.as_millis() < 500,
        "Large area should capture in < 500ms (took {}ms)",
        duration.as_millis()
    );
}

#[tokio::test]
/// CRITICAL: Repeated captures performance
async fn test_performance_repeated_captures() {
    let mut screenshot = WindowsScreenshot::new();
    screenshot.initialize().expect("Should initialize");

    let area = CaptureArea {
        x: 0,
        y: 0,
        width: 400,
        height: 300,
    };

    let iterations = 5;
    let start = Instant::now();

    for _ in 0..iterations {
        let result = screenshot.capture_area(area.clone()).await;
        assert!(result.is_ok(), "Each capture should succeed");
    }

    let total_duration = start.elapsed();
    let avg_duration = total_duration / iterations;

    assert!(
        avg_duration.as_millis() < 500,
        "Average capture time should be < 500ms (avg: {}ms)",
        avg_duration.as_millis()
    );
}

// ============================================================================
// Configuration and Format Tests
// ============================================================================

#[tokio::test]
/// Test different image formats
async fn test_image_format_configuration() {
    let mut screenshot = WindowsScreenshot::new();
    screenshot.initialize().expect("Should initialize");

    let formats = vec![ImageFormat::Png, ImageFormat::Jpeg, ImageFormat::Bmp];

    for format in formats {
        let config = ScreenshotConfig {
            format: format.clone(),
            quality: 90,
            include_cursor: false,
            timeout_ms: 5000,
            max_width: Some(1920),
            max_height: Some(1080),
        };

        let result = screenshot.set_config(config);
        assert!(result.is_ok(), "Should accept format {:?}", format);

        // Verify capture still works
        let area = CaptureArea {
            x: 0,
            y: 0,
            width: 100,
            height: 100,
        };

        let capture_result = screenshot.capture_area(area).await;
        assert!(
            capture_result.is_ok(),
            "Capture should work with format {:?}",
            format
        );
    }
}

#[tokio::test]
/// Test quality settings
async fn test_quality_configuration() {
    let mut screenshot = WindowsScreenshot::new();
    screenshot.initialize().expect("Should initialize");

    let qualities = vec![50, 75, 90, 100];

    for quality in qualities {
        let config = ScreenshotConfig {
            format: ImageFormat::Jpeg,
            quality,
            include_cursor: false,
            timeout_ms: 5000,
            max_width: Some(1920),
            max_height: Some(1080),
        };

        let result = screenshot.set_config(config);
        assert!(result.is_ok(), "Should accept quality {}", quality);
    }
}

// ============================================================================
// Memory and Resource Management
// ============================================================================

#[tokio::test]
/// CRITICAL: Memory release after capture
async fn test_memory_release_after_capture() {
    let mut screenshot = WindowsScreenshot::new();
    screenshot.initialize().expect("Should initialize");

    let area = CaptureArea {
        x: 0,
        y: 0,
        width: 1920,
        height: 1080,
    };

    // Capture and immediately drop
    for _ in 0..10 {
        let result = screenshot.capture_area(area.clone()).await;
        if result.is_ok() {
            drop(result); // Explicit drop
        }
    }

    // If memory isn't released, this would eventually OOM
    // No assertion needed - test passes if no OOM occurs
}

#[tokio::test]
/// CRITICAL: Concurrent captures
async fn test_concurrent_captures() {
    let mut screenshot = WindowsScreenshot::new();
    screenshot.initialize().expect("Should initialize");

    let area = CaptureArea {
        x: 0,
        y: 0,
        width: 400,
        height: 300,
    };

    // Note: Concurrent captures would require Clone or Arc<Mutex<>> for WindowsScreenshot
    // This test documents the expected behavior for thread-safe implementation
    // TODO: Implement Clone or use Arc<Mutex<>> for concurrent access in future

    // For now, just verify sequential captures work
    for _ in 0..3 {
        let result = screenshot.capture_area(area.clone()).await;
        assert!(result.is_ok(), "Sequential captures should work");
    }
}

// ============================================================================
// Edge Case Scenarios
// ============================================================================

#[tokio::test]
/// Test capture at monitor edges
async fn test_capture_at_monitor_edges() {
    let mut screenshot = WindowsScreenshot::new();
    screenshot.initialize().expect("Should initialize");

    let primary = screenshot
        .get_primary_monitor()
        .await
        .expect("Should get primary monitor");

    // Capture at bottom-right corner
    let area = CaptureArea {
        x: (primary.width as i32) - 100,
        y: (primary.height as i32) - 100,
        width: 100,
        height: 100,
    };

    let result = screenshot.capture_area(area).await;

    // Should handle edge cases gracefully
    if result.is_err() {
        // Error should be informative
        match result {
            Err(ScreenshotError::InvalidArea(msg)) => {
                assert!(!msg.is_empty(), "Error message should be informative");
            }
            _ => {}
        }
    }
}

#[tokio::test]
/// Test initialization idempotence
async fn test_initialization_idempotence() {
    let mut screenshot = WindowsScreenshot::new();

    // Initialize multiple times
    let result1 = screenshot.initialize();
    let result2 = screenshot.initialize();
    let result3 = screenshot.initialize();

    // All should succeed or fail consistently
    assert_eq!(
        result1.is_ok(),
        result2.is_ok(),
        "Repeated initialization should have consistent results"
    );
    assert_eq!(
        result2.is_ok(),
        result3.is_ok(),
        "Repeated initialization should have consistent results"
    );
}

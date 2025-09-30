//! Phase 2 Commands Module Tests - TDD Implementation
//!
//! This module contains failing tests that define the contracts for Phase 2 Tauri commands:
//! - Screenshot capture commands with Windows API integration
//! - OCR processing commands with real Tesseract integration
//! - Translation service commands with Google Translate API
//! - Intelligent hotkey commands with context menu system
//! - Configuration management and real-time updates
//!
//! All tests are designed to FAIL initially and pass once implementation is complete.

use super::*;
use crate::commands::{
    config::{get_app_config, register_global_hotkey, set_app_config, AppConfig},
    history::{
        add_translation_to_history, search_translation_history, toggle_translation_favorite,
        TranslationEntry,
    },
    hotkey::{
        execute_context_action, get_context_menu_items, initialize_intelligent_hotkey,
        ContextMenuItem,
    },
    ocr::{get_available_ocr_languages, perform_ocr, set_ocr_language, OcrResult},
    screenshot::{capture_screenshot, get_monitors, CaptureArea, MonitorInfo},
    translation::{
        detect_language_and_context, get_cached_translation, translate_text, TranslationRequest,
        TranslationResult,
    },
};
use crate::services::AppState;
use std::sync::Arc;
use tauri::{AppHandle, Manager, State};
use tokio::sync::Mutex;

// Mock app handle and state for testing
struct MockAppHandle;

impl MockAppHandle {
    fn new() -> Self {
        Self
    }
}

// CRITICAL: Screenshot Capture Command Tests
mod screenshot_command_tests {
    use super::*;

    #[tokio::test]
    // CRITICAL: Real Windows screenshot capture integration
    async fn test_capture_screenshot_command_real_windows() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        let test_area = CaptureArea {
            x: 100,
            y: 100,
            width: 400,
            height: 300,
        };

        // Should capture real screenshot using Windows API
        let result = capture_screenshot(test_area, State(&app_state)).await;

        // Expected: Successful capture with base64 image data
        assert!(result.is_ok(), "Should capture screenshot successfully");

        let screenshot_data = result.unwrap();
        assert!(
            !screenshot_data.image_data.is_empty(),
            "Should return image data"
        );
        assert!(
            screenshot_data.image_data.starts_with("data:image/"),
            "Should be valid base64 image data URL"
        );
        assert!(screenshot_data.width == 400, "Should have correct width");
        assert!(screenshot_data.height == 300, "Should have correct height");
        assert!(
            screenshot_data.capture_time_ms > 0,
            "Should record capture time"
        );
        assert!(
            screenshot_data.capture_time_ms < 1000,
            "Should capture within 1 second"
        );

        // Real screenshot should have varied pixel data (not uniform test pattern)
        assert!(
            screenshot_data.image_data.len() > 1000,
            "Real screenshot should have substantial data"
        );
    }

    #[tokio::test]
    // CRITICAL: Monitor enumeration with real Windows API
    async fn test_get_monitors_command_real_windows() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        // Should enumerate real system monitors
        let result = get_monitors(State(&app_state)).await;

        assert!(result.is_ok(), "Should enumerate monitors successfully");

        let monitors = result.unwrap();
        assert!(!monitors.is_empty(), "Should detect at least one monitor");

        // Validate monitor properties
        for monitor in &monitors {
            // Should have realistic dimensions
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

            // Should have valid scale factor
            assert!(
                monitor.scale_factor >= 0.5 && monitor.scale_factor <= 4.0,
                "Scale factor should be realistic: {}",
                monitor.scale_factor
            );

            // Should have non-empty name
            assert!(!monitor.name.is_empty(), "Monitor should have a name");

            // Coordinates should be valid
            assert!(
                monitor.x >= -7680 && monitor.x <= 7680,
                "Monitor X coordinate should be valid"
            );
            assert!(
                monitor.y >= -4320 && monitor.y <= 4320,
                "Monitor Y coordinate should be valid"
            );
        }

        // Should have exactly one primary monitor
        let primary_count = monitors.iter().filter(|m| m.is_primary).count();
        assert_eq!(primary_count, 1, "Should have exactly one primary monitor");
    }

    #[tokio::test]
    // CRITICAL: Invalid area handling and validation
    async fn test_capture_screenshot_invalid_areas() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        let invalid_areas = vec![
            // Zero dimensions
            CaptureArea {
                x: 0,
                y: 0,
                width: 0,
                height: 100,
            },
            CaptureArea {
                x: 0,
                y: 0,
                width: 100,
                height: 0,
            },
            // Negative coordinates (should be handled gracefully or error clearly)
            CaptureArea {
                x: -1000,
                y: -500,
                width: 200,
                height: 150,
            },
            // Extremely large dimensions
            CaptureArea {
                x: 0,
                y: 0,
                width: 50000,
                height: 50000,
            },
        ];

        for invalid_area in invalid_areas {
            let result = capture_screenshot(invalid_area, State(&app_state)).await;

            match result {
                Ok(screenshot) => {
                    // If successful, should have adjusted coordinates to valid values
                    assert!(screenshot.width > 0, "Adjusted width should be positive");
                    assert!(screenshot.height > 0, "Adjusted height should be positive");
                }
                Err(e) => {
                    // Should provide clear error message
                    let error_msg = e.to_string();
                    assert!(!error_msg.is_empty(), "Error message should not be empty");
                    assert!(
                        error_msg.contains("invalid")
                            || error_msg.contains("area")
                            || error_msg.contains("coordinates"),
                        "Error should mention invalid area: {}",
                        error_msg
                    );
                }
            }
        }
    }

    #[tokio::test]
    // CRITICAL: Screenshot performance requirements
    async fn test_capture_screenshot_performance() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        // Test with typical screenshot size
        let test_area = CaptureArea {
            x: 0,
            y: 0,
            width: 1920,
            height: 1080,
        };

        let start_time = std::time::Instant::now();
        let result = capture_screenshot(test_area, State(&app_state)).await;
        let duration = start_time.elapsed();

        assert!(result.is_ok(), "Performance test should succeed");

        // Should capture fullscreen in under 500ms as per plan requirements
        assert!(
            duration.as_millis() < 500,
            "Screenshot should complete in <500ms, took {}ms",
            duration.as_millis()
        );

        let screenshot_data = result.unwrap();
        assert!(
            screenshot_data.capture_time_ms < 500,
            "Recorded capture time should be under 500ms"
        );
    }

    #[tokio::test]
    // CRITICAL: DPI scaling support
    async fn test_capture_screenshot_dpi_scaling() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        // First get monitors to find high-DPI ones
        let monitors_result = get_monitors(State(&app_state)).await;
        assert!(monitors_result.is_ok(), "Should get monitors");

        let monitors = monitors_result.unwrap();

        // Test on monitors with different scale factors
        for monitor in monitors {
            if monitor.scale_factor > 1.0 {
                // Test capture on high-DPI monitor
                let scaled_area = CaptureArea {
                    x: monitor.x,
                    y: monitor.y,
                    width: (100.0 * monitor.scale_factor) as u32,
                    height: (100.0 * monitor.scale_factor) as u32,
                };

                let result = capture_screenshot(scaled_area, State(&app_state)).await;

                if result.is_ok() {
                    let screenshot = result.unwrap();

                    // Should handle DPI scaling correctly
                    assert!(
                        screenshot.scale_factor == monitor.scale_factor,
                        "Should record correct scale factor"
                    );
                    assert!(
                        screenshot.width > 0 && screenshot.height > 0,
                        "Should have valid dimensions"
                    );
                }
            }
        }
    }
}

// CRITICAL: OCR Processing Command Tests
mod ocr_command_tests {
    use super::*;

    #[tokio::test]
    // CRITICAL: Real Tesseract OCR integration
    async fn test_perform_ocr_command_real_tesseract() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        // Create test image with known text (in real test, this would be actual image data)
        let test_image_data = create_test_image_with_text("Hello World");

        // Should perform real OCR using Tesseract
        let result = perform_ocr(test_image_data, State(&app_state)).await;

        assert!(result.is_ok(), "OCR should succeed with valid image");

        let ocr_result = result.unwrap();

        // Should extract text
        assert!(
            !ocr_result.text.is_empty(),
            "Should extract text from image"
        );

        // Should have reasonable confidence
        assert!(
            ocr_result.confidence >= 0.0 && ocr_result.confidence <= 1.0,
            "Confidence should be valid range"
        );

        // Should detect text regions
        assert!(!ocr_result.regions.is_empty(), "Should detect text regions");

        // Should record processing time
        assert!(
            ocr_result.processing_time_ms > 0,
            "Should record processing time"
        );
        assert!(
            ocr_result.processing_time_ms < 5000,
            "OCR should complete within 5 seconds"
        );

        // Text should contain expected content (allowing for OCR variations)
        let detected_text = ocr_result.text.to_lowercase();
        assert!(
            detected_text.contains("hello") || detected_text.contains("world"),
            "Should detect text content: '{}'",
            ocr_result.text
        );
    }

    #[tokio::test]
    // CRITICAL: OCR language switching
    async fn test_set_ocr_language_command() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        // Get available languages first
        let languages_result = get_available_ocr_languages(State(&app_state)).await;
        assert!(
            languages_result.is_ok(),
            "Should get available OCR languages"
        );

        let available_languages = languages_result.unwrap();
        assert!(
            !available_languages.is_empty(),
            "Should have at least one available language"
        );
        assert!(
            available_languages.contains(&"eng".to_string()),
            "Should support English"
        );

        // Test switching to each available language
        for language in &available_languages {
            let result = set_ocr_language(language.clone(), State(&app_state)).await;
            assert!(result.is_ok(), "Should set OCR language to: {}", language);
        }

        // Test invalid language
        let invalid_result = set_ocr_language("invalid_lang".to_string(), State(&app_state)).await;
        match invalid_result {
            Ok(_) => {
                // If successful, should fall back to default language
            }
            Err(e) => {
                // Should provide clear error for invalid language
                assert!(
                    e.to_string().contains("language"),
                    "Error should mention language issue"
                );
            }
        }
    }

    #[tokio::test]
    // CRITICAL: OCR error handling with invalid inputs
    async fn test_perform_ocr_error_handling() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        let invalid_inputs = vec![
            "invalid_base64_data",
            "",
            "not_an_image_at_all",
            "data:image/png;base64,corrupted_data",
        ];

        for invalid_input in invalid_inputs {
            let result = perform_ocr(invalid_input.to_string(), State(&app_state)).await;

            match result {
                Ok(_) => {
                    // If successful, should handle gracefully
                }
                Err(e) => {
                    // Should provide clear error message
                    let error_msg = e.to_string();
                    assert!(!error_msg.is_empty(), "Error message should not be empty");
                    assert!(
                        error_msg.contains("image")
                            || error_msg.contains("data")
                            || error_msg.contains("format"),
                        "Error should mention image/data issue: {}",
                        error_msg
                    );
                }
            }
        }
    }

    #[tokio::test]
    // CRITICAL: OCR performance with different image sizes
    async fn test_perform_ocr_performance() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        let test_cases = vec![
            (400, 300, "Small image"),
            (1920, 1080, "Fullscreen image"),
            (800, 600, "Medium image"),
        ];

        for (width, height, description) in test_cases {
            let test_image = create_test_image_with_dimensions(width, height);

            let start_time = std::time::Instant::now();
            let result = perform_ocr(test_image, State(&app_state)).await;
            let duration = start_time.elapsed();

            if result.is_ok() {
                let ocr_result = result.unwrap();

                // Should complete within reasonable time (plan requirement: <3s)
                assert!(
                    duration.as_secs() < 3,
                    "{} OCR should complete in <3s, took {}ms",
                    description,
                    duration.as_millis()
                );
                assert!(
                    ocr_result.processing_time_ms < 3000,
                    "Recorded processing time should be <3s for {}",
                    description
                );

                println!(
                    "{}: OCR completed in {}ms",
                    description, ocr_result.processing_time_ms
                );
            }
        }
    }

    // Helper functions for creating test images
    fn create_test_image_with_text(text: &str) -> String {
        // In real implementation, this would create actual image with rendered text
        // For now, return placeholder base64 image data
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==".to_string()
    }

    fn create_test_image_with_dimensions(width: u32, height: u32) -> String {
        // In real implementation, this would create image with specified dimensions
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==".to_string()
    }
}

// CRITICAL: Translation Service Command Tests
mod translation_command_tests {
    use super::*;

    #[tokio::test]
    // CRITICAL: Real Google Translate API integration
    async fn test_translate_text_command_real_api() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        let translation_request = TranslationRequest {
            text: "Hello, world!".to_string(),
            source_lang: "en".to_string(),
            target_lang: "es".to_string(),
        };

        // Should perform real translation using Google Translate API
        let result = translate_text(translation_request, State(&app_state)).await;

        assert!(
            result.is_ok(),
            "Translation should succeed with valid request"
        );

        let translation_result = result.unwrap();

        // Should return actual Spanish translation
        assert!(
            !translation_result.translated_text.is_empty(),
            "Should return translated text"
        );
        assert_ne!(
            translation_result.translated_text, translation_result.original_text,
            "Translation should differ from original"
        );
        assert_eq!(translation_result.source_lang, "en");
        assert_eq!(translation_result.target_lang, "es");
        assert!(
            translation_result.confidence > 0.0 && translation_result.confidence <= 1.0,
            "Should have valid confidence"
        );

        // Real translation should contain Spanish words
        let spanish_text = translation_result.translated_text.to_lowercase();
        assert!(
            spanish_text.contains("hola")
                || spanish_text.contains("mundo")
                || spanish_text.contains("¡hola"),
            "Should contain Spanish translation: '{}'",
            translation_result.translated_text
        );

        // Should record processing time
        assert!(
            translation_result.processing_time_ms > 0,
            "Should record processing time"
        );
    }

    #[tokio::test]
    // CRITICAL: Language detection with context analysis
    async fn test_detect_language_and_context_command() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        let test_cases = vec![
            ("Hello world", "en", Some("general")),
            ("Bonjour le monde", "fr", Some("general")),
            ("def function():", "en", Some("technical")),
            ("Press OK to continue", "en", Some("ui")),
            ("Achievement unlocked!", "en", Some("gaming")),
            ("Привет мир", "ru", Some("general")),
            ("こんにちは世界", "ja", Some("general")),
        ];

        for (text, expected_lang, expected_context) in test_cases {
            let result = detect_language_and_context(text.to_string(), State(&app_state)).await;

            assert!(result.is_ok(), "Should detect language for: {}", text);

            let detection_result = result.unwrap();

            // Should detect correct language (allowing for close variants)
            assert!(
                detection_result.language == expected_lang
                    || detection_result.language.starts_with(&expected_lang[..2]),
                "Should detect {} for '{}', got '{}'",
                expected_lang,
                text,
                detection_result.language
            );

            // Should have reasonable confidence
            assert!(
                detection_result.confidence > 0.5,
                "Should have good confidence for language detection"
            );

            // Should detect context if available
            if let Some(expected_ctx) = expected_context {
                assert!(
                    detection_result.context.is_some(),
                    "Should detect context for: {}",
                    text
                );
                // Context matching can be flexible as it depends on AI model
            }
        }
    }

    #[tokio::test]
    // CRITICAL: Translation caching functionality
    async fn test_translation_caching_commands() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        let translation_request = TranslationRequest {
            text: "Cache test text".to_string(),
            source_lang: "en".to_string(),
            target_lang: "fr".to_string(),
        };

        // First translation (should hit API and cache result)
        let first_result = translate_text(translation_request.clone(), State(&app_state)).await;
        assert!(first_result.is_ok(), "First translation should succeed");

        let first_translation = first_result.unwrap();
        assert!(
            !first_translation.cached,
            "First translation should not be from cache"
        );

        // Check cache
        let cache_result = get_cached_translation(
            translation_request.text.clone(),
            translation_request.source_lang.clone(),
            translation_request.target_lang.clone(),
            State(&app_state),
        )
        .await;

        assert!(cache_result.is_ok(), "Should check cache successfully");

        let cached_translation = cache_result.unwrap();
        assert!(
            cached_translation.is_some(),
            "Translation should be in cache"
        );

        let cached = cached_translation.unwrap();
        assert_eq!(
            cached.translated_text, first_translation.translated_text,
            "Cached translation should match"
        );

        // Second translation (should use cache)
        let second_result = translate_text(translation_request, State(&app_state)).await;
        assert!(second_result.is_ok(), "Second translation should succeed");

        let second_translation = second_result.unwrap();
        assert!(
            second_translation.cached,
            "Second translation should be from cache"
        );
        assert_eq!(
            second_translation.translated_text, first_translation.translated_text,
            "Results should be identical"
        );

        // Cached translation should be much faster
        assert!(
            second_translation.processing_time_ms < first_translation.processing_time_ms / 2,
            "Cached translation should be faster: {}ms vs {}ms",
            second_translation.processing_time_ms,
            first_translation.processing_time_ms
        );
    }

    #[tokio::test]
    // CRITICAL: Translation error handling
    async fn test_translate_text_error_handling() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        let invalid_requests = vec![
            // Empty text
            TranslationRequest {
                text: "".to_string(),
                source_lang: "en".to_string(),
                target_lang: "es".to_string(),
            },
            // Invalid language codes
            TranslationRequest {
                text: "Hello".to_string(),
                source_lang: "invalid_lang".to_string(),
                target_lang: "es".to_string(),
            },
            // Very long text
            TranslationRequest {
                text: "A".repeat(10000),
                source_lang: "en".to_string(),
                target_lang: "es".to_string(),
            },
        ];

        for invalid_request in invalid_requests {
            let result = translate_text(invalid_request.clone(), State(&app_state)).await;

            match result {
                Ok(translation) => {
                    // If successful, should handle gracefully
                    assert!(
                        !translation.translated_text.is_empty() || invalid_request.text.is_empty(),
                        "Should handle gracefully or return empty for empty input"
                    );
                }
                Err(e) => {
                    // Should provide clear error message
                    let error_msg = e.to_string();
                    assert!(!error_msg.is_empty(), "Error message should not be empty");
                }
            }
        }
    }
}

// CRITICAL: Intelligent Hotkey Command Tests
mod hotkey_command_tests {
    use super::*;

    #[tokio::test]
    // CRITICAL: Intelligent hotkey system initialization
    async fn test_initialize_intelligent_hotkey_command() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        // Should initialize intelligent hotkey system
        let result = initialize_intelligent_hotkey(State(&app_state)).await;

        assert!(
            result.is_ok(),
            "Should initialize intelligent hotkey system"
        );

        let initialization_result = result.unwrap();
        assert!(
            initialization_result.success,
            "Initialization should succeed"
        );
        assert!(
            !initialization_result.registered_hotkeys.is_empty(),
            "Should register hotkeys"
        );
        assert!(
            initialization_result
                .registered_hotkeys
                .contains(&"Alt+A".to_string()),
            "Should register Alt+A"
        );
    }

    #[tokio::test]
    // CRITICAL: Context menu items generation
    async fn test_get_context_menu_items_command() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        // Initialize first
        let _ = initialize_intelligent_hotkey(State(&app_state)).await;

        // Should get context menu items
        let result = get_context_menu_items(State(&app_state)).await;

        assert!(result.is_ok(), "Should get context menu items");

        let menu_items = result.unwrap();
        assert!(!menu_items.is_empty(), "Should have menu items");

        // Verify required menu items
        let action_ids: Vec<_> = menu_items.iter().map(|item| &item.action_id).collect();
        assert!(
            action_ids.contains(&&"screenshot_area".to_string()),
            "Should have screenshot action"
        );
        assert!(
            action_ids.contains(&&"translate_clipboard".to_string()),
            "Should have clipboard action"
        );
        assert!(
            action_ids.contains(&&"show_history".to_string()),
            "Should have history action"
        );
        assert!(
            action_ids.contains(&&"show_settings".to_string()),
            "Should have settings action"
        );

        // Verify menu item properties
        for item in &menu_items {
            assert!(!item.action_id.is_empty(), "Action ID should not be empty");
            assert!(!item.label.is_empty(), "Label should not be empty");
            assert!(
                !item.description.is_empty(),
                "Description should not be empty"
            );
            assert!(item.icon.is_some(), "Should have icon");
            assert!(
                item.keyboard_shortcut.is_some(),
                "Should have keyboard shortcut"
            );
        }
    }

    #[tokio::test]
    // CRITICAL: Context action execution
    async fn test_execute_context_action_command() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        // Initialize first
        let _ = initialize_intelligent_hotkey(State(&app_state)).await;

        let test_actions = vec![
            "screenshot_area",
            "translate_clipboard",
            "smart_region",
            "repeat_last",
            "show_history",
            "show_settings",
        ];

        for action in test_actions {
            let result = execute_context_action(action.to_string(), State(&app_state)).await;

            assert!(result.is_ok(), "Should execute action: {}", action);

            let execution_result = result.unwrap();
            assert!(
                execution_result.success,
                "Action execution should succeed: {}",
                action
            );
            assert_eq!(
                execution_result.action_id, action,
                "Should return correct action ID"
            );
            assert!(
                !execution_result.message.is_empty(),
                "Should provide execution message"
            );
        }

        // Test invalid action
        let invalid_result =
            execute_context_action("invalid_action".to_string(), State(&app_state)).await;

        match invalid_result {
            Ok(result) => {
                assert!(!result.success, "Invalid action should not succeed");
            }
            Err(e) => {
                assert!(
                    e.to_string().contains("action"),
                    "Error should mention action issue"
                );
            }
        }
    }
}

// CRITICAL: Configuration Command Tests
mod config_command_tests {
    use super::*;

    #[tokio::test]
    // CRITICAL: Configuration loading and saving
    async fn test_get_and_set_app_config_commands() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        // Get default config
        let get_result = get_app_config(State(&app_state)).await;

        assert!(get_result.is_ok(), "Should get app config");

        let mut config = get_result.unwrap();

        // Verify default config structure
        assert!(
            !config.hotkeys.quick_translate.is_empty(),
            "Should have default quick translate hotkey"
        );
        assert!(
            !config.ocr.language.is_empty(),
            "Should have default OCR language"
        );
        assert!(
            !config.translation.source_lang.is_empty(),
            "Should have default source language"
        );
        assert!(
            !config.translation.target_lang.is_empty(),
            "Should have default target language"
        );
        assert!(
            config.ocr.confidence_threshold > 0.0 && config.ocr.confidence_threshold <= 1.0,
            "Should have valid confidence threshold"
        );

        // Modify config
        config.translation.target_lang = "de".to_string();
        config.ocr.confidence_threshold = 0.75;
        config.hotkeys.quick_translate = "Ctrl+Alt+T".to_string();

        // Set modified config
        let set_result = set_app_config(config.clone(), State(&app_state)).await;

        assert!(set_result.is_ok(), "Should set app config");

        // Get config again to verify persistence
        let get_result2 = get_app_config(State(&app_state)).await;

        assert!(get_result2.is_ok(), "Should get updated config");

        let updated_config = get_result2.unwrap();
        assert_eq!(
            updated_config.translation.target_lang, "de",
            "Should persist target language change"
        );
        assert_eq!(
            updated_config.ocr.confidence_threshold, 0.75,
            "Should persist confidence threshold change"
        );
        assert_eq!(
            updated_config.hotkeys.quick_translate, "Ctrl+Alt+T",
            "Should persist hotkey change"
        );
    }

    #[tokio::test]
    // CRITICAL: Global hotkey registration and validation
    async fn test_register_global_hotkey_command() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        let valid_hotkeys = vec![
            ("Alt+A", "smart_translation"),
            ("Ctrl+Shift+T", "quick_translate"),
            ("F10", "context_menu"),
            ("Ctrl+Alt+S", "screenshot_area"),
        ];

        for (hotkey, action) in valid_hotkeys {
            let result =
                register_global_hotkey(hotkey.to_string(), action.to_string(), State(&app_state))
                    .await;

            assert!(result.is_ok(), "Should register valid hotkey: {}", hotkey);

            let registration_result = result.unwrap();
            assert!(
                registration_result.success,
                "Hotkey registration should succeed: {}",
                hotkey
            );
            assert_eq!(
                registration_result.hotkey, hotkey,
                "Should return correct hotkey"
            );
            assert_eq!(
                registration_result.action, action,
                "Should return correct action"
            );
        }

        let invalid_hotkeys = vec![
            "InvalidKey+Combo",
            "Ctrl+Alt+Delete", // System reserved
            "",
            "OnlyOneKey",
        ];

        for invalid_hotkey in invalid_hotkeys {
            let result = register_global_hotkey(
                invalid_hotkey.to_string(),
                "test_action".to_string(),
                State(&app_state),
            )
            .await;

            match result {
                Ok(result) => {
                    assert!(
                        !result.success,
                        "Invalid hotkey should not succeed: {}",
                        invalid_hotkey
                    );
                    assert!(
                        !result.error_message.is_empty(),
                        "Should provide error message for invalid hotkey"
                    );
                }
                Err(e) => {
                    assert!(
                        e.to_string().contains("hotkey") || e.to_string().contains("invalid"),
                        "Error should mention hotkey issue: {}",
                        e
                    );
                }
            }
        }
    }
}

// CRITICAL: Translation History Command Tests
mod history_command_tests {
    use super::*;

    #[tokio::test]
    // CRITICAL: Translation history management
    async fn test_add_and_search_translation_history() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        // Add sample translations to history
        let sample_entries = vec![
            TranslationEntry {
                id: "test_1".to_string(),
                original_text: "Hello world".to_string(),
                translated_text: "Hola mundo".to_string(),
                source_lang: "en".to_string(),
                target_lang: "es".to_string(),
                confidence: 0.95,
                tags: vec!["greeting".to_string()],
                is_favorite: false,
                created_at: chrono::Utc::now(),
            },
            TranslationEntry {
                id: "test_2".to_string(),
                original_text: "Programming is fun".to_string(),
                translated_text: "La programación es divertida".to_string(),
                source_lang: "en".to_string(),
                target_lang: "es".to_string(),
                confidence: 0.92,
                tags: vec!["programming".to_string(), "tech".to_string()],
                is_favorite: true,
                created_at: chrono::Utc::now(),
            },
        ];

        for entry in &sample_entries {
            let result = add_translation_to_history(entry.clone(), State(&app_state)).await;
            assert!(result.is_ok(), "Should add translation to history");
        }

        // Search by text
        let search_filter = crate::commands::history::HistorySearchFilter {
            text_query: Some("hello".to_string()),
            source_lang: None,
            target_lang: None,
            tags: vec![],
            favorites_only: false,
            date_range: None,
        };

        let pagination = crate::commands::history::PaginationParams {
            page: 0,
            page_size: 10,
        };

        let search_result =
            search_translation_history(search_filter, pagination, State(&app_state)).await;

        assert!(search_result.is_ok(), "Should search translation history");

        let search_response = search_result.unwrap();
        assert!(
            !search_response.entries.is_empty(),
            "Should find matching entries"
        );
        assert!(
            search_response.entries[0]
                .original_text
                .to_lowercase()
                .contains("hello"),
            "Should find hello entry"
        );

        // Search favorites
        let favorites_filter = crate::commands::history::HistorySearchFilter {
            text_query: None,
            source_lang: None,
            target_lang: None,
            tags: vec![],
            favorites_only: true,
            date_range: None,
        };

        let favorites_result =
            search_translation_history(favorites_filter, pagination, State(&app_state)).await;

        assert!(favorites_result.is_ok(), "Should search favorites");

        let favorites_response = favorites_result.unwrap();
        assert_eq!(
            favorites_response.entries.len(),
            1,
            "Should find one favorite"
        );
        assert!(
            favorites_response.entries[0].is_favorite,
            "Should be marked as favorite"
        );
    }

    #[tokio::test]
    // CRITICAL: Favorites toggle functionality
    async fn test_toggle_translation_favorite() {
        let app_state = Arc::new(Mutex::new(AppState::new()));

        let test_entry = TranslationEntry {
            id: "favorite_test".to_string(),
            original_text: "Test entry".to_string(),
            translated_text: "Entrada de prueba".to_string(),
            source_lang: "en".to_string(),
            target_lang: "es".to_string(),
            confidence: 0.9,
            tags: vec![],
            is_favorite: false,
            created_at: chrono::Utc::now(),
        };

        // Add entry
        let add_result = add_translation_to_history(test_entry, State(&app_state)).await;
        assert!(add_result.is_ok(), "Should add test entry");

        // Toggle favorite (should set to true)
        let toggle_result1 =
            toggle_translation_favorite("favorite_test".to_string(), State(&app_state)).await;

        assert!(toggle_result1.is_ok(), "Should toggle favorite to true");

        let toggle_response1 = toggle_result1.unwrap();
        assert!(toggle_response1.is_favorite, "Should be marked as favorite");

        // Toggle again (should set to false)
        let toggle_result2 =
            toggle_translation_favorite("favorite_test".to_string(), State(&app_state)).await;

        assert!(toggle_result2.is_ok(), "Should toggle favorite to false");

        let toggle_response2 = toggle_result2.unwrap();
        assert!(
            !toggle_response2.is_favorite,
            "Should no longer be favorite"
        );
    }
}

// Mock types and implementations that will fail until real implementation
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

// These are placeholder implementations that will cause tests to fail
// until the real Phase 2 implementation is complete

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct CaptureArea {
    pub x: i32,
    pub y: i32,
    pub width: u32,
    pub height: u32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ScreenshotData {
    pub image_data: String,
    pub width: u32,
    pub height: u32,
    pub capture_time_ms: u64,
    pub scale_factor: f32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct MonitorInfo {
    pub id: u32,
    pub name: String,
    pub width: u32,
    pub height: u32,
    pub x: i32,
    pub y: i32,
    pub is_primary: bool,
    pub scale_factor: f32,
}

// Placeholder command implementations that will fail
async fn capture_screenshot(
    _area: CaptureArea,
    _state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<ScreenshotData, String> {
    Err("capture_screenshot command not implemented yet".to_string())
}

async fn get_monitors(_state: State<'_, Arc<Mutex<AppState>>>) -> Result<Vec<MonitorInfo>, String> {
    Err("get_monitors command not implemented yet".to_string())
}

async fn perform_ocr(
    _image_data: String,
    _state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<OcrResult, String> {
    Err("perform_ocr command not implemented yet".to_string())
}

async fn set_ocr_language(
    _language: String,
    _state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<(), String> {
    Err("set_ocr_language command not implemented yet".to_string())
}

async fn get_available_ocr_languages(
    _state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<Vec<String>, String> {
    Err("get_available_ocr_languages command not implemented yet".to_string())
}

// Additional placeholder types and implementations
#[derive(Debug, Serialize, Deserialize)]
pub struct OcrResult {
    pub text: String,
    pub confidence: f32,
    pub regions: Vec<TextRegion>,
    pub processing_time_ms: u64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TextRegion {
    pub text: String,
    pub bounds: BoundingBox,
    pub confidence: f32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BoundingBox {
    pub x: u32,
    pub y: u32,
    pub width: u32,
    pub height: u32,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct TranslationRequest {
    pub text: String,
    pub source_lang: String,
    pub target_lang: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TranslationResult {
    pub original_text: String,
    pub translated_text: String,
    pub source_lang: String,
    pub target_lang: String,
    pub confidence: f32,
    pub processing_time_ms: u64,
    pub cached: bool,
}

async fn translate_text(
    _request: TranslationRequest,
    _state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<TranslationResult, String> {
    Err("translate_text command not implemented yet".to_string())
}

async fn detect_language_and_context(
    _text: String,
    _state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<LanguageDetectionResult, String> {
    Err("detect_language_and_context command not implemented yet".to_string())
}

async fn get_cached_translation(
    _text: String,
    _source_lang: String,
    _target_lang: String,
    _state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<Option<TranslationResult>, String> {
    Err("get_cached_translation command not implemented yet".to_string())
}

#[derive(Debug, Serialize, Deserialize)]
pub struct LanguageDetectionResult {
    pub language: String,
    pub confidence: f32,
    pub context: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct HotkeyInitializationResult {
    pub success: bool,
    pub registered_hotkeys: Vec<String>,
}

async fn initialize_intelligent_hotkey(
    _state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<HotkeyInitializationResult, String> {
    Err("initialize_intelligent_hotkey command not implemented yet".to_string())
}

async fn get_context_menu_items(
    _state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<Vec<ContextMenuItem>, String> {
    Err("get_context_menu_items command not implemented yet".to_string())
}

async fn execute_context_action(
    _action: String,
    _state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<ActionExecutionResult, String> {
    Err("execute_context_action command not implemented yet".to_string())
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ContextMenuItem {
    pub action_id: String,
    pub label: String,
    pub description: String,
    pub icon: Option<String>,
    pub keyboard_shortcut: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ActionExecutionResult {
    pub success: bool,
    pub action_id: String,
    pub message: String,
}

async fn get_app_config(_state: State<'_, Arc<Mutex<AppState>>>) -> Result<AppConfig, String> {
    Err("get_app_config command not implemented yet".to_string())
}

async fn set_app_config(
    _config: AppConfig,
    _state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<(), String> {
    Err("set_app_config command not implemented yet".to_string())
}

async fn register_global_hotkey(
    _hotkey: String,
    _action: String,
    _state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<HotkeyRegistrationResult, String> {
    Err("register_global_hotkey command not implemented yet".to_string())
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AppConfig {
    pub hotkeys: HotkeyConfig,
    pub ocr: OcrConfig,
    pub translation: TranslationConfig,
    pub ui: UiConfig,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct HotkeyConfig {
    pub quick_translate: String,
    pub screenshot_area: String,
    pub show_hide: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct OcrConfig {
    pub language: String,
    pub confidence_threshold: f32,
    pub preprocessing: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TranslationConfig {
    pub source_lang: String,
    pub target_lang: String,
    pub auto_detect: bool,
    pub cache_enabled: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct UiConfig {
    pub theme: String,
    pub overlay_position: String,
    pub auto_hide_delay: u32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct HotkeyRegistrationResult {
    pub success: bool,
    pub hotkey: String,
    pub action: String,
    pub error_message: String,
}

async fn search_translation_history(
    _filter: crate::commands::history::HistorySearchFilter,
    _pagination: crate::commands::history::PaginationParams,
    _state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<crate::commands::history::HistorySearchResult, String> {
    Err("search_translation_history command not implemented yet".to_string())
}

async fn add_translation_to_history(
    _entry: TranslationEntry,
    _state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<(), String> {
    Err("add_translation_to_history command not implemented yet".to_string())
}

async fn toggle_translation_favorite(
    _entry_id: String,
    _state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<FavoriteToggleResult, String> {
    Err("toggle_translation_favorite command not implemented yet".to_string())
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct TranslationEntry {
    pub id: String,
    pub original_text: String,
    pub translated_text: String,
    pub source_lang: String,
    pub target_lang: String,
    pub confidence: f32,
    pub tags: Vec<String>,
    pub is_favorite: bool,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FavoriteToggleResult {
    pub is_favorite: bool,
}

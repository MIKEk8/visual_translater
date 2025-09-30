//! Phase 2 Services Module Tests - TDD Implementation
//!
//! PHASE 4 TESTS - Currently disabled due to missing implementations
//!
//! This module contains failing tests that define the contracts for Phase 4 services:
//! - Translation service integration with Google Translate API
//! - Intelligent hotkey system with time-based detection
//! - Translation cache with LRU and TTL management
//! - Configuration persistence and real-time updates
//!
//! All tests are designed to FAIL initially and pass once implementation is complete.
//! These tests are temporarily disabled until Phase 4 service implementations are ready.

#![allow(dead_code, unused_imports)]

use super::*;
/* DISABLED UNTIL PHASE 4 - Service implementations not yet available
use crate::services::{
    cache::{
        CacheConfig, CacheStats, HistorySearchFilter, TranslationCacheService, TranslationEntry,
    },
    config::{ConfigObserver, ConfigService},
    hotkey::{GlobalHotkey, HotkeyEvent, HotkeyService},
    intelligent_hotkey::{
        HotkeyAction, IntelligentHotkeyManager, SmartTranslationRequest, TranslationSource,
    },
    translation::{
        GoogleTranslationService, TranslationRequest, TranslationResult, TranslationService,
    },
};
*/
use std::sync::{Arc, Mutex};
use std::time::Duration;

// CRITICAL: Translation Service Integration Tests
// PHASE 4 - All tests in this module are disabled until service implementations are complete
#[cfg(feature = "phase4_services")] // Disabled by default
mod translation_service_tests {
    use super::*;

    #[test]
    // CRITICAL: Real Google Translate API integration
    fn test_real_google_translate_api_integration() {
        let mut translation_service = GoogleTranslationService::new();

        // Should initialize with API key (from environment or config)
        translation_service
            .initialize()
            .expect("Should initialize Google Translate API");
        assert!(
            translation_service.is_available(),
            "Google Translate should be available"
        );

        // Create translation request
        let request = TranslationRequest {
            text: "Hello, world!".to_string(),
            source_lang: "en".to_string(),
            target_lang: "es".to_string(),
        };

        // Should perform real translation (not mock)
        let result = translation_service
            .translate(request)
            .expect("Should translate text");

        // Should return actual Spanish translation
        assert!(
            !result.translated_text.is_empty(),
            "Should return translated text"
        );
        assert_ne!(
            result.translated_text, result.original_text,
            "Translation should be different from original"
        );
        assert_eq!(result.source_lang, "en");
        assert_eq!(result.target_lang, "es");
        assert!(
            result.confidence > 0.0 && result.confidence <= 1.0,
            "Should have valid confidence score"
        );

        // Real translation should contain Spanish words
        let spanish_translation = result.translated_text.to_lowercase();
        // Common Spanish translations for "Hello, world!"
        assert!(
            spanish_translation.contains("hola")
                || spanish_translation.contains("mundo")
                || spanish_translation.contains("¡hola"),
            "Should contain Spanish translation: '{}'",
            result.translated_text
        );
    }

    #[test]
    // CRITICAL: Language detection with real API
    fn test_real_language_detection() {
        let mut translation_service = GoogleTranslationService::new();
        translation_service.initialize().expect("Should initialize");

        // Test various languages
        let test_cases = vec![
            ("Hello world", "en"),
            ("Bonjour le monde", "fr"),
            ("Hola mundo", "es"),
            ("Привет мир", "ru"),
            ("こんにちは世界", "ja"),
        ];

        for (text, expected_lang) in test_cases {
            let detected = translation_service
                .detect_language(text)
                .expect("Should detect language");

            // Should detect correct language (allowing for close variants)
            assert!(
                detected.language == expected_lang
                    || detected.language.starts_with(&expected_lang[..2]),
                "Should detect {} for '{}', got '{}'",
                expected_lang,
                text,
                detected.language
            );
            assert!(
                detected.confidence > 0.5,
                "Should have reasonable confidence for language detection"
            );
        }
    }

    #[test]
    // CRITICAL: Translation caching and performance
    fn test_translation_caching_performance() {
        let mut translation_service = GoogleTranslationService::new();
        translation_service.initialize().expect("Should initialize");

        let request = TranslationRequest {
            text: "Cache test text".to_string(),
            source_lang: "en".to_string(),
            target_lang: "fr".to_string(),
        };

        // First translation (should hit API)
        let start = std::time::Instant::now();
        let result1 = translation_service
            .translate(request.clone())
            .expect("Should translate");
        let first_duration = start.elapsed();

        // Second translation (should use cache)
        let start = std::time::Instant::now();
        let result2 = translation_service
            .translate(request)
            .expect("Should translate from cache");
        let cached_duration = start.elapsed();

        // Results should be identical
        assert_eq!(result1.translated_text, result2.translated_text);
        assert_eq!(result1.source_lang, result2.source_lang);
        assert_eq!(result1.target_lang, result2.target_lang);

        // Cached translation should be marked as cached
        assert!(result2.cached, "Second translation should be from cache");

        // Cached translation should be significantly faster
        assert!(
            cached_duration < first_duration / 2,
            "Cached translation should be faster: {}ms vs {}ms",
            cached_duration.as_millis(),
            first_duration.as_millis()
        );
    }

    #[test]
    // CRITICAL: Error handling for API failures
    fn test_translation_error_handling() {
        let mut translation_service = GoogleTranslationService::new();

        // Test with invalid API key or no network
        let invalid_request = TranslationRequest {
            text: "".to_string(), // Empty text
            source_lang: "invalid".to_string(),
            target_lang: "invalid".to_string(),
        };

        let result = translation_service.translate(invalid_request);

        // Should handle errors gracefully
        match result {
            Ok(_) => {
                // If successful, should have fallback behavior
            }
            Err(e) => {
                // Should provide clear error message
                assert!(
                    !e.to_string().is_empty(),
                    "Error message should not be empty"
                );
            }
        }

        // Test with very long text
        let long_text_request = TranslationRequest {
            text: "A".repeat(10000), // Very long text
            source_lang: "en".to_string(),
            target_lang: "es".to_string(),
        };

        let result = translation_service.translate(long_text_request);
        // Should either succeed or provide clear error about text length
        match result {
            Ok(translation) => {
                assert!(!translation.translated_text.is_empty());
            }
            Err(e) => {
                assert!(e.to_string().contains("length") || e.to_string().contains("long"));
            }
        }
    }
}

// CRITICAL: Intelligent Hotkey System Tests
#[cfg(feature = "phase4_services")] // Disabled by default
mod intelligent_hotkey_tests {
    use super::*;

    #[test]
    // CRITICAL: Time-based Alt+A detection
    fn test_time_based_alt_a_detection() {
        let mut hotkey_manager = IntelligentHotkeyManager::new();
        hotkey_manager
            .initialize()
            .expect("Should initialize hotkey manager");

        // Enable Alt+A intelligent detection
        hotkey_manager
            .enable_intelligent_alt_a()
            .expect("Should enable Alt+A detection");

        // Simulate quick press (< 1 second)
        let quick_press_event = HotkeyEvent {
            hotkey: "Alt+A".to_string(),
            press_duration: Duration::from_millis(500),
            timestamp: std::time::Instant::now(),
        };

        let action = hotkey_manager
            .process_hotkey_event(quick_press_event)
            .expect("Should process quick press");

        // Should trigger smart translation action
        assert_eq!(
            action,
            HotkeyAction::SmartTranslation,
            "Quick press should trigger smart translation"
        );

        // Simulate long press (>= 1 second)
        let long_press_event = HotkeyEvent {
            hotkey: "Alt+A".to_string(),
            press_duration: Duration::from_millis(1200),
            timestamp: std::time::Instant::now(),
        };

        let action = hotkey_manager
            .process_hotkey_event(long_press_event)
            .expect("Should process long press");

        // Should trigger context menu action
        assert_eq!(
            action,
            HotkeyAction::ShowContextMenu,
            "Long press should show context menu"
        );
    }

    #[test]
    // CRITICAL: Smart translation source prioritization
    fn test_smart_translation_source_prioritization() {
        let mut hotkey_manager = IntelligentHotkeyManager::new();
        hotkey_manager.initialize().expect("Should initialize");

        // Test with selected text (highest priority)
        let request_with_selection = SmartTranslationRequest {
            selected_text: Some("Selected text for translation".to_string()),
            clipboard_text: Some("Clipboard text".to_string()),
            clipboard_image: None,
            previous_area: None,
        };

        let source = hotkey_manager
            .determine_translation_source(&request_with_selection)
            .expect("Should determine source");

        assert_eq!(
            source,
            TranslationSource::SelectedText,
            "Should prioritize selected text"
        );

        // Test with clipboard text (second priority)
        let request_with_clipboard = SmartTranslationRequest {
            selected_text: None,
            clipboard_text: Some("Clipboard text for translation".to_string()),
            clipboard_image: None,
            previous_area: None,
        };

        let source = hotkey_manager
            .determine_translation_source(&request_with_clipboard)
            .expect("Should determine source");

        assert_eq!(
            source,
            TranslationSource::ClipboardText,
            "Should use clipboard text when no selection"
        );

        // Test with clipboard image (third priority)
        let request_with_image = SmartTranslationRequest {
            selected_text: None,
            clipboard_text: None,
            clipboard_image: Some(vec![1, 2, 3, 4]), // Mock image data
            previous_area: None,
        };

        let source = hotkey_manager
            .determine_translation_source(&request_with_image)
            .expect("Should determine source");

        assert_eq!(
            source,
            TranslationSource::ClipboardImage,
            "Should use clipboard image when no text"
        );

        // Test with previous area (fourth priority)
        let request_with_previous = SmartTranslationRequest {
            selected_text: None,
            clipboard_text: None,
            clipboard_image: None,
            previous_area: Some((100, 100, 300, 200)),
        };

        let source = hotkey_manager
            .determine_translation_source(&request_with_previous)
            .expect("Should determine source");

        assert_eq!(
            source,
            TranslationSource::PreviousArea,
            "Should use previous area when no clipboard content"
        );

        // Test with nothing available (should trigger new selection)
        let empty_request = SmartTranslationRequest {
            selected_text: None,
            clipboard_text: None,
            clipboard_image: None,
            previous_area: None,
        };

        let source = hotkey_manager
            .determine_translation_source(&empty_request)
            .expect("Should determine source");

        assert_eq!(
            source,
            TranslationSource::NewSelection,
            "Should trigger new selection when nothing available"
        );
    }

    #[test]
    // CRITICAL: Previous area memory management
    fn test_previous_area_memory_management() {
        let mut hotkey_manager = IntelligentHotkeyManager::new();
        hotkey_manager.initialize().expect("Should initialize");

        // Add several previous areas
        let areas = vec![
            (100, 100, 300, 200),
            (400, 200, 250, 150),
            (50, 50, 500, 300),
            (200, 300, 400, 250),
            (0, 0, 800, 600),
        ];

        for area in &areas {
            hotkey_manager
                .add_previous_area(*area, "Test area".to_string())
                .expect("Should add previous area");
        }

        // Should remember areas in order
        let remembered_areas = hotkey_manager
            .get_previous_areas(None)
            .expect("Should get previous areas");
        assert!(!remembered_areas.is_empty(), "Should have remembered areas");
        assert!(
            remembered_areas.len() <= 5,
            "Should limit number of remembered areas"
        );

        // Most recent area should be first
        assert_eq!(
            remembered_areas[0].coordinates,
            areas[areas.len() - 1],
            "Most recent area should be first"
        );

        // Should be able to clear previous areas
        hotkey_manager
            .clear_previous_areas()
            .expect("Should clear previous areas");
        let cleared_areas = hotkey_manager
            .get_previous_areas(None)
            .expect("Should get cleared areas");
        assert!(
            cleared_areas.is_empty(),
            "Should have no areas after clearing"
        );
    }

    #[test]
    // CRITICAL: Hotkey performance and timing accuracy
    fn test_hotkey_timing_accuracy() {
        let mut hotkey_manager = IntelligentHotkeyManager::new();
        hotkey_manager.initialize().expect("Should initialize");

        // Test timing accuracy for edge cases
        let edge_cases = vec![
            (Duration::from_millis(999), HotkeyAction::SmartTranslation), // Just under 1 second
            (Duration::from_millis(1000), HotkeyAction::ShowContextMenu), // Exactly 1 second
            (Duration::from_millis(1001), HotkeyAction::ShowContextMenu), // Just over 1 second
        ];

        for (duration, expected_action) in edge_cases {
            let event = HotkeyEvent {
                hotkey: "Alt+A".to_string(),
                press_duration: duration,
                timestamp: std::time::Instant::now(),
            };

            let action = hotkey_manager
                .process_hotkey_event(event)
                .expect("Should process edge case");
            assert_eq!(
                action,
                expected_action,
                "Timing accuracy failed for {}ms",
                duration.as_millis()
            );
        }

        // Test performance stats
        let stats = hotkey_manager
            .get_performance_stats()
            .expect("Should get performance stats");
        assert!(
            stats.average_detection_time_ms < 50.0,
            "Detection should be fast (<50ms)"
        );
    }
}

// CRITICAL: Translation Cache Service Tests
#[cfg(feature = "phase4_services")] // Disabled by default
mod translation_cache_tests {
    use super::*;

    #[test]
    // CRITICAL: LRU cache with TTL management
    fn test_lru_cache_with_ttl_management() {
        let cache_config = CacheConfig {
            max_entries: 3,
            ttl_seconds: 2, // Short TTL for testing
            enable_persistence: false,
        };

        let mut cache_service = TranslationCacheService::new(cache_config);
        cache_service.initialize().expect("Should initialize cache");

        // Add entries to fill cache
        let entries = vec![
            TranslationEntry {
                id: "1".to_string(),
                original_text: "Hello".to_string(),
                translated_text: "Hola".to_string(),
                source_lang: "en".to_string(),
                target_lang: "es".to_string(),
                confidence: 0.95,
                created_at: chrono::Utc::now(),
                ..Default::default()
            },
            TranslationEntry {
                id: "2".to_string(),
                original_text: "World".to_string(),
                translated_text: "Mundo".to_string(),
                source_lang: "en".to_string(),
                target_lang: "es".to_string(),
                confidence: 0.92,
                created_at: chrono::Utc::now(),
                ..Default::default()
            },
            TranslationEntry {
                id: "3".to_string(),
                original_text: "Test".to_string(),
                translated_text: "Prueba".to_string(),
                source_lang: "en".to_string(),
                target_lang: "es".to_string(),
                confidence: 0.88,
                created_at: chrono::Utc::now(),
                ..Default::default()
            },
        ];

        // Add all entries
        for entry in &entries {
            cache_service
                .add_translation(entry.clone())
                .expect("Should add entry");
        }

        // Should have all entries
        let stats = cache_service.get_stats().expect("Should get stats");
        assert_eq!(stats.total_entries, 3, "Should have 3 entries");

        // Add fourth entry (should evict oldest)
        let fourth_entry = TranslationEntry {
            id: "4".to_string(),
            original_text: "New".to_string(),
            translated_text: "Nuevo".to_string(),
            source_lang: "en".to_string(),
            target_lang: "es".to_string(),
            confidence: 0.90,
            created_at: chrono::Utc::now(),
            ..Default::default()
        };

        cache_service
            .add_translation(fourth_entry)
            .expect("Should add fourth entry");

        // Should still have max entries
        let stats = cache_service
            .get_stats()
            .expect("Should get stats after eviction");
        assert_eq!(stats.total_entries, 3, "Should maintain max entries limit");

        // Wait for TTL expiration
        std::thread::sleep(Duration::from_secs(3));

        // Cleanup expired entries
        let expired_count = cache_service
            .cleanup_expired()
            .expect("Should cleanup expired");
        assert!(expired_count > 0, "Should have cleaned up expired entries");

        // Should have fewer entries after TTL cleanup
        let stats_after_ttl = cache_service
            .get_stats()
            .expect("Should get stats after TTL cleanup");
        assert!(
            stats_after_ttl.total_entries < 3,
            "Should have fewer entries after TTL cleanup"
        );
    }

    #[test]
    // CRITICAL: Translation history search and filtering
    fn test_translation_history_search_filtering() {
        let cache_config = CacheConfig::default();
        let mut cache_service = TranslationCacheService::new(cache_config);
        cache_service.initialize().expect("Should initialize cache");

        // Add diverse test entries
        let test_entries = vec![
            TranslationEntry {
                original_text: "Programming is fun".to_string(),
                translated_text: "La programación es divertida".to_string(),
                source_lang: "en".to_string(),
                target_lang: "es".to_string(),
                tags: vec!["programming".to_string(), "tech".to_string()],
                is_favorite: true,
                ..Default::default()
            },
            TranslationEntry {
                original_text: "Hello world".to_string(),
                translated_text: "Hola mundo".to_string(),
                source_lang: "en".to_string(),
                target_lang: "es".to_string(),
                tags: vec!["greeting".to_string()],
                is_favorite: false,
                ..Default::default()
            },
            TranslationEntry {
                original_text: "Good morning".to_string(),
                translated_text: "Bonjour".to_string(),
                source_lang: "en".to_string(),
                target_lang: "fr".to_string(),
                tags: vec!["greeting".to_string()],
                is_favorite: false,
                ..Default::default()
            },
        ];

        for entry in &test_entries {
            cache_service
                .add_translation(entry.clone())
                .expect("Should add test entry");
        }

        // Test text search
        let text_filter = HistorySearchFilter {
            text_query: Some("programming".to_string()),
            source_lang: None,
            target_lang: None,
            tags: vec![],
            favorites_only: false,
            date_range: None,
        };

        let pagination = crate::services::cache::PaginationParams {
            page: 0,
            page_size: 10,
        };

        let search_result = cache_service
            .search_history(&text_filter, &pagination)
            .expect("Should search by text");

        assert_eq!(
            search_result.entries.len(),
            1,
            "Should find one programming entry"
        );
        assert!(search_result.entries[0]
            .original_text
            .contains("Programming"));

        // Test language filtering
        let lang_filter = HistorySearchFilter {
            text_query: None,
            source_lang: Some("en".to_string()),
            target_lang: Some("fr".to_string()),
            tags: vec![],
            favorites_only: false,
            date_range: None,
        };

        let lang_result = cache_service
            .search_history(&lang_filter, &pagination)
            .expect("Should search by language");

        assert_eq!(lang_result.entries.len(), 1, "Should find one en->fr entry");
        assert_eq!(lang_result.entries[0].target_lang, "fr");

        // Test favorites filtering
        let favorites_filter = HistorySearchFilter {
            text_query: None,
            source_lang: None,
            target_lang: None,
            tags: vec![],
            favorites_only: true,
            date_range: None,
        };

        let favorites_result = cache_service
            .search_history(&favorites_filter, &pagination)
            .expect("Should search favorites");

        assert_eq!(
            favorites_result.entries.len(),
            1,
            "Should find one favorite entry"
        );
        assert!(favorites_result.entries[0].is_favorite);

        // Test tag filtering
        let tag_filter = HistorySearchFilter {
            text_query: None,
            source_lang: None,
            target_lang: None,
            tags: vec!["greeting".to_string()],
            favorites_only: false,
            date_range: None,
        };

        let tag_result = cache_service
            .search_history(&tag_filter, &pagination)
            .expect("Should search by tags");

        assert_eq!(
            tag_result.entries.len(),
            2,
            "Should find two greeting entries"
        );
    }

    #[test]
    // CRITICAL: Similar translation detection using Levenshtein distance
    fn test_similar_translation_detection() {
        let cache_config = CacheConfig::default();
        let mut cache_service = TranslationCacheService::new(cache_config);
        cache_service.initialize().expect("Should initialize cache");

        // Add base entry
        let base_entry = TranslationEntry {
            original_text: "Hello world".to_string(),
            translated_text: "Hola mundo".to_string(),
            source_lang: "en".to_string(),
            target_lang: "es".to_string(),
            ..Default::default()
        };

        cache_service
            .add_translation(base_entry)
            .expect("Should add base entry");

        // Add similar entries
        let similar_entries = vec![
            "Hello world!",              // Very similar (punctuation)
            "Hello, world",              // Similar (punctuation)
            "Hello world today",         // Similar (added word)
            "Hi world",                  // Somewhat similar
            "Completely different text", // Not similar
        ];

        for text in &similar_entries {
            let entry = TranslationEntry {
                original_text: text.to_string(),
                translated_text: format!("Translation of {}", text),
                source_lang: "en".to_string(),
                target_lang: "es".to_string(),
                ..Default::default()
            };
            cache_service
                .add_translation(entry)
                .expect("Should add similar entry");
        }

        // Find similar translations
        let similar = cache_service
            .get_similar_translations("Hello world", 3)
            .expect("Should find similar translations");

        // Should find similar entries but not completely different ones
        assert!(
            similar.len() >= 2,
            "Should find at least 2 similar translations"
        );
        assert!(
            similar.len() <= 4,
            "Should not find completely different translations"
        );

        // Results should be ordered by similarity
        let distances: Vec<_> = similar
            .iter()
            .map(|entry| levenshtein_distance("Hello world", &entry.original_text))
            .collect();

        for i in 1..distances.len() {
            assert!(
                distances[i] >= distances[i - 1],
                "Results should be ordered by similarity"
            );
        }
    }

    // Helper function for Levenshtein distance calculation
    fn levenshtein_distance(s1: &str, s2: &str) -> usize {
        let len1 = s1.chars().count();
        let len2 = s2.chars().count();

        if len1 == 0 {
            return len2;
        }
        if len2 == 0 {
            return len1;
        }

        let mut matrix = vec![vec![0; len2 + 1]; len1 + 1];

        for i in 0..=len1 {
            matrix[i][0] = i;
        }
        for j in 0..=len2 {
            matrix[0][j] = j;
        }

        let s1_chars: Vec<char> = s1.chars().collect();
        let s2_chars: Vec<char> = s2.chars().collect();

        for i in 1..=len1 {
            for j in 1..=len2 {
                let cost = if s1_chars[i - 1] == s2_chars[j - 1] {
                    0
                } else {
                    1
                };
                matrix[i][j] = std::cmp::min(
                    std::cmp::min(matrix[i - 1][j] + 1, matrix[i][j - 1] + 1),
                    matrix[i - 1][j - 1] + cost,
                );
            }
        }

        matrix[len1][len2]
    }
}

// CRITICAL: Configuration Service Tests
#[cfg(feature = "phase4_services")] // Disabled by default
mod config_service_tests {
    use super::*;

    #[test]
    // CRITICAL: Real-time configuration updates with observers
    fn test_realtime_config_updates_with_observers() {
        let mut config_service = ConfigService::new();
        config_service
            .initialize()
            .expect("Should initialize config service");

        // Add observer
        let observer_called = Arc::new(Mutex::new(false));
        let observer_called_clone = observer_called.clone();

        config_service.add_observer(Box::new(move |key, _old_value, _new_value| {
            println!("Config changed: {}", key);
            *observer_called_clone.lock().unwrap() = true;
        }));

        // Update configuration
        config_service
            .set_config_value("translation.target_lang", "fr")
            .expect("Should update config value");

        // Observer should be called immediately
        assert!(
            *observer_called.lock().unwrap(),
            "Observer should be called on config change"
        );

        // Configuration should persist
        let value = config_service
            .get_config_value("translation.target_lang")
            .expect("Should get config value");
        assert_eq!(value, "fr", "Config value should be persisted");
    }

    #[test]
    // CRITICAL: Configuration validation and error handling
    fn test_configuration_validation_error_handling() {
        let mut config_service = ConfigService::new();
        config_service
            .initialize()
            .expect("Should initialize config service");

        // Test invalid hotkey combination
        let invalid_hotkey_result =
            config_service.set_config_value("hotkeys.quick_translate", "InvalidKey+Combo");

        match invalid_hotkey_result {
            Ok(_) => {
                // If accepted, should validate and normalize the hotkey
                let normalized = config_service
                    .get_config_value("hotkeys.quick_translate")
                    .expect("Should get normalized hotkey");
                assert!(!normalized.is_empty(), "Should have normalized hotkey");
            }
            Err(e) => {
                // Should provide clear validation error
                assert!(
                    e.to_string().contains("hotkey") || e.to_string().contains("invalid"),
                    "Error should mention hotkey validation: {}",
                    e
                );
            }
        }

        // Test invalid confidence threshold
        let invalid_confidence_result =
            config_service.set_config_value("ocr.confidence_threshold", "1.5");

        match invalid_confidence_result {
            Ok(_) => {
                // If accepted, should clamp to valid range
                let clamped = config_service
                    .get_config_value("ocr.confidence_threshold")
                    .expect("Should get clamped confidence");
                let confidence: f32 = clamped.parse().expect("Should parse as float");
                assert!(
                    confidence >= 0.0 && confidence <= 1.0,
                    "Should clamp confidence to valid range"
                );
            }
            Err(e) => {
                // Should provide clear validation error
                assert!(
                    e.to_string().contains("confidence") || e.to_string().contains("range"),
                    "Error should mention confidence validation: {}",
                    e
                );
            }
        }

        // Test invalid language code
        let invalid_lang_result =
            config_service.set_config_value("translation.source_lang", "invalid_lang_code");

        match invalid_lang_result {
            Ok(_) => {
                // If accepted, should validate or fall back to default
                let lang = config_service
                    .get_config_value("translation.source_lang")
                    .expect("Should get language");
                assert!(
                    lang.len() >= 2 && lang.len() <= 5,
                    "Should have valid language code format"
                );
            }
            Err(e) => {
                // Should provide clear validation error
                assert!(
                    e.to_string().contains("language") || e.to_string().contains("invalid"),
                    "Error should mention language validation: {}",
                    e
                );
            }
        }
    }

    #[test]
    // CRITICAL: Configuration persistence across restarts
    fn test_configuration_persistence_across_restarts() {
        let temp_dir = tempfile::TempDir::new().expect("Should create temp dir");
        let config_path = temp_dir.path().join("test_config.json");

        // First instance: set configuration
        {
            let mut config_service = ConfigService::with_path(config_path.clone());
            config_service
                .initialize()
                .expect("Should initialize first instance");

            config_service
                .set_config_value("translation.target_lang", "de")
                .expect("Should set target language");
            config_service
                .set_config_value("ocr.confidence_threshold", "0.75")
                .expect("Should set confidence threshold");

            // Force save
            config_service.save_config().expect("Should save config");
        }

        // Second instance: load configuration
        {
            let mut config_service = ConfigService::with_path(config_path);
            config_service
                .initialize()
                .expect("Should initialize second instance");

            // Should load persisted values
            let target_lang = config_service
                .get_config_value("translation.target_lang")
                .expect("Should get persisted target language");
            assert_eq!(target_lang, "de", "Should load persisted target language");

            let confidence = config_service
                .get_config_value("ocr.confidence_threshold")
                .expect("Should get persisted confidence");
            assert_eq!(
                confidence, "0.75",
                "Should load persisted confidence threshold"
            );
        }
    }
}

// Placeholder types and implementations for compilation
use std::fmt;

// HotkeyAction and TranslationSource removed - using imports from actual modules

pub struct HotkeyEvent {
    pub hotkey: String,
    pub press_duration: Duration,
    pub timestamp: std::time::Instant,
}

// All duplicate types removed - using imports from actual modules
// TranslationEntry Default impl disabled - not available until Phase 4
// CacheConfig, CacheStats, TranslationEntry removed - using imports from actual modules

// HistorySearchFilter removed - using import from actual module

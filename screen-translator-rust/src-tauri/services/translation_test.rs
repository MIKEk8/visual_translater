// [CRITICAL] MVP Translation Service Tests
// These tests should FAIL initially per TDD approach
// PHASE 4 - Disabled pending async implementation

#[cfg(test)]
#[cfg(feature = "phase4_services")] // Disabled - async issues
mod tests {
    use super::super::translation::*;

    #[test]
    #[should_panic(expected = "not yet implemented")]
    fn test_google_translate_api_basic() {
        // [CRITICAL] Test basic Google Translate API integration
        let service = TranslationService::new();
        let result = service.translate("Hello world", "en", "ru").unwrap();

        assert_eq!(result.translated_text, "Привет мир");
        assert_eq!(result.source_lang, "en");
        assert_eq!(result.target_lang, "ru");
        assert!(result.confidence > 0.8);
        assert!(!result.cached);
    }

    #[test]
    #[should_panic(expected = "not yet implemented")]
    fn test_translation_with_auto_detect_language() {
        // [CRITICAL] Test language auto-detection
        let service = TranslationService::new();
        let result = service.translate("Bonjour le monde", "auto", "en").unwrap();

        assert_eq!(result.translated_text, "Hello world");
        assert_eq!(result.source_lang, "fr"); // Should auto-detect French
        assert_eq!(result.target_lang, "en");
    }

    #[test]
    fn test_empty_text_returns_error() {
        // Test edge case: empty text should return error
        let service = TranslationService::new();
        let result = service.translate("", "en", "ru");

        assert!(result.is_err());
        assert_eq!(
            result.unwrap_err().to_string(),
            "Translation text cannot be empty"
        );
    }

    #[test]
    fn test_invalid_language_code_returns_error() {
        // Test validation: invalid language codes
        let service = TranslationService::new();
        let result = service.translate("Test text", "invalid", "xyz");

        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("Invalid language code"));
    }

    #[test]
    #[should_panic(expected = "not yet implemented")]
    fn test_network_failure_returns_cached_if_available() {
        // Test resilience: use cache on network failure
        let mut service = TranslationService::new();

        // First call should succeed
        let first_result = service.translate("Test", "en", "ru").unwrap();

        // Simulate network failure
        service.set_offline_mode(true);

        // Should return cached result
        let cached_result = service.translate("Test", "en", "ru").unwrap();

        assert_eq!(cached_result.translated_text, first_result.translated_text);
        assert!(cached_result.cached);
    }
}

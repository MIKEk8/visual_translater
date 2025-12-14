// Core functionality tests using real implementations
// These tests verify the Phase 2 implementation works

use screen_translator::services::translation::{TranslationRequest, TranslationService};
use screen_translator::services::translation_async::AsyncTranslationService;

#[tokio::test]
async fn test_translation_service_initialization() {
    let mut service = TranslationService::new();

    // Test basic translation (should use mock provider)
    let request = TranslationRequest {
        text: "Hello".to_string(),
        source_lang: "en".to_string(),
        target_lang: "ru".to_string(),
        context: None,
    };
    let result = service.translate(request).await;

    assert!(result.is_ok(), "Translation should work with mock provider");

    let translation = result.unwrap();
    assert!(
        !translation.translated_text.is_empty(),
        "Should return translated text"
    );
    assert_eq!(translation.source_lang, "en");
    assert_eq!(translation.target_lang, "ru");
    assert!(translation.confidence > 0.0, "Should have some confidence");
}

#[tokio::test]
async fn test_translation_caching() {
    let mut service = TranslationService::new();

    let text = "Test caching";

    // First translation
    let start1 = std::time::Instant::now();
    let request1 = TranslationRequest {
        text: text.to_string(),
        source_lang: "en".to_string(),
        target_lang: "ru".to_string(),
        context: None,
    };
    let result1 = service.translate(request1).await;
    let duration1 = start1.elapsed();

    assert!(result1.is_ok(), "First translation should succeed");

    // Second translation (should be cached)
    let start2 = std::time::Instant::now();
    let request2 = TranslationRequest {
        text: text.to_string(),
        source_lang: "en".to_string(),
        target_lang: "ru".to_string(),
        context: None,
    };
    let result2 = service.translate(request2).await;
    let duration2 = start2.elapsed();

    assert!(result2.is_ok(), "Second translation should succeed");

    // Cache should make it faster (or at least not slower)
    assert!(
        duration2 <= duration1 * 2,
        "Cached translation should not be significantly slower"
    );

    // Results should be identical
    let trans1 = result1.unwrap();
    let trans2 = result2.unwrap();
    assert_eq!(trans1.translated_text, trans2.translated_text);
}

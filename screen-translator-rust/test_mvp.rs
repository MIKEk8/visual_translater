// Simple MVP test to verify core functionality

use screen_translator::services::translation::TranslationService;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize logging
    env_logger::init();

    println!("Testing MVP Translation Service...");

    let rt = tokio::runtime::Runtime::new()?;

    rt.block_on(async {
        // Test TranslationService
        let mut service = TranslationService::new();

        let request = screen_translator::services::translation::TranslationRequest {
            text: "Hello, world!".to_string(),
            source_lang: "en".to_string(),
            target_lang: "ru".to_string(),
            context: None,
        };

        println!(
            "Translating: '{}' from {} to {}",
            request.text, request.source_lang, request.target_lang
        );

        match service.translate(request).await {
            Ok(result) => {
                println!("Translation successful!");
                println!("Original: {}", result.original_text);
                println!("Translated: {}", result.translated_text);
                println!("Confidence: {}", result.confidence);
                println!("Provider: {}", result.provider);
            }
            Err(e) => {
                println!("Translation failed: {}", e);
                std::process::exit(1);
            }
        }
    });

    println!("MVP Translation Service test completed successfully!");
    Ok(())
}

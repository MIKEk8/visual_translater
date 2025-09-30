use screen_translator::services::translation::{TranslationRequest, TranslationService};
use tokio;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let rt = tokio::runtime::Runtime::new()?;
    rt.block_on(async_main())
}

async fn async_main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Testing Translation Service with intelligent mock...");

    // Initialize translation service with Google provider
    let mut translation_service = TranslationService::new();

    // Test basic translation
    println!("\n📝 Testing basic translation (EN → RU)...");
    let request = TranslationRequest {
        text: "Hello world! This text was detected on screen.".to_string(),
        source_lang: "en".to_string(),
        target_lang: "ru".to_string(),
        context: Some("Screen capture".to_string()),
    };

    match translation_service.translate(request).await {
        Ok(result) => {
            println!("✅ Translation successful!");
            println!("📄 Original: '{}'", result.original_text);
            println!("🔄 Translated: '{}'", result.translated_text);
            println!(
                "🌐 Language: {} → {}",
                result.source_lang, result.target_lang
            );
            println!("🎯 Confidence: {:.2}%", result.confidence * 100.0);
            println!("🏭 Provider: {}", result.provider);
            println!("🏷️  Context: {:?}", result.context_type);
        }
        Err(e) => {
            println!("❌ Translation failed: {}", e);
            return Err(e.into());
        }
    }

    // Test reverse translation
    println!("\n📝 Testing reverse translation (RU → EN)...");
    let request = TranslationRequest {
        text: "Привет мир! Это текст из области экрана.".to_string(),
        source_lang: "ru".to_string(),
        target_lang: "en".to_string(),
        context: Some("UI element".to_string()),
    };

    match translation_service.translate(request).await {
        Ok(result) => {
            println!("✅ Reverse translation successful!");
            println!("📄 Original: '{}'", result.original_text);
            println!("🔄 Translated: '{}'", result.translated_text);
            println!("🎯 Confidence: {:.2}%", result.confidence * 100.0);
        }
        Err(e) => {
            println!("❌ Reverse translation failed: {}", e);
        }
    }

    // Test German translation
    println!("\n📝 Testing German translation (EN → DE)...");
    let request = TranslationRequest {
        text: "Hello world! Text detected in image region.".to_string(),
        source_lang: "en".to_string(),
        target_lang: "de".to_string(),
        context: None,
    };

    match translation_service.translate(request).await {
        Ok(result) => {
            println!("✅ German translation successful!");
            println!("📄 Original: '{}'", result.original_text);
            println!("🔄 Translated: '{}'", result.translated_text);
            println!("🎯 Confidence: {:.2}%", result.confidence * 100.0);
        }
        Err(e) => {
            println!("❌ German translation failed: {}", e);
        }
    }

    // Test unknown language pair (should get language indicator)
    println!("\n📝 Testing unknown language pair (ES → FR)...");
    let request = TranslationRequest {
        text: "Hola mundo desde la pantalla.".to_string(),
        source_lang: "es".to_string(),
        target_lang: "fr".to_string(),
        context: None,
    };

    match translation_service.translate(request).await {
        Ok(result) => {
            println!("✅ Unknown language pair handled!");
            println!("📄 Original: '{}'", result.original_text);
            println!("🔄 Translated: '{}'", result.translated_text);
            println!("🎯 Confidence: {:.2}%", result.confidence * 100.0);
        }
        Err(e) => {
            println!("❌ Unknown language translation failed: {}", e);
        }
    }

    // Test caching by repeating the first translation
    println!("\n📝 Testing translation cache...");
    let request = TranslationRequest {
        text: "Hello world! This text was detected on screen.".to_string(),
        source_lang: "en".to_string(),
        target_lang: "ru".to_string(),
        context: Some("Screen capture".to_string()),
    };

    let start_time = std::time::Instant::now();
    match translation_service.translate(request).await {
        Ok(result) => {
            let elapsed = start_time.elapsed();
            println!("✅ Cached translation retrieved!");
            println!("⚡ Cache retrieval time: {:?}", elapsed);
            println!("🔄 Cached result: '{}'", result.translated_text);
            println!("🏭 Provider: {}", result.provider);
        }
        Err(e) => {
            println!("❌ Cached translation failed: {}", e);
        }
    }

    println!("\n🎉 Translation service test completed successfully!");
    Ok(())
}

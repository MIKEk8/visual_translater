use screen_translator::core::ocr::{OcrConfig, OcrEngine, TesseractOcr};
use screen_translator::core::screenshot::{CaptureArea, ScreenshotCapture, WindowsScreenshot};
use tokio;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let rt = tokio::runtime::Runtime::new()?;
    rt.block_on(async_main())
}

async fn async_main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Testing OCR with real screenshots...");

    // Initialize screenshot service
    let mut screenshot = WindowsScreenshot::new();
    screenshot
        .initialize()
        .expect("Should initialize screenshot service");

    // Capture a small area from the screen
    let test_area = CaptureArea {
        x: 100,
        y: 100,
        width: 400,
        height: 200,
    };

    println!("📸 Capturing screenshot for OCR test...");
    let image = screenshot.capture_area(test_area).await?;
    println!(
        "✅ Screenshot captured: {}x{}",
        image.width(),
        image.height()
    );

    // Initialize OCR engine
    let mut ocr = TesseractOcr::new();
    let config = OcrConfig::default();

    println!("\n🔤 Initializing OCR engine...");
    ocr.initialize(&config)?;
    println!(
        "✅ OCR engine initialized with language: {}",
        config.language
    );

    // Test OCR on the screenshot
    println!("\n📝 Running OCR on screenshot...");
    match ocr.extract_text(&image) {
        Ok(result) => {
            println!("✅ OCR completed successfully!");
            println!("📄 Extracted text: '{}'", result.text);
            println!("🎯 Confidence: {:.2}%", result.confidence * 100.0);
            println!("🌐 Language: {}", result.language);
            println!("⏱️  Processing time: {}ms", result.processing_time_ms);
            println!("📍 Text regions found: {}", result.regions.len());

            for (i, region) in result.regions.iter().enumerate() {
                println!(
                    "   Region {}: {}x{} at ({}, {}) - confidence: {:.2}%",
                    i + 1,
                    region.width,
                    region.height,
                    region.x,
                    region.y,
                    region.confidence * 100.0
                );
            }
        }
        Err(e) => {
            println!("❌ OCR failed: {}", e);
            return Err(e.into());
        }
    }

    // Test supported languages
    println!("\n🌍 Supported languages:");
    let languages = ocr.get_supported_languages();
    for lang in languages {
        println!("   - {}", lang);
    }

    // Test engine info
    println!("\n🔧 Engine information:");
    let info = ocr.get_info();
    for (key, value) in info {
        println!("   {}: {}", key, value);
    }

    println!("\n🎉 OCR test completed successfully!");
    Ok(())
}

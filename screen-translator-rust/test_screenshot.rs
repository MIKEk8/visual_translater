use screen_translator::core::screenshot::{CaptureArea, ScreenshotCapture, WindowsScreenshot};
use tokio;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let rt = tokio::runtime::Runtime::new()?;
    rt.block_on(async_main())
}

async fn async_main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Testing screenshot capture...");

    let mut screenshot = WindowsScreenshot::new();

    // Initialize the screenshot service
    match screenshot.initialize() {
        Ok(()) => println!("✅ Screenshot service initialized successfully"),
        Err(e) => {
            println!("❌ Failed to initialize screenshot service: {}", e);
            return Err(e.into());
        }
    }

    // Test monitor enumeration
    println!("\nTesting monitor enumeration...");
    match screenshot.get_monitors().await {
        Ok(monitors) => {
            println!("✅ Found {} monitor(s):", monitors.len());
            for monitor in monitors {
                println!(
                    "  - Monitor {}: {}x{} at ({}, {}), scale: {}, primary: {}",
                    monitor.id,
                    monitor.width,
                    monitor.height,
                    monitor.x,
                    monitor.y,
                    monitor.scale_factor,
                    monitor.is_primary
                );
            }
        }
        Err(e) => {
            println!("❌ Failed to get monitors: {}", e);
            return Err(e.into());
        }
    }

    // Test small area capture (100x100 at top-left)
    println!("\nTesting area capture...");
    let test_area = CaptureArea {
        x: 100,
        y: 100,
        width: 100,
        height: 100,
    };

    match screenshot.capture_area(test_area).await {
        Ok(image) => {
            println!(
                "✅ Successfully captured area: {}x{}",
                image.width(),
                image.height()
            );

            // Save to file for verification
            if let Err(e) = image.save("test_screenshot.png") {
                println!("⚠️  Could not save image: {}", e);
            } else {
                println!("📸 Test screenshot saved as test_screenshot.png");
            }
        }
        Err(e) => {
            println!("❌ Failed to capture area: {}", e);
            return Err(e.into());
        }
    }

    // Test fullscreen capture
    println!("\nTesting fullscreen capture...");
    match screenshot.capture_fullscreen(None).await {
        Ok(image) => {
            println!(
                "✅ Successfully captured fullscreen: {}x{}",
                image.width(),
                image.height()
            );
        }
        Err(e) => {
            println!("❌ Failed to capture fullscreen: {}", e);
            return Err(e.into());
        }
    }

    println!("\n🎉 All screenshot tests passed!");
    Ok(())
}

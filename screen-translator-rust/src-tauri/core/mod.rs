// Core functionality modules

pub mod config;
#[cfg(feature = "image_processing")]
pub mod image_processor;
#[cfg(feature = "image_processing")]
pub mod ocr;
pub mod screenshot; // Screenshot is a core P0 feature, always available

// Re-export commonly used types
pub use config::Config;
#[cfg(feature = "image_processing")]
pub use image_processor::{ImageProcessor, PreprocessingConfig, Rectangle, TextDetectionConfig};
#[cfg(feature = "image_processing")]
pub use ocr::{OcrConfig, OcrEngine, OcrResult, TesseractOcr, TextRegion};
pub use screenshot::{
    CaptureArea, ImageFormat, MonitorInfo, ScreenshotCapture, ScreenshotConfig, WindowsScreenshot,
};

// Include test module when testing
#[cfg(test)]
pub mod tests;

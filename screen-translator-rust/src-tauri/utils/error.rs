// Application error types

use thiserror::Error;

pub type AppResult<T> = Result<T, AppError>;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("Configuration error: {0}")]
    Config(String),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Serialization error: {0}")]
    Serialization(#[from] toml::ser::Error),

    #[error("Deserialization error: {0}")]
    Deserialization(#[from] toml::de::Error),

    #[error("OCR error: {0}")]
    Ocr(String),

    #[error("Translation error: {0}")]
    Translation(String),

    #[error("Screenshot error: {0}")]
    Screenshot(String),

    #[error("Hotkey error: {0}")]
    Hotkey(String),

    #[error("System error: {0}")]
    System(String),

    #[error("Unknown error: {0}")]
    Other(String),
}

impl AppError {
    pub fn ocr<S: Into<String>>(msg: S) -> Self {
        Self::Ocr(msg.into())
    }

    pub fn translation<S: Into<String>>(msg: S) -> Self {
        Self::Translation(msg.into())
    }

    pub fn screenshot<S: Into<String>>(msg: S) -> Self {
        Self::Screenshot(msg.into())
    }

    pub fn hotkey<S: Into<String>>(msg: S) -> Self {
        Self::Hotkey(msg.into())
    }

    pub fn system<S: Into<String>>(msg: S) -> Self {
        Self::System(msg.into())
    }

    pub fn other<S: Into<String>>(msg: S) -> Self {
        Self::Other(msg.into())
    }
}

// Specific error types for OCR functionality

#[derive(Error, Debug)]
pub enum OcrError {
    #[error("OCR engine not initialized")]
    NotInitialized,

    #[error("Language not supported: {0}")]
    UnsupportedLanguage(String),

    #[error("Image processing failed: {0}")]
    ImageProcessingError(String),

    #[error("Tesseract error: {0}")]
    TesseractError(String),

    #[error("OCR timeout after {0} seconds")]
    Timeout(u64),

    #[error("Invalid OCR configuration: {0}")]
    InvalidConfig(String),

    #[error("OCR engine unavailable: {0}")]
    Unavailable(String),
}

// Screenshot-specific error types

#[derive(Error, Debug)]
pub enum ScreenshotError {
    #[error("Screenshot capture failed: {0}")]
    CaptureError(String),

    #[error("Screenshot service not available: {0}")]
    NotAvailable(String),

    #[error("Invalid capture area: {0}")]
    InvalidArea(String),

    #[error("Monitor not found: {0}")]
    NotFound(String),

    #[error("Permission denied: {0}")]
    PermissionDenied(String),

    #[error("Screenshot timeout after {0}ms")]
    Timeout(u64),

    #[error("Invalid screenshot configuration: {0}")]
    InvalidConfig(String),

    #[error("Platform not supported: {0}")]
    UnsupportedPlatform(String),

    #[error("System error: {0}")]
    SystemError(String),
}

// Image processing error types

#[derive(Error, Debug)]
pub enum ImageProcessingError {
    #[error("Image processing failed: {0}")]
    ProcessingFailed(String),

    #[error("Invalid image format: {0}")]
    InvalidFormat(String),

    #[error("Image too large: {width}x{height} (max: {max_width}x{max_height})")]
    ImageTooLarge {
        width: u32,
        height: u32,
        max_width: u32,
        max_height: u32,
    },

    #[error("Invalid processing configuration: {0}")]
    InvalidConfig(String),

    #[error("Memory allocation failed: {0}")]
    MemoryError(String),

    #[error("Unsupported operation: {0}")]
    UnsupportedOperation(String),

    #[error("Filter application failed: {0}")]
    FilterError(String),
}

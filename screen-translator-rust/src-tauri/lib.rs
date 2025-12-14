// Screen Translator Rust Library
// Provides core functionality for screen translation with OCR

// Allow dead code for MVP phase - many components are placeholders
#![allow(dead_code)]
#![allow(unused_imports)]

pub mod ai;
pub mod commands;
pub mod core;
pub mod gui;
pub mod services;
pub mod types;
pub mod utils;

// Re-export commonly used types for easier access
// Note: Specific re-exports to avoid ambiguous glob conflicts
pub use ai::{ContextAwareTranslator, DetectionMethod, SmartAreaDetector};
pub use services::config::ConfigManager;
pub use services::translation::TranslationService;
pub use services::{AppState, HotkeyManager};
pub use types::{AppConfig, OcrResult, TranslationRequest};
pub use utils::error::*;

// Include tests modules when testing
#[cfg(test)]
mod tests {
    // Import all test modules
    #[allow(unused_imports)]
    use crate::ai::tests::*;
    // Note: commands module doesn't have tests submodule
    #[allow(unused_imports)]
    use crate::core::tests::*;
    #[allow(unused_imports)]
    use crate::services::tests::*;
}

// Basic types for MVP implementation without OCR dependencies

use serde::{Deserialize, Serialize};

// Translation types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranslationRequest {
    pub text: String,
    pub source_lang: String,
    pub target_lang: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranslationResult {
    pub original_text: String,
    pub translated_text: String,
    pub source_lang: String,
    pub target_lang: String,
    pub confidence: f32,
    pub cached: bool,
}

// Text region for future OCR integration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TextRegion {
    pub x: u32,
    pub y: u32,
    pub width: u32,
    pub height: u32,
    pub confidence: f32,
    pub text: String,
}

// OCR result type (simplified for MVP)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OcrResult {
    pub text: String,
    pub confidence: f32,
    pub regions: Vec<TextRegion>,
    pub processing_time_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OcrConfig {
    pub language: String,
    pub confidence_threshold: f32,
    pub preprocessing: bool,
}

// Cache types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheStats {
    pub cache_size: usize,
    pub cache_capacity: usize,
    pub history_size: usize,
    pub oldest_entry: Option<chrono::DateTime<chrono::Utc>>,
    pub newest_entry: Option<chrono::DateTime<chrono::Utc>>,
    pub total_translations: u64,
    pub hit_count: u64,
    pub miss_count: u64,
    pub hit_rate: f64,
}

// History types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistoryEntry {
    pub id: String,
    pub original_text: String,
    pub translated_text: String,
    pub source_lang: String,
    pub target_lang: String,
    pub confidence: f32,
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub tags: Vec<String>,
    pub is_favorite: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistorySearchFilter {
    pub text_query: Option<String>,
    pub source_lang: Option<String>,
    pub target_lang: Option<String>,
    pub tags: Vec<String>,
    pub favorites_only: bool,
    pub date_range: Option<(chrono::DateTime<chrono::Utc>, chrono::DateTime<chrono::Utc>)>,
    pub context_type: Option<String>,
    pub source_type: Option<String>,
    pub date_from: Option<chrono::DateTime<chrono::Utc>>,
    pub date_to: Option<chrono::DateTime<chrono::Utc>>,
    pub min_confidence: Option<f32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistorySearchResult {
    pub entries: Vec<HistoryEntry>,
    pub total_count: usize,
    pub page: usize,
    pub page_size: usize,
    pub search_time_ms: u64,
}

// Context aware types
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub enum ContextType {
    #[default]
    General,
    Technical,
    Gaming,
    UiInterface,
    Document,
    Subtitle,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LanguageDetection {
    pub language: String,
    pub context_confidence: f32,
    pub processing_time_ms: u64,
}

// Configuration types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub hotkeys: HotkeyConfig,
    pub ocr: OcrConfig,
    pub translation: TranslationConfig,
    pub ui: UiConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HotkeyConfig {
    pub quick_translate: String,
    pub screenshot_area: String,
    pub show_hide: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranslationConfig {
    pub source_lang: String,
    pub target_lang: String,
    pub auto_detect: bool,
    pub cache_enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UiConfig {
    pub theme: String,
    pub overlay_position: String,
    pub auto_hide_delay: u32,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            hotkeys: HotkeyConfig {
                quick_translate: "Alt+A".to_string(),
                screenshot_area: "Ctrl+Shift+S".to_string(),
                show_hide: "Ctrl+Alt+H".to_string(),
            },
            ocr: OcrConfig {
                language: "eng".to_string(),
                confidence_threshold: 0.7,
                preprocessing: true,
            },
            translation: TranslationConfig {
                source_lang: "auto".to_string(),
                target_lang: "en".to_string(),
                auto_detect: true,
                cache_enabled: true,
            },
            ui: UiConfig {
                theme: "dark".to_string(),
                overlay_position: "center".to_string(),
                auto_hide_delay: 5000,
            },
        }
    }
}

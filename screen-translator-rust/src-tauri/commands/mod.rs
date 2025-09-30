// Tauri commands for frontend-backend communication - MVP VERSION

use crate::services::intelligent_hotkey::{
    ContextMenuItem, HotkeyPerformanceStats, IntelligentHotkeyManager, PreviousArea,
};
use crate::services::translation::TranslationService;
use crate::types::*;
use serde_json::Value;
use tauri::State;

// Basic translation commands for MVP
#[tauri::command]
pub async fn translate_text(request: TranslationRequest) -> Result<TranslationResult, String> {
    log::info!("Translating text: {:.50}...", request.text);

    let mut service = TranslationService::new();
    let service_request = crate::services::translation::TranslationRequest {
        text: request.text.clone(),
        source_lang: request.source_lang.clone(),
        target_lang: request.target_lang.clone(),
        context: None,
    };
    service
        .translate(service_request)
        .await
        .map(|result| TranslationResult {
            original_text: result.original_text,
            translated_text: result.translated_text,
            source_lang: result.source_lang,
            target_lang: result.target_lang,
            confidence: result.confidence,
            cached: false, // MVP - always false for now
        })
        .map_err(|e| format!("Translation failed: {}", e))
}

#[tauri::command]
pub async fn get_app_config() -> Result<AppConfig, String> {
    log::info!("Getting app configuration");
    Ok(AppConfig::default())
}

#[tauri::command]
pub async fn set_app_config(_config: AppConfig) -> Result<(), String> {
    log::info!("Setting app configuration");
    // TODO: Implement actual config persistence for MVP
    Ok(())
}

// Basic clipboard support
#[tauri::command]
pub async fn get_clipboard_text() -> Result<String, String> {
    log::info!("Getting clipboard text");
    get_clipboard_content()
}

#[tauri::command]
pub async fn set_clipboard_text(text: String) -> Result<(), String> {
    log::info!("Setting clipboard text");
    set_clipboard_content(&text);
    Ok(())
}

// Simplified history for MVP
#[tauri::command]
pub async fn get_translation_history() -> Result<Vec<HistoryEntry>, String> {
    log::info!("Getting translation history");
    // TODO: Return actual history for MVP
    Ok(vec![])
}

// Language detection (mock for MVP)
#[tauri::command]
pub async fn detect_language_and_context(text: &str) -> Result<LanguageDetection, String> {
    log::info!("Detecting language for text: {:.50}...", text);

    // Simple language detection for MVP
    let language = if text.chars().any(|c| c as u32 > 127) {
        "auto".to_string() // Non-ASCII, auto-detect
    } else {
        "en".to_string() // ASCII, assume English
    };

    Ok(LanguageDetection {
        language,
        context_confidence: 0.8,
        processing_time_ms: 1,
    })
}

// Screenshot commands (disabled for MVP)
#[tauri::command]
pub async fn capture_screenshot(_area: Option<Value>) -> Result<String, String> {
    log::info!("Screenshot capture not implemented in MVP");
    Err("Screenshot capture disabled for MVP".to_string())
}

// OCR commands (disabled for MVP)
#[tauri::command]
pub async fn perform_ocr(_image_data: &str, _config: Option<Value>) -> Result<OcrResult, String> {
    log::info!("OCR not implemented in MVP");
    Err("OCR disabled for MVP".to_string())
}

// Cache commands (basic for MVP)
#[tauri::command]
pub async fn get_cache_statistics() -> Result<CacheStats, String> {
    log::info!("Getting cache statistics");
    Ok(CacheStats {
        cache_size: 0,
        cache_capacity: 100,
        hit_count: 0,
        miss_count: 0,
        hit_rate: 0.0,
        history_size: 0,
        oldest_entry: None,
        newest_entry: None,
        total_translations: 0,
    })
}

// Helper functions
fn get_clipboard_content() -> Result<String, String> {
    // TODO: Implement actual clipboard reading for MVP
    Ok("Sample clipboard text".to_string())
}

fn set_clipboard_content(_content: &str) {
    // TODO: Implement actual clipboard writing for MVP
}

// ============================================================================
// Intelligent Hotkey Commands (FR-4)
// ============================================================================

#[tauri::command]
pub async fn initialize_intelligent_hotkey(
    state: State<'_, crate::services::AppState>,
) -> Result<(), String> {
    log::info!("Initializing intelligent hotkey system");
    let mut manager = state
        .intelligent_hotkey_manager
        .lock()
        .map_err(|e| format!("Failed to lock hotkey manager: {}", e))?;
    manager
        .register_intelligent_hotkey()
        .map_err(|e| format!("Failed to register hotkey: {}", e))?;
    Ok(())
}

#[tauri::command]
pub async fn get_hotkey_performance_stats(
    state: State<'_, crate::services::AppState>,
) -> Result<HotkeyPerformanceStats, String> {
    log::info!("Getting hotkey performance stats");
    let manager = state
        .intelligent_hotkey_manager
        .lock()
        .map_err(|e| format!("Failed to lock hotkey manager: {}", e))?;
    manager
        .get_performance_stats()
        .map_err(|e| format!("Failed to get stats: {}", e))
}

#[tauri::command]
pub async fn update_quick_press_threshold(
    state: State<'_, crate::services::AppState>,
    threshold_ms: u64,
) -> Result<(), String> {
    log::info!("Updating quick press threshold to {}ms", threshold_ms);
    let mut manager = state
        .intelligent_hotkey_manager
        .lock()
        .map_err(|e| format!("Failed to lock hotkey manager: {}", e))?;
    manager.set_quick_press_threshold(threshold_ms);
    Ok(())
}

#[tauri::command]
pub async fn get_previous_areas(
    state: State<'_, crate::services::AppState>,
    limit: usize,
) -> Result<Vec<PreviousArea>, String> {
    log::info!("Getting previous areas (limit: {})", limit);
    let manager = state
        .intelligent_hotkey_manager
        .lock()
        .map_err(|e| format!("Failed to lock hotkey manager: {}", e))?;
    manager
        .get_top_areas(limit)
        .map_err(|e| format!("Failed to get areas: {}", e))
}

#[tauri::command]
pub async fn clear_previous_areas(
    state: State<'_, crate::services::AppState>,
) -> Result<(), String> {
    log::info!("Clearing previous areas");
    let manager = state
        .intelligent_hotkey_manager
        .lock()
        .map_err(|e| format!("Failed to lock hotkey manager: {}", e))?;
    manager
        .clear_previous_areas()
        .map_err(|e| format!("Failed to clear areas: {}", e))
}

#[tauri::command]
pub async fn get_context_menu_items() -> Result<Vec<ContextMenuItem>, String> {
    log::info!("Getting context menu items");
    Ok(crate::services::intelligent_hotkey::get_default_context_menu())
}

#[tauri::command]
pub async fn execute_context_action(
    _state: State<'_, crate::services::AppState>,
    action: String,
) -> Result<(), String> {
    log::info!("Executing context action: {}", action);
    // TODO: Implement actual action execution based on action ID
    // For now, just log the action
    match action.as_str() {
        "screenshot_area" => log::info!("Action: Screenshot Area"),
        "clipboard_translate" => log::info!("Action: Clipboard Translation"),
        "region_selection" => log::info!("Action: Region Selection"),
        "repeat_last" => log::info!("Action: Repeat Last Translation"),
        "show_history" => log::info!("Action: Show History"),
        "open_settings" => log::info!("Action: Open Settings"),
        _ => log::warn!("Unknown action: {}", action),
    }
    Ok(())
}

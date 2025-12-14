// Application services and state management

pub mod cache;
pub mod config;
pub mod hotkey;
pub mod intelligent_hotkey;
pub mod translation;

// Re-export IntelligentHotkeyManager for easy access
pub use intelligent_hotkey::IntelligentHotkeyManager;

// Include test modules when testing
#[cfg(test)]
mod cache_test;
#[cfg(test)]
mod translation_test;

use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

pub struct AppState {
    pub config: Arc<Mutex<AppConfiguration>>,
    pub translation_cache: Arc<Mutex<TranslationCache>>,
    pub hotkey_manager: Arc<Mutex<HotkeyManager>>,
    pub intelligent_hotkey_manager: Arc<Mutex<IntelligentHotkeyManager>>,
}

// Manual Debug implementation since IntelligentHotkeyManager can't derive Debug
impl std::fmt::Debug for AppState {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("AppState")
            .field("config", &self.config)
            .field("translation_cache", &"TranslationCache")
            .field("hotkey_manager", &"HotkeyManager")
            .field("intelligent_hotkey_manager", &"IntelligentHotkeyManager")
            .finish()
    }
}

impl Default for AppState {
    fn default() -> Self {
        // Note: intelligent_hotkey_manager requires AppHandle and must be initialized
        // after Tauri app is created. Use a placeholder until proper initialization.
        panic!("AppState::default() should not be called directly. Use AppState::new_with_handle() instead");
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfiguration {
    pub ocr_language: String,
    pub source_language: String,
    pub target_language: String,
    pub auto_detect_language: bool,
    pub hotkeys: HotkeyConfiguration,
    pub ui_theme: String,
    pub overlay_settings: OverlaySettings,
}

#[derive(Debug, Default, Clone, Serialize, Deserialize)]
pub struct HotkeyConfiguration {
    pub quick_translate: String,
    pub screenshot_area: String,
    pub show_hide_window: String,
    pub toggle_overlay: String,
}

#[derive(Debug, Default, Clone, Serialize, Deserialize)]
pub struct OverlaySettings {
    pub position: String,
    pub auto_hide_delay: u32,
    pub transparency: f32,
    pub font_size: u16,
}

#[derive(Debug, Default)]
pub struct TranslationCache {
    // TODO: Implement LRU cache with TTL
    cache: std::collections::HashMap<String, CachedTranslation>,
}

#[derive(Debug, Clone)]
pub struct CachedTranslation {
    pub translated_text: String,
    pub confidence: f32,
    pub timestamp: std::time::SystemTime,
    pub source_lang: String,
    pub target_lang: String,
}

#[derive(Debug, Default)]
pub struct HotkeyManager {
    // TODO: Implement global hotkey management
    registered_hotkeys: std::collections::HashMap<String, String>,
}

impl AppState {
    /// Create new AppState with Tauri AppHandle for intelligent hotkey integration
    pub fn new_with_handle(app_handle: tauri::AppHandle) -> Self {
        // Try to initialize intelligent hotkey manager, but don't panic if it fails
        let intelligent_hotkey_manager = match IntelligentHotkeyManager::new(app_handle.clone()) {
            Ok(manager) => {
                log::info!("✅ Intelligent hotkey manager initialized successfully");
                manager
            }
            Err(e) => {
                log::warn!("⚠️ Failed to initialize intelligent hotkey manager: {}", e);
                log::warn!("⚠️ Application will continue without hotkey support");
                // Create a minimal fallback manager that won't panic
                IntelligentHotkeyManager::new_fallback(app_handle)
            }
        };

        Self {
            config: Arc::new(Mutex::new(AppConfiguration::default())),
            translation_cache: Arc::new(Mutex::new(TranslationCache::default())),
            hotkey_manager: Arc::new(Mutex::new(HotkeyManager::default())),
            intelligent_hotkey_manager: Arc::new(Mutex::new(intelligent_hotkey_manager)),
        }
    }

    /// Legacy constructor for backward compatibility (deprecated)
    #[deprecated(note = "Use new_with_handle() instead")]
    pub fn new() -> Self {
        panic!("AppState::new() is deprecated. Use new_with_handle() with Tauri AppHandle");
    }

    pub fn load_config(&self) -> Result<AppConfiguration, Box<dyn std::error::Error>> {
        // TODO: Load config from file
        Ok(AppConfiguration::default())
    }

    pub fn save_config(&self, config: &AppConfiguration) -> Result<(), Box<dyn std::error::Error>> {
        // TODO: Save config to file
        let mut app_config = self.config.lock().unwrap();
        *app_config = config.clone();
        Ok(())
    }
}

impl Default for AppConfiguration {
    fn default() -> Self {
        Self {
            ocr_language: "eng".to_string(),
            source_language: "auto".to_string(),
            target_language: "en".to_string(),
            auto_detect_language: true,
            hotkeys: HotkeyConfiguration {
                quick_translate: "Alt+A".to_string(),
                screenshot_area: "Alt+S".to_string(),
                show_hide_window: "Alt+T".to_string(),
                toggle_overlay: "Alt+O".to_string(),
            },
            ui_theme: "dark".to_string(),
            overlay_settings: OverlaySettings {
                position: "center".to_string(),
                auto_hide_delay: 5000,
                transparency: 0.9,
                font_size: 16,
            },
        }
    }
}

impl TranslationCache {
    pub fn get(&self, key: &str) -> Option<CachedTranslation> {
        self.cache.get(key).cloned()
    }

    pub fn insert(&mut self, key: String, translation: CachedTranslation) {
        // TODO: Implement TTL and LRU eviction
        self.cache.insert(key, translation);
    }

    pub fn clear(&mut self) {
        self.cache.clear();
    }
}

impl HotkeyManager {
    pub fn register(&mut self, hotkey: String, action: String) -> Result<(), String> {
        // TODO: Implement global hotkey registration using global-hotkey crate
        self.registered_hotkeys
            .insert(hotkey.clone(), action.clone());
        log::info!("Registered hotkey: {} for action: {}", hotkey, action);
        Ok(())
    }

    pub fn unregister(&mut self, hotkey: &str) -> Result<(), String> {
        // TODO: Implement global hotkey unregistration
        self.registered_hotkeys.remove(hotkey);
        log::info!("Unregistered hotkey: {}", hotkey);
        Ok(())
    }

    pub fn is_registered(&self, hotkey: &str) -> bool {
        self.registered_hotkeys.contains_key(hotkey)
    }
}

// Include test module when testing
#[cfg(test)]
pub mod tests;
pub mod translation_async;

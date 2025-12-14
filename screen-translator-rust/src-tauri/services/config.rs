// Configuration management service

use dirs;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct AppConfig {
    pub version: String,
    pub ocr: OcrSettings,
    pub translation: TranslationSettings,
    pub hotkeys: HotkeySettings,
    pub ui: UiSettings,
    pub advanced: AdvancedSettings,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct OcrSettings {
    pub language: String,
    pub confidence_threshold: f32,
    pub preprocessing_enabled: bool,
    pub text_detection_method: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct TranslationSettings {
    pub source_language: String,
    pub target_language: String,
    pub auto_detect: bool,
    pub service_provider: String,
    pub cache_enabled: bool,
    pub cache_ttl_hours: u32,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct HotkeySettings {
    pub quick_translate: String,
    pub screenshot_area: String,
    pub show_hide_window: String,
    pub context_menu: String,
    pub intelligent_mode_enabled: bool,
    pub press_timeout_ms: u64,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct UiSettings {
    pub theme: String,
    pub language: String,
    pub overlay_position: String,
    pub overlay_auto_hide_delay: u32,
    pub overlay_transparency: f32,
    pub font_family: String,
    pub font_size: u16,
    pub animations_enabled: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct AdvancedSettings {
    pub logging_level: String,
    pub performance_mode: bool,
    pub system_tray_enabled: bool,
    pub startup_minimized: bool,
    pub auto_update_enabled: bool,
    pub telemetry_enabled: bool,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            version: "3.0.0".to_string(),
            ocr: OcrSettings::default(),
            translation: TranslationSettings::default(),
            hotkeys: HotkeySettings::default(),
            ui: UiSettings::default(),
            advanced: AdvancedSettings::default(),
        }
    }
}

impl Default for OcrSettings {
    fn default() -> Self {
        Self {
            language: "eng".to_string(),
            confidence_threshold: 0.6,
            preprocessing_enabled: true,
            text_detection_method: "hybrid".to_string(),
        }
    }
}

impl Default for TranslationSettings {
    fn default() -> Self {
        Self {
            source_language: "auto".to_string(),
            target_language: "en".to_string(),
            auto_detect: true,
            service_provider: "google".to_string(),
            cache_enabled: true,
            cache_ttl_hours: 24,
        }
    }
}

impl Default for HotkeySettings {
    fn default() -> Self {
        Self {
            quick_translate: "Alt+A".to_string(),
            screenshot_area: "Alt+S".to_string(),
            show_hide_window: "Alt+T".to_string(),
            context_menu: "Alt+C".to_string(),
            intelligent_mode_enabled: true,
            press_timeout_ms: 1000,
        }
    }
}

impl Default for UiSettings {
    fn default() -> Self {
        Self {
            theme: "dark".to_string(),
            language: "en".to_string(),
            overlay_position: "center".to_string(),
            overlay_auto_hide_delay: 5000,
            overlay_transparency: 0.9,
            font_family: "Segoe UI".to_string(),
            font_size: 16,
            animations_enabled: true,
        }
    }
}

impl Default for AdvancedSettings {
    fn default() -> Self {
        Self {
            logging_level: "Info".to_string(),
            performance_mode: false,
            system_tray_enabled: true,
            startup_minimized: true,
            auto_update_enabled: false,
            telemetry_enabled: false,
        }
    }
}

pub struct ConfigManager {
    config_path: PathBuf,
    config: AppConfig,
}

impl ConfigManager {
    pub fn new() -> Result<Self, Box<dyn std::error::Error>> {
        let config_path = Self::get_config_path()?;
        let config = Self::load_config(&config_path)?;

        Ok(Self {
            config_path,
            config,
        })
    }

    pub fn get_config(&self) -> &AppConfig {
        &self.config
    }

    pub fn update_config(&mut self, config: AppConfig) -> Result<(), Box<dyn std::error::Error>> {
        self.config = config;
        self.save_config()
    }

    pub fn save_config(&self) -> Result<(), Box<dyn std::error::Error>> {
        let config_json = serde_json::to_string_pretty(&self.config)?;
        std::fs::write(&self.config_path, config_json)?;
        Ok(())
    }

    fn get_config_path() -> Result<PathBuf, Box<dyn std::error::Error>> {
        let mut config_dir = dirs::config_dir().ok_or("Failed to get config directory")?;

        config_dir.push("ScreenTranslator");

        if !config_dir.exists() {
            std::fs::create_dir_all(&config_dir)?;
        }

        config_dir.push("config.json");
        Ok(config_dir)
    }

    fn load_config(config_path: &PathBuf) -> Result<AppConfig, Box<dyn std::error::Error>> {
        if config_path.exists() {
            let config_content = std::fs::read_to_string(config_path)?;
            let config: AppConfig = serde_json::from_str(&config_content)?;
            Ok(config)
        } else {
            // Create default config
            let default_config = AppConfig::default();
            let config_json = serde_json::to_string_pretty(&default_config)?;
            std::fs::write(config_path, config_json)?;
            Ok(default_config)
        }
    }
}

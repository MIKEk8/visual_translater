// Configuration management with type safety

use anyhow::{Context, Result};
use log::{info, warn};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub general: GeneralConfig,
    pub hotkeys: HotkeyConfig,
    pub ocr: OcrConfig,
    pub translation: TranslationConfig,
    pub ui: UiConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeneralConfig {
    pub auto_copy_to_clipboard: bool,
    pub show_notifications: bool,
    pub minimize_to_tray: bool,
    pub auto_start: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HotkeyConfig {
    pub capture_area: String,
    pub capture_fullscreen: String,
    pub toggle_window: String,
    pub repeat_last: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OcrConfig {
    pub language: String,
    pub engine: String,
    pub confidence_threshold: f32,
    pub preprocessing: PreprocessingConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PreprocessingConfig {
    pub auto_enhance: bool,
    pub grayscale: bool,
    pub noise_reduction: bool,
    pub contrast_enhancement: bool,
    pub deskew: bool,
    pub dpi: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranslationConfig {
    pub source_language: String,
    pub target_language: String,
    pub service: String,
    pub api_key: Option<String>,
    pub auto_detect_language: bool,
    pub cache_translations: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UiConfig {
    pub theme: String,
    pub font_size: f32,
    pub window_opacity: f32,
    pub overlay_timeout: u32,
    pub remember_window_position: bool,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            general: GeneralConfig {
                auto_copy_to_clipboard: true,
                show_notifications: true,
                minimize_to_tray: true,
                auto_start: false,
            },
            hotkeys: HotkeyConfig {
                capture_area: "Alt+A".to_string(),
                capture_fullscreen: "Alt+S".to_string(),
                toggle_window: "Alt+T".to_string(),
                repeat_last: "Alt+R".to_string(),
            },
            ocr: OcrConfig {
                language: "eng".to_string(),
                engine: "tesseract".to_string(),
                confidence_threshold: 0.5,
                preprocessing: PreprocessingConfig {
                    auto_enhance: true,
                    grayscale: true,
                    noise_reduction: true,
                    contrast_enhancement: false,
                    deskew: false,
                    dpi: 300,
                },
            },
            translation: TranslationConfig {
                source_language: "auto".to_string(),
                target_language: "en".to_string(),
                service: "google".to_string(),
                api_key: None,
                auto_detect_language: true,
                cache_translations: true,
            },
            ui: UiConfig {
                theme: "dark".to_string(),
                font_size: 14.0,
                window_opacity: 0.95,
                overlay_timeout: 5,
                remember_window_position: true,
            },
        }
    }
}

impl Config {
    /// Load configuration from file
    pub fn load() -> Result<Self> {
        let config_path = Self::config_file_path()?;

        if !config_path.exists() {
            info!("Config file not found, creating default configuration");
            let config = Self::default();
            config.save()?;
            return Ok(config);
        }

        let config_str =
            std::fs::read_to_string(&config_path).context("Failed to read config file")?;

        let config: Config = toml::from_str(&config_str).context("Failed to parse config file")?;

        info!("Configuration loaded from: {}", config_path.display());
        Ok(config)
    }

    /// Save configuration to file
    pub fn save(&self) -> Result<()> {
        let config_path = Self::config_file_path()?;

        // Create config directory if it doesn't exist
        if let Some(parent) = config_path.parent() {
            std::fs::create_dir_all(parent).context("Failed to create config directory")?;
        }

        let config_str = toml::to_string_pretty(self).context("Failed to serialize config")?;

        std::fs::write(&config_path, config_str).context("Failed to write config file")?;

        info!("Configuration saved to: {}", config_path.display());
        Ok(())
    }

    /// Get the path to the configuration file
    pub fn config_file_path() -> Result<PathBuf> {
        let config_dir = dirs::config_dir()
            .context("Failed to get config directory")?
            .join("screen-translator");

        Ok(config_dir.join("config.toml"))
    }

    /// Get the path to the application data directory
    pub fn data_dir() -> Result<PathBuf> {
        let data_dir = dirs::data_dir()
            .context("Failed to get data directory")?
            .join("screen-translator");

        // Create directory if it doesn't exist
        std::fs::create_dir_all(&data_dir).context("Failed to create data directory")?;

        Ok(data_dir)
    }

    /// Validate configuration values
    pub fn validate(&self) -> Result<()> {
        // Validate confidence threshold
        if self.ocr.confidence_threshold < 0.0 || self.ocr.confidence_threshold > 1.0 {
            warn!("OCR confidence threshold should be between 0.0 and 1.0");
        }

        // Validate font size
        if self.ui.font_size < 8.0 || self.ui.font_size > 72.0 {
            warn!("UI font size should be between 8.0 and 72.0");
        }

        // Validate opacity
        if self.ui.window_opacity < 0.1 || self.ui.window_opacity > 1.0 {
            warn!("Window opacity should be between 0.1 and 1.0");
        }

        Ok(())
    }
}

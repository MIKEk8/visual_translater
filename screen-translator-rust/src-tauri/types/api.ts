// API Types for Screen Translator Tauri App

export interface OcrResult {
  text: string;
  confidence: number;
  processing_time_ms: number;
  language_detected: string;
  regions?: TextRegion[];
}

export interface TextRegion {
  x: number;
  y: number;
  width: number;
  height: number;
  text: string;
  confidence: number;
}

export interface TranslationRequest {
  text: string;
  source_lang: string;
  target_lang: string;
}

export interface TranslationResult {
  original_text: string;
  translated_text: string;
  source_lang: string;
  target_lang: string;
  confidence: number;
}

export interface CaptureArea {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface AppConfig {
  hotkeys: HotkeyConfig;
  ocr: OcrConfigType;
  translation: TranslationConfig;
  ui: UiConfig;
}

export interface HotkeyConfig {
  quick_translate: string;
  screenshot_area: string;
  show_hide: string;
}

export interface OcrConfigType {
  language: string;
  confidence_threshold: number;
  preprocessing: boolean;
}

export interface TranslationConfig {
  source_lang: string;
  target_lang: string;
  auto_detect: boolean;
  cache_enabled: boolean;
}

export interface UiConfig {
  theme: string;
  overlay_position: string;
  auto_hide_delay: number;
}
// Screen Translator Rust - MVP Entry Point
#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]
// Allow dead code for MVP phase - many components are placeholders
#![allow(dead_code)]
#![allow(unused_imports)]

use log::info;

mod commands;
mod services;
mod types;
mod utils;

use commands::*;
use services::AppState;
use tauri::Manager;

// Simple greet command for testing
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

fn main() {
    // Initialize logging
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();
    info!("Starting Screen Translator MVP...");

    tauri::Builder::default()
        .setup(|app| {
            // Initialize AppState with app handle for intelligent hotkey integration
            let app_handle = app.handle().clone();
            app.manage(AppState::new_with_handle(app_handle));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            greet,
            translate_text,
            get_app_config,
            set_app_config,
            get_clipboard_text,
            set_clipboard_text,
            get_translation_history,
            detect_language_and_context,
            capture_screenshot,
            perform_ocr,
            get_cache_statistics,
            // FR-4 Intelligent Hotkey Commands
            initialize_intelligent_hotkey,
            get_hotkey_performance_stats,
            update_quick_press_threshold,
            get_previous_areas,
            clear_previous_areas,
            get_context_menu_items,
            execute_context_action,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

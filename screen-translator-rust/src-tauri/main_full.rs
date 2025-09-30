// Screen Translator Rust - Tauri Main Entry Point
#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use log::info;

mod ai;
mod commands;
mod core;
mod services;
mod utils;

use commands::*;
use services::AppState;
use tauri::{CustomMenuItem, Manager, SystemTray, SystemTrayEvent, SystemTrayMenu};

fn main() {
    // Initialize logging with DEBUG level
    env_logger::Builder::from_default_env()
        .filter_level(log::LevelFilter::Debug)
        .init();

    info!("Starting Screen Translator Rust v3.0.0 with Tauri");

    // Initialize app state
    let app_state = AppState::new();

    // Create system tray
    let tray_menu = SystemTrayMenu::new()
        .add_item(CustomMenuItem::new("show", "Show"))
        .add_item(CustomMenuItem::new("hide", "Hide"))
        .add_item(CustomMenuItem::new("translate", "Quick Translate"))
        .add_item(CustomMenuItem::new("settings", "Settings"))
        .add_item(CustomMenuItem::new("quit", "Quit"));

    let system_tray = SystemTray::new().with_menu(tray_menu);

    tauri::Builder::default()
        .manage(app_state)
        .system_tray(system_tray)
        .on_system_tray_event(|app, event| match event {
            SystemTrayEvent::LeftClick {
                position: _,
                size: _,
                ..
            } => {
                if let Some(window) = app.get_window("main") {
                    match window.is_visible() {
                        Ok(true) => {
                            if let Err(e) = window.hide() {
                                log::error!("Failed to hide window: {}", e);
                            }
                        }
                        Ok(false) => {
                            if let Err(e) = window.show() {
                                log::error!("Failed to show window: {}", e);
                            } else if let Err(e) = window.set_focus() {
                                log::error!("Failed to set window focus: {}", e);
                            }
                        }
                        Err(e) => {
                            log::error!("Failed to check window visibility: {}", e);
                        }
                    }
                } else {
                    log::error!("Main window not found");
                }
            }
            SystemTrayEvent::MenuItemClick { id, .. } => match id.as_str() {
                "quit" => {
                    // Graceful shutdown instead of forced exit
                    app.exit(0);
                }
                "show" => {
                    if let Some(window) = app.get_window("main") {
                        if let Err(e) = window.show() {
                            log::error!("Failed to show window: {}", e);
                        } else if let Err(e) = window.set_focus() {
                            log::error!("Failed to set window focus: {}", e);
                        }
                    } else {
                        log::error!("Main window not found");
                    }
                }
                "hide" => {
                    if let Some(window) = app.get_window("main") {
                        if let Err(e) = window.hide() {
                            log::error!("Failed to hide window: {}", e);
                        }
                    } else {
                        log::error!("Main window not found");
                    }
                }
                "settings" => {
                    if let Some(window) = app.get_window("main") {
                        if let Err(e) = window.show() {
                            log::error!("Failed to show settings window: {}", e);
                        }
                        // TODO: Navigate to settings view
                    } else {
                        log::error!("Main window not found for settings");
                    }
                }
                "translate" => {
                    // TODO: Trigger quick translation
                    log::info!("Quick translate requested");
                }
                _ => {}
            },
            _ => {}
        })
        .invoke_handler(tauri::generate_handler![
            greet,
            capture_screenshot,
            perform_ocr,
            translate_text,
            get_app_config,
            set_app_config,
            register_global_hotkey,
            unregister_global_hotkey,
            // AI-Enhanced Commands
            detect_language_and_context,
            get_translation_suggestions,
            smart_translate_with_context,
            detect_text_regions,
            get_preprocessing_suggestions,
            // Intelligent Hotkey Commands
            initialize_intelligent_hotkey,
            get_context_menu_items,
            execute_context_action,
            get_hotkey_performance_stats,
            update_quick_press_threshold,
            get_previous_areas,
            clear_previous_areas,
            // Translation History & Cache Commands
            search_translation_history,
            add_translation_to_history,
            get_cached_translation,
            update_translation_tags,
            toggle_translation_favorite,
            delete_translation_entry,
            clear_translation_history,
            export_translation_history,
            get_translation_cache_stats,
            cleanup_expired_cache,
            get_similar_translations,
            update_cache_config
        ])
        .setup(|app| {
            // Initialize global hotkeys
            let app_handle = app.handle();
            tauri::async_runtime::spawn(async move {
                if let Err(e) = services::hotkey::initialize_hotkeys(app_handle).await {
                    log::error!("Failed to initialize hotkeys: {}", e);
                }
            });

            // Show window on startup for testing
            if let Some(window) = app.get_window("main") {
                info!("Window object created");

                // Try to get window URL to debug
                let url = window.url();
                info!("Window URL: {}", url);

                if let Err(e) = window.show() {
                    log::error!("Failed to show window during setup: {}", e);
                    return Err(Box::new(std::io::Error::new(std::io::ErrorKind::Other, "Failed to show main window")));
                }
                info!("Window show() called");

                // Open DevTools for debugging
                #[cfg(debug_assertions)]
                {
                    window.open_devtools();
                    info!("DevTools opened");
                }

                // Try to evaluate some JavaScript to test if WebView is working
                if let Err(e) = window.eval("console.log('JavaScript is working!'); document.title = 'JS Test - Screen Translator';") {
                    log::warn!("Failed to evaluate JavaScript: {}", e);
                } else {
                    info!("JavaScript evaluation successful");
                }
            } else {
                log::error!("Main window not found during setup");
                return Err(Box::new(std::io::Error::new(std::io::ErrorKind::Other, "Main window not found")));
            }

            // Set system tray tooltip
            if let Err(e) = app.tray_handle().set_tooltip("Screen Translator") {
                log::error!("Failed to set tray tooltip: {}", e);
                return Err(Box::new(std::io::Error::new(std::io::ErrorKind::Other, format!("Failed to set tray tooltip: {}", e))));
            }

            info!("Setup completed successfully");

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

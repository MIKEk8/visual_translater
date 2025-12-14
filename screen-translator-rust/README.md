# Screen Translator v3.0 - Rust + Tauri

A modern screen translation application built with Rust backend and React frontend using Tauri framework.

## 🚀 Features

- **Intelligent Hotkey System** - Alt+A with time-based detection for quick/long press actions
- **Advanced OCR** - Tesseract integration with image preprocessing
- **Multi-Provider Translation** - Google, Microsoft, DeepL, Yandex support
- **Modern Web UI** - React + TypeScript with Tailwind CSS
- **System Tray Integration** - Background operation with quick access
- **Area Selection** - Precise screen region selection with magnifier
- **Translation Overlay** - Floating results with auto-copy functionality
- **Cross-platform** - Windows, macOS, and Linux support

## 🏗️ Architecture

### Core Modules
- `core/config` - Type-safe configuration management
- `core/screenshot` - Screen capture functionality
- `core/ocr` - OCR engine with preprocessing
- `core/translation` - Multi-service translation

### GUI Modules
- `gui/main_window` - Primary application interface
- `gui/settings_dialog` - Configuration interface
- `gui/overlay` - Translation result overlay

### Services
- `services/hotkey_manager` - Global hotkey registration
- `services/tray` - System tray integration

## 🛠️ Development

### Prerequisites
```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install additional components
rustup component add clippy rustfmt rust-analyzer
```

### Building
```bash
# Development build
cargo build

# Release build
cargo build --release

# Run
cargo run
```

### Development Tools
```bash
# Auto-rebuild on changes
cargo install cargo-watch
cargo watch -x run

# Code formatting
cargo fmt

# Linting
cargo clippy

# Testing
cargo test
```

## 📦 Dependencies

### Core Dependencies
- **egui/eframe** - Modern immediate mode GUI framework
- **leptess** - Tesseract OCR bindings
- **reqwest** - HTTP client for translation APIs
- **image** - Image processing and manipulation
- **screenshots** - Cross-platform screenshot capture

### System Integration
- **tray-icon** - System tray functionality
- **global-hotkey** - Global keyboard shortcuts
- **clipboard** - Clipboard operations

### Utilities
- **serde** - Serialization/deserialization
- **tokio** - Async runtime
- **anyhow/thiserror** - Error handling
- **log/env_logger** - Logging

## 🎯 Current Status

This is **Phase 1** of the Rust migration - basic project structure and minimal GUI prototype.

### ✅ Completed
- [x] Project structure setup
- [x] Basic Cargo configuration
- [x] Core module architecture
- [x] Minimal GUI with egui
- [x] Configuration management
- [x] Error handling framework

### 🚧 In Progress
- [ ] Basic screenshot capture
- [ ] OCR integration
- [ ] Translation services
- [ ] Hotkey management

### 📋 Planned
- [ ] Advanced image preprocessing
- [ ] Multiple translation services
- [ ] Translation history
- [ ] System tray integration
- [ ] Auto-updates
- [ ] Performance optimizations

## 🔄 Migration Strategy

We're following a **phased migration approach**:

1. **Phase 1** - Basic structure and GUI prototype *(Current)*
2. **Phase 2** - Core functionality (screenshot, OCR, translation)
3. **Phase 3** - Advanced UI and UX features
4. **Phase 4** - Feature parity with Python version

This allows us to:
- Get quick feedback on architecture decisions
- Compare performance with Python version at each phase
- Maintain working Python version during development
- Iterate and improve design incrementally

## 🎊 Why Rust?

When **code quality is the priority**, Rust provides:

- **Memory safety** without garbage collection
- **Thread safety** enforced at compile-time
- **Zero-cost abstractions** for high-level code with native performance
- **Excellent error handling** that prevents silent failures
- **Fearless refactoring** - compiler prevents breaking changes
- **Best-in-class tooling** with Cargo package manager

## 📄 License

MIT License - see LICENSE file for details.
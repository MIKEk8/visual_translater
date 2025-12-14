# 🚀 Getting Started with Screen Translator Rust

## 📋 Prerequisites

### 1. Install Rust
```bash
# Install Rust toolchain
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Add to PATH (restart terminal or run):
source ~/.cargo/env

# Verify installation
rustc --version
cargo --version
```

### 2. Install Development Tools
```bash
# Essential components
rustup component add clippy rustfmt rust-analyzer

# Helpful cargo extensions
cargo install cargo-watch    # Auto-rebuild on file changes
cargo install cargo-edit     # Easy dependency management
cargo install cargo-audit    # Security vulnerability scanning
```

## 🏗️ Building the Project

### First Time Setup
```bash
# Navigate to project directory
cd screen-translator-rust

# Check project (fastest - just compilation check)
cargo check

# Build in debug mode (with debug symbols)
cargo build

# Build optimized release version
cargo build --release
```

### Development Workflow
```bash
# Auto-rebuild and run on file changes
cargo watch -x run

# Format code (auto-fix formatting)
cargo fmt

# Lint code (find potential issues)
cargo clippy

# Run tests
cargo test
```

## 🚀 Running the Application

### Debug Mode (Development)
```bash
cargo run
```

### Release Mode (Optimized)
```bash
cargo run --release
```

### Direct Execution
```bash
# After building, you can run the binary directly:
./target/debug/screen-translator        # Debug build
./target/release/screen-translator      # Release build (Windows: .exe)
```

## 🛠️ Development Environment Setup

### VS Code (Recommended)
1. Install VS Code
2. Install the `rust-analyzer` extension
3. Install `CodeLLDB` extension for debugging
4. Open the `screen-translator-rust` folder

### RustRover (JetBrains)
1. Install RustRover IDE
2. Open the project folder
3. All Rust tooling is built-in

### Other Editors
- **Vim/Neovim**: Install `rust-tools.nvim` or `coc-rust-analyzer`
- **Emacs**: Use `rustic` mode
- **Sublime Text**: Install `LSP-rust-analyzer` package

## 🐛 Troubleshooting

### Common Issues

#### 1. "cargo: command not found"
```bash
# Restart terminal or manually add to PATH:
export PATH="$HOME/.cargo/bin:$PATH"
```

#### 2. Compilation Errors
```bash
# Update Rust to latest version
rustup update

# Clear cache and rebuild
cargo clean
cargo build
```

#### 3. Missing System Dependencies
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install build-essential pkg-config

# macOS (with Homebrew)
brew install pkg-config

# Windows
# Install Visual Studio Build Tools or Visual Studio Community
```

#### 4. Permission Issues (Windows)
- Run terminal as Administrator
- Disable Windows Defender real-time protection temporarily
- Add Rust directories to antivirus exclusions

## 📊 Performance Comparison

Once you have both versions running, you can compare:

### Startup Time
```bash
# Python version
time python src/main.py

# Rust version
time cargo run --release
```

### Memory Usage
```bash
# Monitor with htop, Task Manager, or Activity Monitor
# Rust version should use significantly less memory
```

### Binary Size
```bash
# Python (PyInstaller)
ls -lh dist/ScreenTranslator.exe

# Rust
ls -lh target/release/screen-translator*
```

## 🎯 What to Expect

### Phase 1 (Current)
- ✅ Compiles successfully
- ✅ Opens GUI window
- ✅ Basic navigation (tabs, menus)
- ✅ Settings interface
- 🚧 Placeholder functionality (buttons work but don't do actual operations)

### Next Steps
1. **Verify compilation** - `cargo check`
2. **Run the app** - `cargo run`
3. **Explore the GUI** - click around, check that it works
4. **Start Phase 2** - implement actual screenshot capture

## 📈 Expected Performance Gains

Based on Rust vs Python benchmarks for similar applications:
- **Startup time**: 5-10x faster
- **Memory usage**: 3-5x less
- **OCR processing**: 30-50% faster
- **Binary size**: 50-70% smaller (vs PyInstaller)

## 🎊 Ready to Start!

Your Rust Screen Translator project is ready for development. The foundation is solid and follows Rust best practices for maximum code quality.

**Next command to run:**
```bash
cd screen-translator-rust
cargo run
```

Happy coding with Rust! 🦀
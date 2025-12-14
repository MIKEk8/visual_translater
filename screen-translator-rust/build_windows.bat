@echo off
echo Setting up Rust environment and building Tauri app...

REM Add Rust to PATH for this session
set PATH=%USERPROFILE%\.cargo\bin;%PATH%

REM Verify Rust is available
cargo --version
if %ERRORLEVEL% neq 0 (
    echo Error: Cargo not found. Please install Rust first.
    echo Run: curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs ^| sh
    pause
    exit /b 1
)

echo Building frontend...
npm run build
if %ERRORLEVEL% neq 0 (
    echo Frontend build failed!
    pause
    exit /b 1
)

echo Building Tauri application...
cargo build --release
if %ERRORLEVEL% neq 0 (
    echo Rust build failed!
    pause
    exit /b 1
)

echo.
echo Build completed successfully!
echo Executable should be in target\release\screen-translator.exe
echo.
pause
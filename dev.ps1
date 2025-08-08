# Screen Translator v2.0 - Development Helper (PowerShell)
# Modern replacement for dev.bat with better error handling and Unicode support

param(
    [Parameter(Position=0)]
    [string]$Command = "help",
    
    [Parameter(Position=1)]
    [string]$SubCommand = "",
    
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$RemainingArgs = @()
)

# Set error handling
$ErrorActionPreference = "Stop"

# Colors for output
function Write-Info { param($Message) Write-Host "[INFO] $Message" -ForegroundColor Cyan }
function Write-Success { param($Message) Write-Host "[SUCCESS] $Message" -ForegroundColor Green }
function Write-Error { param($Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }
function Write-Warning { param($Message) Write-Host "[WARNING] $Message" -ForegroundColor Yellow }

function Show-Help {
    Write-Host "=============================================" -ForegroundColor Blue
    Write-Host " Screen Translator v2.0 - Development Helper" -ForegroundColor Blue  
    Write-Host "=============================================" -ForegroundColor Blue
    Write-Host ""
    Write-Host "[IMPORTANT] This file is the ONLY interface for developers!" -ForegroundColor Yellow
    Write-Host "   DO NOT use python build.py, pytest, build_exe.bat directly" -ForegroundColor Yellow
    Write-Host "   ONLY use dev.ps1 commands for all project operations!" -ForegroundColor Yellow
    Write-Host ""
    
    # Check environment status
    if ($env:VIRTUAL_ENV) {
        Write-Success "[PYTHON] Virtual Environment: ACTIVE"
        Write-Host "    Location: $env:VIRTUAL_ENV" -ForegroundColor Gray
    } elseif (Test-Path "wenv\Scripts\python.exe") {
        Write-Success "[WENV] Windows Environment: AVAILABLE (recommended)"
        Write-Host "    Location: wenv\" -ForegroundColor Gray
    } elseif (Test-Path ".venv\Scripts\python.exe") {
        Write-Warning "[VENV] Virtual Environment: AVAILABLE (legacy - use wenv instead)"
        Write-Host "    Location: .venv\" -ForegroundColor Gray
    } else {
        Write-Error "[ERROR] No virtual environment found"
        Write-Host "    Run '.\dev.ps1 setup' to create wenv" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "Main Commands:" -ForegroundColor Blue
    Write-Host "  .\dev.ps1 setup                 - Setup wenv environment"
    Write-Host "  .\dev.ps1 test                  - Run all tests in wenv"
    Write-Host "  .\dev.ps1 test unit             - Run unit tests in wenv"
    Write-Host "  .\dev.ps1 test coverage         - Run tests with coverage in wenv"
    Write-Host "  .\dev.ps1 lint                  - Check code quality in wenv"
    Write-Host "  .\dev.ps1 lint fix              - Fix code quality issues in wenv"
    Write-Host "  .\dev.ps1 build                 - Build release version (.exe) in wenv"
    Write-Host "  .\dev.ps1 build debug           - Build debug version in wenv"
    Write-Host "  .\dev.ps1 run                   - Run from source in wenv"
    Write-Host "  .\dev.ps1 run debug             - Run with debug logging in wenv"
    Write-Host "  .\dev.ps1 quality               - Full quality check"
    Write-Host "  .\dev.ps1 quality fix           - Auto-fix quality issues"
    Write-Host ""
}

function Get-PythonCommand {
    # Determine Python command and venv flag
    $venvFlag = ""
    $pythonCmd = "python"
    
    if ($env:VIRTUAL_ENV) {
        Write-Info "[PYTHON] Virtual environment detected: $env:VIRTUAL_ENV"
        $venvFlag = "--venv"
    } elseif (Test-Path "wenv\Scripts\python.exe") {
        Write-Info "[WENV] Windows environment available - using automatically"
        $venvFlag = "--wenv"
        $pythonCmd = "wenv\Scripts\python.exe"
    } elseif (Test-Path ".venv\Scripts\python.exe") {
        Write-Warning "[VENV] Virtual environment available - using automatically (legacy)"
        $venvFlag = "--venv"
        $pythonCmd = ".venv\Scripts\python.exe"
    }
    
    # Check if Python is available
    try {
        & $pythonCmd --version | Out-Null
        if ($LASTEXITCODE -ne 0) { throw }
    } catch {
        Write-Error "Python not found! Please install Python 3.8+ and add it to PATH."
        Write-Host "Download from: https://python.org/downloads/" -ForegroundColor Gray
        exit 1
    }
    
    return @{
        Command = $pythonCmd
        VenvFlag = $venvFlag
    }
}

function Invoke-Setup {
    Write-Host "============================================" -ForegroundColor Blue
    Write-Host "[SETUP] Screen Translator v2.0 Environment Setup" -ForegroundColor Blue
    Write-Host "============================================" -ForegroundColor Blue
    Write-Host ""
    
    $python = Get-PythonCommand
    
    # Create wenv if it doesn't exist
    if (!(Test-Path "wenv\Scripts\python.exe")) {
        Write-Info "[CREATE] Creating Windows environment (wenv)..."
        & $python.Command build.py wenv-create
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to create Windows environment!"
            exit 1
        }
    } else {
        Write-Success "[OK] Windows environment already exists"
    }
    
    Write-Host ""
    Write-Info "[INSTALL] Installing development and build dependencies..."
    & "wenv\Scripts\python.exe" build.py wenv-install --dev --build
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install dependencies!"
        exit 1
    }
    
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Success "[SUCCESS] Environment configured successfully!"
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Available commands:"
    Write-Host "  .\dev.ps1 test          - Run tests"
    Write-Host "  .\dev.ps1 build         - Build application"
    Write-Host "  .\dev.ps1 run           - Run from source"
    Write-Host "  .\dev.ps1 lint          - Check code quality"
}

function Invoke-Test {
    $python = Get-PythonCommand
    
    $args = @("build.py", "test")
    
    if ($SubCommand -eq "unit") {
        $args += @("--type", "unit")
    } elseif ($SubCommand -eq "integration") {
        $args += @("--type", "integration")
    } elseif ($SubCommand -eq "coverage") {
        $args += "--coverage"
    }
    
    if ($python.VenvFlag) {
        $args += $python.VenvFlag
    }
    
    $args += $RemainingArgs
    
    & $python.Command @args
}

function Invoke-Lint {
    $python = Get-PythonCommand
    
    $args = @("build.py", "lint")
    
    if ($SubCommand -eq "fix") {
        $args += "--fix"
    }
    
    if ($python.VenvFlag) {
        $args += $python.VenvFlag
    }
    
    $args += $RemainingArgs
    
    & $python.Command @args
}

function Invoke-Build {
    $python = Get-PythonCommand
    
    $args = @("build.py", "build")
    
    if ($SubCommand -eq "debug") {
        $args += @("--mode", "debug")
    }
    
    if ($python.VenvFlag) {
        $args += $python.VenvFlag
    }
    
    $args += $RemainingArgs
    
    & $python.Command @args
}

function Invoke-Run {
    $python = Get-PythonCommand
    
    Write-Info "[RUN] Starting Screen Translator..."
    
    $args = @("main.py")
    
    if ($SubCommand -eq "debug") {
        $args += "--debug"
    } elseif ($SubCommand -eq "test") {
        $args += "--test"
    } else {
        $args += $SubCommand
        $args += $RemainingArgs
    }
    
    & $python.Command @args
}

function Invoke-Quality {
    $python = Get-PythonCommand
    
    Write-Info "[QUALITY] Running code quality checks..."
    
    $args = @("build.py", "quality")
    
    if ($python.VenvFlag) {
        $args += $python.VenvFlag
    }
    
    $args += $RemainingArgs
    
    if ($SubCommand -eq "fix") {
        # Add --fix flag for comprehensive quality fixes
        $args += "--fix"
        & $python.Command @args
    } else {
        & $python.Command @args
    }
}

function Invoke-Passthrough {
    $python = Get-PythonCommand
    
    $args = @("build.py", $Command)
    
    if ($python.VenvFlag) {
        $args += $python.VenvFlag
    }
    
    $args += $SubCommand
    $args += $RemainingArgs
    
    & $python.Command @args
}

# Main execution
try {
    switch ($Command.ToLower()) {
        "help" { Show-Help }
        "setup" { Invoke-Setup }
        "test" { Invoke-Test }
        "lint" { Invoke-Lint }
        "build" { Invoke-Build }
        "run" { Invoke-Run }
        "quality" { Invoke-Quality }
        default { Invoke-Passthrough }
    }
} catch {
    Write-Error "An error occurred: $_"
    exit 1
}
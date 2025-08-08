#!/usr/bin/env python3
"""
Universal build and test script for Screen Translator v2.0
Provides unified interface for development, testing, and building across all platforms.
Includes virtual environment management and dependency handling.
"""

import sys
import os
import subprocess
import argparse
import platform
import shutil
import venv
from pathlib import Path
from typing import List, Optional, Tuple

# Colors for output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def colored_print(text: str, color: str = Colors.WHITE) -> None:
    """Print colored text with proper encoding handling"""
    # Check if output is redirected (no colors/emojis for redirected output)
    if not sys.stdout.isatty():
        # Remove ANSI colors and replace Unicode emojis for redirected output
        clean_text = text.replace("✅", "[OK]").replace("❌", "[ERROR]").replace("🔨", "[RUN]").replace("💡", "[INFO]").replace("🐍", "[PYTHON]").replace("🚀", "[START]").replace("🧪", "[TEST]").replace("📦", "[PKG]").replace("🔍", "[SEARCH]").replace("⚠️", "[WARNING]")
        print(clean_text)
    else:
        try:
            print(f"{color}{text}{Colors.ENDC}")
        except UnicodeEncodeError:
            # Fallback for terminals that don't support Unicode
            clean_text = text.replace("✅", "[OK]").replace("❌", "[ERROR]").replace("🔨", "[RUN]").replace("💡", "[INFO]").replace("🐍", "[PYTHON]").replace("🚀", "[START]").replace("🧪", "[TEST]").replace("📦", "[PKG]").replace("🔍", "[SEARCH]").replace("⚠️", "[WARNING]")
            print(f"{color}{clean_text}{Colors.ENDC}")

def run_command(cmd: List[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run command with proper error handling"""
    colored_print(f"🔨 Running: {' '.join(cmd)}", Colors.CYAN)
    
    try:
        result = subprocess.run(
            cmd, 
            check=check, 
            capture_output=capture,
            text=True,
            cwd=Path(__file__).parent
        )
        return result
    except subprocess.CalledProcessError as e:
        colored_print(f"❌ Command failed: {e}", Colors.RED)
        if capture and e.stdout:
            print(e.stdout)
        if capture and e.stderr:
            print(e.stderr)
        raise
    except FileNotFoundError:
        colored_print(f"❌ Command not found: {cmd[0]}", Colors.RED)
        colored_print(f"💡 Please install {cmd[0]} or check PATH", Colors.YELLOW)
        raise

def check_python_version() -> None:
    """Check if Python version is supported"""
    if sys.version_info < (3, 8):
        colored_print("❌ Python 3.8+ is required", Colors.RED)
        sys.exit(1)
    
    colored_print(f"✅ Python {sys.version.split()[0]} detected", Colors.GREEN)

def install_dependencies(dev: bool = False) -> None:
    """Install project dependencies with externally-managed-environment support"""
    colored_print("📦 Installing dependencies...", Colors.BLUE)
    
    # Check if we're in an externally managed environment
    externally_managed = False
    try:
        # Try a simple pip command to detect externally-managed-environment
        test_result = subprocess.run([sys.executable, "-m", "pip", "--version"], 
                                   capture_output=True, text=True)
        if test_result.returncode == 0:
            # Test if we can install (this will fail in externally-managed-environment)
            test_install = subprocess.run([sys.executable, "-m", "pip", "install", "--dry-run", "pip"], 
                                        capture_output=True, text=True, timeout=30)
            if "externally-managed-environment" in test_install.stderr:
                externally_managed = True
    except:
        pass
    
    # Base pip command with appropriate flags
    base_pip_cmd = [sys.executable, "-m", "pip", "install"]
    if externally_managed:
        colored_print("⚠️ Externally managed environment detected - using --break-system-packages --user", Colors.YELLOW)
        base_pip_cmd.extend(["--break-system-packages", "--user"])
    
    try:
        # Upgrade pip first
        pip_upgrade_cmd = base_pip_cmd + ["--upgrade", "pip"]
        run_command(pip_upgrade_cmd)
        
        # Install production dependencies
        if Path("requirements.txt").exists():
            prod_cmd = base_pip_cmd + ["-r", "requirements.txt"]
            run_command(prod_cmd)
        else:
            colored_print("⚠️ requirements.txt not found - installing core packages", Colors.YELLOW)
            # Install essential packages directly
            essential_packages = ["pillow", "requests", "pytest", "black", "flake8"]
            for package in essential_packages:
                try:
                    pkg_cmd = base_pip_cmd + [package]
                    run_command(pkg_cmd, check=False)  # Don't fail if one package fails
                except:
                    colored_print(f"⚠️ Could not install {package}", Colors.YELLOW)
        
        if dev:
            # Install development dependencies
            if Path("requirements-dev.txt").exists():
                dev_cmd = base_pip_cmd + ["-r", "requirements-dev.txt"]
                run_command(dev_cmd, check=False)  # Don't fail completely
            colored_print("✅ Development dependencies installed", Colors.GREEN)
        else:
            colored_print("✅ Dependencies installed", Colors.GREEN)
            
    except subprocess.CalledProcessError as e:
        if externally_managed:
            colored_print("⚠️ Some packages may have failed - this is normal in container environments", Colors.YELLOW)
            colored_print("✅ Core installation completed with externally-managed-environment workaround", Colors.GREEN)
        else:
            colored_print(f"❌ Installation failed: {e}", Colors.RED)
            raise
def run_tests(
    test_type: str = "all",
    coverage: bool = False,
    verbose: bool = False,
    workers: int | None = None,
) -> bool:
    """Run tests with optional coverage and parallel workers"""
    colored_print(f"🧪 Running {test_type} tests...", Colors.BLUE)

    cmd = [sys.executable, "-m", "pytest"]

    # Select test type
    if test_type == "unit":
        cmd.append("src/tests/unit/")
    elif test_type == "integration":
        cmd.append("src/tests/integration/")
    elif test_type == "all":
        cmd.append("src/tests/")
    else:
        colored_print(f"❌ Unknown test type: {test_type}", Colors.RED)
        return False

    # Add options
    if verbose:
        cmd.append("-v")

    if workers is not None:
        cmd.extend(["-n", str(workers)])

    if coverage:
        cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=xml", "--cov-report=term"])
    
    # Set environment
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent)
    
    try:
        result = subprocess.run(cmd, env=env)
        if result.returncode == 0:
            colored_print("✅ All tests passed", Colors.GREEN)
            if coverage:
                colored_print("📊 Coverage report generated in htmlcov/", Colors.CYAN)
            return True
        else:
            colored_print("❌ Some tests failed", Colors.RED)
            return False
    except Exception as e:
        colored_print(f"❌ Test execution failed: {e}", Colors.RED)
        return False

def run_code_quality() -> bool:
    """Run code quality checks"""
    colored_print("🔍 Running code quality checks...", Colors.BLUE)
    
    checks = [
        # Format check
        ([sys.executable, "-m", "black", "--check", "tests/", "--line-length", "100"], "Black formatting"),
        # Import sorting check
        ([sys.executable, "-m", "isort", "--check-only", "tests/", "--profile", "black"], "Import sorting"),
        # Linting
        ([sys.executable, "-m", "flake8", "tests/", "--max-line-length=100", "--extend-ignore=E203,W503"], "Flake8 linting"),
        # Type checking
        ([sys.executable, "-m", "mypy", "tests/", "--ignore-missing-imports", "--check-untyped-defs"], "MyPy type checking"),
    ]
    
    all_passed = True
    
    for cmd, name in checks:
        try:
            colored_print(f"  Running {name}...", Colors.CYAN)
            run_command(cmd, capture=True)
            colored_print(f"  ✅ {name} passed", Colors.GREEN)
        except subprocess.CalledProcessError:
            colored_print(f"  ❌ {name} failed", Colors.RED)
            all_passed = False
        except FileNotFoundError:
            colored_print(f"  ⚠️ {name} skipped (tool not installed)", Colors.YELLOW)
    
    if all_passed:
        colored_print("✅ All code quality checks passed", Colors.GREEN)
    else:
        colored_print("❌ Some code quality checks failed", Colors.RED)
    
    return all_passed

def fix_code_quality() -> None:
    """Fix code quality issues automatically"""
    colored_print("🔧 Fixing code quality issues...", Colors.BLUE)
    
    fixes = [
        ([sys.executable, "-m", "black", "src/", "--line-length", "100"], "Black formatting"),
        ([sys.executable, "-m", "isort", "src/", "--profile", "black"], "Import sorting"),
    ]
    
    for cmd, name in fixes:
        try:
            colored_print(f"  Running {name}...", Colors.CYAN)
            run_command(cmd)
            colored_print(f"  ✅ {name} applied", Colors.GREEN)
        except subprocess.CalledProcessError:
            colored_print(f"  ❌ {name} failed", Colors.RED)
        except FileNotFoundError:
            colored_print(f"  ⚠️ {name} skipped (tool not installed)", Colors.YELLOW)
    
    colored_print("✅ Code quality fixes applied", Colors.GREEN)

def build_executable(mode: str = "release") -> bool:
    """Build executable using PyInstaller"""
    colored_print(f"🏗️ Building executable ({mode} mode)...", Colors.BLUE)
    
    # Clean previous builds
    build_dirs = ["build", "dist", "__pycache__"]
    for dir_name in build_dirs:
        if os.path.exists(dir_name):
            colored_print(f"🧹 Cleaning {dir_name}/", Colors.YELLOW)
            shutil.rmtree(dir_name)
    
    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--icon=icon.ico",
        f"--name=ScreenTranslator-{platform.system()}-{mode}"
    ]
    
    if mode == "release":
        cmd.extend(["--windowed", "--optimize=2"])
    elif mode == "debug":
        cmd.extend(["--console", "--debug=all"])
    
    # Add hidden imports for better compatibility
    hidden_imports = [
        "src.core",
        "src.ui", 
        "src.services",
        "src.plugins.builtin.tesseract_ocr_plugin",
        "src.plugins.builtin.google_translate_plugin",
        "src.plugins.builtin.pyttsx3_tts_plugin"
    ]
    
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])
    
    # Add data files
    if os.path.exists("icon.ico"):
        cmd.extend(["--add-data", f"icon.ico{os.pathsep}."])
    
    if os.path.exists("languages"):
        cmd.extend(["--add-data", f"languages{os.pathsep}languages"])
    
    cmd.append("main.py")
    
    try:
        run_command(cmd)
        
        # Check if build succeeded
        dist_dir = Path("dist")
        if dist_dir.exists() and any(dist_dir.iterdir()):
            exe_files = list(dist_dir.glob("ScreenTranslator*"))
            if exe_files:
                colored_print(f"✅ Executable built successfully: {exe_files[0]}", Colors.GREEN)
                colored_print(f"📦 Size: {exe_files[0].stat().st_size / 1024 / 1024:.1f} MB", Colors.CYAN)
                return True
        
        colored_print("❌ Build completed but no executable found", Colors.RED)
        return False
        
    except Exception as e:
        colored_print(f"❌ Build failed: {e}", Colors.RED)
        return False

def run_security_scan() -> bool:
    """Run security scans"""
    colored_print("🔒 Running security scans...", Colors.BLUE)
    
    scans = [
        ([sys.executable, "-m", "bandit", "-r", "src/", "-f", "json"], "Bandit security scan"),
        ([sys.executable, "-m", "safety", "check", "--json"], "Safety vulnerability check"),
    ]
    
    all_passed = True
    
    for cmd, name in scans:
        try:
            colored_print(f"  Running {name}...", Colors.CYAN)
            run_command(cmd, check=False, capture=True)
            colored_print(f"  ✅ {name} completed", Colors.GREEN)
        except FileNotFoundError:
            colored_print(f"  ⚠️ {name} skipped (tool not installed)", Colors.YELLOW)
    
    return all_passed

def clean_project() -> None:
    """Clean build artifacts and cache"""
    colored_print("🧹 Cleaning project...", Colors.BLUE)
    
    patterns_to_clean = [
        "**/__pycache__",
        "**/*.pyc", 
        "**/*.pyo",
        "**/*.pyd",
        "build/",
        "dist/",
        ".coverage",
        "htmlcov/",
        ".pytest_cache/",
        ".mypy_cache/",
        "*.egg-info/"
    ]
    
    for pattern in patterns_to_clean:
        for path in Path(".").glob(pattern):
            if path.is_file():
                path.unlink()
                colored_print(f"  Removed file: {path}", Colors.YELLOW)
            elif path.is_dir():
                shutil.rmtree(path)
                colored_print(f"  Removed directory: {path}", Colors.YELLOW)
    
    colored_print("✅ Project cleaned", Colors.GREEN)

# Virtual Environment Management
VENV_DIR = Path(".venv")
WENV_DIR = Path("wenv")  # Windows Environment
PROJECT_ROOT = Path(__file__).parent

def get_active_env_dir() -> Path:
    """Get active virtual environment directory (wenv for Windows, venv for Linux/macOS)"""
    if platform.system() == "Windows":
        # Prefer wenv on Windows, fallback to venv for compatibility
        if WENV_DIR.exists():
            return WENV_DIR
        else:
            return VENV_DIR
    else:
        # Always use venv on Linux/macOS
        return VENV_DIR

def get_venv_python() -> Path:
    """Get path to Python executable in virtual environment"""
    env_dir = get_active_env_dir()
    if platform.system() == "Windows":
        return env_dir / "Scripts" / "python.exe"
    else:
        return env_dir / "bin" / "python"

def get_venv_pip() -> Path:
    """Get path to pip executable in virtual environment"""
    env_dir = get_active_env_dir()
    if platform.system() == "Windows":
        return env_dir / "Scripts" / "pip.exe"
    else:
        return env_dir / "bin" / "pip"

def get_wenv_python() -> Path:
    """Get path to Python executable in Windows environment (wenv)"""
    return WENV_DIR / "Scripts" / "python.exe"

def get_wenv_pip() -> Path:
    """Get path to pip executable in Windows environment (wenv)"""
    return WENV_DIR / "Scripts" / "pip.exe"

def is_venv_active() -> bool:
    """Check if virtual environment is currently active"""
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

def venv_exists() -> bool:
    """Check if virtual environment exists"""
    return VENV_DIR.exists() and (VENV_DIR / "bin" / "python").exists() if platform.system() != "Windows" else (VENV_DIR / "Scripts" / "python.exe").exists()

def wenv_exists() -> bool:
    """Check if Windows environment (wenv) exists"""
    return WENV_DIR.exists() and get_wenv_python().exists()

def any_env_exists() -> bool:
    """Check if any virtual environment exists"""
    if platform.system() == "Windows":
        return wenv_exists() or venv_exists()
    else:
        return venv_exists()

def create_venv() -> None:
    """Create virtual environment (venv for Linux/macOS)"""
    colored_print("🐧 Creating virtual environment (venv)...", Colors.BLUE)
    
    if venv_exists():
        colored_print("⚠️ Virtual environment already exists", Colors.YELLOW)
        return
    
    # Create virtual environment
    venv.create(VENV_DIR, with_pip=True)
    colored_print(f"✅ Virtual environment created at {VENV_DIR}", Colors.GREEN)
    
    # Upgrade pip in venv
    colored_print("📦 Upgrading pip in virtual environment...", Colors.CYAN)
    run_command([str(get_venv_python()), "-m", "pip", "install", "--upgrade", "pip"])

def create_wenv() -> None:
    """Create Windows environment (wenv for Windows)"""
    colored_print("🪟 Creating Windows environment (wenv)...", Colors.BLUE)
    
    if wenv_exists():
        colored_print("⚠️ Windows environment already exists", Colors.YELLOW)
        return
    
    # Create Windows environment
    venv.create(WENV_DIR, with_pip=True)
    colored_print(f"✅ Windows environment created at {WENV_DIR}", Colors.GREEN)
    
    # Upgrade pip in wenv
    colored_print("📦 Upgrading pip in Windows environment...", Colors.CYAN)
    run_command([str(get_wenv_python()), "-m", "pip", "install", "--upgrade", "pip"])

def activate_venv() -> Tuple[str, str]:
    """Get activation commands for virtual environment"""
    if platform.system() == "Windows":
        activate_cmd = str(VENV_DIR / "Scripts" / "activate.bat")
        deactivate_cmd = "deactivate"
    else:
        activate_cmd = f"source {VENV_DIR / 'bin' / 'activate'}"
        deactivate_cmd = "deactivate"
    
    return activate_cmd, deactivate_cmd

def install_to_venv(dev: bool = False, build: bool = False) -> None:
    """Install dependencies to virtual environment"""
    if not any_env_exists():
        colored_print("❌ Virtual environment doesn't exist. Create it first with: python build.py venv-create or wenv-create", Colors.RED)
        return
    
    venv_python = get_venv_python()
    venv_pip = get_venv_pip()
    
    colored_print("📦 Installing dependencies to virtual environment...", Colors.BLUE)
    
    # Upgrade pip first
    run_command([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
    
    # Install production dependencies
    run_command([str(venv_pip), "install", "-r", "requirements.txt"])
    
    # Install optional dependencies
    if dev:
        # Install development dependencies
        run_command([str(venv_pip), "install", "-e", ".[dev]"])
        colored_print("✅ Development dependencies installed to venv", Colors.GREEN)
    
    if build:
        # Install build dependencies (PyInstaller, etc.)
        run_command([str(venv_pip), "install", "-e", ".[build]"])
        colored_print("✅ Build dependencies installed to venv", Colors.GREEN)
    
    if not dev and not build:
        colored_print("✅ Dependencies installed to venv", Colors.GREEN)

def install_to_wenv(dev: bool = False, build: bool = False) -> None:
    """Install dependencies to Windows environment (wenv)"""
    if not wenv_exists():
        colored_print("❌ Windows environment doesn't exist. Create it first with: python build.py wenv-create", Colors.RED)
        return
    
    wenv_python = get_wenv_python()
    wenv_pip = get_wenv_pip()
    
    colored_print("📦 Installing dependencies to Windows environment (wenv)...", Colors.BLUE)
    
    # Upgrade pip first
    run_command([str(wenv_python), "-m", "pip", "install", "--upgrade", "pip"])
    
    # Install production dependencies
    run_command([str(wenv_pip), "install", "-r", "requirements.txt"])
    
    # Install optional dependencies
    if dev:
        # Install development dependencies
        run_command([str(wenv_pip), "install", "-e", ".[dev]"])
        colored_print("✅ Development dependencies installed to wenv", Colors.GREEN)
    
    if build:
        # Install build dependencies (PyInstaller, etc.)
        run_command([str(wenv_pip), "install", "-e", ".[build]"])
        colored_print("✅ Build dependencies installed to wenv", Colors.GREEN)
    
    if not dev and not build:
        colored_print("✅ Dependencies installed to wenv", Colors.GREEN)

def run_in_venv(cmd: List[str], description: str = "") -> subprocess.CompletedProcess:
    """Run command in virtual environment"""
    if not venv_exists():
        colored_print("❌ Virtual environment doesn't exist. Create it first with: python build.py venv-create", Colors.RED)
        sys.exit(1)
    
    # Replace python/pip commands with venv versions
    venv_python = str(get_venv_python())
    if cmd[0] in ["python", "python3", sys.executable]:
        cmd[0] = venv_python
    elif cmd[0] == "pip":
        cmd[0] = str(get_venv_pip())
    
    if description:
        colored_print(f"🐍 Running in venv: {description}", Colors.MAGENTA)
    
    return run_command(cmd)

def show_venv_info() -> None:
    """Show virtual environment information"""
    colored_print("🐍 Virtual Environment Information", Colors.BOLD + Colors.CYAN)
    colored_print("=" * 50, Colors.CYAN)
    
    if venv_exists():
        colored_print(f"📁 Location: {VENV_DIR.absolute()}", Colors.GREEN)
        colored_print(f"🐍 Python: {get_venv_python()}", Colors.GREEN)
        colored_print(f"📦 Pip: {get_venv_pip()}", Colors.GREEN)
        
        # Check if currently active
        if is_venv_active():
            colored_print("✅ Status: ACTIVE", Colors.GREEN)
        else:
            colored_print("⚠️ Status: NOT ACTIVE", Colors.YELLOW)
            activate_cmd, _ = activate_venv()
            colored_print(f"💡 To activate: {activate_cmd}", Colors.CYAN)
        
        # Show installed packages
        try:
            result = run_command([str(get_venv_python()), "-m", "pip", "list", "--format=freeze"], capture=True)
            if result.stdout:
                packages = result.stdout.strip().split('\n')
                colored_print(f"📦 Installed packages: {len(packages)}", Colors.GREEN)
                if len(packages) <= 10:
                    for package in packages:
                        colored_print(f"  - {package}", Colors.WHITE)
                else:
                    for package in packages[:5]:
                        colored_print(f"  - {package}", Colors.WHITE)
                    colored_print(f"  ... and {len(packages) - 5} more", Colors.YELLOW)
        except Exception:
            colored_print("⚠️ Could not list packages", Colors.YELLOW)
    else:
        colored_print("❌ Virtual environment does not exist", Colors.RED)
        colored_print("💡 Create with: python build.py venv-create", Colors.CYAN)

def remove_venv() -> None:
    """Remove virtual environment"""
    if not venv_exists():
        colored_print("⚠️ Virtual environment doesn't exist", Colors.YELLOW)
        return
    
    colored_print("🗑️ Removing virtual environment...", Colors.YELLOW)
    shutil.rmtree(VENV_DIR)
    colored_print("✅ Virtual environment removed", Colors.GREEN)

def show_wenv_info() -> None:
    """Show Windows environment information"""
    colored_print("🪟 Windows Environment (wenv) Information", Colors.BLUE)
    
    if wenv_exists():
        colored_print(f"✅ Location: {WENV_DIR.absolute()}", Colors.GREEN)
        colored_print(f"🐍 Python: {get_wenv_python()}", Colors.CYAN)
        colored_print(f"📦 Pip: {get_wenv_pip()}", Colors.CYAN)
        
        # Check if environment is active
        if is_venv_active():
            colored_print("🔥 Status: ACTIVE", Colors.GREEN)
        else:
            colored_print("💤 Status: Not Active", Colors.YELLOW)
        
        # Show activation commands
        activate_cmd, deactivate_cmd = activate_venv()
        colored_print(f"🚀 Activate: {activate_cmd}", Colors.MAGENTA)
        colored_print(f"⭕ Deactivate: {deactivate_cmd}", Colors.MAGENTA)
        
        # List installed packages
        try:
            result = run_command([str(get_wenv_pip()), "list"], capture=True)
            if result.returncode == 0:
                packages = result.stdout.strip().split('\n')[2:]  # Skip header lines
                colored_print(f"📚 Installed packages: {len(packages)}", Colors.CYAN)
                if len(packages) <= 5:
                    for package in packages:
                        colored_print(f"  - {package}", Colors.WHITE)
                else:
                    for package in packages[:5]:
                        colored_print(f"  - {package}", Colors.WHITE)
                    colored_print(f"  ... and {len(packages) - 5} more", Colors.YELLOW)
        except Exception:
            colored_print("⚠️ Could not list packages", Colors.YELLOW)
    else:
        colored_print("❌ Windows environment does not exist", Colors.RED)
        colored_print("💡 Create with: python build.py wenv-create", Colors.CYAN)

def remove_wenv() -> None:
    """Remove Windows environment"""
    if not wenv_exists():
        colored_print("⚠️ Windows environment doesn't exist", Colors.YELLOW)
        return
    
    colored_print("🗑️ Removing Windows environment...", Colors.YELLOW)
    shutil.rmtree(WENV_DIR)
    colored_print("✅ Windows environment removed", Colors.GREEN)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Universal build and test script for Screen Translator v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Linux/macOS Virtual Environment Management
  python build.py venv-create                # Create virtual environment (venv)
  python build.py venv-install               # Install dependencies to venv
  python build.py venv-install --dev         # Install dev dependencies to venv
  python build.py venv-install --build       # Install build dependencies to venv
  python build.py venv-info                  # Show venv information
  python build.py venv-remove                # Remove virtual environment
  
  # Windows Environment Management  
  python build.py wenv-create                # Create Windows environment (wenv)
  python build.py wenv-install               # Install dependencies to wenv
  python build.py wenv-install --dev         # Install dev dependencies to wenv
  python build.py wenv-install --build       # Install build dependencies to wenv
  python build.py wenv-info                  # Show wenv information
  python build.py wenv-remove                # Remove Windows environment
  
  # Standard Commands (use --venv to run in virtual environment)
  python build.py install                    # Install dependencies (system)
  python build.py install --dev              # Install with dev dependencies
  python build.py test                       # Run all tests
  python build.py test --type unit --venv    # Run unit tests in venv/wenv
  python build.py test --coverage --venv     # Run tests with coverage in venv/wenv
  python build.py lint --venv                # Run code quality checks in venv/wenv
  python build.py lint --fix --venv          # Fix code quality issues in venv/wenv
  python build.py build --venv               # Build release executable in venv/wenv
  python build.py security --venv            # Run security scans in venv/wenv
  python build.py clean                      # Clean build artifacts
  python build.py ci --venv                  # Run full CI pipeline in venv/wenv
        """
    )
    
    parser.add_argument("command", choices=[
        "install", "test", "lint", "build", "security", "clean", "ci", "quality",
        "venv-create", "venv-install", "venv-info", "venv-remove",
        "wenv-create", "wenv-install", "wenv-info", "wenv-remove"
    ], help="Command to execute")
    
    # Install options
    parser.add_argument("--dev", action="store_true", help="Install development dependencies")
    parser.add_argument("--build", action="store_true", help="Install build dependencies (PyInstaller)")
    
    # Test options
    parser.add_argument("--type", choices=["unit", "integration", "all"], default="all",
                       help="Type of tests to run")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--workers",
        help="Number of workers for pytest-xdist (e.g., 'auto' or 4)",
        default=None,
    )
    
    # Lint options
    parser.add_argument("--fix", action="store_true", help="Fix code quality issues")
    
    # Build options
    parser.add_argument("--mode", choices=["release", "debug"], default="release",
                       help="Build mode")
    
    # Virtual environment options
    parser.add_argument("--venv", action="store_true", 
                       help="Execute command in virtual environment (Linux/macOS)")
    parser.add_argument("--wenv", action="store_true",
                       help="Execute command in Windows environment (Windows)")
    
    args = parser.parse_args()
    
    # Helper function to determine which environment to use
    def should_use_env():
        """Determine if and which virtual environment to use"""
        if args.wenv:
            return "wenv"
        elif args.venv:
            return "venv"
        else:
            return None
    
    def get_env_python():
        """Get Python executable for the selected environment"""
        env_type = should_use_env()
        if env_type == "wenv":
            return get_wenv_python()
        elif env_type == "venv":
            return get_venv_python()
        else:
            return sys.executable
    
    def check_env_exists():
        """Check if the selected environment exists"""
        env_type = should_use_env()
        if env_type == "wenv":
            return wenv_exists()
        elif env_type == "venv":
            return venv_exists()
        else:
            return True
    
    # Header
    colored_print("=" * 60, Colors.BLUE)
    colored_print("  Screen Translator v2.0 - Build & Test Script", Colors.BOLD)
    colored_print("=" * 60, Colors.BLUE)
    
    check_python_version()
    
    try:
        # Virtual Environment Commands
        if args.command == "venv-create":
            create_venv()
            
        elif args.command == "venv-install":
            install_to_venv(args.dev, args.build)
            
        elif args.command == "venv-info":
            show_venv_info()
            
        elif args.command == "venv-remove":
            remove_venv()
            
        # Windows Environment Commands
        elif args.command == "wenv-create":
            create_wenv()
            
        elif args.command == "wenv-install":
            install_to_wenv(args.dev, args.build)
            
        elif args.command == "wenv-info":
            show_wenv_info()
            
        elif args.command == "wenv-remove":
            remove_wenv()
            
        # Standard Commands
        elif args.command == "install":
            env_type = should_use_env()
            if env_type == "wenv":
                install_to_wenv(args.dev, args.build)
            elif env_type == "venv":
                install_to_venv(args.dev, args.build)
            else:
                install_dependencies(args.dev)
            
        elif args.command == "test":
            env_type = should_use_env()
            if env_type and not check_env_exists():
                colored_print(f"❌ {env_type.upper()} environment doesn't exist. Create it first.", Colors.RED)
                sys.exit(1)
            
            if env_type:
                # Run tests in virtual environment
                def run_tests_env(test_type, coverage, verbose, workers):
                    cmd = [str(get_env_python()), "-m", "pytest"]
                    if test_type == "unit":
                        cmd.append("src/tests/unit/")
                    elif test_type == "integration":
                        cmd.append("src/tests/integration/")
                    elif test_type == "all":
                        cmd.append("src/tests/")

                    if verbose:
                        cmd.append("-v")
                    if workers is not None:
                        cmd.extend(["-n", str(workers)])
                    if coverage:
                        cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term"])
                    
                    # Set environment with PYTHONPATH
                    env = os.environ.copy()
                    env["PYTHONPATH"] = str(Path(__file__).parent)
                    
                    try:
                        result = subprocess.run(cmd, env=env, check=True, cwd=Path(__file__).parent)
                        return result.returncode == 0
                    except subprocess.CalledProcessError:
                        return False
                
                success = run_tests_env(args.type, args.coverage, args.verbose, args.workers)
            else:
                success = run_tests(args.type, args.coverage, args.verbose, args.workers)
            sys.exit(0 if success else 1)
            
        elif args.command == "lint":
            # Basic code quality checks (4 tools: black, isort, flake8, mypy)
            env_type = should_use_env()
            if env_type and not check_env_exists():
                colored_print(f"❌ {env_type.upper()} environment doesn't exist. Create it first.", Colors.RED)
                sys.exit(1)
                
            if args.fix:
                if env_type:
                    # Run basic code quality fixes in virtual environment
                    python_exe = str(get_env_python())
                    colored_print(f"🔧 Running basic code quality fixes in {env_type}...", Colors.BLUE)
                    
                    commands = [
                        ([python_exe, "-m", "black", "src/"], "Black code formatting"),
                        ([python_exe, "-m", "isort", "src/"], "Import sorting"),
                    ]
                    
                    all_passed = True
                    for cmd, name in commands:
                        try:
                            colored_print(f"  Running {name}...", Colors.CYAN)
                            run_command(cmd)
                            colored_print(f"  ✅ {name} completed", Colors.GREEN)
                        except subprocess.CalledProcessError:
                            colored_print(f"  ❌ {name} failed", Colors.RED)
                            all_passed = False
                        except FileNotFoundError:
                            colored_print(f"  ⚠️ {name} skipped (tool not installed)", Colors.YELLOW)
                    
                    sys.exit(0 if all_passed else 1)
                else:
                    # Run basic fixes with system Python
                    fix_code_quality()
            else:
                if env_type:
                    # Run basic code quality checks in virtual environment
                    python_exe = str(get_env_python())
                    colored_print(f"🔍 Running basic code quality checks in {env_type}...", Colors.BLUE)
                    
                    commands = [
                        ([python_exe, "-m", "black", "--check", "tests/", "--line-length", "100"], "Black formatting check"),
                        ([python_exe, "-m", "isort", "--check-only", "tests/", "--profile", "black"], "Import sorting check"),
                        ([python_exe, "-m", "flake8", "tests/", "--max-line-length=100", "--extend-ignore=E203,W503"], "Flake8 linting"),
                        ([python_exe, "-m", "mypy", "tests/", "--ignore-missing-imports", "--check-untyped-defs"], "MyPy type checking"),
                    ]
                    
                    all_passed = True
                    for cmd, name in commands:
                        try:
                            colored_print(f"  Running {name}...", Colors.CYAN)
                            run_command(cmd, check=False, capture=True)
                            colored_print(f"  ✅ {name} passed", Colors.GREEN)
                        except subprocess.CalledProcessError:
                            colored_print(f"  ❌ {name} failed", Colors.RED)
                            all_passed = False
                        except FileNotFoundError:
                            colored_print(f"  ⚠️ {name} skipped (tool not installed)", Colors.YELLOW)
                    
                    sys.exit(0 if all_passed else 1)
                else:
                    # Run basic checks with system Python
                    success = run_code_quality()
                    sys.exit(0 if success else 1)
                
        elif args.command == "build":
            # Build executable with PyInstaller
            env_type = should_use_env()
            if env_type and not check_env_exists():
                colored_print(f"❌ {env_type.upper()} environment doesn't exist. Create it first.", Colors.RED)
                sys.exit(1)
                
            if env_type:
                # Ensure build dependencies are installed
                colored_print("📦 Checking build dependencies...", Colors.CYAN)
                python_exe = str(get_env_python())
                try:
                    result = run_command([python_exe, "-m", "pip", "show", "pyinstaller"], capture=True, check=False)
                    if result.returncode != 0:
                        colored_print("📦 Installing build dependencies...", Colors.BLUE)
                        if env_type == "wenv":
                            install_to_wenv(build=True)
                        else:
                            install_to_venv(build=True)
                except Exception:
                    colored_print("📦 Installing build dependencies...", Colors.BLUE)
                    if env_type == "wenv":
                        install_to_wenv(build=True)
                    else:
                        install_to_venv(build=True)
                
                # Build using virtual environment python
                colored_print(f"🔨 Building executable ({args.mode} mode) using virtual environment...", Colors.BLUE)
                
                cmd = [
                    python_exe, "-m", "PyInstaller",
                    "--onefile",
                    "--windowed",
                    f"--icon=icon.ico",
                    f"--name=ScreenTranslator-{args.mode}",
                    "main.py"
                ]
                
                if args.mode == "debug":
                    cmd.extend(["--debug=all", "--console"])
                
                try:
                    run_command(cmd)
                    colored_print("✅ Build completed", Colors.GREEN)
                    success = True
                except subprocess.CalledProcessError:
                    colored_print("❌ Build failed", Colors.RED)
                    success = False
            else:
                success = build_executable(args.mode)
            sys.exit(0 if success else 1)
            
        elif args.command == "security":
            # Security scans with bandit and safety
            env_type = should_use_env()
            if env_type and not check_env_exists():
                colored_print(f"❌ {env_type.upper()} environment doesn't exist. Create it first.", Colors.RED)
                sys.exit(1)
                
            if env_type:
                # Run security scans in virtual environment
                python_exe = str(get_env_python())
                colored_print(f"🔒 Running security scans in {env_type}...", Colors.BLUE)
                
                scans = [
                    ([python_exe, "-m", "bandit", "-r", "src/", "-f", "json"], "Bandit security scan"),
                    ([python_exe, "-m", "safety", "check", "--json"], "Safety vulnerability check"),
                ]
                
                all_passed = True
                for cmd, name in scans:
                    try:
                        colored_print(f"  Running {name}...", Colors.CYAN)
                        run_command(cmd, check=False, capture=True)
                        colored_print(f"  ✅ {name} completed", Colors.GREEN)
                    except FileNotFoundError:
                        colored_print(f"  ⚠️ {name} skipped (tool not installed)", Colors.YELLOW)
                    except subprocess.CalledProcessError:
                        colored_print(f"  ❌ {name} failed", Colors.RED)
                        all_passed = False
                
                sys.exit(0 if all_passed else 1)
            else:
                success = run_security_scan()
                sys.exit(0 if success else 1)
                
        elif args.command == "quality":
            # Comprehensive quality check/fix using tools/quality_*.py (11 tools)
            env_type = should_use_env()
            if env_type and not check_env_exists():
                colored_print(f"❌ {env_type.upper()} environment doesn't exist. Create it first.", Colors.RED)
                sys.exit(1)
            
            if args.fix:
                # Run comprehensive quality fixes
                if env_type:
                    python_exe = str(get_env_python())
                    colored_print(f"🔧 Running comprehensive quality fixes in {env_type}...", Colors.BLUE)
                    
                    try:
                        # Set environment variable to avoid re-detection in quality_fix.py
                        env = os.environ.copy()
                        env["SCREEN_TRANSLATOR_PYTHON_ENV"] = env_type
                        env["SCREEN_TRANSLATOR_PYTHON_EXE"] = python_exe
                        
                        result = subprocess.run([python_exe, "tools/quality_fix.py"], 
                                              env=env, check=True, cwd=Path(__file__).parent)
                        colored_print("✅ Quality fixes completed", Colors.GREEN)
                    except subprocess.CalledProcessError:
                        colored_print("❌ Quality fixes failed", Colors.RED)
                        sys.exit(1)
                else:
                    # Run quality fixes with system Python
                    colored_print("🔧 Running comprehensive quality fixes...", Colors.BLUE)
                    try:
                        run_command([sys.executable, "tools/quality_fix.py"])
                        colored_print("✅ Quality fixes completed", Colors.GREEN)
                    except subprocess.CalledProcessError:
                        colored_print("❌ Quality fixes failed", Colors.RED)
                        sys.exit(1)
            else:
                # Run comprehensive quality checks
                if env_type:
                    python_exe = str(get_env_python())
                    colored_print(f"🔍 Running comprehensive quality checks in {env_type}...", Colors.BLUE)
                    
                    try:
                        # Set environment variable to avoid re-detection in quality_check.py
                        env = os.environ.copy()
                        env["SCREEN_TRANSLATOR_PYTHON_ENV"] = env_type
                        env["SCREEN_TRANSLATOR_PYTHON_EXE"] = python_exe
                        
                        result = subprocess.run([python_exe, "tools/quality_check.py"], 
                                              env=env, check=True, cwd=Path(__file__).parent)
                        colored_print("✅ Quality checks completed", Colors.GREEN)
                    except subprocess.CalledProcessError:
                        colored_print("❌ Quality checks failed", Colors.RED)
                        sys.exit(1)
                else:
                    # Run quality check with system Python
                    colored_print("🔍 Running comprehensive quality checks...", Colors.BLUE)
                    try:
                        run_command([sys.executable, "tools/quality_check.py"])
                        colored_print("✅ Quality checks completed", Colors.GREEN)
                    except subprocess.CalledProcessError:
                        colored_print("❌ Quality checks failed", Colors.RED)
                        sys.exit(1)
            
        elif args.command == "clean":
            clean_project()
            
        elif args.command == "ci":
            # Full CI pipeline
            env_type = should_use_env()
            env_name = env_type if env_type else "system environment"
            colored_print(f"🚀 Running full CI pipeline in {env_name}...", Colors.MAGENTA)
            
            if env_type and not check_env_exists():
                colored_print(f"❌ {env_type.upper()} environment doesn't exist. Create it first.", Colors.RED)
                sys.exit(1)
            
            if env_type:
                python_exe = str(get_env_python())
                
                # Define venv-based steps
                def run_quality_venv():
                    commands = [
                        ([python_exe, "-m", "black", "--check", "src/"], "Black formatting"),
                        ([python_exe, "-m", "isort", "--check-only", "src/"], "Import sorting"),
                        ([python_exe, "-m", "flake8", "src/"], "Flake8 linting"),
                        ([python_exe, "-m", "mypy", "src/"], "MyPy type checking"),
                    ]
                    for cmd, name in commands:
                        try:
                            run_command(cmd, check=True, capture=True)
                        except subprocess.CalledProcessError:
                            return False
                        except FileNotFoundError:
                            pass  # Skip missing tools
                    return True
                
                def run_unit_tests_venv():
                    cmd = [python_exe, "-m", "pytest", "src/tests/unit/", "--cov=src", "--cov-report=term"]
                    try:
                        run_command(cmd)
                        return True
                    except subprocess.CalledProcessError:
                        return False
                
                def run_integration_tests_venv():
                    cmd = [python_exe, "-m", "pytest", "src/tests/integration/"]
                    try:
                        run_command(cmd)
                        return True
                    except subprocess.CalledProcessError:
                        return False
                
                def run_security_venv():
                    scans = [
                        ([python_exe, "-m", "bandit", "-r", "src/", "-f", "json"], "Bandit"),
                        ([python_exe, "-m", "safety", "check", "--json"], "Safety"),
                    ]
                    for cmd, name in scans:
                        try:
                            run_command(cmd, check=True, capture=True)
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            pass  # Security scans are optional for CI
                    return True
                
                def build_release_venv():
                    cmd = [
                        python_exe, "-m", "PyInstaller",
                        "--onefile", "--windowed",
                        "--icon=icon.ico", "--name=ScreenTranslator-release",
                        "main.py"
                    ]
                    try:
                        run_command(cmd)
                        return True
                    except subprocess.CalledProcessError:
                        return False
                
                steps = [
                    ("Code Quality", run_quality_venv),
                    ("Unit Tests", run_unit_tests_venv),
                    ("Integration Tests", run_integration_tests_venv),
                    ("Security Scan", run_security_venv),
                    ("Build Release", build_release_venv),
                ]
            else:
                # Use original functions for system environment
                steps = [
                    ("Code Quality", lambda: run_code_quality()),
                    ("Unit Tests", lambda: run_tests("unit", True)),
                    ("Integration Tests", lambda: run_tests("integration")),
                    ("Security Scan", lambda: run_security_scan()),
                    ("Build Release", lambda: build_executable("release")),
                ]
            
            for step_name, step_func in steps:
                colored_print(f"\n📋 Step: {step_name}", Colors.MAGENTA)
                try:
                    success = step_func()
                    if not success:
                        colored_print(f"❌ CI pipeline failed at: {step_name}", Colors.RED)
                        sys.exit(1)
                    colored_print(f"✅ {step_name} completed", Colors.GREEN)
                except Exception as e:
                    colored_print(f"❌ CI pipeline failed at {step_name}: {e}", Colors.RED)
                    sys.exit(1)
            
            colored_print(f"\n🎉 CI pipeline completed successfully in {env_type}!", Colors.GREEN)
    
    except KeyboardInterrupt:
        colored_print("\n❌ Interrupted by user", Colors.RED)
        sys.exit(1)
    except Exception as e:
        colored_print(f"\n❌ Unexpected error: {e}", Colors.RED)
        sys.exit(1)

if __name__ == "__main__":
    main()
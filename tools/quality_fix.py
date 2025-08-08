#!/usr/bin/env python3
"""
Automatic code quality fixes for Screen Translator project.
"""

import subprocess
import sys
import os
import platform
from pathlib import Path


def get_cmd_prefix():
    """Get command prefix for virtual environment"""
    cmd_prefix = []
    
    # Check if environment info was passed from build.py (optimized)
    env_type = os.environ.get("SCREEN_TRANSLATOR_PYTHON_ENV")
    python_exe_path = os.environ.get("SCREEN_TRANSLATOR_PYTHON_EXE")
    
    if env_type and python_exe_path:
        # Use pre-determined environment info (avoids redundant detection)
        cmd_prefix = [python_exe_path, "-m"]
        print(f"Using {env_type.upper()} environment (from build.py): {python_exe_path}")
    else:
        # Fallback to auto-detection (for direct script calls)
        # Check for wenv first (Windows Environment - preferred on Windows)
        if os.path.exists("wenv") and platform.system() == "Windows":
            python_exe = Path("wenv") / "Scripts" / "python.exe"
            if python_exe.exists():
                cmd_prefix = [str(python_exe), "-m"]
                print(f"Using Windows Environment (wenv): {python_exe}")
        # Check for .venv (legacy or Linux/macOS)
        elif os.path.exists(".venv"):
            if platform.system() == "Windows":
                python_exe = Path(".venv") / "Scripts" / "python.exe"
            else:
                python_exe = Path(".venv") / "bin" / "python"
            if python_exe.exists():
                cmd_prefix = [str(python_exe), "-m"]
                print(f"Using Virtual Environment (.venv): {python_exe}")
        else:
            print("No virtual environment found, using system Python")
    
    return cmd_prefix


def run_command(cmd: list, description: str):
    """Run a command and show progress"""
    print(f"\n🔧 {description}...")
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"   ✅ Success!")
        if result.stdout:
            print(f"   Output: {result.stdout[:200]}...")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed: {e}")
        if e.stderr:
            print(f"   Error: {e.stderr}")
        return False


def main():
    """Run automatic fixes"""
    print("="*60)
    print("🛠️  AUTOMATIC CODE QUALITY FIXES")
    print("="*60)
    
    src_path = "src"
    cmd_prefix = get_cmd_prefix()
    
    fixes = [
        (cmd_prefix + ["black", src_path], "Formatting code with Black"),
        (cmd_prefix + ["isort", src_path], "Sorting imports with isort"),
        (cmd_prefix + ["autoflake", "--in-place", "--remove-unused-variables", 
          "--remove-all-unused-imports", "--recursive", src_path], 
         "Removing unused imports and variables"),
    ]
    
    success_count = 0
    for cmd, description in fixes:
        if run_command(cmd, description):
            success_count += 1
    
    print("\n" + "="*60)
    print(f"✨ Completed {success_count}/{len(fixes)} fixes successfully!")
    print("="*60)
    print("\n💡 Next steps:")
    print("   1. Review the changes with: git diff")
    print("   2. Run quality checks with: python quality_check.py")
    print("   3. Commit the improvements!")
    
    return success_count == len(fixes)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
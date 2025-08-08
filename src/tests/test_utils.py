"""
Common test utilities and unittest skip decorators for platform-specific tests
"""

import os
import sys
import unittest

# Platform detection
is_windows = sys.platform == "win32"
is_linux = sys.platform.startswith("linux")
is_macos = sys.platform == "darwin"

# Display detection
has_display = bool(os.environ.get("DISPLAY") or is_windows)


def _check_tesseract_available():
    """Check if Tesseract is available"""
    try:
        import subprocess

        result = subprocess.run(
            ["tesseract", "--version"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.SubprocessError, subprocess.TimeoutExpired):
        return False


# Common unittest skip decorators
skip_on_linux = unittest.skipIf(is_linux, "Windows-specific functionality")

skip_on_windows = unittest.skipIf(is_windows, "Linux/Unix-specific functionality")

skip_without_display = unittest.skipIf(not has_display, "GUI tests require display")

skip_on_ci = unittest.skipIf(
    os.environ.get("CI", "").lower() == "true", "Test not suitable for CI environment"
)

requires_windows = unittest.skipIf(not is_windows, "Requires Windows platform")

requires_linux = unittest.skipIf(not is_linux, "Requires Linux platform")

requires_tesseract = unittest.skipIf(
    not _check_tesseract_available(), "Tesseract OCR not installed"
)


# Test utilities for common operations
def create_temp_image():
    """Create a temporary test image"""
    import tempfile

    from PIL import Image

    img = Image.new("RGB", (100, 100), color="white")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img.save(f, "PNG")
        return f.name


def cleanup_temp_file(filepath):
    """Clean up temporary file"""
    try:
        os.unlink(filepath)
    except (OSError, FileNotFoundError, PermissionError):
        pass


def create_mock_display():
    """Create a mock display for headless testing"""
    if not has_display:
        from unittest.mock import MagicMock

        mock_root = MagicMock()
        mock_root.winfo_screenwidth.return_value = 1920
        mock_root.winfo_screenheight.return_value = 1080
        return mock_root
    return None

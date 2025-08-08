"""
Pytest configuration and fixtures.
"""

import sys
from pathlib import Path

# Add src to Python path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest


@pytest.fixture
def sample_translation_data():
    """Sample translation data for tests."""
    return {
        "original": "Hello World",
        "translated": "Привет Мир",
        "source_language": "en",
        "target_language": "ru",
        "confidence": 0.95,
    }


@pytest.fixture
def sample_coordinates():
    """Sample screen coordinates for tests."""
    return {"x1": 10, "y1": 20, "x2": 100, "y2": 150}

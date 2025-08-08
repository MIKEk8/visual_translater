"""Unit tests for settings window module"""

try:
    import tkinter as tk
except ImportError:
    print("tkinter не доступен в данной среде")
    tk = None
from unittest.mock import MagicMock, patch

import pytest

from src.ui.settings_window import SettingsWindow


class TestSettingsWindow:
    """Test cases for SettingsWindow"""

    @pytest.fixture
    def mock_config_manager(self):
        """Mock configuration manager"""
        config_manager = MagicMock()

        # Mock config structure
        mock_config = MagicMock()
        mock_config.languages.ocr_languages = ["en", "ru"]
        mock_config.languages.target_languages = ["en", "ru", "es"]
        mock_config.tts.enabled = True
        mock_config.tts.rate = 150
        mock_config.tts.volume = 0.8

        config_manager.get_config.return_value = mock_config
        return config_manager

    @pytest.fixture
    def mock_tts_processor(self):
        """Mock TTS processor"""
        return MagicMock()

    @patch("src.ui.settings_window.(tk.Toplevel if tk else None)")
    def test_settings_window_creation(self, mock_toplevel, mock_config_manager, mock_tts_processor):
        """Test that settings window can be created without errors"""

        # This should not raise errors
        window = SettingsWindow(mock_config_manager, mock_tts_processor)

        # Verify window was created
        mock_toplevel.assert_called_once()

        # Verify components exist
        assert hasattr(window, "window")
        assert hasattr(window, "config_manager")
        assert hasattr(window, "tts_processor")

    @patch("src.ui.settings_window.(tk.Toplevel if tk else None)")
    def test_show_window(self, mock_toplevel, mock_config_manager, mock_tts_processor):
        """Test showing the settings window"""

        window = SettingsWindow(mock_config_manager, mock_tts_processor)

        # Mock window methods
        window.window.deiconify = MagicMock()
        window.window.lift = MagicMock()
        window.window.focus_force = MagicMock()

        window.show()

        # Verify window was shown
        window.window.deiconify.assert_called_once()
        window.window.lift.assert_called_once()
        window.window.focus_force.assert_called_once()

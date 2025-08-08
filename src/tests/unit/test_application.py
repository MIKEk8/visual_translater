"""Unit tests for application module"""

import threading
import unittest.mock as mock
from unittest.mock import MagicMock, patch

import pytest

from src.core.application import ScreenTranslatorApp
from src.services.config_manager import ConfigManager
from src.services.container import DIContainer


class TestScreenTranslatorApp:
    """Test cases for ScreenTranslatorApp"""

    @pytest.fixture
    def mock_container(self):
        """Mock DI container with required services"""
        container = MagicMock(spec=DIContainer)

        # Mock services
        container.get.side_effect = lambda service_type: {
            ConfigManager: MagicMock(),
            "ScreenshotEngine": MagicMock(),
            "PluginService": MagicMock(),
            "OCRProcessor": MagicMock(),
            "TranslationProcessor": MagicMock(),
            "TTSProcessor": MagicMock(),
        }.get(service_type, MagicMock())

        return container

    @patch("src.core.application.tk.Tk")
    @patch("src.core.application.get_task_queue")
    @patch("src.core.application.get_event_bus")
    @patch("src.core.application.get_performance_monitor")
    def test_init_creates_lock_first(
        self, mock_perf_monitor, mock_event_bus, mock_task_queue, mock_tk, mock_container
    ):
        """Test that _lock is created before being used"""

        # This should not raise AttributeError
        app = ScreenTranslatorApp(mock_container)

        # Verify lock exists
        assert hasattr(app, "_lock")
        assert isinstance(app._lock, threading.Lock)

        # Verify GUI was initialized
        mock_tk.assert_called_once()

    @patch("src.core.application.tk.Tk")
    @patch("src.core.application.get_task_queue")
    @patch("src.core.application.get_event_bus")
    @patch("src.core.application.get_performance_monitor")
    def test_init_thread_safety(
        self, mock_perf_monitor, mock_event_bus, mock_task_queue, mock_tk, mock_container
    ):
        """Test thread safety during initialization"""

        app = ScreenTranslatorApp(mock_container)

        # Test accessing shared state with lock
        with app._lock:
            app.current_language_index = 1
            app.last_translation = "test"
            app.translation_history = ["item1"]

        # Should not deadlock or raise errors
        assert app.current_language_index == 1
        assert app.last_translation == "test"
        assert len(app.translation_history) == 1

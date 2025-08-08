"""
Tests for logger utility module.
"""

import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.utils.logger import AppLogger, logger


class TestAppLogger:
    """Test AppLogger functionality."""

    def test_singleton_pattern(self):
        """Test that AppLogger follows singleton pattern."""
        logger1 = AppLogger()
        logger2 = AppLogger()

        assert logger1 is logger2
        assert id(logger1) == id(logger2)

    def test_initialization(self):
        """Test AppLogger initialization."""
        app_logger = AppLogger()

        assert app_logger.logger is not None
        assert app_logger.logger.name == "screen_translator"
        assert app_logger._initialized is True

    def test_setup_logging_basic(self):
        """Test basic logging setup."""
        app_logger = AppLogger()

        # Test with different log levels
        app_logger.setup_logging("DEBUG")
        assert app_logger.logger.level == logging.DEBUG

        app_logger.setup_logging("WARNING")
        assert app_logger.logger.level == logging.WARNING

    def test_setup_logging_with_file(self):
        """Test logging setup with file handler."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file_path = temp_file.name

        app_logger = AppLogger()
        app_logger.setup_logging("INFO", temp_file_path)

        # Check that file handler was added
        file_handlers = [
            h for h in app_logger.logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1

        # Cleanup
        Path(temp_file_path).unlink(missing_ok=True)

    def test_setup_logging_file_permission_error(self):
        """Test logging setup with file permission error."""
        app_logger = AppLogger()

        # Use invalid path that should cause permission error
        invalid_path = "/root/nonexistent/test.log"

        with patch.object(app_logger.logger, "warning") as mock_warning:
            app_logger.setup_logging("INFO", invalid_path)
            # Should warn about file creation failure
            mock_warning.assert_called()

    def test_log_translation(self):
        """Test translation logging."""
        app_logger = AppLogger()

        with patch.object(app_logger.logger, "info") as mock_info:
            app_logger.log_translation(
                original="Hello",
                translated="Bonjour",
                source_lang="en",
                target_lang="fr",
                duration=1.23,
                cached=True,
            )

            mock_info.assert_called_once()
            log_message = mock_info.call_args[0][0]
            assert "Translation completed" in log_message
            assert "en" in log_message
            assert "fr" in log_message
            assert "5->7" in log_message  # length change
            assert "1.23s" in log_message
            assert "Cached: True" in log_message

    def test_log_translation_not_cached(self):
        """Test translation logging without cache."""
        app_logger = AppLogger()

        with patch.object(app_logger.logger, "info") as mock_info:
            app_logger.log_translation(
                original="Test",
                translated="Prueba",
                source_lang="en",
                target_lang="es",
                duration=0.5,
            )

            log_message = mock_info.call_args[0][0]
            assert "Cached: False" in log_message

    def test_log_screenshot(self):
        """Test screenshot logging."""
        app_logger = AppLogger()

        with patch.object(app_logger.logger, "info") as mock_info:
            app_logger.log_screenshot(
                coordinates=(100, 200, 300, 400), size=(200, 200), duration=0.1
            )

            mock_info.assert_called_once()
            log_message = mock_info.call_args[0][0]
            assert "Screenshot captured" in log_message
            assert "(100, 200, 300, 400)" in log_message
            assert "(200, 200)" in log_message
            assert "0.10s" in log_message

    def test_log_ocr_with_confidence(self):
        """Test OCR logging with confidence score."""
        app_logger = AppLogger()

        with patch.object(app_logger.logger, "info") as mock_info:
            app_logger.log_ocr(text_length=150, confidence=95.5, duration=2.1)

            mock_info.assert_called_once()
            log_message = mock_info.call_args[0][0]
            assert "OCR completed" in log_message
            assert "150" in log_message
            assert "95.50" in log_message
            assert "2.10s" in log_message

    def test_log_ocr_without_confidence(self):
        """Test OCR logging without confidence score."""
        app_logger = AppLogger()

        with patch.object(app_logger.logger, "info") as mock_info:
            app_logger.log_ocr(text_length=75, confidence=None, duration=1.0)

            log_message = mock_info.call_args[0][0]
            assert "N/A" in log_message

    def test_log_tts_with_voice(self):
        """Test TTS logging with voice ID."""
        app_logger = AppLogger()

        with patch.object(app_logger.logger, "info") as mock_info:
            app_logger.log_tts(text_length=50, voice_id="en-US-Female", duration=3.2)

            mock_info.assert_called_once()
            log_message = mock_info.call_args[0][0]
            assert "TTS completed" in log_message
            assert "50" in log_message
            assert "en-US-Female" in log_message
            assert "3.20s" in log_message

    def test_log_tts_without_voice(self):
        """Test TTS logging without voice ID."""
        app_logger = AppLogger()

        with patch.object(app_logger.logger, "info") as mock_info:
            app_logger.log_tts(text_length=30, voice_id=None, duration=2.0)

            log_message = mock_info.call_args[0][0]
            assert "default" in log_message

    def test_log_error_basic(self):
        """Test basic error logging."""
        app_logger = AppLogger()

        with patch.object(app_logger.logger, "error") as mock_error:
            test_exception = ValueError("Test error message")
            app_logger.log_error("test_operation", test_exception)

            mock_error.assert_called_once()
            log_message = mock_error.call_args[0][0]
            assert "Error in test_operation" in log_message
            assert "ValueError" in log_message
            assert "Test error message" in log_message

    def test_log_error_with_context(self):
        """Test error logging with context."""
        app_logger = AppLogger()

        with patch.object(app_logger.logger, "error") as mock_error:
            test_exception = RuntimeError("Runtime issue")
            context = {"user_id": "123", "action": "translate"}
            app_logger.log_error("translation", test_exception, context)

            log_message = mock_error.call_args[0][0]
            assert "user_id: 123" in log_message
            assert "action: translate" in log_message

    def test_log_config_change(self):
        """Test configuration change logging."""
        app_logger = AppLogger()

        with patch.object(app_logger.logger, "info") as mock_info:
            app_logger.log_config_change(key="language.target", old_value="en", new_value="fr")

            mock_info.assert_called_once()
            log_message = mock_info.call_args[0][0]
            assert "Config changed" in log_message
            assert "language.target" in log_message
            assert "Old: en" in log_message
            assert "New: fr" in log_message

    def test_log_startup(self):
        """Test startup logging."""
        app_logger = AppLogger()

        with patch.object(app_logger.logger, "info") as mock_info:
            app_logger.log_startup("2.0.1")

            mock_info.assert_called_once()
            log_message = mock_info.call_args[0][0]
            assert "Screen Translator v2.0.1 starting up" in log_message

    def test_log_shutdown(self):
        """Test shutdown logging."""
        app_logger = AppLogger()

        with patch.object(app_logger.logger, "info") as mock_info:
            app_logger.log_shutdown()

            mock_info.assert_called_once()
            log_message = mock_info.call_args[0][0]
            assert "Screen Translator shutting down" in log_message

    def test_convenience_methods(self):
        """Test convenience logging methods."""
        app_logger = AppLogger()

        with patch.object(app_logger.logger, "debug") as mock_debug:
            app_logger.debug("Debug message", key1="value1")
            log_message = mock_debug.call_args[0][0]
            assert "Debug message" in log_message
            assert "key1: value1" in log_message

        with patch.object(app_logger.logger, "info") as mock_info:
            app_logger.info("Info message", status="ok")
            log_message = mock_info.call_args[0][0]
            assert "Info message" in log_message
            assert "status: ok" in log_message

        with patch.object(app_logger.logger, "warning") as mock_warning:
            app_logger.warning("Warning message", code=404)
            log_message = mock_warning.call_args[0][0]
            assert "Warning message" in log_message
            assert "code: 404" in log_message

        with patch.object(app_logger.logger, "error") as mock_error:
            app_logger.error("Error message", fatal=True)
            log_message = mock_error.call_args[0][0]
            assert "Error message" in log_message
            assert "fatal: True" in log_message

    def test_convenience_methods_without_kwargs(self):
        """Test convenience methods without keyword arguments."""
        app_logger = AppLogger()

        with patch.object(app_logger.logger, "debug") as mock_debug:
            app_logger.debug("Plain debug message")
            mock_debug.assert_called_with("Plain debug message")

        with patch.object(app_logger.logger, "info") as mock_info:
            app_logger.info("Plain info message")
            mock_info.assert_called_with("Plain info message")


class TestGlobalLoggerInstance:
    """Test the global logger instance."""

    def test_global_logger_is_app_logger(self):
        """Test that global logger is an AppLogger instance."""
        assert isinstance(logger, AppLogger)

    def test_global_logger_is_singleton(self):
        """Test that global logger follows singleton pattern."""
        new_logger = AppLogger()
        assert logger is new_logger

    def test_global_logger_methods_work(self):
        """Test that global logger methods work."""
        with patch.object(logger.logger, "info") as mock_info:
            logger.info("Test global logger")
            mock_info.assert_called_once()

    def test_formatter_setup(self):
        """Test that formatter is properly configured."""
        app_logger = AppLogger()

        # Check that handlers have formatters
        for handler in app_logger.logger.handlers:
            assert handler.formatter is not None
            format_string = handler.formatter._fmt
            assert "%(asctime)s" in format_string
            assert "%(levelname)" in format_string
            assert "%(name)s" in format_string
            assert "%(message)s" in format_string

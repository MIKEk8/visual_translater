"""
Tests for custom exceptions module.
"""

import pytest

from src.utils.exceptions import (
    CacheCorruptionError,
    CacheError,
    ConfigurationError,
    HotkeyError,
    HotkeyRegistrationError,
    InvalidAreaError,
    OCREngineNotAvailableError,
    OCRError,
    PluginError,
    PluginInitializationError,
    PluginNotFoundError,
    ScreenshotCaptureError,
    ScreenshotError,
    ScreenTranslatorError,
    ServiceError,
    ServiceNotAvailableError,
    SpeechFailedError,
    TaskExecutionError,
    TaskQueueError,
    TaskQueueFullError,
    TextExtractionError,
    TranslationEngineNotAvailableError,
    TranslationError,
    TranslationFailedError,
    TTSEngineNotAvailableError,
    TTSError,
    UIError,
    UnsupportedLanguageError,
    WindowCreationError,
    wrap_exception,
)


class TestBaseExceptions:
    """Test base exception classes."""

    def test_screen_translator_error_basic(self):
        """Test basic ScreenTranslatorError functionality."""
        error = ScreenTranslatorError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.details == {}

    def test_screen_translator_error_with_details(self):
        """Test ScreenTranslatorError with details."""
        details = {"code": 500, "source": "test"}
        error = ScreenTranslatorError("Error with details", details)

        assert error.message == "Error with details"
        assert error.details == details
        assert "Details:" in str(error)
        assert "code" in str(error)

    def test_screen_translator_error_inheritance(self):
        """Test that ScreenTranslatorError inherits from Exception."""
        error = ScreenTranslatorError("Test")
        assert isinstance(error, Exception)

    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Config file not found")
        assert isinstance(error, ScreenTranslatorError)
        assert str(error) == "Config file not found"


class TestPluginExceptions:
    """Test plugin-related exceptions."""

    def test_plugin_error(self):
        """Test PluginError base class."""
        error = PluginError("Plugin failed")
        assert isinstance(error, ScreenTranslatorError)
        assert str(error) == "Plugin failed"

    def test_plugin_not_found_error_basic(self):
        """Test PluginNotFoundError with just type."""
        error = PluginNotFoundError("ocr")
        assert isinstance(error, PluginError)
        assert error.plugin_type == "ocr"
        assert error.plugin_name is None
        assert "Plugin not found: ocr" in str(error)

    def test_plugin_not_found_error_with_name(self):
        """Test PluginNotFoundError with type and name."""
        error = PluginNotFoundError("translation", "google_translate")
        assert error.plugin_type == "translation"
        assert error.plugin_name == "google_translate"
        assert "translation (google_translate)" in str(error)
        assert error.details["plugin_type"] == "translation"
        assert error.details["plugin_name"] == "google_translate"

    def test_plugin_initialization_error(self):
        """Test PluginInitializationError."""
        error = PluginInitializationError("tesseract", "Missing executable")
        assert isinstance(error, PluginError)
        assert error.plugin_name == "tesseract"
        assert error.reason == "Missing executable"
        assert "tesseract" in str(error)
        assert "Missing executable" in str(error)


class TestScreenshotExceptions:
    """Test screenshot-related exceptions."""

    def test_screenshot_error(self):
        """Test ScreenshotError base class."""
        error = ScreenshotError("Screenshot failed")
        assert isinstance(error, ScreenTranslatorError)
        assert str(error) == "Screenshot failed"

    def test_screenshot_capture_error(self):
        """Test ScreenshotCaptureError."""
        error = ScreenshotCaptureError((0, 0, 100, 100), "Invalid coordinates")
        assert isinstance(error, ScreenshotError)
        assert error.coordinates == (0, 0, 100, 100)
        assert error.reason == "Invalid coordinates"
        assert "Invalid coordinates" in str(error)

    def test_invalid_area_error(self):
        """Test InvalidAreaError."""
        error = InvalidAreaError((0, 0, -100, -100))
        assert isinstance(error, ScreenshotError)
        assert error.coordinates == (0, 0, -100, -100)
        assert "Invalid screenshot area" in str(error)


class TestOCRExceptions:
    """Test OCR-related exceptions."""

    def test_ocr_error(self):
        """Test OCRError base class."""
        error = OCRError("OCR processing failed")
        assert isinstance(error, ScreenTranslatorError)
        assert str(error) == "OCR processing failed"

    def test_ocr_engine_not_available_error(self):
        """Test OCREngineNotAvailableError."""
        error = OCREngineNotAvailableError("tesseract", "Not installed")
        assert isinstance(error, OCRError)
        assert error.engine_name == "tesseract"
        assert error.reason == "Not installed"
        assert "tesseract" in str(error)
        assert "Not installed" in str(error)

    def test_text_extraction_error(self):
        """Test TextExtractionError."""
        error = TextExtractionError("Low quality image", (100, 100))
        assert isinstance(error, OCRError)
        assert error.reason == "Low quality image"
        assert error.image_size == (100, 100)
        assert "Low quality image" in str(error)

    def test_text_extraction_error_no_size(self):
        """Test TextExtractionError without image size."""
        error = TextExtractionError("Processing failed")
        assert error.reason == "Processing failed"
        assert error.image_size is None


class TestTranslationExceptions:
    """Test translation-related exceptions."""

    def test_translation_error(self):
        """Test TranslationError base class."""
        error = TranslationError("Translation failed")
        assert isinstance(error, ScreenTranslatorError)
        assert str(error) == "Translation failed"

    def test_translation_engine_not_available_error(self):
        """Test TranslationEngineNotAvailableError."""
        error = TranslationEngineNotAvailableError("google", "API key invalid")
        assert isinstance(error, TranslationError)
        assert error.engine_name == "google"
        assert error.reason == "API key invalid"
        assert "google" in str(error)
        assert "API key invalid" in str(error)

    def test_translation_failed_error(self):
        """Test TranslationFailedError."""
        error = TranslationFailedError("Hello world", "en", "fr", "API quota exceeded")
        assert isinstance(error, TranslationError)
        assert error.text == "Hello world"
        assert error.source_lang == "en"
        assert error.target_lang == "fr"
        assert error.reason == "API quota exceeded"
        assert "en -> fr" in str(error)
        assert error.details["text_length"] == 11

    def test_unsupported_language_error(self):
        """Test UnsupportedLanguageError."""
        error = UnsupportedLanguageError("klingon", "google_translate")
        assert isinstance(error, TranslationError)
        assert error.language == "klingon"
        assert error.engine_name == "google_translate"
        assert "klingon" in str(error)
        assert "google_translate" in str(error)


class TestTTSExceptions:
    """Test TTS-related exceptions."""

    def test_tts_error(self):
        """Test TTSError base class."""
        error = TTSError("TTS failed")
        assert isinstance(error, ScreenTranslatorError)
        assert str(error) == "TTS failed"

    def test_tts_engine_not_available_error(self):
        """Test TTSEngineNotAvailableError."""
        error = TTSEngineNotAvailableError("espeak", "Not installed")
        assert isinstance(error, TTSError)
        assert error.engine_name == "espeak"
        assert error.reason == "Not installed"
        assert "espeak" in str(error)

    def test_speech_failed_error(self):
        """Test SpeechFailedError."""
        error = SpeechFailedError("Hello world", "en", "Voice not found")
        assert isinstance(error, TTSError)
        assert error.text == "Hello world"
        assert error.language == "en"
        assert error.reason == "Voice not found"
        assert "en" in str(error)
        assert error.details["text_length"] == 11


class TestCacheExceptions:
    """Test cache-related exceptions."""

    def test_cache_error(self):
        """Test CacheError base class."""
        error = CacheError("Cache operation failed")
        assert isinstance(error, ScreenTranslatorError)
        assert str(error) == "Cache operation failed"

    def test_cache_corruption_error(self):
        """Test CacheCorruptionError."""
        error = CacheCorruptionError("translation_key", "Invalid JSON")
        assert isinstance(error, CacheError)
        assert error.key == "translation_key"
        assert error.reason == "Invalid JSON"
        assert "translation_key" in str(error)
        assert "Invalid JSON" in str(error)


class TestUIExceptions:
    """Test UI-related exceptions."""

    def test_ui_error(self):
        """Test UIError base class."""
        error = UIError("UI error")
        assert isinstance(error, ScreenTranslatorError)
        assert str(error) == "UI error"

    def test_window_creation_error(self):
        """Test WindowCreationError."""
        error = WindowCreationError("settings", "Display not available")
        assert isinstance(error, UIError)
        assert error.window_type == "settings"
        assert error.reason == "Display not available"
        assert "settings" in str(error)
        assert "Display not available" in str(error)


class TestHotkeyExceptions:
    """Test hotkey-related exceptions."""

    def test_hotkey_error(self):
        """Test HotkeyError base class."""
        error = HotkeyError("Hotkey registration failed")
        assert isinstance(error, ScreenTranslatorError)
        assert str(error) == "Hotkey registration failed"

    def test_hotkey_registration_error(self):
        """Test HotkeyRegistrationError."""
        error = HotkeyRegistrationError("ctrl+c", "Already registered")
        assert isinstance(error, HotkeyError)
        assert error.hotkey == "ctrl+c"
        assert error.reason == "Already registered"
        assert "ctrl+c" in str(error)
        assert "Already registered" in str(error)


class TestServiceExceptions:
    """Test service-related exceptions."""

    def test_service_error(self):
        """Test ServiceError base class."""
        error = ServiceError("Service error")
        assert isinstance(error, ScreenTranslatorError)
        assert str(error) == "Service error"

    def test_service_not_available_error(self):
        """Test ServiceNotAvailableError."""
        error = ServiceNotAvailableError("translation_service")
        assert isinstance(error, ServiceError)
        assert error.service_name == "translation_service"
        assert "translation_service" in str(error)


class TestTaskQueueExceptions:
    """Test task queue-related exceptions."""

    def test_task_queue_error(self):
        """Test TaskQueueError base class."""
        error = TaskQueueError("Queue error")
        assert isinstance(error, ScreenTranslatorError)
        assert str(error) == "Queue error"

    def test_task_queue_full_error(self):
        """Test TaskQueueFullError."""
        error = TaskQueueFullError(100)
        assert isinstance(error, TaskQueueError)
        assert error.queue_size == 100
        assert "100" in str(error)
        assert "full" in str(error)

    def test_task_execution_error(self):
        """Test TaskExecutionError."""
        error = TaskExecutionError("task_123", "translate_text", "Timeout")
        assert isinstance(error, TaskQueueError)
        assert error.task_id == "task_123"
        assert error.task_name == "translate_text"
        assert error.reason == "Timeout"
        assert "translate_text" in str(error)
        assert "Timeout" in str(error)


class TestWrapException:
    """Test the wrap_exception decorator."""

    def test_wrap_exception_passes_through_custom_exceptions(self):
        """Test that wrap_exception passes through custom exceptions."""

        @wrap_exception
        def failing_function():
            raise ConfigurationError("Config error")

        with pytest.raises(ConfigurationError):
            failing_function()

    def test_wrap_exception_wraps_standard_exceptions(self):
        """Test that wrap_exception wraps standard exceptions."""

        @wrap_exception
        def failing_function():
            raise ValueError("Standard error")

        with pytest.raises(ScreenTranslatorError) as exc_info:
            failing_function()

        assert "Unexpected error in failing_function" in str(exc_info.value)
        assert "Standard error" in str(exc_info.value)
        assert exc_info.value.details["function"] == "failing_function"
        assert exc_info.value.details["original_error"] == "Standard error"

    def test_wrap_exception_returns_normal_result(self):
        """Test that wrap_exception returns normal results."""

        @wrap_exception
        def normal_function(x, y):
            return x + y

        result = normal_function(2, 3)
        assert result == 5


class TestExceptionInheritance:
    """Test exception inheritance chains."""

    def test_all_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from ScreenTranslatorError."""
        exception_classes = [
            ConfigurationError,
            PluginError,
            PluginNotFoundError,
            PluginInitializationError,
            ScreenshotError,
            ScreenshotCaptureError,
            InvalidAreaError,
            OCRError,
            OCREngineNotAvailableError,
            TextExtractionError,
            TranslationError,
            TranslationEngineNotAvailableError,
            TranslationFailedError,
            UnsupportedLanguageError,
            TTSError,
            TTSEngineNotAvailableError,
            SpeechFailedError,
            CacheError,
            CacheCorruptionError,
            UIError,
            WindowCreationError,
            HotkeyError,
            HotkeyRegistrationError,
            ServiceError,
            ServiceNotAvailableError,
            TaskQueueError,
            TaskQueueFullError,
            TaskExecutionError,
        ]

        for exception_cls in exception_classes:
            # Create instance with minimal args
            if exception_cls in [PluginNotFoundError]:
                error = exception_cls("test")
            elif exception_cls in [
                PluginInitializationError,
                OCREngineNotAvailableError,
                TranslationEngineNotAvailableError,
                TTSEngineNotAvailableError,
                HotkeyRegistrationError,
                CacheCorruptionError,
                WindowCreationError,
            ]:
                error = exception_cls("test", "reason")
            elif exception_cls in [ScreenshotCaptureError]:
                error = exception_cls((0, 0, 100, 100), "reason")
            elif exception_cls in [InvalidAreaError]:
                error = exception_cls((0, 0, 100, 100))
            elif exception_cls in [TextExtractionError]:
                error = exception_cls("reason")
            elif exception_cls in [TranslationFailedError]:
                error = exception_cls("text", "en", "fr", "reason")
            elif exception_cls in [UnsupportedLanguageError]:
                error = exception_cls("lang", "engine")
            elif exception_cls in [SpeechFailedError]:
                error = exception_cls("text", "en", "reason")
            elif exception_cls in [ServiceNotAvailableError]:
                error = exception_cls("service")
            elif exception_cls in [TaskQueueFullError]:
                error = exception_cls(100)
            elif exception_cls in [TaskExecutionError]:
                error = exception_cls("id", "name", "reason")
            else:
                error = exception_cls("test message")

            assert isinstance(error, ScreenTranslatorError)
            assert isinstance(error, Exception)

    def test_exception_chaining(self):
        """Test exception chaining functionality."""
        # Test that exceptions can be caught by base class
        with pytest.raises(ScreenTranslatorError):
            raise PluginNotFoundError("test_plugin")

        with pytest.raises(PluginError):
            raise PluginInitializationError("test", "failed")

        with pytest.raises(OCRError):
            raise TextExtractionError("failed")

        with pytest.raises(TranslationError):
            raise UnsupportedLanguageError("klingon", "google")

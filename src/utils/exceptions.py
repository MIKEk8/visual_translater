"""
Custom exceptions for Screen Translator v2.0.
Provides specific error types for better error handling and debugging.
"""

from typing import Optional


class ScreenTranslatorError(Exception):
    """Base exception class for Screen Translator"""

    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class ConfigurationError(ScreenTranslatorError):
    """Raised when configuration is invalid or missing"""


class PluginError(ScreenTranslatorError):
    """Base class for plugin-related errors"""


class PluginNotFoundError(PluginError):
    """Raised when a required plugin is not found"""

    def __init__(self, plugin_type: str, plugin_name: Optional[str] = None):
        self.plugin_type = plugin_type
        self.plugin_name = plugin_name

        message = f"Plugin not found: {plugin_type}"
        if plugin_name:
            message += f" ({plugin_name})"

        super().__init__(message, {"plugin_type": plugin_type, "plugin_name": plugin_name})


class PluginInitializationError(PluginError):
    """Raised when plugin fails to initialize"""

    def __init__(self, plugin_name: str, reason: str):
        self.plugin_name = plugin_name
        self.reason = reason

        message = f"Plugin initialization failed: {plugin_name} - {reason}"
        super().__init__(message, {"plugin_name": plugin_name, "reason": reason})


class ScreenshotError(ScreenTranslatorError):
    """Base class for screenshot-related errors"""


class ScreenshotCaptureError(ScreenshotError):
    """Raised when screenshot capture fails"""

    def __init__(self, coordinates: tuple, reason: str):
        self.coordinates = coordinates
        self.reason = reason

        message = f"Screenshot capture failed at {coordinates}: {reason}"
        super().__init__(message, {"coordinates": coordinates, "reason": reason})


class InvalidAreaError(ScreenshotError):
    """Raised when screenshot area is invalid"""

    def __init__(self, coordinates: tuple):
        self.coordinates = coordinates

        message = f"Invalid screenshot area: {coordinates}"
        super().__init__(message, {"coordinates": coordinates})


class OCRError(ScreenTranslatorError):
    """Base class for OCR-related errors"""


class OCREngineNotAvailableError(OCRError):
    """Raised when OCR engine is not available"""

    def __init__(self, engine_name: str, reason: str):
        self.engine_name = engine_name
        self.reason = reason

        message = f"OCR engine not available: {engine_name} - {reason}"
        super().__init__(message, {"engine_name": engine_name, "reason": reason})


class TextExtractionError(OCRError):
    """Raised when text extraction fails"""

    def __init__(self, reason: str, image_size: Optional[tuple] = None):
        self.reason = reason
        self.image_size = image_size

        message = f"Text extraction failed: {reason}"
        super().__init__(message, {"reason": reason, "image_size": image_size})


class TranslationError(ScreenTranslatorError):
    """Base class for translation-related errors"""


class TranslationEngineNotAvailableError(TranslationError):
    """Raised when translation engine is not available"""

    def __init__(self, engine_name: str, reason: str):
        self.engine_name = engine_name
        self.reason = reason

        message = f"Translation engine not available: {engine_name} - {reason}"
        super().__init__(message, {"engine_name": engine_name, "reason": reason})


class TranslationFailedError(TranslationError):
    """Raised when translation fails"""

    def __init__(self, text: str, source_lang: str, target_lang: str, reason: str):
        self.text = text
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.reason = reason

        message = f"Translation failed ({source_lang} -> {target_lang}): {reason}"
        super().__init__(
            message,
            {
                "text_length": len(text),
                "source_lang": source_lang,
                "target_lang": target_lang,
                "reason": reason,
            },
        )


class UnsupportedLanguageError(TranslationError):
    """Raised when language is not supported"""

    def __init__(self, language: str, engine_name: str):
        self.language = language
        self.engine_name = engine_name

        message = f"Unsupported language '{language}' for engine {engine_name}"
        super().__init__(message, {"language": language, "engine_name": engine_name})


class InvalidLanguageError(TranslationError):
    """Raised when language code is invalid"""

    def __init__(self, language: str, reason: str = "Invalid language code"):
        self.language = language
        self.reason = reason

        message = f"Invalid language '{language}': {reason}"
        super().__init__(message, {"language": language, "reason": reason})


class TTSError(ScreenTranslatorError):
    """Base class for TTS-related errors"""


class TTSEngineNotAvailableError(TTSError):
    """Raised when TTS engine is not available"""

    def __init__(self, engine_name: str, reason: str):
        self.engine_name = engine_name
        self.reason = reason

        message = f"TTS engine not available: {engine_name} - {reason}"
        super().__init__(message, {"engine_name": engine_name, "reason": reason})


class SpeechFailedError(TTSError):
    """Raised when speech synthesis fails"""

    def __init__(self, text: str, language: str, reason: str):
        self.text = text
        self.language = language
        self.reason = reason

        message = f"Speech synthesis failed ({language}): {reason}"
        super().__init__(
            message, {"text_length": len(text), "language": language, "reason": reason}
        )


class CacheError(ScreenTranslatorError):
    """Base class for cache-related errors"""


class CacheCorruptionError(CacheError):
    """Raised when cache data is corrupted"""

    def __init__(self, key: str, reason: str):
        self.key = key
        self.reason = reason

        message = f"Cache corruption detected for key {key}: {reason}"
        super().__init__(message, {"key": key, "reason": reason})


class UIError(ScreenTranslatorError):
    """Base class for UI-related errors"""


class WindowCreationError(UIError):
    """Raised when window creation fails"""

    def __init__(self, window_type: str, reason: str):
        self.window_type = window_type
        self.reason = reason

        message = f"Window creation failed ({window_type}): {reason}"
        super().__init__(message, {"window_type": window_type, "reason": reason})


class HotkeyError(ScreenTranslatorError):
    """Base class for hotkey-related errors"""


class HotkeyRegistrationError(HotkeyError):
    """Raised when hotkey registration fails"""

    def __init__(self, hotkey: str, reason: str):
        self.hotkey = hotkey
        self.reason = reason

        message = f"Hotkey registration failed ({hotkey}): {reason}"
        super().__init__(message, {"hotkey": hotkey, "reason": reason})


class ServiceError(ScreenTranslatorError):
    """Base class for service-related errors"""


class ServiceNotAvailableError(ServiceError):
    """Raised when required service is not available"""

    def __init__(self, service_name: str):
        self.service_name = service_name

        message = f"Service not available: {service_name}"
        super().__init__(message, {"service_name": service_name})


class TaskQueueError(ScreenTranslatorError):
    """Base class for task queue errors"""


class TaskQueueFullError(TaskQueueError):
    """Raised when task queue is full"""

    def __init__(self, queue_size: int):
        self.queue_size = queue_size

        message = f"Task queue is full (size: {queue_size})"
        super().__init__(message, {"queue_size": queue_size})


class TaskExecutionError(TaskQueueError):
    """Raised when task execution fails"""

    def __init__(self, task_id: str, task_name: str, reason: str):
        self.task_id = task_id
        self.task_name = task_name
        self.reason = reason

        message = f"Task execution failed ({task_name}): {reason}"
        super().__init__(message, {"task_id": task_id, "task_name": task_name, "reason": reason})


# Convenience function for error context
def wrap_exception(func):
    """Decorator to wrap exceptions with context"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ScreenTranslatorError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap other exceptions
            raise ScreenTranslatorError(
                f"Unexpected error in {func.__name__}: {str(e)}",
                {"function": func.__name__, "original_error": str(e)},
            ) from e

    return wrapper

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional


class AppLogger:
    """Centralized logging system for Screen Translator"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.logger = logging.getLogger("screen_translator")
            self.setup_logging()
            self._initialized = True

    def setup_logging(self, log_level: str = "INFO", log_file: Optional[str] = None):
        """Setup logging configuration"""
        # Clear existing handlers
        self.logger.handlers.clear()

        # Set level
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler if specified
        if log_file:
            try:
                Path(log_file).parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.FileHandler(log_file, encoding="utf-8")
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except (OSError, PermissionError) as e:
                self.logger.warning(f"Could not create log file {log_file}: {e}")

    def log_translation(
        self,
        original: str,
        translated: str,
        source_lang: str,
        target_lang: str,
        duration: float,
        cached: bool = False,
    ):
        """Log translation activity"""
        self.logger.info(
            f"Translation completed | "
            f"Source: {source_lang} | Target: {target_lang} | "
            f"Length: {len(original)}->{len(translated)} | "
            f"Duration: {duration:.2f}s | "
            f"Cached: {cached}"
        )

    def log_screenshot(self, coordinates: tuple, size: tuple, duration: float):
        """Log screenshot capture"""
        self.logger.info(
            f"Screenshot captured | "
            f"Coordinates: {coordinates} | "
            f"Size: {size} | "
            f"Duration: {duration:.2f}s"
        )

    def log_ocr(self, text_length: int, confidence: Optional[float], duration: float):
        """Log OCR processing"""
        confidence_str = f"{confidence:.2f}" if confidence else "N/A"
        self.logger.info(
            f"OCR completed | "
            f"Text length: {text_length} | "
            f"Confidence: {confidence_str} | "
            f"Duration: {duration:.2f}s"
        )

    def log_tts(self, text_length: int, voice_id: str, duration: float):
        """Log TTS activity"""
        self.logger.info(
            f"TTS completed | "
            f"Text length: {text_length} | "
            f"Voice: {voice_id or 'default'} | "
            f"Duration: {duration:.2f}s"
        )

    def log_error(self, operation: str, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Log errors with context"""
        context_str = ""
        if context:
            context_str = " | " + " | ".join(f"{k}: {v}" for k, v in context.items())

        self.logger.error(
            f"Error in {operation} | "
            f"Type: {type(error).__name__} | "
            f"Message: {str(error)}{context_str}"
        )

    def log_config_change(self, key: str, old_value: Any, new_value: Any):
        """Log configuration changes"""
        self.logger.info(
            f"Config changed | " f"Key: {key} | " f"Old: {old_value} | " f"New: {new_value}"
        )

    def log_startup(self, version: str):
        """Log application startup"""
        self.logger.info(f"Screen Translator v{version} starting up")

    def log_shutdown(self):
        """Log application shutdown"""
        self.logger.info("Screen Translator shutting down")

    # Convenience methods
    def debug(self, message: str, **kwargs):
        if kwargs:
            message += " | " + " | ".join(f"{k}: {v}" for k, v in kwargs.items())
        self.logger.debug(message)

    def info(self, message: str, **kwargs):
        if kwargs:
            message += " | " + " | ".join(f"{k}: {v}" for k, v in kwargs.items())
        self.logger.info(message)

    def warning(self, message: str, **kwargs):
        if kwargs:
            message += " | " + " | ".join(f"{k}: {v}" for k, v in kwargs.items())
        self.logger.warning(message)

    def error(self, message: str, **kwargs):
        if kwargs:
            message += " | " + " | ".join(f"{k}: {v}" for k, v in kwargs.items())
        self.logger.error(message)


# Global logger instance
logger = AppLogger()

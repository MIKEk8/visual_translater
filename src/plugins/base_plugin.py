"""
Base plugin classes and interfaces for Screen Translator v2.0 plugin system.
Provides abstract base classes for different types of plugins.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PluginType(Enum):
    """Types of plugins supported by the system."""

    OCR = "ocr"
    TRANSLATION = "translation"
    TTS = "tts"
    UI = "ui"
    FILTER = "filter"


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""

    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    dependencies: Optional[List[str]] = None
    config_schema: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.config_schema is None:
            self.config_schema = {}


class BasePlugin(ABC):
    """Base class for all plugins."""

    def __init__(self):
        self._metadata: Optional[PluginMetadata] = None
        self._config: Dict[str, Any] = {}
        self._enabled: bool = True
        self._initialized: bool = False

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the plugin with configuration."""

    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup resources when plugin is unloaded."""

    def is_available(self) -> bool:
        """Check if plugin dependencies are available."""
        return True

    def get_config_schema(self) -> Dict[str, Any]:
        """Return configuration schema for this plugin."""
        return self.metadata.config_schema or {}

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate plugin configuration."""
        # Basic validation - plugins can override for specific validation
        errors = []
        schema = self.get_config_schema()

        for key, requirements in schema.items():
            if requirements.get("required", False) and key not in config:
                errors.append(f"Required configuration key '{key}' is missing")

        return len(errors) == 0, errors

    @property
    def enabled(self) -> bool:
        """Check if plugin is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable the plugin."""
        self._enabled = True

    def disable(self) -> None:
        """Disable the plugin."""
        self._enabled = False

    @property
    def initialized(self) -> bool:
        """Check if plugin is initialized."""
        return self._initialized


class OCRPlugin(BasePlugin):
    """Base class for OCR plugins."""

    @abstractmethod
    def extract_text(self, image_data: bytes, languages: List[str]) -> Tuple[str, float]:
        """
        Extract text from image data.

        Args:
            image_data: Raw image bytes
            languages: List of language codes to use for OCR

        Returns:
            Tuple of (extracted_text, confidence_score)
        """

    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Return list of supported language codes."""

    def preprocess_image(self, image_data: bytes) -> bytes:
        """Preprocess image before OCR (optional override)."""
        return image_data


class TranslationPlugin(BasePlugin):
    """Base class for translation plugins."""

    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> Tuple[str, float]:
        """
        Translate text from source to target language.

        Args:
            text: Text to translate
            source_lang: Source language code ('auto' for detection)
            target_lang: Target language code

        Returns:
            Tuple of (translated_text, confidence_score)
        """

    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Return list of supported language codes."""

    def detect_language(self, text: str) -> str:
        """Detect language of text (optional override)."""
        return "auto"

    def get_usage_cost(self, text: str) -> float:
        """Calculate cost for translating text (optional override)."""
        return 0.0


class TTSPlugin(BasePlugin):
    """Base class for TTS plugins."""

    @abstractmethod
    def speak(self, text: str, language: str, voice_id: Optional[str] = None) -> bool:
        """
        Speak text using TTS engine.

        Args:
            text: Text to speak
            language: Language code
            voice_id: Optional specific voice ID

        Returns:
            True if successful, False otherwise
        """

    @abstractmethod
    def get_available_voices(self, language: str) -> List[Dict[str, str]]:
        """
        Get available voices for a language.

        Returns:
            List of voice info dicts with keys: id, name, gender, quality
        """

    def set_speech_rate(self, rate: int) -> None:
        """Set speech rate (optional override)."""

    def set_volume(self, volume: float) -> None:
        """Set volume level 0.0-1.0 (optional override)."""


class UIPlugin(BasePlugin):
    """Base class for UI plugins."""

    @abstractmethod
    def create_ui_components(self) -> Dict[str, Any]:
        """Create UI components for this plugin."""

    @abstractmethod
    def register_menu_items(self) -> List[Dict[str, Any]]:
        """Register menu items for this plugin."""

    def on_ui_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle UI events (optional override)."""
        _ = event_type  # Unused parameter - interface requirement


class FilterPlugin(BasePlugin):
    """Base class for text filter plugins."""

    @abstractmethod
    def filter_text(self, text: str, context: Dict[str, Any]) -> str:
        """
        Filter/modify text.

        Args:
            text: Input text
            context: Processing context (source_lang, target_lang, etc.)

        Returns:
            Filtered text
        """

    @abstractmethod
    def get_filter_priority(self) -> int:
        """
        Return filter priority (lower numbers run first).

        Returns:
            Priority number (0-100)
        """


class PluginError(Exception):
    """Base exception for plugin-related errors."""


class PluginInitializationError(PluginError):
    """Raised when plugin initialization fails."""


class PluginDependencyError(PluginError):
    """Raised when plugin dependencies are not met."""


class PluginConfigurationError(PluginError):
    """Raised when plugin configuration is invalid."""

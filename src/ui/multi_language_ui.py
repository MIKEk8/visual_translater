"""
Multi-language UI support for Screen Translator v2.0.
Provides internationalization (i18n) and localization (l10n) capabilities.
"""

import json
import locale
import os
from dataclasses import dataclass
from enum import Enum
from tkinter import TclError
from typing import Any, Dict, List, Optional

from src.utils.logger import logger


class SupportedLanguage(Enum):
    """Supported UI languages."""

    ENGLISH = "en"
    RUSSIAN = "ru"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    JAPANESE = "ja"
    CHINESE_SIMPLIFIED = "zh-CN"
    CHINESE_TRADITIONAL = "zh-TW"
    KOREAN = "ko"
    PORTUGUESE = "pt"
    ITALIAN = "it"
    DUTCH = "nl"
    POLISH = "pl"
    TURKISH = "tr"
    ARABIC = "ar"


@dataclass
class LanguageMetadata:
    """Metadata for a supported language."""

    code: str
    name: str
    native_name: str
    rtl: bool = False  # Right-to-left text direction
    completion: float = 1.0  # Translation completion percentage
    contributors: Optional[List[str]] = None


class LanguageManager:
    """Manages UI language and translations."""

    def __init__(self, languages_dir: Optional[str] = None):
        """
        Initialize language manager.

        Args:
            languages_dir: Directory containing language files
        """
        self.languages_dir = languages_dir or os.path.join(
            os.path.dirname(__file__), "..", "..", "languages"
        )

        self.current_language = SupportedLanguage.ENGLISH
        self.translations: Dict[str, Dict[str, str]] = {}
        self.language_metadata: Dict[str, LanguageMetadata] = {}

        # Initialize language metadata
        self._initialize_language_metadata()

        # Load available translations
        self._load_available_translations()

        # Set system language as default if available
        self._detect_system_language()

        logger.debug(f"Language manager initialized with {len(self.translations)} languages")

    def _initialize_language_metadata(self) -> None:
        """Initialize metadata for all supported languages."""
        metadata = {
            SupportedLanguage.ENGLISH: LanguageMetadata(
                code="en",
                name="English",
                native_name="English",
                completion=1.0,
                contributors=["Screen Translator Team"],
            ),
            SupportedLanguage.RUSSIAN: LanguageMetadata(
                code="ru",
                name="Russian",
                native_name="Русский",
                completion=1.0,
                contributors=["Screen Translator Team"],
            ),
            SupportedLanguage.SPANISH: LanguageMetadata(
                code="es",
                name="Spanish",
                native_name="Español",
                completion=0.95,
                contributors=["Community"],
            ),
            SupportedLanguage.FRENCH: LanguageMetadata(
                code="fr",
                name="French",
                native_name="Français",
                completion=0.90,
                contributors=["Community"],
            ),
            SupportedLanguage.GERMAN: LanguageMetadata(
                code="de",
                name="German",
                native_name="Deutsch",
                completion=0.88,
                contributors=["Community"],
            ),
            SupportedLanguage.JAPANESE: LanguageMetadata(
                code="ja",
                name="Japanese",
                native_name="日本語",
                completion=0.85,
                contributors=["Community"],
            ),
            SupportedLanguage.CHINESE_SIMPLIFIED: LanguageMetadata(
                code="zh-CN",
                name="Chinese (Simplified)",
                native_name="简体中文",
                completion=0.80,
                contributors=["Community"],
            ),
            SupportedLanguage.CHINESE_TRADITIONAL: LanguageMetadata(
                code="zh-TW",
                name="Chinese (Traditional)",
                native_name="繁體中文",
                completion=0.75,
                contributors=["Community"],
            ),
            SupportedLanguage.KOREAN: LanguageMetadata(
                code="ko",
                name="Korean",
                native_name="한국어",
                completion=0.70,
                contributors=["Community"],
            ),
            SupportedLanguage.PORTUGUESE: LanguageMetadata(
                code="pt",
                name="Portuguese",
                native_name="Português",
                completion=0.85,
                contributors=["Community"],
            ),
            SupportedLanguage.ITALIAN: LanguageMetadata(
                code="it",
                name="Italian",
                native_name="Italiano",
                completion=0.82,
                contributors=["Community"],
            ),
            SupportedLanguage.DUTCH: LanguageMetadata(
                code="nl",
                name="Dutch",
                native_name="Nederlands",
                completion=0.78,
                contributors=["Community"],
            ),
            SupportedLanguage.POLISH: LanguageMetadata(
                code="pl",
                name="Polish",
                native_name="Polski",
                completion=0.75,
                contributors=["Community"],
            ),
            SupportedLanguage.TURKISH: LanguageMetadata(
                code="tr",
                name="Turkish",
                native_name="Türkçe",
                completion=0.72,
                contributors=["Community"],
            ),
            SupportedLanguage.ARABIC: LanguageMetadata(
                code="ar",
                name="Arabic",
                native_name="العربية",
                rtl=True,
                completion=0.65,
                contributors=["Community"],
            ),
        }

        self.language_metadata = {lang.value: meta for lang, meta in metadata.items()}

    def _load_available_translations(self) -> None:
        """Load translation files from languages directory."""
        if not os.path.exists(self.languages_dir):
            # Create directory and base English translations
            os.makedirs(self.languages_dir, exist_ok=True)
            self._create_base_translations()

        # Load translation files
        for language in SupportedLanguage:
            lang_code = language.value
            lang_file = os.path.join(self.languages_dir, f"{lang_code}.json")

            if os.path.exists(lang_file):
                try:
                    with open(lang_file, "r", encoding="utf-8") as f:
                        self.translations[lang_code] = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to load language file {lang_file}: {e}")
            else:
                # Create missing language file with English base
                if lang_code == "en":
                    self.translations[lang_code] = self._get_base_english_translations()
                    self._save_language_file(lang_code, self.translations[lang_code])

    def _detect_system_language(self) -> None:
        """Detect and set system language if supported."""
        try:
            # Get system locale
            system_locale = locale.getdefaultlocale()[0]
            if system_locale:
                # Extract language code (e.g., 'en_US' -> 'en')
                lang_code = system_locale.split("_")[0]

                # Check if we support this language
                for supported_lang in SupportedLanguage:
                    if supported_lang.value.startswith(lang_code):
                        self.current_language = supported_lang
                        logger.info(f"System language detected: {supported_lang.value}")
                        return

        except Exception as e:
            logger.debug(f"Could not detect system language: {e}")

        # Default to English if detection fails
        self.current_language = SupportedLanguage.ENGLISH

    def get_available_languages(self) -> List[LanguageMetadata]:
        """Get list of available languages with metadata."""
        return [
            self.language_metadata[lang.value]
            for lang in SupportedLanguage
            if lang.value in self.translations
        ]

    def get_current_language(self) -> SupportedLanguage:
        """Get current UI language."""
        return self.current_language

    def set_language(self, language: SupportedLanguage) -> bool:
        """
        Set UI language.

        Args:
            language: Language to set

        Returns:
            True if language was set successfully
        """
        if language.value not in self.translations:
            logger.warning(f"Language {language.value} not available")
            return False

        self.current_language = language
        logger.info(f"UI language changed to: {language.value}")
        return True

    def get_text(self, key: str, **kwargs) -> str:
        """
        Get translated text for a key.

        Args:
            key: Translation key (dot notation supported)
            **kwargs: Variables for string formatting

        Returns:
            Translated text or key if not found
        """
        lang_code = self.current_language.value
        translations = self.translations.get(lang_code, {})

        # Support dot notation (e.g., "window.title")
        keys = key.split(".")
        text = translations

        for k in keys:
            if isinstance(text, dict) and k in text:
                text = text[k]
            else:
                # Fallback to English if key not found
                if lang_code != "en":
                    return self._get_fallback_text(key, **kwargs)
                else:
                    logger.warning(f"Translation key not found: {key}")
                    return key

        # Format string with provided variables
        if isinstance(text, str) and kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError) as e:
                logger.warning(f"String formatting failed for key '{key}': {e}")
                return text

        return text if isinstance(text, str) else key

    def _get_fallback_text(self, key: str, **kwargs) -> str:
        """Get fallback text from English translations."""
        english_translations = self.translations.get("en", {})
        keys = key.split(".")
        text = english_translations

        for k in keys:
            if isinstance(text, dict) and k in text:
                text = text[k]
            else:
                return key

        if isinstance(text, str) and kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError):
                return text

        return text if isinstance(text, str) else key

    def is_rtl_language(self, language: Optional[SupportedLanguage] = None) -> bool:
        """
        Check if language uses right-to-left text direction.

        Args:
            language: Language to check (current if None)

        Returns:
            True if RTL language
        """
        lang = language or self.current_language
        metadata = self.language_metadata.get(lang.value)
        return metadata.rtl if metadata else False

    def get_completion_percentage(self, language: SupportedLanguage) -> float:
        """
        Get translation completion percentage for a language.

        Args:
            language: Language to check

        Returns:
            Completion percentage (0.0 to 1.0)
        """
        metadata = self.language_metadata.get(language.value)
        return metadata.completion if metadata else 0.0

    def _create_base_translations(self) -> None:
        """Create base English translation file."""
        english_translations = self._get_base_english_translations()
        self._save_language_file("en", english_translations)

    def _get_base_english_translations(self) -> Dict[str, Any]:
        """Get base English translations."""
        return {
            "app": {
                "name": "Screen Translator",
                "version": "v2.0",
                "description": "Universal screen text translator",
            },
            "window": {
                "main_title": "Screen Translator",
                "settings_title": "Settings - Screen Translator",
                "history_title": "Translation History - Screen Translator",
                "about_title": "About - Screen Translator",
            },
            "menu": {
                "file": "File",
                "edit": "Edit",
                "view": "View",
                "tools": "Tools",
                "help": "Help",
                "settings": "Settings",
                "history": "History",
                "exit": "Exit",
                "about": "About",
            },
            "buttons": {
                "ok": "OK",
                "cancel": "Cancel",
                "apply": "Apply",
                "close": "Close",
                "save": "Save",
                "load": "Load",
                "reset": "Reset",
                "browse": "Browse...",
                "test": "Test",
                "start": "Start",
                "stop": "Stop",
                "pause": "Pause",
                "resume": "Resume",
            },
            "settings": {
                "general": "General",
                "hotkeys": "Hotkeys",
                "ocr": "OCR",
                "translation": "Translation",
                "tts": "Text-to-Speech",
                "overlay": "Overlay",
                "advanced": "Advanced",
                "language": "Language",
                "ui_language": "Interface Language",
                "auto_detect": "Auto-detect",
                "source_language": "Source Language",
                "target_language": "Target Language",
                "translation_service": "Translation Service",
                "ocr_engine": "OCR Engine",
                "tts_voice": "TTS Voice",
                "hotkey_translate": "Translate",
                "hotkey_ocr": "OCR Only",
                "hotkey_tts": "Text-to-Speech",
                "hotkey_history": "Show History",
                "auto_copy": "Auto-copy translations",
                "show_notifications": "Show notifications",
                "auto_save_history": "Auto-save history",
                "overlay_enabled": "Enable overlay",
                "overlay_opacity": "Overlay opacity",
                "overlay_position": "Overlay position",
                "always_on_top": "Always on top",
            },
            "overlay": {
                "title": "Translation",
                "pin": "Pin",
                "unpin": "Unpin",
                "close": "Close",
                "settings": "Settings",
                "original": "Original",
                "translated": "Translated",
                "confidence": "Confidence: {confidence:.1%}",
                "time": "Time: {time}",
                "cached": "(cached)",
                "copy_translation": "Copy Translation",
                "copy_original": "Copy Original",
            },
            "history": {
                "title": "Translation History",
                "original_text": "Original Text",
                "translated_text": "Translated Text",
                "language_pair": "Languages",
                "timestamp": "Time",
                "confidence": "Confidence",
                "source": "Source",
                "clear_all": "Clear All",
                "export": "Export",
                "import": "Import",
                "search": "Search...",
                "filter_by_language": "Filter by language",
                "filter_by_date": "Filter by date",
                "entries_count": "{count} entries",
                "no_entries": "No translation history",
            },
            "tray": {
                "show": "Show Screen Translator",
                "translate": "Translate",
                "settings": "Settings",
                "history": "History",
                "exit": "Exit",
            },
            "notifications": {
                "translation_copied": "Translation copied to clipboard",
                "ocr_completed": "Text recognition completed",
                "translation_failed": "Translation failed",
                "ocr_failed": "Text recognition failed",
                "settings_saved": "Settings saved",
                "hotkey_registered": "Hotkey registered: {hotkey}",
                "hotkey_failed": "Failed to register hotkey: {hotkey}",
            },
            "messages": {
                "no_text_found": "No text found in selected area",
                "translation_in_progress": "Translation in progress...",
                "ocr_in_progress": "Recognizing text...",
                "connecting_service": "Connecting to translation service...",
                "service_unavailable": "Translation service unavailable",
                "invalid_language": "Invalid language selection",
                "file_not_found": "File not found",
                "permission_denied": "Permission denied",
                "unknown_error": "An unknown error occurred",
            },
            "dialogs": {
                "confirm_exit": "Are you sure you want to exit?",
                "confirm_clear_history": "Are you sure you want to clear all history?",
                "confirm_reset_settings": "Are you sure you want to reset all settings?",
                "save_changes": "Do you want to save your changes?",
                "restart_required": "Restart required for changes to take effect",
            },
            "status": {
                "ready": "Ready",
                "translating": "Translating...",
                "recognizing": "Recognizing text...",
                "completed": "Completed",
                "failed": "Failed",
                "offline": "Offline",
                "connecting": "Connecting...",
            },
            "errors": {
                "translation_failed": "Translation failed: {error}",
                "ocr_failed": "Text recognition failed: {error}",
                "tts_failed": "Text-to-speech failed: {error}",
                "hotkey_conflict": "Hotkey conflict: {hotkey}",
                "file_error": "File error: {error}",
                "network_error": "Network error: {error}",
                "service_error": "Service error: {error}",
                "config_error": "Configuration error: {error}",
            },
        }

    def _save_language_file(self, lang_code: str, translations: Dict[str, Any]) -> None:
        """Save translations to language file."""
        lang_file = os.path.join(self.languages_dir, f"{lang_code}.json")
        try:
            with open(lang_file, "w", encoding="utf-8") as f:
                json.dump(translations, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved language file: {lang_file}")
        except Exception as e:
            logger.error(f"Failed to save language file {lang_file}: {e}")


class UILocalizer:
    """Helper class for UI component localization."""

    def __init__(self, language_manager: LanguageManager):
        """
        Initialize UI localizer.

        Args:
            language_manager: Language manager instance
        """
        self.language_manager = language_manager

    def _(self, key: str, **kwargs) -> str:
        """
        Shorthand for getting translated text.

        Args:
            key: Translation key
            **kwargs: Variables for string formatting

        Returns:
            Translated text
        """
        return self.language_manager.get_text(key, **kwargs)

    def localize_widget(self, widget, text_key: str, **kwargs) -> None:
        """
        Localize a tkinter widget's text.

        Args:
            widget: Tkinter widget to localize
            text_key: Translation key for the text
            **kwargs: Variables for string formatting
        """
        try:
            translated_text = self._(text_key, **kwargs)

            # Handle different widget types
            if hasattr(widget, "config"):
                if hasattr(widget, "cget"):
                    # Try different text attributes
                    for attr in ["text", "title"]:
                        try:
                            widget.cget(attr)
                            widget.config(**{attr: translated_text})
                            break
                        except (TclError, AttributeError):
                            continue
        except Exception as e:
            logger.warning(f"Failed to localize widget: {e}")

    def setup_rtl_support(self, widget) -> None:
        """
        Set up right-to-left text support for a widget.

        Args:
            widget: Tkinter widget to configure
        """
        if self.language_manager.is_rtl_language():
            try:
                # Configure RTL text alignment
                if hasattr(widget, "config"):
                    widget.config(justify="right")

                # Additional RTL configurations can be added here
            except Exception as e:
                logger.warning(f"Failed to setup RTL support: {e}")

    def get_language_display_name(self, language: SupportedLanguage) -> str:
        """
        Get display name for a language.

        Args:
            language: Language to get name for

        Returns:
            Localized language display name
        """
        metadata = self.language_manager.language_metadata.get(language.value)
        if not metadata:
            return language.value

        # Show native name with completion percentage if not 100%
        display_name = metadata.native_name
        if metadata.completion < 1.0:
            percentage = int(metadata.completion * 100)
            display_name += f" ({percentage}%)"

        return display_name


# Global language manager instance
_language_manager: Optional[LanguageManager] = None
_ui_localizer: Optional[UILocalizer] = None


def get_language_manager() -> LanguageManager:
    """Get global language manager instance."""
    global _language_manager
    if _language_manager is None:
        _language_manager = LanguageManager()
    return _language_manager


def get_ui_localizer() -> UILocalizer:
    """Get global UI localizer instance."""
    global _ui_localizer
    if _ui_localizer is None:
        _ui_localizer = UILocalizer(get_language_manager())
    return _ui_localizer


def _(key: str, **kwargs) -> str:
    """Global shorthand for getting translated text."""
    return get_ui_localizer()._(key, **kwargs)

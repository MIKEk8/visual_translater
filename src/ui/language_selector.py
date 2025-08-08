"""
Language selector component for Screen Translator v2.0.
Provides UI for selecting interface language with live preview.
"""

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Callable, List, Optional

from src.ui.multi_language_ui import SupportedLanguage, get_language_manager, get_ui_localizer
from src.utils.logger import logger


@dataclass
class LanguageChangeEvent:
    """Event data for language change."""

    old_language: SupportedLanguage
    new_language: SupportedLanguage
    source: str = "user"  # "user", "system", "config"


class LanguageSelector:
    """Language selector widget with live preview and RTL support."""

    def __init__(
        self,
        parent: tk.Widget,
        on_language_changed: Optional[Callable[[LanguageChangeEvent], None]] = None,
    ):
        """
        Initialize language selector.

        Args:
            parent: Parent widget
            on_language_changed: Callback for language change events
        """
        self.parent = parent
        self.on_language_changed = on_language_changed

        self.language_manager = get_language_manager()
        self.localizer = get_ui_localizer()

        # UI components
        self.frame: Optional[tk.Frame] = None
        self.label: Optional[tk.Label] = None
        self.combobox: Optional[ttk.Combobox] = None
        self.preview_label: Optional[tk.Label] = None
        self.completion_label: Optional[tk.Label] = None

        # State
        self.available_languages: List[SupportedLanguage] = []
        self.language_display_names: List[str] = []

        # Create UI
        self._create_ui()
        self._load_languages()
        self._update_current_selection()

        logger.debug("Language selector initialized")

    def _create_ui(self) -> None:
        """Create language selector UI components."""
        # Main frame
        self.frame = tk.Frame(self.parent)

        # Language label
        self.label = tk.Label(
            self.frame, text=self.localizer._("settings.ui_language"), font=("Arial", 10)
        )
        self.label.grid(row=0, column=0, sticky="w", padx=(0, 10))

        # Language combobox
        self.combobox = ttk.Combobox(self.frame, state="readonly", width=25, font=("Arial", 10))
        self.combobox.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        self.combobox.bind("<<ComboboxSelected>>", self._on_language_selected)

        # Preview label (shows sample text in selected language)
        self.preview_label = tk.Label(self.frame, text="", font=("Arial", 9), fg="#666666")
        self.preview_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(5, 0))

        # Completion percentage label
        self.completion_label = tk.Label(self.frame, text="", font=("Arial", 8), fg="#888888")
        self.completion_label.grid(row=2, column=0, columnspan=3, sticky="w", pady=(2, 0))

        # Configure grid weights
        self.frame.grid_columnconfigure(1, weight=1)

    def _load_languages(self) -> None:
        """Load available languages into combobox."""
        self.available_languages = []
        self.language_display_names = []

        # Get available languages from manager
        available_metadata = self.language_manager.get_available_languages()

        for metadata in available_metadata:
            # Find corresponding enum
            for lang in SupportedLanguage:
                if lang.value == metadata.code:
                    self.available_languages.append(lang)

                    # Create display name
                    display_name = self.localizer.get_language_display_name(lang)
                    self.language_display_names.append(display_name)
                    break

        # Update combobox values
        self.combobox["values"] = self.language_display_names

        logger.debug(f"Loaded {len(self.available_languages)} languages")

    def _update_current_selection(self) -> None:
        """Update combobox to show current language."""
        current_lang = self.language_manager.get_current_language()

        try:
            index = self.available_languages.index(current_lang)
            self.combobox.current(index)
            self._update_preview(current_lang)
        except ValueError:
            logger.warning(f"Current language {current_lang.value} not in available languages")

    def _on_language_selected(self, event) -> None:
        """Handle language selection from combobox."""
        selection_index = self.combobox.current()
        if 0 <= selection_index < len(self.available_languages):
            old_language = self.language_manager.get_current_language()
            new_language = self.available_languages[selection_index]

            if old_language != new_language:
                # Update language manager
                if self.language_manager.set_language(new_language):
                    # Update preview
                    self._update_preview(new_language)

                    # Notify callback
                    if self.on_language_changed:
                        event_data = LanguageChangeEvent(
                            old_language=old_language, new_language=new_language, source="user"
                        )
                        self.on_language_changed(event_data)

                    logger.info(
                        f"Language changed from {old_language.value} to {new_language.value}"
                    )
                else:
                    # Revert selection if change failed
                    self._update_current_selection()

    def _update_preview(self, language: SupportedLanguage) -> None:
        """
        Update preview text for selected language.

        Args:
            language: Language to preview
        """
        try:
            # Temporarily switch to selected language for preview
            original_language = self.language_manager.get_current_language()

            if original_language != language:
                self.language_manager.set_language(language)

            # Get sample text in selected language
            sample_text = self.language_manager.get_text("app.description")

            # Restore original language if different
            if original_language != language:
                self.language_manager.set_language(original_language)

            # Update preview label
            self.preview_label.config(text=f'Preview: "{sample_text}"')

            # Update completion percentage
            completion = self.language_manager.get_completion_percentage(language)
            if completion < 1.0:
                completion_text = f"Translation completion: {completion:.0%}"
                self.completion_label.config(text=completion_text)
            else:
                self.completion_label.config(text="")

            # Setup RTL support if needed
            if self.language_manager.is_rtl_language(language):
                self.preview_label.config(justify="right")
            else:
                self.preview_label.config(justify="left")

        except Exception as e:
            logger.error(f"Failed to update language preview: {e}")
            self.preview_label.config(text="")
            self.completion_label.config(text="")

    def refresh_ui_text(self) -> None:
        """Refresh UI text after language change."""
        try:
            # Update label text
            self.label.config(text=self.localizer._("settings.ui_language"))

            # Reload language display names
            self._load_languages()

            # Update current selection
            self._update_current_selection()

        except Exception as e:
            logger.error(f"Failed to refresh language selector UI: {e}")

    def set_language(self, language: SupportedLanguage) -> bool:
        """
        Set language programmatically.

        Args:
            language: Language to set

        Returns:
            True if language was set successfully
        """
        if language in self.available_languages:
            old_language = self.language_manager.get_current_language()

            if self.language_manager.set_language(language):
                self._update_current_selection()

                # Notify callback
                if self.on_language_changed:
                    event_data = LanguageChangeEvent(
                        old_language=old_language, new_language=language, source="system"
                    )
                    self.on_language_changed(event_data)

                return True

        return False

    def get_current_language(self) -> SupportedLanguage:
        """Get currently selected language."""
        return self.language_manager.get_current_language()

    def pack(self, **kwargs) -> None:
        """Pack the language selector frame."""
        if self.frame:
            self.frame.pack(**kwargs)

    def grid(self, **kwargs) -> None:
        """Grid the language selector frame."""
        if self.frame:
            self.frame.grid(**kwargs)

    def place(self, **kwargs) -> None:
        """Place the language selector frame."""
        if self.frame:
            self.frame.place(**kwargs)


class LanguageSettingsPanel:
    """Complete language settings panel with additional options."""

    def __init__(self, parent: tk.Widget, config_manager=None):
        """
        Initialize language settings panel.

        Args:
            parent: Parent widget
            config_manager: Configuration manager for saving settings
        """
        self.parent = parent
        self.config_manager = config_manager

        self.language_manager = get_language_manager()
        self.localizer = get_ui_localizer()

        # UI components
        self.frame: Optional[tk.LabelFrame] = None
        self.language_selector: Optional[LanguageSelector] = None
        self.auto_detect_var: Optional[tk.BooleanVar] = None
        self.auto_detect_check: Optional[tk.Checkbutton] = None
        self.restart_label: Optional[tk.Label] = None

        # State
        self.language_changed = False

        # Create UI
        self._create_ui()

        logger.debug("Language settings panel initialized")

    def _create_ui(self) -> None:
        """Create language settings panel UI."""
        # Main frame
        self.frame = tk.LabelFrame(
            self.parent,
            text=self.localizer._("settings.language"),
            font=("Arial", 10, "bold"),
            padx=10,
            pady=10,
        )

        # Language selector
        self.language_selector = LanguageSelector(
            self.frame, on_language_changed=self._on_language_changed
        )
        self.language_selector.pack(fill="x", pady=(0, 10))

        # Auto-detect language option
        self.auto_detect_var = tk.BooleanVar(value=False)
        self.auto_detect_check = tk.Checkbutton(
            self.frame,
            text=self.localizer._("settings.auto_detect"),
            variable=self.auto_detect_var,
            command=self._on_auto_detect_changed,
        )
        self.auto_detect_check.pack(anchor="w", pady=(0, 10))

        # Restart required label (initially hidden)
        self.restart_label = tk.Label(
            self.frame,
            text=self.localizer._("dialogs.restart_required"),
            fg="#ff6600",
            font=("Arial", 9),
        )

    def _on_language_changed(self, event: LanguageChangeEvent) -> None:
        """Handle language change event."""
        self.language_changed = True

        # Show restart required label
        if not self.restart_label.winfo_viewable():
            self.restart_label.pack(anchor="w", pady=(10, 0))

        # Save to config if manager available
        if self.config_manager:
            try:
                config = self.config_manager.get_config()
                config.ui_language = event.new_language.value
                self.config_manager.save_config(config)
            except Exception as e:
                logger.error(f"Failed to save language setting: {e}")

        logger.info(
            f"Language settings changed: {event.old_language.value} → {event.new_language.value}"
        )

    def _on_auto_detect_changed(self) -> None:
        """Handle auto-detect language setting change."""
        auto_detect = self.auto_detect_var.get()

        if auto_detect:
            # Detect and set system language
            try:
                import locale

                system_locale = locale.getdefaultlocale()[0]
                if system_locale:
                    lang_code = system_locale.split("_")[0]

                    # Find matching supported language
                    for lang in SupportedLanguage:
                        if lang.value.startswith(lang_code):
                            self.language_selector.set_language(lang)
                            break
            except Exception as e:
                logger.debug(f"Auto-detect language failed: {e}")

        # Save setting to config
        if self.config_manager:
            try:
                config = self.config_manager.get_config()
                config.auto_detect_ui_language = auto_detect
                self.config_manager.save_config(config)
            except Exception as e:
                logger.error(f"Failed to save auto-detect setting: {e}")

    def refresh_ui_text(self) -> None:
        """Refresh UI text after language change."""
        try:
            # Update frame title
            self.frame.config(text=self.localizer._("settings.language"))

            # Update auto-detect checkbox
            self.auto_detect_check.config(text=self.localizer._("settings.auto_detect"))

            # Update restart label
            self.restart_label.config(text=self.localizer._("dialogs.restart_required"))

            # Refresh language selector
            if self.language_selector:
                self.language_selector.refresh_ui_text()

        except Exception as e:
            logger.error(f"Failed to refresh language panel UI: {e}")

    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved language changes."""
        return self.language_changed

    def apply_changes(self) -> bool:
        """Apply language changes (restart required)."""
        if self.language_changed:
            # Changes require restart to take full effect
            return False
        return True

    def pack(self, **kwargs) -> None:
        """Pack the language settings panel."""
        if self.frame:
            self.frame.pack(**kwargs)

    def grid(self, **kwargs) -> None:
        """Grid the language settings panel."""
        if self.frame:
            self.frame.grid(**kwargs)

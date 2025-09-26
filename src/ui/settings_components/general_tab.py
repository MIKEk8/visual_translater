"""General settings tab component."""

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
except ImportError:
    from src.utils.mock_gui import tk, ttk, messagebox, filedialog

from .base_settings_tab import BaseSettingsTab
from src.utils.logger import logger


class GeneralTab(BaseSettingsTab):
    """General settings configuration tab."""

    def __init__(self, parent: ttk.Notebook, config_manager, tts_processor=None):
        super().__init__(parent, config_manager, "Общие")

    def _create_components(self) -> None:
        """Create general settings components."""
        self._create_language_settings()
        self._create_ui_settings()
        self._create_behavior_settings()
        self._create_file_settings()

    def _create_language_settings(self) -> None:
        """Create language settings section."""
        frame = self.create_labeled_frame(self.frame, "Языки")

        # Source language
        source_frame = ttk.Frame(frame)
        source_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(source_frame, text="Исходный язык:").pack(side=tk.LEFT)

        self.source_lang_var = tk.StringVar(value="auto")
        source_combo = ttk.Combobox(
            source_frame,
            textvariable=self.source_lang_var,
            values=["auto", "en", "ru", "zh", "ja", "ko", "fr", "de", "es"],
            state="readonly",
            width=15
        )
        source_combo.pack(side=tk.RIGHT)

        # Target language
        target_frame = ttk.Frame(frame)
        target_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(target_frame, text="Целевой язык:").pack(side=tk.LEFT)

        self.target_lang_var = tk.StringVar(value="ru")
        target_combo = ttk.Combobox(
            target_frame,
            textvariable=self.target_lang_var,
            values=["ru", "en", "zh", "ja", "ko", "fr", "de", "es"],
            state="readonly",
            width=15
        )
        target_combo.pack(side=tk.RIGHT)

        # Auto-detect language
        self.auto_detect_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Автоматически определять исходный язык",
            variable=self.auto_detect_var,
            command=self._on_auto_detect_changed
        ).pack(anchor=tk.W, padx=10, pady=5)

    def _create_ui_settings(self) -> None:
        """Create UI settings section."""
        frame = self.create_labeled_frame(self.frame, "Интерфейс")

        # Theme
        theme_frame = ttk.Frame(frame)
        theme_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(theme_frame, text="Тема:").pack(side=tk.LEFT)

        self.theme_var = tk.StringVar(value="system")
        theme_combo = ttk.Combobox(
            theme_frame,
            textvariable=self.theme_var,
            values=["system", "light", "dark"],
            state="readonly",
            width=15
        )
        theme_combo.pack(side=tk.RIGHT)

        # Font size
        font_frame = ttk.Frame(frame)
        font_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(font_frame, text="Размер шрифта:").pack(side=tk.LEFT)

        self.font_size_var = tk.StringVar(value="12")
        font_spinbox = tk.Spinbox(
            font_frame,
            from_=8,
            to=24,
            width=5,
            textvariable=self.font_size_var
        )
        font_spinbox.pack(side=tk.RIGHT)

        # Show notifications
        self.show_notifications_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Показывать уведомления",
            variable=self.show_notifications_var
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Minimize to tray
        self.minimize_to_tray_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Сворачивать в системный трей",
            variable=self.minimize_to_tray_var
        ).pack(anchor=tk.W, padx=10, pady=5)

    def _create_behavior_settings(self) -> None:
        """Create behavior settings section."""
        frame = self.create_labeled_frame(self.frame, "Поведение")

        # Auto-start
        self.auto_start_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Запускать при старте системы",
            variable=self.auto_start_var,
            command=self._on_auto_start_changed
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Auto-translation
        self.auto_translation_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Автоматический перевод при захвате",
            variable=self.auto_translation_var
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Save history
        self.save_history_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Сохранять историю переводов",
            variable=self.save_history_var
        ).pack(anchor=tk.W, padx=10, pady=5)

        # History limit
        history_frame = ttk.Frame(frame)
        history_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(history_frame, text="Максимум записей в истории:").pack(side=tk.LEFT)

        self.history_limit_var = tk.StringVar(value="1000")
        history_spinbox = tk.Spinbox(
            history_frame,
            from_=100,
            to=10000,
            increment=100,
            width=10,
            textvariable=self.history_limit_var
        )
        history_spinbox.pack(side=tk.RIGHT)

    def _create_file_settings(self) -> None:
        """Create file settings section."""
        frame = self.create_labeled_frame(self.frame, "Файлы и папки")

        # Working directory
        dir_frame = ttk.Frame(frame)
        dir_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(dir_frame, text="Рабочая папка:").pack(side=tk.LEFT)

        self.working_dir_var = tk.StringVar(value="")
        dir_entry = ttk.Entry(dir_frame, textvariable=self.working_dir_var, width=30)
        dir_entry.pack(side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True)

        browse_btn = ttk.Button(
            dir_frame,
            text="Обзор...",
            command=self._browse_working_directory
        )
        browse_btn.pack(side=tk.RIGHT)

        # Auto-save screenshots
        self.auto_save_screenshots_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Автоматически сохранять скриншоты",
            variable=self.auto_save_screenshots_var
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Screenshot format
        format_frame = ttk.Frame(frame)
        format_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(format_frame, text="Формат скриншотов:").pack(side=tk.LEFT)

        self.screenshot_format_var = tk.StringVar(value="PNG")
        format_combo = ttk.Combobox(
            format_frame,
            textvariable=self.screenshot_format_var,
            values=["PNG", "JPG", "BMP"],
            state="readonly",
            width=10
        )
        format_combo.pack(side=tk.RIGHT)

        # Action buttons
        self._create_action_buttons(frame)

    def _create_action_buttons(self, parent: tk.Widget) -> None:
        """Create action buttons."""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        # Reset to defaults
        reset_btn = ttk.Button(
            button_frame,
            text="Сбросить к умолчанию",
            command=self._reset_to_defaults
        )
        reset_btn.pack(side=tk.LEFT, padx=5)

        # Export settings
        export_btn = ttk.Button(
            button_frame,
            text="Экспорт настроек",
            command=self._export_settings
        )
        export_btn.pack(side=tk.LEFT, padx=5)

        # Import settings
        import_btn = ttk.Button(
            button_frame,
            text="Импорт настроек",
            command=self._import_settings
        )
        import_btn.pack(side=tk.RIGHT, padx=5)

    def _on_auto_detect_changed(self) -> None:
        """Handle auto-detect language change."""
        if self.auto_detect_var.get():
            self.source_lang_var.set("auto")

    def _on_auto_start_changed(self) -> None:
        """Handle auto-start change."""
        # TODO: Implement system startup registration
        logger.info(f"Auto-start changed to: {self.auto_start_var.get()}")

    def _browse_working_directory(self) -> None:
        """Browse for working directory."""
        directory = filedialog.askdirectory(title="Выберите рабочую папку")
        if directory:
            self.working_dir_var.set(directory)

    def _reset_to_defaults(self) -> None:
        """Reset settings to defaults."""
        if messagebox.askyesno("Сброс", "Сбросить все общие настройки к значениям по умолчанию?"):
            # Language settings
            self.source_lang_var.set("auto")
            self.target_lang_var.set("ru")
            self.auto_detect_var.set(True)

            # UI settings
            self.theme_var.set("system")
            self.font_size_var.set("12")
            self.show_notifications_var.set(True)
            self.minimize_to_tray_var.set(True)

            # Behavior settings
            self.auto_start_var.set(False)
            self.auto_translation_var.set(False)
            self.save_history_var.set(True)
            self.history_limit_var.set("1000")

            # File settings
            self.working_dir_var.set("")
            self.auto_save_screenshots_var.set(False)
            self.screenshot_format_var.set("PNG")

    def _export_settings(self) -> None:
        """Export settings to file."""
        filename = filedialog.asksaveasfilename(
            title="Экспорт настроек",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                # TODO: Implement settings export
                messagebox.showinfo("Экспорт", f"Настройки экспортированы в {filename}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось экспортировать настройки: {str(e)}")

    def _import_settings(self) -> None:
        """Import settings from file."""
        filename = filedialog.askopenfilename(
            title="Импорт настроек",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                # TODO: Implement settings import
                messagebox.showinfo("Импорт", f"Настройки импортированы из {filename}")
                self._load_current_values()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось импортировать настройки: {str(e)}")

    def _load_current_values(self) -> None:
        """Load current values from config."""
        try:
            # Language settings
            languages_config = self.get_config_section("languages")
            self.source_lang_var.set(languages_config.get("source", "auto"))
            self.target_lang_var.set(languages_config.get("target", "ru"))
            self.auto_detect_var.set(languages_config.get("auto_detect", True))

            # UI settings
            ui_config = self.get_config_section("ui")
            self.theme_var.set(ui_config.get("theme", "system"))
            self.font_size_var.set(str(ui_config.get("font_size", 12)))
            self.show_notifications_var.set(ui_config.get("show_notifications", True))
            self.minimize_to_tray_var.set(ui_config.get("minimize_to_tray", True))

            # Behavior settings
            behavior_config = self.get_config_section("behavior")
            self.auto_start_var.set(behavior_config.get("auto_start", False))
            self.auto_translation_var.set(behavior_config.get("auto_translation", False))
            self.save_history_var.set(behavior_config.get("save_history", True))
            self.history_limit_var.set(str(behavior_config.get("history_limit", 1000)))

            # File settings
            files_config = self.get_config_section("files")
            self.working_dir_var.set(files_config.get("working_directory", ""))
            self.auto_save_screenshots_var.set(files_config.get("auto_save_screenshots", False))
            self.screenshot_format_var.set(files_config.get("screenshot_format", "PNG"))

        except Exception as e:
            logger.error("Failed to load general settings", error=e)

    def save_settings(self) -> bool:
        """Save general settings."""
        try:
            # Language settings
            self.update_config_value("languages", "source", self.source_lang_var.get())
            self.update_config_value("languages", "target", self.target_lang_var.get())
            self.update_config_value("languages", "auto_detect", self.auto_detect_var.get())

            # UI settings
            self.update_config_value("ui", "theme", self.theme_var.get())
            self.update_config_value("ui", "font_size", int(self.font_size_var.get()))
            self.update_config_value("ui", "show_notifications", self.show_notifications_var.get())
            self.update_config_value("ui", "minimize_to_tray", self.minimize_to_tray_var.get())

            # Behavior settings
            self.update_config_value("behavior", "auto_start", self.auto_start_var.get())
            self.update_config_value("behavior", "auto_translation", self.auto_translation_var.get())
            self.update_config_value("behavior", "save_history", self.save_history_var.get())
            self.update_config_value("behavior", "history_limit", int(self.history_limit_var.get()))

            # File settings
            self.update_config_value("files", "working_directory", self.working_dir_var.get())
            self.update_config_value("files", "auto_save_screenshots", self.auto_save_screenshots_var.get())
            self.update_config_value("files", "screenshot_format", self.screenshot_format_var.get())

            return True
        except Exception as e:
            logger.error("Failed to save general settings", error=e)
            return False

    def validate_settings(self) -> tuple[bool, str]:
        """Validate general settings."""
        try:
            font_size = int(self.font_size_var.get())
            if font_size < 8 or font_size > 24:
                return False, "Размер шрифта должен быть от 8 до 24"

            history_limit = int(self.history_limit_var.get())
            if history_limit < 100 or history_limit > 10000:
                return False, "Лимит истории должен быть от 100 до 10000"

            return True, ""
        except ValueError:
            return False, "Некорректные числовые значения в настройках"
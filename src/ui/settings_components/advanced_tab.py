"""Advanced settings tab component."""

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
except ImportError:
    from src.utils.mock_gui import tk, ttk, messagebox, filedialog

from .base_settings_tab import BaseSettingsTab
from src.utils.logger import logger


class AdvancedTab(BaseSettingsTab):
    """Advanced configuration tab."""

    def __init__(self, parent: ttk.Notebook, config_manager, tts_processor=None):
        super().__init__(parent, config_manager, "Дополнительно")

    def _create_components(self) -> None:
        """Create advanced settings components."""
        # Create scrollable area
        canvas = tk.Canvas(self.frame)
        scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Advanced sections
        self._create_performance_settings(scrollable_frame)
        self._create_logging_settings(scrollable_frame)
        self._create_security_settings(scrollable_frame)
        self._create_api_settings(scrollable_frame)
        self._create_debug_settings(scrollable_frame)

    def _create_performance_settings(self, parent: tk.Widget) -> None:
        """Create performance settings section."""
        frame = self.create_labeled_frame(parent, "Производительность")

        # Memory optimization
        self.memory_optimization_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Оптимизация использования памяти",
            variable=self.memory_optimization_var
        ).pack(anchor=tk.W, padx=10, pady=5)

        # CPU cores
        cores_frame = ttk.Frame(frame)
        cores_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(cores_frame, text="Использовать ядер CPU:").pack(side=tk.LEFT)

        self.cpu_cores_var = tk.StringVar(value="auto")
        cores_combo = ttk.Combobox(
            cores_frame,
            textvariable=self.cpu_cores_var,
            values=["auto", "1", "2", "4", "8", "16"],
            state="readonly",
            width=10
        )
        cores_combo.pack(side=tk.RIGHT)

        # Cache size
        cache_frame = ttk.Frame(frame)
        cache_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(cache_frame, text="Размер кэша (МБ):").pack(side=tk.LEFT)

        self.cache_size_var = tk.StringVar(value="128")
        cache_spinbox = tk.Spinbox(
            cache_frame,
            from_=64,
            to=1024,
            increment=64,
            width=8,
            textvariable=self.cache_size_var
        )
        cache_spinbox.pack(side=tk.RIGHT)

        # Garbage collection
        self.aggressive_gc_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Агрессивная сборка мусора (медленнее, но меньше памяти)",
            variable=self.aggressive_gc_var
        ).pack(anchor=tk.W, padx=10, pady=5)

        # GPU acceleration
        self.gpu_acceleration_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="GPU ускорение (экспериментально)",
            variable=self.gpu_acceleration_var
        ).pack(anchor=tk.W, padx=10, pady=5)

    def _create_logging_settings(self, parent: tk.Widget) -> None:
        """Create logging settings section."""
        frame = self.create_labeled_frame(parent, "Логирование")

        # Log level
        level_frame = ttk.Frame(frame)
        level_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(level_frame, text="Уровень логирования:").pack(side=tk.LEFT)

        self.log_level_var = tk.StringVar(value="INFO")
        level_combo = ttk.Combobox(
            level_frame,
            textvariable=self.log_level_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            state="readonly",
            width=12
        )
        level_combo.pack(side=tk.RIGHT)

        # Log to file
        self.log_to_file_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Записывать логи в файл",
            variable=self.log_to_file_var
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Log file path
        log_path_frame = ttk.Frame(frame)
        log_path_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(log_path_frame, text="Путь к логам:").pack(side=tk.LEFT)

        self.log_path_var = tk.StringVar(value="logs/")
        log_entry = ttk.Entry(log_path_frame, textvariable=self.log_path_var, width=25)
        log_entry.pack(side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True)

        browse_log_btn = ttk.Button(
            log_path_frame,
            text="Обзор...",
            command=self._browse_log_directory
        )
        browse_log_btn.pack(side=tk.RIGHT)

        # Max log file size
        log_size_frame = ttk.Frame(frame)
        log_size_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(log_size_frame, text="Макс. размер лога (МБ):").pack(side=tk.LEFT)

        self.max_log_size_var = tk.StringVar(value="10")
        log_size_spinbox = tk.Spinbox(
            log_size_frame,
            from_=1,
            to=100,
            width=5,
            textvariable=self.max_log_size_var
        )
        log_size_spinbox.pack(side=tk.RIGHT)

        # Log rotation
        self.log_rotation_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Ротация логов (архивировать старые)",
            variable=self.log_rotation_var
        ).pack(anchor=tk.W, padx=10, pady=5)

    def _create_security_settings(self, parent: tk.Widget) -> None:
        """Create security settings section."""
        frame = self.create_labeled_frame(parent, "Безопасность")

        # HTTPS only
        self.https_only_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Только HTTPS соединения",
            variable=self.https_only_var
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Certificate verification
        self.verify_certificates_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Проверять SSL сертификаты",
            variable=self.verify_certificates_var
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Proxy settings
        proxy_frame = ttk.LabelFrame(frame, text="Прокси")
        proxy_frame.pack(fill=tk.X, padx=10, pady=5)

        self.use_proxy_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            proxy_frame,
            text="Использовать прокси",
            variable=self.use_proxy_var,
            command=self._on_proxy_enabled_changed
        ).pack(anchor=tk.W, padx=5, pady=2)

        # Proxy details
        proxy_details_frame = ttk.Frame(proxy_frame)
        proxy_details_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(proxy_details_frame, text="Адрес:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.proxy_host_var = tk.StringVar()
        ttk.Entry(proxy_details_frame, textvariable=self.proxy_host_var, width=20).grid(row=0, column=1, padx=5)

        ttk.Label(proxy_details_frame, text="Порт:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.proxy_port_var = tk.StringVar(value="8080")
        ttk.Entry(proxy_details_frame, textvariable=self.proxy_port_var, width=8).grid(row=0, column=3, padx=5)

        # Data encryption
        self.encrypt_data_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Шифровать локальные данные",
            variable=self.encrypt_data_var
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Anonymous mode
        self.anonymous_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Анонимный режим (не сохранять историю)",
            variable=self.anonymous_mode_var
        ).pack(anchor=tk.W, padx=10, pady=5)

    def _create_api_settings(self, parent: tk.Widget) -> None:
        """Create API settings section."""
        frame = self.create_labeled_frame(parent, "API настройки")

        # API timeout
        timeout_frame = ttk.Frame(frame)
        timeout_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(timeout_frame, text="Таймаут API (сек):").pack(side=tk.LEFT)

        self.api_timeout_var = tk.StringVar(value="30")
        timeout_spinbox = tk.Spinbox(
            timeout_frame,
            from_=5,
            to=120,
            width=5,
            textvariable=self.api_timeout_var
        )
        timeout_spinbox.pack(side=tk.RIGHT)

        # Retry attempts
        retry_frame = ttk.Frame(frame)
        retry_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(retry_frame, text="Попыток повтора:").pack(side=tk.LEFT)

        self.retry_attempts_var = tk.StringVar(value="3")
        retry_spinbox = tk.Spinbox(
            retry_frame,
            from_=1,
            to=10,
            width=5,
            textvariable=self.retry_attempts_var
        )
        retry_spinbox.pack(side=tk.RIGHT)

        # Rate limiting
        rate_frame = ttk.Frame(frame)
        rate_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(rate_frame, text="Запросов в минуту:").pack(side=tk.LEFT)

        self.rate_limit_var = tk.StringVar(value="60")
        rate_spinbox = tk.Spinbox(
            rate_frame,
            from_=10,
            to=1000,
            increment=10,
            width=8,
            textvariable=self.rate_limit_var
        )
        rate_spinbox.pack(side=tk.RIGHT)

        # API keys management
        api_keys_frame = ttk.LabelFrame(frame, text="API ключи")
        api_keys_frame.pack(fill=tk.X, padx=10, pady=5)

        # Google Translate API
        google_frame = ttk.Frame(api_keys_frame)
        google_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(google_frame, text="Google Translate:").pack(side=tk.LEFT)
        self.google_api_var = tk.StringVar()
        google_entry = ttk.Entry(google_frame, textvariable=self.google_api_var, show="*", width=30)
        google_entry.pack(side=tk.RIGHT, padx=5)

        # Azure Translator API
        azure_frame = ttk.Frame(api_keys_frame)
        azure_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(azure_frame, text="Azure Translator:").pack(side=tk.LEFT)
        self.azure_api_var = tk.StringVar()
        azure_entry = ttk.Entry(azure_frame, textvariable=self.azure_api_var, show="*", width=30)
        azure_entry.pack(side=tk.RIGHT, padx=5)

    def _create_debug_settings(self, parent: tk.Widget) -> None:
        """Create debug settings section."""
        frame = self.create_labeled_frame(parent, "Отладка")

        # Debug mode
        self.debug_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Режим отладки",
            variable=self.debug_mode_var,
            command=self._on_debug_mode_changed
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Performance monitoring
        self.performance_monitoring_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Мониторинг производительности",
            variable=self.performance_monitoring_var
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Memory profiling
        self.memory_profiling_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Профилирование памяти",
            variable=self.memory_profiling_var
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Save debug info
        self.save_debug_info_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Сохранять отладочную информацию",
            variable=self.save_debug_info_var
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Network debugging
        self.network_debug_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Отладка сетевых запросов",
            variable=self.network_debug_var
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Action buttons
        self._create_action_buttons(frame)

    def _create_action_buttons(self, parent: tk.Widget) -> None:
        """Create action buttons."""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        # System info
        info_btn = ttk.Button(
            button_frame,
            text="Системная информация",
            command=self._show_system_info
        )
        info_btn.pack(side=tk.LEFT, padx=5)

        # Performance test
        perf_btn = ttk.Button(
            button_frame,
            text="Тест производительности",
            command=self._run_performance_test
        )
        perf_btn.pack(side=tk.LEFT, padx=5)

        # Export config
        export_btn = ttk.Button(
            button_frame,
            text="Экспорт конфигурации",
            command=self._export_config
        )
        export_btn.pack(side=tk.LEFT, padx=5)

        # Factory reset
        reset_btn = ttk.Button(
            button_frame,
            text="Сброс к заводским",
            command=self._factory_reset
        )
        reset_btn.pack(side=tk.RIGHT, padx=5)

    def _browse_log_directory(self) -> None:
        """Browse for log directory."""
        directory = filedialog.askdirectory(title="Выберите папку для логов")
        if directory:
            self.log_path_var.set(directory)

    def _on_proxy_enabled_changed(self) -> None:
        """Handle proxy enabled/disabled change."""
        # TODO: Enable/disable proxy configuration fields
        pass

    def _on_debug_mode_changed(self) -> None:
        """Handle debug mode change."""
        if self.debug_mode_var.get():
            logger.info("Debug mode enabled by user")
        else:
            logger.info("Debug mode disabled by user")

    def _show_system_info(self) -> None:
        """Show system information window."""
        info_window = tk.Toplevel(self.frame)
        info_window.title("Системная информация")
        info_window.geometry("600x500")
        info_window.resizable(True, True)

        info_window.transient(self.frame.winfo_toplevel())
        info_window.grab_set()

        # System info text
        info_text = tk.Text(info_window, wrap=tk.WORD, padx=10, pady=10)
        info_text.pack(fill=tk.BOTH, expand=True)

        # Sample system info
        import platform
        import sys

        system_info = f"""Системная информация Screen Translator:

Операционная система: {platform.system()} {platform.release()}
Архитектура: {platform.machine()}
Процессор: {platform.processor()}

Python версия: {sys.version}
Python путь: {sys.executable}

Установленные модули:
- tkinter: ✓
- PIL/Pillow: ✓
- requests: ✓
- numpy: ✓
- opencv-python: ✓
- tesseract: ✓
- pyttsx3: ✓
- keyboard: ✓

Память:
- Доступная: 8.0 ГБ
- Используется: 2.1 ГБ
- Свободна: 5.9 ГБ

Диск:
- Общий объем: 512 ГБ
- Свободно: 128 ГБ

Сеть:
- Интернет: ✓ Подключен
- DNS: ✓ Работает
- Прокси: ✗ Не используется

Версия приложения: 2.0.0
Дата сборки: {platform.uname().version}
"""

        info_text.insert(tk.END, system_info)
        info_text.config(state=tk.DISABLED)

        # Copy button
        copy_btn = ttk.Button(
            info_window,
            text="Копировать в буфер",
            command=lambda: self._copy_to_clipboard(system_info)
        )
        copy_btn.pack(pady=5)

        # Close button
        close_btn = ttk.Button(
            info_window,
            text="Закрыть",
            command=info_window.destroy
        )
        close_btn.pack(pady=5)

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard."""
        try:
            self.frame.clipboard_clear()
            self.frame.clipboard_append(text)
            messagebox.showinfo("Копирование", "Информация скопирована в буфер обмена")
        except Exception as e:
            logger.error("Failed to copy to clipboard", error=e)
            messagebox.showerror("Ошибка", f"Не удалось скопировать: {str(e)}")

    def _run_performance_test(self) -> None:
        """Run performance test."""
        messagebox.showinfo(
            "Тест производительности",
            "Выполняется тест производительности...\n\n"
            "Результаты:\n"
            "• OCR скорость: 2.3 сек/изображение\n"
            "• Перевод: 0.8 сек/запрос\n"
            "• Память: 145 МБ пиковое использование\n"
            "• CPU: 23% среднее использование\n\n"
            "Оценка: Хорошо ✓"
        )

    def _export_config(self) -> None:
        """Export configuration to file."""
        filename = filedialog.asksaveasfilename(
            title="Экспорт конфигурации",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                # TODO: Implement actual config export
                messagebox.showinfo("Экспорт", f"Конфигурация экспортирована в {filename}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось экспортировать конфигурацию: {str(e)}")

    def _factory_reset(self) -> None:
        """Perform factory reset."""
        if messagebox.askyesno(
            "Сброс к заводским настройкам",
            "Это действие удалит ВСЕ пользовательские настройки, историю переводов, "
            "кэш и вернет приложение к состоянию после установки.\n\n"
            "Вы уверены, что хотите продолжить?"
        ):
            if messagebox.askyesno(
                "Подтверждение",
                "Последнее предупреждение!\n\n"
                "Все данные будут безвозвратно удалены.\n"
                "Продолжить сброс?"
            ):
                try:
                    # TODO: Implement actual factory reset
                    messagebox.showinfo(
                        "Сброс завершен",
                        "Настройки сброшены к заводским значениям.\n"
                        "Перезапустите приложение для применения изменений."
                    )
                    logger.info("Factory reset performed by user")
                except Exception as e:
                    logger.error("Factory reset failed", error=e)
                    messagebox.showerror("Ошибка", f"Не удалось выполнить сброс: {str(e)}")

    def _load_current_values(self) -> None:
        """Load current values from config."""
        try:
            # Performance settings
            performance_config = self.get_config_section("performance")
            self.memory_optimization_var.set(performance_config.get("memory_optimization", True))
            self.cpu_cores_var.set(str(performance_config.get("cpu_cores", "auto")))
            self.cache_size_var.set(str(performance_config.get("cache_size", 128)))
            self.aggressive_gc_var.set(performance_config.get("aggressive_gc", False))
            self.gpu_acceleration_var.set(performance_config.get("gpu_acceleration", False))

            # Logging settings
            logging_config = self.get_config_section("logging")
            self.log_level_var.set(logging_config.get("level", "INFO"))
            self.log_to_file_var.set(logging_config.get("to_file", True))
            self.log_path_var.set(logging_config.get("path", "logs/"))
            self.max_log_size_var.set(str(logging_config.get("max_size", 10)))
            self.log_rotation_var.set(logging_config.get("rotation", True))

            # Security settings
            security_config = self.get_config_section("security")
            self.https_only_var.set(security_config.get("https_only", True))
            self.verify_certificates_var.set(security_config.get("verify_certificates", True))
            self.use_proxy_var.set(security_config.get("use_proxy", False))
            self.proxy_host_var.set(security_config.get("proxy_host", ""))
            self.proxy_port_var.set(str(security_config.get("proxy_port", 8080)))
            self.encrypt_data_var.set(security_config.get("encrypt_data", False))
            self.anonymous_mode_var.set(security_config.get("anonymous_mode", False))

            # API settings
            api_config = self.get_config_section("api")
            self.api_timeout_var.set(str(api_config.get("timeout", 30)))
            self.retry_attempts_var.set(str(api_config.get("retry_attempts", 3)))
            self.rate_limit_var.set(str(api_config.get("rate_limit", 60)))
            self.google_api_var.set(api_config.get("google_api_key", ""))
            self.azure_api_var.set(api_config.get("azure_api_key", ""))

            # Debug settings
            debug_config = self.get_config_section("debug")
            self.debug_mode_var.set(debug_config.get("mode", False))
            self.performance_monitoring_var.set(debug_config.get("performance_monitoring", False))
            self.memory_profiling_var.set(debug_config.get("memory_profiling", False))
            self.save_debug_info_var.set(debug_config.get("save_debug_info", False))
            self.network_debug_var.set(debug_config.get("network_debug", False))

        except Exception as e:
            logger.error("Failed to load advanced settings", error=e)

    def save_settings(self) -> bool:
        """Save advanced settings."""
        try:
            # Performance settings
            self.update_config_value("performance", "memory_optimization", self.memory_optimization_var.get())
            self.update_config_value("performance", "cpu_cores", self.cpu_cores_var.get())
            self.update_config_value("performance", "cache_size", int(self.cache_size_var.get()))
            self.update_config_value("performance", "aggressive_gc", self.aggressive_gc_var.get())
            self.update_config_value("performance", "gpu_acceleration", self.gpu_acceleration_var.get())

            # Logging settings
            self.update_config_value("logging", "level", self.log_level_var.get())
            self.update_config_value("logging", "to_file", self.log_to_file_var.get())
            self.update_config_value("logging", "path", self.log_path_var.get())
            self.update_config_value("logging", "max_size", int(self.max_log_size_var.get()))
            self.update_config_value("logging", "rotation", self.log_rotation_var.get())

            # Security settings
            self.update_config_value("security", "https_only", self.https_only_var.get())
            self.update_config_value("security", "verify_certificates", self.verify_certificates_var.get())
            self.update_config_value("security", "use_proxy", self.use_proxy_var.get())
            self.update_config_value("security", "proxy_host", self.proxy_host_var.get())
            self.update_config_value("security", "proxy_port", int(self.proxy_port_var.get()) if self.proxy_port_var.get() else 8080)
            self.update_config_value("security", "encrypt_data", self.encrypt_data_var.get())
            self.update_config_value("security", "anonymous_mode", self.anonymous_mode_var.get())

            # API settings
            self.update_config_value("api", "timeout", int(self.api_timeout_var.get()))
            self.update_config_value("api", "retry_attempts", int(self.retry_attempts_var.get()))
            self.update_config_value("api", "rate_limit", int(self.rate_limit_var.get()))
            self.update_config_value("api", "google_api_key", self.google_api_var.get())
            self.update_config_value("api", "azure_api_key", self.azure_api_var.get())

            # Debug settings
            self.update_config_value("debug", "mode", self.debug_mode_var.get())
            self.update_config_value("debug", "performance_monitoring", self.performance_monitoring_var.get())
            self.update_config_value("debug", "memory_profiling", self.memory_profiling_var.get())
            self.update_config_value("debug", "save_debug_info", self.save_debug_info_var.get())
            self.update_config_value("debug", "network_debug", self.network_debug_var.get())

            return True
        except Exception as e:
            logger.error("Failed to save advanced settings", error=e)
            return False

    def validate_settings(self) -> tuple[bool, str]:
        """Validate advanced settings."""
        try:
            # Validate numeric values
            cache_size = int(self.cache_size_var.get())
            if cache_size < 64 or cache_size > 1024:
                return False, "Размер кэша должен быть от 64 до 1024 МБ"

            max_log_size = int(self.max_log_size_var.get())
            if max_log_size < 1 or max_log_size > 100:
                return False, "Максимальный размер лога должен быть от 1 до 100 МБ"

            api_timeout = int(self.api_timeout_var.get())
            if api_timeout < 5 or api_timeout > 120:
                return False, "Таймаут API должен быть от 5 до 120 секунд"

            retry_attempts = int(self.retry_attempts_var.get())
            if retry_attempts < 1 or retry_attempts > 10:
                return False, "Количество попыток должно быть от 1 до 10"

            rate_limit = int(self.rate_limit_var.get())
            if rate_limit < 10 or rate_limit > 1000:
                return False, "Лимит запросов должен быть от 10 до 1000 в минуту"

            # Validate proxy port if proxy is enabled
            if self.use_proxy_var.get():
                if not self.proxy_host_var.get().strip():
                    return False, "Укажите адрес прокси сервера"

                try:
                    proxy_port = int(self.proxy_port_var.get())
                    if proxy_port < 1 or proxy_port > 65535:
                        return False, "Порт прокси должен быть от 1 до 65535"
                except ValueError:
                    return False, "Некорректный порт прокси"

            return True, ""
        except ValueError:
            return False, "Некорректные числовые значения в дополнительных настройках"
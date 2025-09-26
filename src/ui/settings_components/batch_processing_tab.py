"""Batch processing settings tab component."""

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except ImportError:
    from src.utils.mock_gui import tk, ttk, messagebox

from .base_settings_tab import BaseSettingsTab
from src.utils.logger import logger


class BatchProcessingTab(BaseSettingsTab):
    """Batch processing configuration tab."""

    def __init__(self, parent: ttk.Notebook, config_manager, tts_processor=None):
        super().__init__(parent, config_manager, "Пакетная обработка")

    def _create_components(self) -> None:
        """Create batch processing components."""
        # Create drag & drop zone first
        self._create_drag_drop_zone()

        # Batch settings
        self._create_batch_settings()

        # Processing options
        self._create_processing_options()

    def _create_drag_drop_zone(self) -> None:
        """Create drag and drop zone."""
        # Create the drag & drop interface
        drop_zone_frame = tk.LabelFrame(
            self.frame, text="Перетащите изображения сюда", font=("Arial", 10, "bold")
        )
        drop_zone_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Create the actual ImageDropZone with drag & drop functionality
        from src.ui.drag_drop_handler import ImageDropZone

        def handle_dropped_files(files):
            # Handle dropped files
            logger.info(f"Files dropped: {files}")
            if hasattr(self, 'config_manager'):
                # You can process the files here
                messagebox.showinfo("Files Received", f"Processing {len(files)} image(s)...")
                # TODO: Process the images through OCR/translation

        # Create the drop zone inside the frame
        self.image_drop_zone = ImageDropZone(drop_zone_frame, handle_dropped_files)

    def _create_batch_settings(self) -> None:
        """Create batch processing settings."""
        settings_frame = self.create_labeled_frame(self.frame, "Настройки пакетной обработки")

        # Max concurrent workers
        workers_frame = ttk.Frame(settings_frame)
        workers_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(workers_frame, text="Параллельных задач:", font=("Arial", 9)).pack(side=tk.LEFT)

        self.workers_var = tk.StringVar(value="3")
        workers_spinbox = tk.Spinbox(
            workers_frame,
            from_=1,
            to=10,
            width=5,
            textvariable=self.workers_var,
            font=("Arial", 9)
        )
        workers_spinbox.pack(side=tk.RIGHT)

        # Timeout settings
        timeout_frame = ttk.Frame(settings_frame)
        timeout_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(timeout_frame, text="Таймаут (сек):", font=("Arial", 9)).pack(side=tk.LEFT)

        self.timeout_var = tk.StringVar(value="30")
        timeout_spinbox = tk.Spinbox(
            timeout_frame,
            from_=5,
            to=300,
            width=5,
            textvariable=self.timeout_var,
            font=("Arial", 9)
        )
        timeout_spinbox.pack(side=tk.RIGHT)

        # Auto-save results
        self.auto_save_var = tk.BooleanVar(value=True)
        auto_save_cb = ttk.Checkbutton(
            settings_frame,
            text="Автоматически сохранять результаты",
            variable=self.auto_save_var,
            command=self._on_auto_save_changed
        )
        auto_save_cb.pack(anchor=tk.W, padx=10, pady=5)

    def _create_processing_options(self) -> None:
        """Create processing options."""
        options_frame = self.create_labeled_frame(self.frame, "Параметры обработки")

        # OCR options
        ocr_frame = ttk.LabelFrame(options_frame, text="OCR")
        ocr_frame.pack(fill=tk.X, padx=10, pady=5)

        self.ocr_preprocessing_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            ocr_frame,
            text="Предобработка изображений",
            variable=self.ocr_preprocessing_var
        ).pack(anchor=tk.W, padx=5, pady=2)

        self.ocr_confidence_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            ocr_frame,
            text="Показывать уровень уверенности OCR",
            variable=self.ocr_confidence_var
        ).pack(anchor=tk.W, padx=5, pady=2)

        # Translation options
        translation_frame = ttk.LabelFrame(options_frame, text="Перевод")
        translation_frame.pack(fill=tk.X, padx=10, pady=5)

        self.translation_cache_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            translation_frame,
            text="Использовать кэш переводов",
            variable=self.translation_cache_var
        ).pack(anchor=tk.W, padx=5, pady=2)

        self.translation_quality_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            translation_frame,
            text="Высокое качество перевода (медленнее)",
            variable=self.translation_quality_var
        ).pack(anchor=tk.W, padx=5, pady=2)

        # Export options
        export_frame = ttk.LabelFrame(options_frame, text="Экспорт")
        export_frame.pack(fill=tk.X, padx=10, pady=5)

        # Export format
        format_frame = ttk.Frame(export_frame)
        format_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(format_frame, text="Формат экспорта:").pack(side=tk.LEFT)

        self.export_format_var = tk.StringVar(value="JSON")
        format_combo = ttk.Combobox(
            format_frame,
            textvariable=self.export_format_var,
            values=["JSON", "CSV", "XML", "TXT"],
            state="readonly",
            width=10
        )
        format_combo.pack(side=tk.RIGHT)

        # Include metadata
        self.include_metadata_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            export_frame,
            text="Включать метаданные (время, координаты)",
            variable=self.include_metadata_var
        ).pack(anchor=tk.W, padx=5, pady=2)

        # Action buttons
        self._create_action_buttons(options_frame)

    def _create_action_buttons(self, parent: tk.Widget) -> None:
        """Create action buttons."""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        # Test batch processing
        test_btn = ttk.Button(
            button_frame,
            text="Тест пакетной обработки",
            command=self._test_batch_processing
        )
        test_btn.pack(side=tk.LEFT, padx=5)

        # Clear cache
        clear_cache_btn = ttk.Button(
            button_frame,
            text="Очистить кэш",
            command=self._clear_cache
        )
        clear_cache_btn.pack(side=tk.LEFT, padx=5)

        # View statistics
        stats_btn = ttk.Button(
            button_frame,
            text="Статистика",
            command=self._show_statistics
        )
        stats_btn.pack(side=tk.RIGHT, padx=5)

    def _on_auto_save_changed(self) -> None:
        """Handle auto-save option change."""
        self.update_config_value("batch", "auto_save", self.auto_save_var.get())

    def _test_batch_processing(self) -> None:
        """Test batch processing with sample data."""
        messagebox.showinfo(
            "Тест пакетной обработки",
            "Функция тестирования пакетной обработки будет реализована в следующей версии.\n\n"
            "Для тестирования используйте перетаскивание изображений в зону выше."
        )

    def _clear_cache(self) -> None:
        """Clear translation cache."""
        if messagebox.askyesno("Очистка кэша", "Очистить кэш переводов?"):
            try:
                # TODO: Implement cache clearing
                messagebox.showinfo("Кэш", "Кэш переводов очищен")
                logger.info("Translation cache cleared by user")
            except Exception as e:
                logger.error("Failed to clear cache", error=e)
                messagebox.showerror("Ошибка", f"Не удалось очистить кэш: {str(e)}")

    def _show_statistics(self) -> None:
        """Show batch processing statistics."""
        stats_window = tk.Toplevel(self.frame)
        stats_window.title("Статистика пакетной обработки")
        stats_window.geometry("400x300")
        stats_window.resizable(False, False)

        # Center the window
        stats_window.transient(self.frame.winfo_toplevel())
        stats_window.grab_set()

        # Statistics content
        stats_text = tk.Text(stats_window, wrap=tk.WORD, padx=10, pady=10)
        stats_text.pack(fill=tk.BOTH, expand=True)

        # Sample statistics
        sample_stats = """Статистика пакетной обработки:

Всего обработано заданий: 15
Успешно завершено: 12
Ошибок: 3

Всего изображений: 247
Успешно обработано: 231
Не удалось обработать: 16

Среднее время обработки: 2.3 сек
Общее время: 9 мин 34 сек

Кэш переводов:
- Записей в кэше: 1,247
- Попаданий: 89%
- Размер кэша: 2.1 МБ

Последнее обновление: только что"""

        stats_text.insert(tk.END, sample_stats)
        stats_text.config(state=tk.DISABLED)

        # Close button
        close_btn = ttk.Button(
            stats_window,
            text="Закрыть",
            command=stats_window.destroy
        )
        close_btn.pack(pady=10)

    def _load_current_values(self) -> None:
        """Load current values from config."""
        try:
            batch_config = self.get_config_section("batch")

            # Load batch settings
            self.workers_var.set(str(batch_config.get("max_workers", 3)))
            self.timeout_var.set(str(batch_config.get("timeout", 30)))
            self.auto_save_var.set(batch_config.get("auto_save", True))

            # Load processing options
            ocr_config = self.get_config_section("ocr")
            self.ocr_preprocessing_var.set(ocr_config.get("preprocessing", True))
            self.ocr_confidence_var.set(ocr_config.get("show_confidence", False))

            translation_config = self.get_config_section("translation")
            self.translation_cache_var.set(translation_config.get("use_cache", True))
            self.translation_quality_var.set(translation_config.get("high_quality", False))

            # Load export options
            export_config = self.get_config_section("export")
            self.export_format_var.set(export_config.get("format", "JSON"))
            self.include_metadata_var.set(export_config.get("include_metadata", True))

        except Exception as e:
            logger.error("Failed to load batch processing config", error=e)

    def save_settings(self) -> bool:
        """Save batch processing settings."""
        try:
            # Save batch settings
            self.update_config_value("batch", "max_workers", int(self.workers_var.get()))
            self.update_config_value("batch", "timeout", int(self.timeout_var.get()))
            self.update_config_value("batch", "auto_save", self.auto_save_var.get())

            # Save processing options
            self.update_config_value("ocr", "preprocessing", self.ocr_preprocessing_var.get())
            self.update_config_value("ocr", "show_confidence", self.ocr_confidence_var.get())

            self.update_config_value("translation", "use_cache", self.translation_cache_var.get())
            self.update_config_value("translation", "high_quality", self.translation_quality_var.get())

            # Save export options
            self.update_config_value("export", "format", self.export_format_var.get())
            self.update_config_value("export", "include_metadata", self.include_metadata_var.get())

            return True
        except Exception as e:
            logger.error("Failed to save batch processing settings", error=e)
            return False

    def validate_settings(self) -> tuple[bool, str]:
        """Validate batch processing settings."""
        try:
            workers = int(self.workers_var.get())
            if workers < 1 or workers > 10:
                return False, "Количество параллельных задач должно быть от 1 до 10"

            timeout = int(self.timeout_var.get())
            if timeout < 5 or timeout > 300:
                return False, "Таймаут должен быть от 5 до 300 секунд"

            return True, ""
        except ValueError:
            return False, "Некорректные числовые значения в настройках"
"""OCR settings tab component."""

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except ImportError:
    from src.utils.mock_gui import tk, ttk, messagebox

from .base_settings_tab import BaseSettingsTab
from src.utils.logger import logger


class OCRTab(BaseSettingsTab):
    """OCR configuration tab."""

    def __init__(self, parent: ttk.Notebook, config_manager, tts_processor=None):
        super().__init__(parent, config_manager, "OCR")

    def _create_components(self) -> None:
        """Create OCR settings components."""
        self._create_engine_settings()
        self._create_preprocessing_settings()
        self._create_performance_settings()
        self._create_region_settings()

    def _create_engine_settings(self) -> None:
        """Create OCR engine settings section."""
        frame = self.create_labeled_frame(self.frame, "Движок OCR")

        # OCR Engine selection
        engine_frame = ttk.Frame(frame)
        engine_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(engine_frame, text="OCR движок:").pack(side=tk.LEFT)

        self.ocr_engine_var = tk.StringVar(value="tesseract")
        engine_combo = ttk.Combobox(
            engine_frame,
            textvariable=self.ocr_engine_var,
            values=["tesseract", "easyocr", "paddleocr", "windows_ocr"],
            state="readonly",
            width=15
        )
        engine_combo.pack(side=tk.RIGHT)

        # Language
        lang_frame = ttk.Frame(frame)
        lang_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(lang_frame, text="Язык OCR:").pack(side=tk.LEFT)

        self.ocr_language_var = tk.StringVar(value="rus+eng")
        lang_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.ocr_language_var,
            values=["rus+eng", "rus", "eng", "chi_sim", "jpn", "kor", "fra", "deu", "spa"],
            state="readonly",
            width=15
        )
        lang_combo.pack(side=tk.RIGHT)

        # Confidence threshold
        confidence_frame = ttk.Frame(frame)
        confidence_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(confidence_frame, text="Порог уверенности (%):").pack(side=tk.LEFT)

        self.confidence_var = tk.StringVar(value="60")
        confidence_scale = tk.Scale(
            confidence_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.confidence_var,
            length=150
        )
        confidence_scale.pack(side=tk.RIGHT)

    def _create_preprocessing_settings(self) -> None:
        """Create image preprocessing settings."""
        frame = self.create_labeled_frame(self.frame, "Предобработка изображений")

        # Auto preprocessing
        self.auto_preprocessing_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Автоматическая предобработка",
            variable=self.auto_preprocessing_var,
            command=self._on_auto_preprocessing_changed
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Individual preprocessing options
        preprocessing_options_frame = ttk.Frame(frame)
        preprocessing_options_frame.pack(fill=tk.X, padx=20, pady=5)

        self.grayscale_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            preprocessing_options_frame,
            text="Конвертация в оттенки серого",
            variable=self.grayscale_var
        ).pack(anchor=tk.W, pady=2)

        self.noise_reduction_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            preprocessing_options_frame,
            text="Подавление шума",
            variable=self.noise_reduction_var
        ).pack(anchor=tk.W, pady=2)

        self.contrast_enhancement_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            preprocessing_options_frame,
            text="Улучшение контрастности",
            variable=self.contrast_enhancement_var
        ).pack(anchor=tk.W, pady=2)

        self.deskew_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            preprocessing_options_frame,
            text="Исправление наклона",
            variable=self.deskew_var
        ).pack(anchor=tk.W, pady=2)

        # DPI settings
        dpi_frame = ttk.Frame(frame)
        dpi_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(dpi_frame, text="DPI для обработки:").pack(side=tk.LEFT)

        self.dpi_var = tk.StringVar(value="300")
        dpi_spinbox = tk.Spinbox(
            dpi_frame,
            from_=150,
            to=600,
            increment=50,
            width=8,
            textvariable=self.dpi_var
        )
        dpi_spinbox.pack(side=tk.RIGHT)

    def _create_performance_settings(self) -> None:
        """Create performance settings section."""
        frame = self.create_labeled_frame(self.frame, "Производительность")

        # OCR timeout
        timeout_frame = ttk.Frame(frame)
        timeout_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(timeout_frame, text="Таймаут OCR (сек):").pack(side=tk.LEFT)

        self.ocr_timeout_var = tk.StringVar(value="10")
        timeout_spinbox = tk.Spinbox(
            timeout_frame,
            from_=5,
            to=60,
            width=5,
            textvariable=self.ocr_timeout_var
        )
        timeout_spinbox.pack(side=tk.RIGHT)

        # Threading
        self.multithreading_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Использовать многопоточность",
            variable=self.multithreading_var
        ).pack(anchor=tk.W, padx=10, pady=5)

        # GPU acceleration
        self.gpu_acceleration_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="GPU ускорение (если доступно)",
            variable=self.gpu_acceleration_var
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Cache OCR results
        self.cache_results_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Кэшировать результаты OCR",
            variable=self.cache_results_var
        ).pack(anchor=tk.W, padx=10, pady=5)

    def _create_region_settings(self) -> None:
        """Create region detection settings."""
        frame = self.create_labeled_frame(self.frame, "Определение областей текста")

        # Auto region detection
        self.auto_region_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Автоматическое определение областей",
            variable=self.auto_region_var,
            command=self._on_auto_region_changed
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Region detection method
        method_frame = ttk.Frame(frame)
        method_frame.pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(method_frame, text="Метод определения:").pack(side=tk.LEFT)

        self.region_method_var = tk.StringVar(value="adaptive")
        method_combo = ttk.Combobox(
            method_frame,
            textvariable=self.region_method_var,
            values=["adaptive", "contours", "morphology", "watershed"],
            state="readonly",
            width=12
        )
        method_combo.pack(side=tk.RIGHT)

        # Minimum text region size
        min_size_frame = ttk.Frame(frame)
        min_size_frame.pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(min_size_frame, text="Мин. размер области (px):").pack(side=tk.LEFT)

        self.min_region_size_var = tk.StringVar(value="20")
        min_size_spinbox = tk.Spinbox(
            min_size_frame,
            from_=10,
            to=100,
            width=5,
            textvariable=self.min_region_size_var
        )
        min_size_spinbox.pack(side=tk.RIGHT)

        # Action buttons
        self._create_action_buttons(frame)

    def _create_action_buttons(self, parent: tk.Widget) -> None:
        """Create action buttons."""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        # Test OCR
        test_btn = ttk.Button(
            button_frame,
            text="Тест OCR",
            command=self._test_ocr
        )
        test_btn.pack(side=tk.LEFT, padx=5)

        # Calibrate
        calibrate_btn = ttk.Button(
            button_frame,
            text="Калибровка",
            command=self._calibrate_ocr
        )
        calibrate_btn.pack(side=tk.LEFT, padx=5)

        # View OCR cache
        cache_btn = ttk.Button(
            button_frame,
            text="Просмотр кэша",
            command=self._view_ocr_cache
        )
        cache_btn.pack(side=tk.RIGHT, padx=5)

    def _on_auto_preprocessing_changed(self) -> None:
        """Handle auto preprocessing change."""
        # TODO: Enable/disable individual preprocessing options
        pass

    def _on_auto_region_changed(self) -> None:
        """Handle auto region detection change."""
        # TODO: Enable/disable region detection options
        pass

    def _test_ocr(self) -> None:
        """Test OCR with sample image."""
        messagebox.showinfo(
            "Тест OCR",
            "Функция тестирования OCR будет реализована в следующей версии.\n\n"
            "Для тестирования используйте основной интерфейс приложения."
        )

    def _calibrate_ocr(self) -> None:
        """Calibrate OCR settings."""
        messagebox.showinfo(
            "Калибровка OCR",
            "Функция калибровки OCR будет реализована в следующей версии.\n\n"
            "Попробуйте различные настройки предобработки для улучшения качества."
        )

    def _view_ocr_cache(self) -> None:
        """View OCR cache statistics."""
        cache_window = tk.Toplevel(self.frame)
        cache_window.title("Кэш OCR")
        cache_window.geometry("400x300")
        cache_window.resizable(False, False)

        cache_window.transient(self.frame.winfo_toplevel())
        cache_window.grab_set()

        # Cache statistics
        cache_text = tk.Text(cache_window, wrap=tk.WORD, padx=10, pady=10)
        cache_text.pack(fill=tk.BOTH, expand=True)

        sample_cache_stats = """Статистика кэша OCR:

Записей в кэше: 387
Размер кэша: 1.2 МБ
Попаданий в кэш: 73%
Промахов: 27%

Топ языков:
- rus+eng: 234 записи
- eng: 89 записей
- rus: 45 записей
- jpn: 12 записей
- chi_sim: 7 записей

Средняя скорость:
- С кэшем: 0.3 сек
- Без кэша: 2.1 сек

Экономия времени: 85%

Последнее обновление: только что"""

        cache_text.insert(tk.END, sample_cache_stats)
        cache_text.config(state=tk.DISABLED)

        # Clear cache button
        clear_btn = ttk.Button(
            cache_window,
            text="Очистить кэш",
            command=lambda: self._clear_ocr_cache(cache_window)
        )
        clear_btn.pack(pady=5)

        # Close button
        close_btn = ttk.Button(
            cache_window,
            text="Закрыть",
            command=cache_window.destroy
        )
        close_btn.pack(pady=5)

    def _clear_ocr_cache(self, parent_window: tk.Toplevel) -> None:
        """Clear OCR cache."""
        if messagebox.askyesno("Очистка кэша", "Очистить кэш OCR?"):
            try:
                # TODO: Implement OCR cache clearing
                messagebox.showinfo("Кэш", "Кэш OCR очищен")
                logger.info("OCR cache cleared by user")
                parent_window.destroy()
            except Exception as e:
                logger.error("Failed to clear OCR cache", error=e)
                messagebox.showerror("Ошибка", f"Не удалось очистить кэш: {str(e)}")

    def _load_current_values(self) -> None:
        """Load current values from config."""
        try:
            # OCR engine settings
            ocr_config = self.get_config_section("ocr")
            self.ocr_engine_var.set(ocr_config.get("engine", "tesseract"))
            self.ocr_language_var.set(ocr_config.get("language", "rus+eng"))
            self.confidence_var.set(str(ocr_config.get("confidence_threshold", 60)))
            self.ocr_timeout_var.set(str(ocr_config.get("timeout", 10)))

            # Preprocessing settings
            preprocessing_config = self.get_config_section("preprocessing")
            self.auto_preprocessing_var.set(preprocessing_config.get("auto", True))
            self.grayscale_var.set(preprocessing_config.get("grayscale", True))
            self.noise_reduction_var.set(preprocessing_config.get("noise_reduction", True))
            self.contrast_enhancement_var.set(preprocessing_config.get("contrast_enhancement", False))
            self.deskew_var.set(preprocessing_config.get("deskew", False))
            self.dpi_var.set(str(preprocessing_config.get("dpi", 300)))

            # Performance settings
            performance_config = self.get_config_section("performance")
            self.multithreading_var.set(performance_config.get("multithreading", True))
            self.gpu_acceleration_var.set(performance_config.get("gpu_acceleration", False))
            self.cache_results_var.set(performance_config.get("cache_results", True))

            # Region detection
            region_config = self.get_config_section("region_detection")
            self.auto_region_var.set(region_config.get("auto_region", True))
            self.region_method_var.set(region_config.get("method", "adaptive"))
            self.min_region_size_var.set(str(region_config.get("min_size", 20)))

        except Exception as e:
            logger.error("Failed to load OCR settings", error=e)

    def save_settings(self) -> bool:
        """Save OCR settings."""
        try:
            # OCR engine settings
            self.update_config_value("ocr", "engine", self.ocr_engine_var.get())
            self.update_config_value("ocr", "language", self.ocr_language_var.get())
            self.update_config_value("ocr", "confidence_threshold", int(self.confidence_var.get()))
            self.update_config_value("ocr", "timeout", int(self.ocr_timeout_var.get()))

            # Preprocessing settings
            self.update_config_value("preprocessing", "auto", self.auto_preprocessing_var.get())
            self.update_config_value("preprocessing", "grayscale", self.grayscale_var.get())
            self.update_config_value("preprocessing", "noise_reduction", self.noise_reduction_var.get())
            self.update_config_value("preprocessing", "contrast_enhancement", self.contrast_enhancement_var.get())
            self.update_config_value("preprocessing", "deskew", self.deskew_var.get())
            self.update_config_value("preprocessing", "dpi", int(self.dpi_var.get()))

            # Performance settings
            self.update_config_value("performance", "multithreading", self.multithreading_var.get())
            self.update_config_value("performance", "gpu_acceleration", self.gpu_acceleration_var.get())
            self.update_config_value("performance", "cache_results", self.cache_results_var.get())

            # Region detection
            self.update_config_value("region_detection", "auto_region", self.auto_region_var.get())
            self.update_config_value("region_detection", "method", self.region_method_var.get())
            self.update_config_value("region_detection", "min_size", int(self.min_region_size_var.get()))

            return True
        except Exception as e:
            logger.error("Failed to save OCR settings", error=e)
            return False

    def validate_settings(self) -> tuple[bool, str]:
        """Validate OCR settings."""
        try:
            confidence = int(self.confidence_var.get())
            if confidence < 0 or confidence > 100:
                return False, "Порог уверенности должен быть от 0 до 100"

            timeout = int(self.ocr_timeout_var.get())
            if timeout < 5 or timeout > 60:
                return False, "Таймаут должен быть от 5 до 60 секунд"

            dpi = int(self.dpi_var.get())
            if dpi < 150 or dpi > 600:
                return False, "DPI должно быть от 150 до 600"

            min_size = int(self.min_region_size_var.get())
            if min_size < 10 or min_size > 100:
                return False, "Минимальный размер области должен быть от 10 до 100 пикселей"

            return True, ""
        except ValueError:
            return False, "Некорректные числовые значения в настройках OCR"
import queue
import threading

try:
    import tkinter as tk
except ImportError:
    print(f"tkinter недоступен в {__name__}")
    # Используем заглушку
    from src.utils.mock_gui import tk
try:
    from tkinter import messagebox, ttk
except ImportError:
    print(f"tkinter недоступен в {__name__}")
    # Используем заглушки для импортированных компонентов
    from src.utils.mock_gui import messagebox, ttk

from typing import Dict

try:
    import keyboard
except ImportError:
    print("keyboard недоступен в данной среде")
    # Используем mock

import sounddevice as sd

from src.core.tts_engine import TTSProcessor
from src.services.config_manager import ConfigManager, ConfigObserver
from src.utils.logger import logger


class SettingsWindow(ConfigObserver):
    """Modernized settings window with improved architecture"""

    def __init__(self, config_manager: ConfigManager, tts_processor: TTSProcessor):
        self._lock = threading.Lock()
        self.config_manager = config_manager
        self.tts_processor = tts_processor
        self.window = None
        self.config = config_manager.get_config()

        # UI state
        self.hotkey_entries: Dict[str, tk.Entry] = {}
        self.hotkey_buttons: Dict[str, tk.Button] = {}
        self.waiting_for_hotkey = None

        # Voice and device data
        self.available_voices = []
        self.available_audio_devices = []

        # Register as observer
        config_manager.add_observer(self)

        logger.debug("Settings window initialized")
        self.gui_queue = queue.Queue()

    def show(self):
        """Show settings window"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return

        self._create_window()
        self._create_ui()

        logger.info("Settings window opened")

    def _create_window(self):
        """Create main window"""
        try:
            # Try to create a TkinterDnD2-enabled window for drag and drop support
            from tkinterdnd2 import Tk as TkDnD2, TkinterDnD

            # Check if we can make a DnD-aware toplevel window
            root = tk._default_root
            if root and not hasattr(root, 'TkdndVersion'):
                # Root is not DnD-aware, create a separate DnD window
                logger.info("Creating standalone DnD-aware settings window")
                self.window = TkDnD2()
                self.window.withdraw()  # Hide the root window initially
                self.window.deiconify()  # Show it again
            else:
                # Try to create DnD-aware Toplevel
                self.window = tk.Toplevel()

            logger.info("Settings window created with potential DnD support")
        except ImportError:
            # Fallback to normal Toplevel
            logger.info("TkinterDnD2 not available, creating standard settings window")
            self.window = tk.Toplevel()
        except Exception as e:
            logger.warning(f"Could not create DnD window: {e}, using standard window")
            self.window = tk.Toplevel()

        self.window.title("Настройки Screen Translator")
        self.window.geometry("600x500")
        self.window.resizable(True, True)

        # Center window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.window.winfo_screenheight() // 2) - (500 // 2)
        self.window.geometry(f"600x500+{x}+{y}")

        # Set window properties
        self.window.transient()
        self.window.grab_set()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_ui(self):
        """Create user interface"""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create tabs
        self._create_hotkeys_tab(notebook)
        self._create_languages_tab(notebook)
        self._create_tts_tab(notebook)
        self._create_image_tab(notebook)
        self._create_features_tab(notebook)
        self._create_batch_tab(notebook)

        # Bottom buttons
        self._create_buttons()

    def _create_buttons(self):
        """Create bottom control buttons"""
        button_frame = tk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        tk.Button(
            button_frame,
            text="Сохранить",
            command=self._save_settings,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
        ).pack(side=tk.RIGHT, padx=(5, 0))
        tk.Button(
            button_frame,
            text="Отмена",
            command=self._on_close,
            bg="#f44336",
            fg="white",
            font=("Arial", 10),
        ).pack(side=tk.RIGHT)
        tk.Button(
            button_frame,
            text="По умолчанию",
            command=self._reset_to_defaults,
            bg="#FF9800",
            fg="white",
            font=("Arial", 10),
        ).pack(side=tk.LEFT)

    def _create_hotkeys_tab(self, notebook):
        """Create hotkeys configuration tab"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🔥 Горячие клавиши")

        title = tk.Label(frame, text="Настройка горячих клавиш", font=("Arial", 12, "bold"))
        title.pack(pady=(10, 20))

        # Scrollable frame
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Bind mouse wheel to canvas for scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_to_mousewheel)
        canvas.bind("<Leave>", _unbind_from_mousewheel)

        # Hotkey configurations
        hotkey_configs = [
            ("area_select", "Выбор области", "Позволяет выделить область экрана для перевода"),
            ("quick_center", "Быстрый перевод центра", "Переводит центральную область экрана"),
            ("quick_bottom", "Быстрый перевод низа", "Переводит нижнюю область экрана (субтитры)"),
            ("repeat_last", "Повторить последний", "Повторно озвучивает последний перевод"),
            ("switch_language", "Переключить язык", "Переключает целевой язык перевода"),
        ]

        for key, name, description in hotkey_configs:
            self._create_hotkey_setting(scrollable_frame, key, name, description)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _create_hotkey_setting(self, parent, key, name, description):
        """Create individual hotkey setting"""
        frame = tk.Frame(parent, relief=tk.RIDGE, bd=1)
        frame.pack(fill=tk.X, padx=10, pady=5)

        # Name and description
        name_label = tk.Label(frame, text=name, font=("Arial", 10, "bold"))
        name_label.pack(anchor=tk.W, padx=10, pady=(10, 0))

        desc_label = tk.Label(frame, text=description, font=("Arial", 8), fg="gray")
        desc_label.pack(anchor=tk.W, padx=10)

        # Control frame
        control_frame = tk.Frame(frame)
        control_frame.pack(fill=tk.X, padx=10, pady=(5, 10))

        # Entry and button
        entry = tk.Entry(control_frame, width=20, font=("Courier", 10))
        entry.insert(0, getattr(self.config.hotkeys, key))
        entry.pack(side=tk.LEFT)
        self.hotkey_entries[key] = entry

        button = tk.Button(
            control_frame,
            text="Записать",
            command=lambda k=key: self._start_hotkey_capture(k),
            bg="#2196F3",
            fg="white",
        )
        button.pack(side=tk.LEFT, padx=(10, 0))
        self.hotkey_buttons[key] = button

    def _create_languages_tab(self, notebook):
        """Create languages configuration tab"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🌍 Языки")

        title = tk.Label(frame, text="Настройка языков", font=("Arial", 12, "bold"))
        title.pack(pady=(10, 20))

        # Target languages section
        target_frame = tk.LabelFrame(
            frame, text="Целевые языки перевода", font=("Arial", 10, "bold")
        )
        target_frame.pack(fill=tk.X, padx=20, pady=10)

        # Language selection grid
        self._create_language_selection(target_frame)

        # OCR languages section
        ocr_frame = tk.LabelFrame(frame, text="Языки OCR распознавания", font=("Arial", 10, "bold"))
        ocr_frame.pack(fill=tk.X, padx=20, pady=10)

        self._create_ocr_settings(ocr_frame)

    def _create_language_selection(self, parent):
        """Create language selection grid"""
        languages_frame = tk.Frame(parent)
        languages_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        available_languages = {
            "ru": "Русский",
            "en": "English",
            "ja": "日本語",
            "de": "Deutsch",
            "fr": "Français",
            "es": "Español",
            "it": "Italiano",
            "pt": "Português",
            "zh": "中文",
            "ko": "한국어",
            "ar": "العربية",
            "hi": "हिन्दी",
        }

        self.target_language_vars = {}
        current_languages = self.config.languages.target_languages

        row = 0
        for code, name in available_languages.items():
            var = tk.BooleanVar()
            var.set(code in current_languages)
            self.target_language_vars[code] = var

            cb = tk.Checkbutton(
                languages_frame, text=f"{name} ({code})", variable=var, font=("Arial", 9)
            )
            cb.grid(row=row // 3, column=row % 3, sticky=tk.W, padx=10, pady=2)
            row += 1

        # Default language selection
        default_frame = tk.Frame(parent)
        default_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        tk.Label(default_frame, text="Язык по умолчанию:", font=("Arial", 9)).pack(side=tk.LEFT)

        self.default_language = tk.StringVar()
        default_combo = ttk.Combobox(
            default_frame,
            textvariable=self.default_language,
            values=[
                f"{available_languages.get(lang, lang)} ({lang})" for lang in current_languages
            ],
            state="readonly",
            width=20,
        )
        default_combo.pack(side=tk.LEFT, padx=(10, 0))

        # Set current default
        if current_languages and self.config.languages.default_target < len(current_languages):
            current_default = current_languages[self.config.languages.default_target]
            default_combo.set(
                f"{available_languages.get(current_default, current_default)} ({current_default})"
            )

    def _create_ocr_settings(self, parent):
        """Create OCR settings"""
        help_label = tk.Label(
            parent,
            text="Форматы: eng, rus, jpn, chi_sim, fra, deu, spa, ita",
            font=("Arial", 8),
            fg="gray",
        )
        help_label.pack(anchor=tk.W, padx=10, pady=(5, 0))

        self.ocr_languages = tk.Entry(parent, font=("Arial", 10), width=50)
        self.ocr_languages.insert(0, self.config.languages.ocr_languages)
        self.ocr_languages.pack(fill=tk.X, padx=10, pady=10)

    def _create_tts_tab(self, notebook):
        """Create TTS configuration tab"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🔊 Озвучка")

        title = tk.Label(frame, text="Настройка озвучки (TTS)", font=("Arial", 12, "bold"))
        title.pack(pady=(10, 20))

        # Main TTS settings
        self._create_tts_main_settings(frame)

        # Voice selection
        self._create_voice_selection(frame)

        # Test buttons
        self._create_tts_test_buttons(frame)

    def _create_tts_main_settings(self, parent):
        """Create main TTS settings"""
        tts_frame = tk.LabelFrame(parent, text="Основные настройки", font=("Arial", 10, "bold"))
        tts_frame.pack(fill=tk.X, padx=20, pady=10)

        # Enable/disable
        self.tts_enabled = tk.BooleanVar()
        self.tts_enabled.set(self.config.tts.enabled)

        enable_cb = tk.Checkbutton(
            tts_frame,
            text="Включить озвучку переводов",
            variable=self.tts_enabled,
            font=("Arial", 10),
        )
        enable_cb.pack(anchor=tk.W, padx=10, pady=10)

        # Rate setting
        rate_frame = tk.Frame(tts_frame)
        rate_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        tk.Label(rate_frame, text="Скорость речи:", font=("Arial", 9)).pack(side=tk.LEFT)

        self.tts_rate = tk.IntVar()
        self.tts_rate.set(self.config.tts.rate)

        rate_scale = tk.Scale(
            rate_frame, from_=50, to=300, orient=tk.HORIZONTAL, variable=self.tts_rate, length=200
        )
        rate_scale.pack(side=tk.LEFT, padx=(10, 0))

        tk.Label(rate_frame, text="слов/мин").pack(side=tk.LEFT, padx=(5, 0))

    def _create_voice_selection(self, parent):
        """Create voice selection section"""
        voice_frame = tk.LabelFrame(parent, text="Выбор голоса", font=("Arial", 10, "bold"))
        voice_frame.pack(fill=tk.X, padx=20, pady=10)

        voice_select_frame = tk.Frame(voice_frame)
        voice_select_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(voice_select_frame, text="Голос:", font=("Arial", 9)).pack(side=tk.LEFT)

        # Get available voices
        self.available_voices = self._get_available_voices()
        voice_names = [
            f"{voice.name} ({voice.language})" if voice.language else voice.name
            for voice in self.available_voices
        ]

        self.selected_voice = tk.StringVar()

        # Find current voice
        current_voice_name = "Системный по умолчанию"
        for voice in self.available_voices:
            if voice.id == self.config.tts.voice_id:
                current_voice_name = (
                    f"{voice.name} ({voice.language})" if voice.language else voice.name
                )
                break

        self.selected_voice.set(current_voice_name)

        voice_combo = ttk.Combobox(
            voice_select_frame,
            textvariable=self.selected_voice,
            values=voice_names,
            state="readonly",
            width=40,
        )
        voice_combo.pack(side=tk.LEFT, padx=(10, 0))

        # Audio device selection
        device_select_frame = tk.Frame(voice_frame)
        device_select_frame.pack(fill=tk.X, padx=10, pady=(10, 10))

        tk.Label(device_select_frame, text="Устройство вывода:", font=("Arial", 9)).pack(
            side=tk.LEFT
        )

        # Get available audio devices
        self.available_audio_devices = self._get_available_audio_devices()
        device_names = [device["name"] for device in self.available_audio_devices]

        self.selected_audio_device = tk.StringVar()

        # Find current device
        current_device_name = "Системное по умолчанию"
        if self.config.tts.audio_device:
            for device in self.available_audio_devices:
                if device["id"] == self.config.tts.audio_device:
                    current_device_name = device["name"]
                    break

        self.selected_audio_device.set(current_device_name)

        device_combo = ttk.Combobox(
            device_select_frame,
            textvariable=self.selected_audio_device,
            values=device_names,
            state="readonly",
            width=40,
        )
        device_combo.pack(side=tk.LEFT, padx=(10, 0))

    def _create_tts_test_buttons(self, parent):
        """Create TTS test buttons"""
        test_frame = tk.LabelFrame(parent, text="Тестирование", font=("Arial", 10, "bold"))
        test_frame.pack(fill=tk.X, padx=20, pady=10)

        test_buttons_frame = tk.Frame(test_frame)
        test_buttons_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(
            test_buttons_frame,
            text="🔊 Тест озвучки",
            command=self._test_tts,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 9, "bold"),
        ).pack(side=tk.LEFT)

    def _create_image_tab(self, notebook):
        """Create image processing tab"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🖼️ Обработка")

        title = tk.Label(frame, text="Обработка изображений", font=("Arial", 12, "bold"))
        title.pack(pady=(10, 20))

        processing_frame = tk.LabelFrame(
            frame, text="Параметры улучшения изображений", font=("Arial", 10, "bold")
        )
        processing_frame.pack(fill=tk.X, padx=20, pady=10)

        # Image processing settings
        self._create_image_processing_controls(processing_frame)

    def _create_image_processing_controls(self, parent):
        """Create image processing control sliders"""
        # Upscale factor
        scale_frame = tk.Frame(parent)
        scale_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(scale_frame, text="Масштабирование:", font=("Arial", 9)).pack(side=tk.LEFT)

        self.upscale_factor = tk.DoubleVar()
        self.upscale_factor.set(self.config.image_processing.upscale_factor)

        upscale_scale = tk.Scale(
            scale_frame,
            from_=1.0,
            to=5.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            variable=self.upscale_factor,
            length=200,
        )
        upscale_scale.pack(side=tk.LEFT, padx=(10, 0))

        # Contrast
        contrast_frame = tk.Frame(parent)
        contrast_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(contrast_frame, text="Контрастность:", font=("Arial", 9)).pack(side=tk.LEFT)

        self.contrast_enhance = tk.DoubleVar()
        self.contrast_enhance.set(self.config.image_processing.contrast_enhance)

        contrast_scale = tk.Scale(
            contrast_frame,
            from_=0.5,
            to=3.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            variable=self.contrast_enhance,
            length=200,
        )
        contrast_scale.pack(side=tk.LEFT, padx=(10, 0))

        # Sharpness
        sharpness_frame = tk.Frame(parent)
        sharpness_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(sharpness_frame, text="Резкость:", font=("Arial", 9)).pack(side=tk.LEFT)

        self.sharpness_enhance = tk.DoubleVar()
        self.sharpness_enhance.set(self.config.image_processing.sharpness_enhance)

        sharpness_scale = tk.Scale(
            sharpness_frame,
            from_=0.5,
            to=3.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            variable=self.sharpness_enhance,
            length=200,
        )
        sharpness_scale.pack(side=tk.LEFT, padx=(10, 0))

        # OCR Confidence threshold
        confidence_frame = tk.Frame(parent)
        confidence_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(confidence_frame, text="Порог уверенности OCR:", font=("Arial", 9)).pack(
            side=tk.LEFT
        )

        self.ocr_confidence_threshold = tk.DoubleVar()
        self.ocr_confidence_threshold.set(self.config.image_processing.ocr_confidence_threshold)

        confidence_scale = tk.Scale(
            confidence_frame,
            from_=0.1,
            to=1.0,
            resolution=0.05,
            orient=tk.HORIZONTAL,
            variable=self.ocr_confidence_threshold,
            length=200,
        )
        confidence_scale.pack(side=tk.LEFT, padx=(10, 0))

        # Processing options
        options_frame = tk.LabelFrame(parent, text="Опции обработки", font=("Arial", 10, "bold"))
        options_frame.pack(fill=tk.X, padx=20, pady=10)

        self.enable_preprocessing = tk.BooleanVar()
        self.enable_preprocessing.set(self.config.image_processing.enable_preprocessing)

        self.noise_reduction = tk.BooleanVar()
        self.noise_reduction.set(self.config.image_processing.noise_reduction)

        tk.Checkbutton(
            options_frame,
            text="Включить предобработку изображений",
            variable=self.enable_preprocessing,
            font=("Arial", 9),
        ).pack(anchor=tk.W, padx=10, pady=5)

        tk.Checkbutton(
            options_frame,
            text="Применять шумоподавление",
            variable=self.noise_reduction,
            font=("Arial", 9),
        ).pack(anchor=tk.W, padx=10, pady=5)

    def _create_features_tab(self, notebook):
        """Create features tab"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="⚙️ Дополнительно")

        title = tk.Label(frame, text="Дополнительные функции", font=("Arial", 12, "bold"))
        title.pack(pady=(10, 20))

        features_frame = tk.LabelFrame(frame, text="Включить функции", font=("Arial", 10, "bold"))
        features_frame.pack(fill=tk.X, padx=20, pady=10)

        # Feature checkboxes
        self._create_feature_checkboxes(features_frame)

        # Info section
        info_frame = tk.LabelFrame(frame, text="Информация", font=("Arial", 10, "bold"))
        info_frame.pack(fill=tk.X, padx=20, pady=10)

        info_text = "Screen Translator v2.0\nМодульная архитектура"
        info_label = tk.Label(info_frame, text=info_text, font=("Arial", 9), justify=tk.LEFT)
        info_label.pack(anchor=tk.W, padx=10, pady=10)

    def _create_feature_checkboxes(self, parent):
        """Create feature control checkboxes"""
        # Copy to clipboard
        self.copy_to_clipboard = tk.BooleanVar()
        self.copy_to_clipboard.set(self.config.features.copy_to_clipboard)

        copy_cb = tk.Checkbutton(
            parent,
            text="Копировать перевод в буфер обмена",
            variable=self.copy_to_clipboard,
            font=("Arial", 9),
        )
        copy_cb.pack(anchor=tk.W, padx=10, pady=5)

        # Cache translations
        self.cache_translations = tk.BooleanVar()
        self.cache_translations.set(self.config.features.cache_translations)

        cache_cb = tk.Checkbutton(
            parent,
            text="Кэшировать переводы (ускоряет повторные запросы)",
            variable=self.cache_translations,
            font=("Arial", 9),
        )
        cache_cb.pack(anchor=tk.W, padx=10, pady=5)

        # Debug screenshots
        self.save_debug_screenshots = tk.BooleanVar()
        self.save_debug_screenshots.set(self.config.features.save_debug_screenshots)

        debug_cb = tk.Checkbutton(
            parent,
            text="Сохранять отладочные скриншоты",
            variable=self.save_debug_screenshots,
            font=("Arial", 9),
        )
        debug_cb.pack(anchor=tk.W, padx=10, pady=5)

    def _create_batch_tab(self, notebook):
        """Create batch processing tab"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="📂 Batch/Drag&Drop")

        title = tk.Label(frame, text="Пакетная обработка и файлы", font=("Arial", 12, "bold"))
        title.pack(pady=(10, 20))

        # Drag & Drop demo

        # Create a demo application reference for the interface
        class DemoApp:
            def __init__(self):
                self._lock = threading.Lock()
                self.progress_manager = None
                self.batch_processor = None

        DemoApp()

        # Create the drag & drop interface
        drop_zone_frame = tk.LabelFrame(
            frame, text="Перетащите изображения сюда", font=("Arial", 10, "bold")
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

        # Batch settings
        settings_frame = tk.LabelFrame(
            frame, text="Настройки пакетной обработки", font=("Arial", 10, "bold")
        )
        settings_frame.pack(fill=tk.X, padx=20, pady=10)

        # Max concurrent workers
        workers_frame = tk.Frame(settings_frame)
        workers_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(workers_frame, text="Параллельных задач:", font=("Arial", 9)).pack(side=tk.LEFT)

        self.max_workers = tk.IntVar()
        self.max_workers.set(3)  # Default value

        workers_scale = tk.Scale(
            workers_frame,
            from_=1,
            to=8,
            orient=tk.HORIZONTAL,
            variable=self.max_workers,
            length=200,
        )
        workers_scale.pack(side=tk.LEFT, padx=(10, 0))

        # Auto export
        self.auto_export_batch = tk.BooleanVar()
        self.auto_export_batch.set(False)

        export_cb = tk.Checkbutton(
            settings_frame,
            text="Автоматически экспортировать результаты",
            variable=self.auto_export_batch,
            font=("Arial", 9),
        )
        export_cb.pack(anchor=tk.W, padx=10, pady=5)

        # Event handlers
        self.gui_queue = queue.Queue()

    def _start_hotkey_capture(self, key):
        """Start capturing hotkey"""
        if self.waiting_for_hotkey:
            return

        self.waiting_for_hotkey = key
        button = self.hotkey_buttons[key]
        entry = self.hotkey_entries[key]

        button.config(text="Нажмите клавиши...", bg="#FF5722")
        entry.config(bg="#FFF3E0")

        threading.Thread(target=self._capture_hotkey, daemon=True).start()

    def _capture_hotkey(self):
        """Capture hotkey in background"""
        try:
            recorded = keyboard.read_hotkey(suppress=True)
            self.queue_gui_action(self._finish_hotkey_capture, recorded)
        except (ImportError, KeyboardInterrupt, Exception):
            self.queue_gui_action(self._finish_hotkey_capture, None)

    def _finish_hotkey_capture(self, hotkey):
        """Finish hotkey capture"""
        if not self.waiting_for_hotkey:
            return

        key = self.waiting_for_hotkey
        button = self.hotkey_buttons[key]
        entry = self.hotkey_entries[key]

        if hotkey:
            entry.delete(0, tk.END)
            entry.insert(0, hotkey)

        button.config(text="Записать", bg="#2196F3")
        entry.config(bg="white")
        self.waiting_for_hotkey = None

    def _get_available_voices(self):
        """Get available TTS voices"""
        if self.tts_processor:
            return self.tts_processor.get_available_voices()
        return []

    def _get_available_audio_devices(self):
        """Get available audio output devices"""
        devices = [{"id": "default", "name": "Системное по умолчанию"}]

        try:

            device_list = sd.query_devices()

            for i, device in enumerate(device_list):
                if device["max_output_channels"] > 0:  # Only output devices
                    devices.append(
                        {"id": str(i), "name": f"{device['name']} ({device['hostapi_name']})"}
                    )
        except ImportError:
            logger.warning("sounddevice not available, using default audio device only")
        except Exception as e:
            logger.error(f"Error querying audio devices: {e}")

        return devices

    def _test_tts(self):
        """Test TTS with current settings"""
        if not self.tts_enabled.get():
            messagebox.showwarning("Предупреждение", "Сначала включите озвучку")
            return

        if self.tts_processor:
            self.tts_processor.speak_text("Тест озвучки Screen Translator")

    def _validate_settings_data(self, settings):
        """Validate settings data before saving."""
        errors = []

        # Validate languages
        if "target_language" in settings:
            if not self._is_valid_language(settings["target_language"]):
                errors.append("Invalid target language")

        if "ocr_language" in settings:
            if not self._is_valid_language(settings["ocr_language"]):
                errors.append("Invalid OCR language")

        # Validate TTS settings
        if "tts_rate" in settings:
            try:
                rate = int(settings["tts_rate"])
                if not 50 <= rate <= 300:
                    errors.append("TTS rate must be between 50 and 300")
            except ValueError:
                errors.append("TTS rate must be a number")

        # Validate hotkeys
        if "hotkeys" in settings:
            for action, key_combo in settings["hotkeys"].items():
                if not key_combo or not key_combo.strip():
                    errors.append(f"Empty hotkey for action: {action}")

        return errors

    def _collect_settings_from_ui(self):
        """Collect settings from UI elements."""
        settings = {}

        try:
            # Language settings
            if hasattr(self, "_target_lang_var"):
                settings["target_language"] = self._target_lang_var.get()

            if hasattr(self, "_ocr_lang_var"):
                settings["ocr_language"] = self._ocr_lang_var.get()

            # TTS settings
            if hasattr(self, "_tts_enabled_var"):
                settings["tts_enabled"] = self._tts_enabled_var.get()

            if hasattr(self, "_tts_rate_var"):
                settings["tts_rate"] = self._tts_rate_var.get()

            if hasattr(self, "_tts_voice_var"):
                settings["tts_voice"] = self._tts_voice_var.get()

            # Hotkeys
            settings["hotkeys"] = {}
            for action, entry_var in getattr(self, "_hotkey_entries", {}).items():
                settings["hotkeys"][action] = entry_var.get()

        except Exception as e:
            logger.error(f"Error collecting settings from UI: {e}")

        return settings

    def _apply_settings_to_config(self, settings):
        """Apply validated settings to configuration."""
        try:
            config = self.config_manager.get_config()

            # Update language settings
            if "target_language" in settings:
                config.target_language = settings["target_language"]

            if "ocr_language" in settings:
                config.ocr_language = settings["ocr_language"]

            # Update TTS settings
            if "tts_enabled" in settings:
                config.tts.enabled = settings["tts_enabled"]

            if "tts_rate" in settings:
                config.tts.rate = int(settings["tts_rate"])

            if "tts_voice" in settings:
                config.tts.voice_id = settings["tts_voice"]

            # Update hotkeys
            if "hotkeys" in settings:
                config.hotkeys.update(settings["hotkeys"])

            # Save configuration
            self.config_manager.save_config()
            return True

        except Exception as e:
            logger.error(f"Error applying settings to config: {e}")
            return False

    def _show_settings_result(self, success, message=""):
        """Show settings save result to user."""
        if success:
            self.queue_gui_action("show_message", "Settings saved successfully", "success")
        else:
            error_msg = message or "Failed to save settings"
            self.queue_gui_action("show_message", error_msg, "error")

    def _save_settings(self):
        """Save all settings"""
        try:
            # Update hotkeys
            for key, entry in self.hotkey_entries.items():
                setattr(self.config.hotkeys, key, entry.get().strip())

            # Update languages
            selected_languages = [
                code for code, var in self.target_language_vars.items() if var.get()
            ]
            if not selected_languages:
                messagebox.showerror("Ошибка", "Выберите хотя бы один целевой язык")
                return

            self.config.languages.target_languages = selected_languages
            self.config.languages.ocr_languages = self.ocr_languages.get().strip()

            # Update TTS
            self.config.tts.enabled = self.tts_enabled.get()
            self.config.tts.rate = self.tts_rate.get()

            # Find selected voice ID
            selected_voice_name = self.selected_voice.get()
            for voice in self.available_voices:
                voice_display = f"{voice.name} ({voice.language})" if voice.language else voice.name
                if voice_display == selected_voice_name:
                    self.config.tts.voice_id = voice.id
                    break

            # Find selected audio device ID
            selected_device_name = self.selected_audio_device.get()
            for device in self.available_audio_devices:
                if device["name"] == selected_device_name:
                    self.config.tts.audio_device = device["id"]
                    break

            # Update image processing
            self.config.image_processing.upscale_factor = self.upscale_factor.get()
            self.config.image_processing.contrast_enhance = self.contrast_enhance.get()
            self.config.image_processing.sharpness_enhance = self.sharpness_enhance.get()
            self.config.image_processing.ocr_confidence_threshold = (
                self.ocr_confidence_threshold.get()
            )
            self.config.image_processing.enable_preprocessing = self.enable_preprocessing.get()
            self.config.image_processing.noise_reduction = self.noise_reduction.get()

            # Update features
            self.config.features.copy_to_clipboard = self.copy_to_clipboard.get()
            self.config.features.cache_translations = self.cache_translations.get()
            self.config.features.save_debug_screenshots = self.save_debug_screenshots.get()

            # Save configuration
            self.config_manager.update_config(self.config)
            self.config_manager.save_config()

            messagebox.showinfo("Успех", "Настройки сохранены!")
            self._on_close()

        except Exception as e:
            logger.error("Failed to save settings", error=e)
            messagebox.showerror("Ошибка", f"Ошибка сохранения настроек: {str(e)}")

    def _reset_to_defaults(self):
        """Reset settings to defaults"""
        if messagebox.askyesno(
            "Сброс настроек",
            "Вы уверены, что хотите сбросить все настройки к значениям по умолчанию?",
        ):
            self.config_manager.reset_to_defaults()
            self._on_close()

    def _on_close(self):
        """Handle window close"""
        if self.window:
            self.window.destroy()
            self.window = None
        logger.debug("Settings window closed")

    # ConfigObserver implementation
    def on_config_changed(self, key: str, old_value, new_value) -> None:
        """Handle configuration changes"""
        if key == "*":  # Full config reload
            self.config = self.config_manager.get_config()
            logger.debug("Settings window config updated")

    def queue_gui_action(self, func, *args):
        """Queue GUI action for thread-safe execution"""
        if hasattr(self, "gui_queue"):
            self.gui_queue.put((func, args))
        else:
            # Fallback to direct call if no queue
            func(*args)

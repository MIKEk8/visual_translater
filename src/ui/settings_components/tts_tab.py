"""TTS (Text-to-Speech) settings tab component."""

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except ImportError:
    from src.utils.mock_gui import tk, ttk, messagebox

from .base_settings_tab import BaseSettingsTab
from src.utils.logger import logger


class TTSTab(BaseSettingsTab):
    """TTS configuration tab."""

    def __init__(self, parent: ttk.Notebook, config_manager, tts_processor=None):
        super().__init__(parent, config_manager, "TTS")
        self.tts_processor = tts_processor

    def _create_components(self) -> None:
        """Create TTS settings components."""
        self._create_engine_settings()
        self._create_voice_settings()
        self._create_playback_settings()
        self._create_advanced_settings()

    def _create_engine_settings(self) -> None:
        """Create TTS engine settings section."""
        frame = self.create_labeled_frame(self.frame, "Движок TTS")

        # TTS Engine selection
        engine_frame = ttk.Frame(frame)
        engine_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(engine_frame, text="TTS движок:").pack(side=tk.LEFT)

        self.tts_engine_var = tk.StringVar(value="pyttsx3")
        engine_combo = ttk.Combobox(
            engine_frame,
            textvariable=self.tts_engine_var,
            values=["pyttsx3", "windows_sapi", "espeak", "festival", "google_tts", "azure_tts"],
            state="readonly",
            width=15
        )
        engine_combo.pack(side=tk.RIGHT)
        engine_combo.bind("<<ComboboxSelected>>", self._on_engine_changed)

        # Enable TTS
        self.enable_tts_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Включить озвучивание переводов",
            variable=self.enable_tts_var,
            command=self._on_tts_enabled_changed
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Auto-play on translation
        self.auto_play_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Автоматически озвучивать переводы",
            variable=self.auto_play_var
        ).pack(anchor=tk.W, padx=10, pady=5)

    def _create_voice_settings(self) -> None:
        """Create voice settings section."""
        frame = self.create_labeled_frame(self.frame, "Настройки голоса")

        # Voice selection
        voice_frame = ttk.Frame(frame)
        voice_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(voice_frame, text="Голос:").pack(side=tk.LEFT)

        self.voice_var = tk.StringVar(value="default")
        self.voice_combo = ttk.Combobox(
            voice_frame,
            textvariable=self.voice_var,
            values=["default", "male", "female"],
            state="readonly",
            width=15
        )
        self.voice_combo.pack(side=tk.RIGHT)

        # Language for TTS
        lang_frame = ttk.Frame(frame)
        lang_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(lang_frame, text="Язык озвучивания:").pack(side=tk.LEFT)

        self.tts_language_var = tk.StringVar(value="ru")
        lang_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.tts_language_var,
            values=["ru", "en", "zh", "ja", "ko", "fr", "de", "es", "auto"],
            state="readonly",
            width=15
        )
        lang_combo.pack(side=tk.RIGHT)

        # Speed
        speed_frame = ttk.Frame(frame)
        speed_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(speed_frame, text="Скорость:").pack(side=tk.LEFT)

        self.speed_var = tk.StringVar(value="150")
        speed_scale = tk.Scale(
            speed_frame,
            from_=50,
            to=300,
            orient=tk.HORIZONTAL,
            variable=self.speed_var,
            length=150,
            resolution=10
        )
        speed_scale.pack(side=tk.RIGHT)

        # Volume
        volume_frame = ttk.Frame(frame)
        volume_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(volume_frame, text="Громкость:").pack(side=tk.LEFT)

        self.volume_var = tk.StringVar(value="70")
        volume_scale = tk.Scale(
            volume_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.volume_var,
            length=150
        )
        volume_scale.pack(side=tk.RIGHT)

        # Pitch
        pitch_frame = ttk.Frame(frame)
        pitch_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(pitch_frame, text="Высота тона:").pack(side=tk.LEFT)

        self.pitch_var = tk.StringVar(value="50")
        pitch_scale = tk.Scale(
            pitch_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.pitch_var,
            length=150
        )
        pitch_scale.pack(side=tk.RIGHT)

    def _create_playback_settings(self) -> None:
        """Create playback settings section."""
        frame = self.create_labeled_frame(self.frame, "Воспроизведение")

        # Output device
        device_frame = ttk.Frame(frame)
        device_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(device_frame, text="Устройство вывода:").pack(side=tk.LEFT)

        self.output_device_var = tk.StringVar(value="default")
        self.device_combo = ttk.Combobox(
            device_frame,
            textvariable=self.output_device_var,
            values=["default", "speakers", "headphones"],
            state="readonly",
            width=15
        )
        self.device_combo.pack(side=tk.RIGHT)

        # Audio format
        format_frame = ttk.Frame(frame)
        format_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(format_frame, text="Формат аудио:").pack(side=tk.LEFT)

        self.audio_format_var = tk.StringVar(value="WAV")
        format_combo = ttk.Combobox(
            format_frame,
            textvariable=self.audio_format_var,
            values=["WAV", "MP3", "OGG"],
            state="readonly",
            width=10
        )
        format_combo.pack(side=tk.RIGHT)

        # Sample rate
        rate_frame = ttk.Frame(frame)
        rate_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(rate_frame, text="Частота дискретизации:").pack(side=tk.LEFT)

        self.sample_rate_var = tk.StringVar(value="22050")
        rate_combo = ttk.Combobox(
            rate_frame,
            textvariable=self.sample_rate_var,
            values=["16000", "22050", "44100", "48000"],
            state="readonly",
            width=10
        )
        rate_combo.pack(side=tk.RIGHT)

        # Save audio files
        self.save_audio_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Сохранять аудиофайлы",
            variable=self.save_audio_var
        ).pack(anchor=tk.W, padx=10, pady=5)

    def _create_advanced_settings(self) -> None:
        """Create advanced TTS settings."""
        frame = self.create_labeled_frame(self.frame, "Дополнительные настройки")

        # Text preprocessing
        self.preprocess_text_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Предобработка текста (удаление спецсимволов)",
            variable=self.preprocess_text_var
        ).pack(anchor=tk.W, padx=10, pady=5)

        # SSML support
        self.ssml_support_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Поддержка SSML разметки",
            variable=self.ssml_support_var
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Emotional voice
        self.emotional_voice_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Эмоциональное озвучивание",
            variable=self.emotional_voice_var
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Text length limit
        length_frame = ttk.Frame(frame)
        length_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(length_frame, text="Макс. длина текста:").pack(side=tk.LEFT)

        self.max_text_length_var = tk.StringVar(value="500")
        length_spinbox = tk.Spinbox(
            length_frame,
            from_=100,
            to=2000,
            increment=100,
            width=8,
            textvariable=self.max_text_length_var
        )
        length_spinbox.pack(side=tk.RIGHT)

        # Pause between sentences
        pause_frame = ttk.Frame(frame)
        pause_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(pause_frame, text="Пауза между предложениями (мс):").pack(side=tk.LEFT)

        self.sentence_pause_var = tk.StringVar(value="300")
        pause_spinbox = tk.Spinbox(
            pause_frame,
            from_=0,
            to=2000,
            increment=100,
            width=8,
            textvariable=self.sentence_pause_var
        )
        pause_spinbox.pack(side=tk.RIGHT)

        # Action buttons
        self._create_action_buttons(frame)

    def _create_action_buttons(self, parent: tk.Widget) -> None:
        """Create action buttons."""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        # Test TTS
        test_btn = ttk.Button(
            button_frame,
            text="Тест голоса",
            command=self._test_tts
        )
        test_btn.pack(side=tk.LEFT, padx=5)

        # Refresh voices
        refresh_btn = ttk.Button(
            button_frame,
            text="Обновить голоса",
            command=self._refresh_voices
        )
        refresh_btn.pack(side=tk.LEFT, padx=5)

        # Voice manager
        manager_btn = ttk.Button(
            button_frame,
            text="Менеджер голосов",
            command=self._open_voice_manager
        )
        manager_btn.pack(side=tk.RIGHT, padx=5)

    def _on_engine_changed(self, event=None) -> None:
        """Handle TTS engine change."""
        self._refresh_voices()

    def _on_tts_enabled_changed(self) -> None:
        """Handle TTS enabled/disabled change."""
        # TODO: Enable/disable other TTS controls
        pass

    def _test_tts(self) -> None:
        """Test TTS with sample text."""
        test_text = "Привет! Это тест голосового движка. Hello! This is a voice engine test."

        try:
            if self.tts_processor:
                # Use actual TTS processor if available
                self.tts_processor.speak(test_text)
                messagebox.showinfo("Тест TTS", "Воспроизводится тестовое сообщение")
            else:
                messagebox.showinfo(
                    "Тест TTS",
                    f"Тест голоса:\n\n{test_text}\n\n"
                    "Движок: " + self.tts_engine_var.get() + "\n"
                    "Голос: " + self.voice_var.get() + "\n"
                    "Скорость: " + self.speed_var.get() + "\n"
                    "Громкость: " + self.volume_var.get()
                )
        except Exception as e:
            logger.error("TTS test failed", error=e)
            messagebox.showerror("Ошибка TTS", f"Не удалось протестировать TTS: {str(e)}")

    def _refresh_voices(self) -> None:
        """Refresh available voices list."""
        try:
            # TODO: Get actual available voices from TTS engine
            engine = self.tts_engine_var.get()

            if engine == "pyttsx3":
                voices = ["default", "male", "female", "Microsoft David", "Microsoft Zira"]
            elif engine == "windows_sapi":
                voices = ["default", "Microsoft David", "Microsoft Zira", "Microsoft Hazel"]
            elif engine == "google_tts":
                voices = ["default", "en-US-Wavenet-A", "en-US-Wavenet-B", "ru-RU-Wavenet-A"]
            else:
                voices = ["default", "male", "female"]

            self.voice_combo.config(values=voices)

            # Update output devices
            devices = ["default", "speakers", "headphones", "bluetooth"]
            self.device_combo.config(values=devices)

            logger.info(f"Refreshed voices for {engine}")

        except Exception as e:
            logger.error("Failed to refresh voices", error=e)
            messagebox.showerror("Ошибка", f"Не удалось обновить список голосов: {str(e)}")

    def _open_voice_manager(self) -> None:
        """Open voice manager window."""
        manager_window = tk.Toplevel(self.frame)
        manager_window.title("Менеджер голосов")
        manager_window.geometry("500x400")
        manager_window.resizable(True, True)

        manager_window.transient(self.frame.winfo_toplevel())
        manager_window.grab_set()

        # Voice list
        list_frame = ttk.Frame(manager_window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(list_frame, text="Доступные голоса:", font=("Arial", 10, "bold")).pack(anchor=tk.W)

        # Listbox with scrollbar
        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        voice_listbox = tk.Listbox(listbox_frame)
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=voice_listbox.yview)
        voice_listbox.config(yscrollcommand=scrollbar.set)

        voice_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Sample voices data
        sample_voices = [
            "Microsoft David (En-US, Male)",
            "Microsoft Zira (En-US, Female)",
            "Microsoft Hazel (En-GB, Female)",
            "Google Wavenet A (En-US, Male)",
            "Google Wavenet B (En-US, Female)",
            "Yandex SpeechKit (Ru-RU, Female)",
            "Amazon Polly Matthew (En-US, Male)"
        ]

        for voice in sample_voices:
            voice_listbox.insert(tk.END, voice)

        # Voice details
        details_frame = ttk.LabelFrame(list_frame, text="Информация о голосе")
        details_frame.pack(fill=tk.X, pady=5)

        details_text = tk.Text(details_frame, height=6, wrap=tk.WORD)
        details_text.pack(fill=tk.X, padx=5, pady=5)

        sample_details = """Голос: Microsoft David
Язык: Английский (США)
Пол: Мужской
Качество: Высокое
Размер: 15 МБ
Статус: Установлен"""

        details_text.insert(tk.END, sample_details)
        details_text.config(state=tk.DISABLED)

        # Buttons
        button_frame = ttk.Frame(manager_window)
        button_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(
            button_frame,
            text="Скачать голос",
            command=lambda: messagebox.showinfo("Скачивание", "Функция скачивания голосов будет добавлена")
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Удалить голос",
            command=lambda: messagebox.showinfo("Удаление", "Функция удаления голосов будет добавлена")
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Закрыть",
            command=manager_window.destroy
        ).pack(side=tk.RIGHT, padx=5)

    def _load_current_values(self) -> None:
        """Load current values from config."""
        try:
            # TTS engine settings
            tts_config = self.get_config_section("tts")
            self.tts_engine_var.set(tts_config.get("engine", "pyttsx3"))
            self.enable_tts_var.set(tts_config.get("enabled", True))
            self.auto_play_var.set(tts_config.get("auto_play", False))

            # Voice settings
            voice_config = self.get_config_section("voice")
            self.voice_var.set(voice_config.get("voice", "default"))
            self.tts_language_var.set(voice_config.get("language", "ru"))
            self.speed_var.set(str(voice_config.get("speed", 150)))
            self.volume_var.set(str(voice_config.get("volume", 70)))
            self.pitch_var.set(str(voice_config.get("pitch", 50)))

            # Playback settings
            playback_config = self.get_config_section("playback")
            self.output_device_var.set(playback_config.get("output_device", "default"))
            self.audio_format_var.set(playback_config.get("audio_format", "WAV"))
            self.sample_rate_var.set(str(playback_config.get("sample_rate", 22050)))
            self.save_audio_var.set(playback_config.get("save_audio", False))

            # Advanced settings
            advanced_config = self.get_config_section("advanced_tts")
            self.preprocess_text_var.set(advanced_config.get("preprocess_text", True))
            self.ssml_support_var.set(advanced_config.get("ssml_support", False))
            self.emotional_voice_var.set(advanced_config.get("emotional_voice", False))
            self.max_text_length_var.set(str(advanced_config.get("max_text_length", 500)))
            self.sentence_pause_var.set(str(advanced_config.get("sentence_pause", 300)))

        except Exception as e:
            logger.error("Failed to load TTS settings", error=e)

    def save_settings(self) -> bool:
        """Save TTS settings."""
        try:
            # TTS engine settings
            self.update_config_value("tts", "engine", self.tts_engine_var.get())
            self.update_config_value("tts", "enabled", self.enable_tts_var.get())
            self.update_config_value("tts", "auto_play", self.auto_play_var.get())

            # Voice settings
            self.update_config_value("voice", "voice", self.voice_var.get())
            self.update_config_value("voice", "language", self.tts_language_var.get())
            self.update_config_value("voice", "speed", int(self.speed_var.get()))
            self.update_config_value("voice", "volume", int(self.volume_var.get()))
            self.update_config_value("voice", "pitch", int(self.pitch_var.get()))

            # Playback settings
            self.update_config_value("playback", "output_device", self.output_device_var.get())
            self.update_config_value("playback", "audio_format", self.audio_format_var.get())
            self.update_config_value("playback", "sample_rate", int(self.sample_rate_var.get()))
            self.update_config_value("playback", "save_audio", self.save_audio_var.get())

            # Advanced settings
            self.update_config_value("advanced_tts", "preprocess_text", self.preprocess_text_var.get())
            self.update_config_value("advanced_tts", "ssml_support", self.ssml_support_var.get())
            self.update_config_value("advanced_tts", "emotional_voice", self.emotional_voice_var.get())
            self.update_config_value("advanced_tts", "max_text_length", int(self.max_text_length_var.get()))
            self.update_config_value("advanced_tts", "sentence_pause", int(self.sentence_pause_var.get()))

            return True
        except Exception as e:
            logger.error("Failed to save TTS settings", error=e)
            return False

    def validate_settings(self) -> tuple[bool, str]:
        """Validate TTS settings."""
        try:
            speed = int(self.speed_var.get())
            if speed < 50 or speed > 300:
                return False, "Скорость речи должна быть от 50 до 300"

            volume = int(self.volume_var.get())
            if volume < 0 or volume > 100:
                return False, "Громкость должна быть от 0 до 100"

            pitch = int(self.pitch_var.get())
            if pitch < 0 or pitch > 100:
                return False, "Высота тона должна быть от 0 до 100"

            max_length = int(self.max_text_length_var.get())
            if max_length < 100 or max_length > 2000:
                return False, "Максимальная длина текста должна быть от 100 до 2000 символов"

            pause = int(self.sentence_pause_var.get())
            if pause < 0 or pause > 2000:
                return False, "Пауза между предложениями должна быть от 0 до 2000 мс"

            return True, ""
        except ValueError:
            return False, "Некорректные числовые значения в настройках TTS"
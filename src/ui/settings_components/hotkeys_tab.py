"""Hotkeys settings tab component."""

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except ImportError:
    from src.utils.mock_gui import tk, ttk, messagebox

try:
    import keyboard
except ImportError:
    keyboard = None

from typing import Dict, Optional
from .base_settings_tab import BaseSettingsTab
from src.utils.logger import logger


class HotkeysTab(BaseSettingsTab):
    """Hotkeys configuration tab."""

    def __init__(self, parent: ttk.Notebook, config_manager, tts_processor=None):
        super().__init__(parent, config_manager, "Горячие клавиши")

        # Hotkey management
        self.hotkey_entries: Dict[str, tk.Entry] = {}
        self.hotkey_buttons: Dict[str, tk.Button] = {}
        self.waiting_for_hotkey: Optional[str] = None

    def _create_components(self) -> None:
        """Create hotkey configuration components."""
        # Main scroll area
        canvas = tk.Canvas(self.frame)
        scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack scroll components
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Hotkey sections
        self._create_main_hotkeys_section(scrollable_frame)
        self._create_quick_actions_section(scrollable_frame)
        self._create_system_hotkeys_section(scrollable_frame)

        # Buttons frame
        self._create_action_buttons(scrollable_frame)

    def _create_main_hotkeys_section(self, parent: tk.Widget) -> None:
        """Create main hotkeys section."""
        frame = self.create_labeled_frame(parent, "Основные действия")

        hotkeys = [
            ("translate_selection", "Перевести выделенную область", "Alt+A"),
            ("quick_translate_center", "Быстрый перевод (центр)", "Alt+Q"),
            ("quick_translate_bottom", "Быстрый перевод (субтитры)", "Alt+W"),
            ("repeat_last", "Повторить последний перевод", "Alt+S"),
            ("switch_language", "Переключить язык", "Alt+L"),
        ]

        for key, description, default in hotkeys:
            self._create_hotkey_row(frame, key, description, default)

    def _create_quick_actions_section(self, parent: tk.Widget) -> None:
        """Create quick actions section."""
        frame = self.create_labeled_frame(parent, "Быстрые действия")

        hotkeys = [
            ("show_history", "Показать историю", "Alt+H"),
            ("show_settings", "Открыть настройки", "Alt+Comma"),
            ("toggle_overlay", "Показать/скрыть оверлей", "Alt+O"),
        ]

        for key, description, default in hotkeys:
            self._create_hotkey_row(frame, key, description, default)

    def _create_system_hotkeys_section(self, parent: tk.Widget) -> None:
        """Create system hotkeys section."""
        frame = self.create_labeled_frame(parent, "Системные")

        hotkeys = [
            ("emergency_stop", "Экстренная остановка", "Ctrl+Alt+X"),
            ("pause_translation", "Пауза/возобновить", "Ctrl+Alt+P"),
        ]

        for key, description, default in hotkeys:
            self._create_hotkey_row(frame, key, description, default)

    def _create_hotkey_row(self, parent: tk.Widget, key: str, description: str, default: str) -> None:
        """Create a hotkey configuration row."""
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, padx=5, pady=2)

        # Description label
        desc_label = ttk.Label(row_frame, text=description, width=25)
        desc_label.pack(side=tk.LEFT, anchor=tk.W)

        # Hotkey entry
        entry = ttk.Entry(row_frame, width=15, state='readonly')
        entry.pack(side=tk.LEFT, padx=(10, 5))
        self.hotkey_entries[key] = entry

        # Set hotkey button
        button = ttk.Button(
            row_frame,
            text="Задать",
            width=8,
            command=lambda k=key: self._start_hotkey_capture(k)
        )
        button.pack(side=tk.LEFT, padx=5)
        self.hotkey_buttons[key] = button

        # Clear button
        clear_btn = ttk.Button(
            row_frame,
            text="Очистить",
            width=8,
            command=lambda k=key: self._clear_hotkey(k)
        )
        clear_btn.pack(side=tk.LEFT, padx=5)

        # Reset to default
        reset_btn = ttk.Button(
            row_frame,
            text="По умолчанию",
            width=12,
            command=lambda k=key, d=default: self._set_default_hotkey(k, d)
        )
        reset_btn.pack(side=tk.RIGHT, padx=5)

    def _create_action_buttons(self, parent: tk.Widget) -> None:
        """Create action buttons."""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        # Test hotkeys button
        test_btn = ttk.Button(
            button_frame,
            text="Тестировать горячие клавиши",
            command=self._test_hotkeys
        )
        test_btn.pack(side=tk.LEFT, padx=5)

        # Reset all button
        reset_btn = ttk.Button(
            button_frame,
            text="Сбросить все",
            command=self._reset_all_hotkeys
        )
        reset_btn.pack(side=tk.RIGHT, padx=5)

    def _start_hotkey_capture(self, key: str) -> None:
        """Start capturing hotkey for the specified action."""
        if keyboard is None:
            messagebox.showerror("Ошибка", "Модуль keyboard недоступен")
            return

        self.waiting_for_hotkey = key
        entry = self.hotkey_entries[key]
        button = self.hotkey_buttons[key]

        entry.config(state='normal')
        entry.delete(0, tk.END)
        entry.insert(0, "Нажмите комбинацию клавиш...")
        entry.config(state='readonly', foreground='blue')

        button.config(text="Отмена", command=lambda: self._cancel_hotkey_capture(key))

        # Start keyboard listener
        try:
            self._setup_keyboard_listener()
        except Exception as e:
            logger.error(f"Failed to setup keyboard listener: {e}")
            self._cancel_hotkey_capture(key)

    def _setup_keyboard_listener(self) -> None:
        """Setup keyboard listener for hotkey capture."""
        if keyboard is None:
            return

        def on_key_event(event):
            if self.waiting_for_hotkey and event.event_type == keyboard.KEY_DOWN:
                # Build hotkey string
                modifiers = []
                if keyboard.is_pressed('ctrl'):
                    modifiers.append('ctrl')
                if keyboard.is_pressed('alt'):
                    modifiers.append('alt')
                if keyboard.is_pressed('shift'):
                    modifiers.append('shift')

                # Get the main key
                key_name = event.name
                if key_name not in ['ctrl', 'alt', 'shift']:
                    hotkey_str = '+'.join(modifiers + [key_name])
                    self._finish_hotkey_capture(hotkey_str)
                    return False  # Stop listener

        # Start listener
        keyboard.hook(on_key_event)

    def _finish_hotkey_capture(self, hotkey: str) -> None:
        """Finish hotkey capture with the recorded hotkey."""
        if not self.waiting_for_hotkey:
            return

        key = self.waiting_for_hotkey
        entry = self.hotkey_entries[key]
        button = self.hotkey_buttons[key]

        # Update UI
        entry.config(state='normal', foreground='black')
        entry.delete(0, tk.END)
        entry.insert(0, hotkey)
        entry.config(state='readonly')

        button.config(text="Задать", command=lambda k=key: self._start_hotkey_capture(k))

        # Save to config
        self.update_config_value("hotkeys", key, hotkey)

        # Stop keyboard listener
        if keyboard:
            keyboard.unhook_all()

        self.waiting_for_hotkey = None

    def _cancel_hotkey_capture(self, key: str) -> None:
        """Cancel hotkey capture."""
        entry = self.hotkey_entries[key]
        button = self.hotkey_buttons[key]

        # Restore previous value
        self._load_hotkey_value(key)

        entry.config(foreground='black')
        button.config(text="Задать", command=lambda k=key: self._start_hotkey_capture(k))

        # Stop keyboard listener
        if keyboard:
            keyboard.unhook_all()

        self.waiting_for_hotkey = None

    def _clear_hotkey(self, key: str) -> None:
        """Clear a hotkey."""
        entry = self.hotkey_entries[key]
        entry.config(state='normal')
        entry.delete(0, tk.END)
        entry.config(state='readonly')

        self.update_config_value("hotkeys", key, "")

    def _set_default_hotkey(self, key: str, default: str) -> None:
        """Set hotkey to default value."""
        entry = self.hotkey_entries[key]
        entry.config(state='normal')
        entry.delete(0, tk.END)
        entry.insert(0, default)
        entry.config(state='readonly')

        self.update_config_value("hotkeys", key, default)

    def _load_current_values(self) -> None:
        """Load current hotkey values from config."""
        for key in self.hotkey_entries:
            self._load_hotkey_value(key)

    def _load_hotkey_value(self, key: str) -> None:
        """Load a single hotkey value."""
        try:
            hotkeys_config = self.get_config_section("hotkeys")
            value = hotkeys_config.get(key, "")

            entry = self.hotkey_entries[key]
            entry.config(state='normal')
            entry.delete(0, tk.END)
            entry.insert(0, value)
            entry.config(state='readonly')
        except Exception as e:
            logger.error(f"Failed to load hotkey {key}", error=e)

    def _test_hotkeys(self) -> None:
        """Test current hotkey configuration."""
        messagebox.showinfo(
            "Тест горячих клавиш",
            "Тест горячих клавиш будет реализован в следующей версии.\n\n"
            "Пока что проверьте работу клавиш в основном интерфейсе."
        )

    def _reset_all_hotkeys(self) -> None:
        """Reset all hotkeys to defaults."""
        if messagebox.askyesno("Сброс", "Сбросить все горячие клавиши к значениям по умолчанию?"):
            defaults = {
                "translate_selection": "Alt+A",
                "quick_translate_center": "Alt+Q",
                "quick_translate_bottom": "Alt+W",
                "repeat_last": "Alt+S",
                "switch_language": "Alt+L",
                "show_history": "Alt+H",
                "show_settings": "Alt+Comma",
                "toggle_overlay": "Alt+O",
                "emergency_stop": "Ctrl+Alt+X",
                "pause_translation": "Ctrl+Alt+P",
            }

            for key, default in defaults.items():
                if key in self.hotkey_entries:
                    self._set_default_hotkey(key, default)

    def save_settings(self) -> bool:
        """Save hotkey settings."""
        try:
            # All changes are saved immediately, so just return True
            return True
        except Exception as e:
            logger.error("Failed to save hotkey settings", error=e)
            return False
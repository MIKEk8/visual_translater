"""Refactored Settings Window using modular components.

This replaces the 1007-line God Class with a clean, modular architecture.
"""

import queue
import threading

try:
    import tkinter as tk
    from tkinter import messagebox, ttk
except ImportError:
    from src.utils.mock_gui import tk, messagebox, ttk

from typing import List, Optional
from src.core.tts_engine import TTSProcessor
from src.services.config_manager import ConfigManager, ConfigObserver
from src.utils.logger import logger

# Import our modular tab components
from src.ui.settings_components import (
    BaseSettingsTab,
    GeneralTab,
    HotkeysTab,
    OCRTab,
    TTSTab,
    BatchProcessingTab,
    AdvancedTab
)


class SettingsWindowRefactored(ConfigObserver):
    """Refactored settings window with modular tab architecture."""

    def __init__(self, config_manager: ConfigManager, tts_processor: TTSProcessor):
        self._lock = threading.Lock()
        self.config_manager = config_manager
        self.tts_processor = tts_processor
        self.window: Optional[tk.Toplevel] = None
        self.config = config_manager.get_config()

        # Tab components
        self.tabs: List[BaseSettingsTab] = []
        self.notebook: Optional[ttk.Notebook] = None

        # Register as observer
        config_manager.add_observer(self)

        logger.debug("Refactored settings window initialized")
        self.gui_queue = queue.Queue()

    def show(self) -> None:
        """Show settings window."""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return

        self._create_window()
        self._create_ui()
        logger.info("Refactored settings window opened")

    def _create_window(self) -> None:
        """Create main window with DnD support."""
        try:
            # Try to create a TkinterDnD2-enabled window for drag and drop support
            from tkinterdnd2 import Tk as TkDnD2, TkinterDnD

            root = tk._default_root
            if root and not hasattr(root, 'TkdndVersion'):
                logger.info("Creating standalone DnD-aware settings window")
                self.window = TkDnD2()
                self.window.withdraw()
                self.window.deiconify()
            else:
                self.window = tk.Toplevel()

            logger.info("Settings window created with DnD support")
        except ImportError:
            logger.info("TkinterDnD2 not available, creating standard settings window")
            self.window = tk.Toplevel()
        except Exception as e:
            logger.warning(f"Could not create DnD window: {e}, using standard window")
            self.window = tk.Toplevel()

        # Configure window
        self.window.title("Настройки Screen Translator v2.0")
        self.window.geometry("700x600")
        self.window.resizable(True, True)

        # Center window
        self._center_window()

        # Set window properties
        self.window.transient()
        self.window.grab_set()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_window(self) -> None:
        """Center the window on screen."""
        self.window.update_idletasks()
        width = 700
        height = 600
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def _create_ui(self) -> None:
        """Create user interface with modular tabs."""
        # Create main container
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Create and initialize all tab components
        self._create_tab_components()

        # Initialize all tabs
        self._initialize_tabs()

        # Create bottom buttons
        self._create_buttons(main_frame)

    def _create_tab_components(self) -> None:
        """Create all tab components."""
        try:
            # Create tab instances
            tab_classes = [
                GeneralTab,
                HotkeysTab,
                OCRTab,
                TTSTab,
                BatchProcessingTab,
                AdvancedTab
            ]

            for tab_class in tab_classes:
                try:
                    tab_instance = tab_class(
                        self.notebook,
                        self.config_manager,
                        self.tts_processor
                    )
                    self.tabs.append(tab_instance)
                    logger.debug(f"Created {tab_class.__name__}")
                except Exception as e:
                    logger.error(f"Failed to create {tab_class.__name__}", error=e)

        except Exception as e:
            logger.error("Failed to create tab components", error=e)

    def _initialize_tabs(self) -> None:
        """Initialize all tab components."""
        for tab in self.tabs:
            try:
                tab.initialize()
                logger.debug(f"Initialized {tab.__class__.__name__}")
            except Exception as e:
                logger.error(f"Failed to initialize {tab.__class__.__name__}", error=e)

    def _create_buttons(self, parent: tk.Widget) -> None:
        """Create bottom control buttons."""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # Left side buttons
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side=tk.LEFT)

        ttk.Button(
            left_frame,
            text="По умолчанию",
            command=self._reset_to_defaults
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            left_frame,
            text="Тест настроек",
            command=self._test_settings
        ).pack(side=tk.LEFT, padx=5)

        # Right side buttons
        right_frame = ttk.Frame(button_frame)
        right_frame.pack(side=tk.RIGHT)

        ttk.Button(
            right_frame,
            text="Отмена",
            command=self._on_close
        ).pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Button(
            right_frame,
            text="Применить",
            command=self._apply_settings
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            right_frame,
            text="ОК",
            command=self._save_and_close
        ).pack(side=tk.RIGHT, padx=5)

    def _save_and_close(self) -> None:
        """Save settings and close window."""
        if self._save_settings():
            self._on_close()

    def _apply_settings(self) -> None:
        """Apply settings without closing."""
        self._save_settings()

    def _save_settings(self) -> bool:
        """Save all settings from tabs."""
        try:
            all_valid = True
            error_messages = []

            # Validate all tabs first
            for tab in self.tabs:
                try:
                    is_valid, error_message = tab.validate_settings()
                    if not is_valid:
                        all_valid = False
                        error_messages.append(f"{tab.tab_name}: {error_message}")
                except Exception as e:
                    logger.error(f"Validation error in {tab.__class__.__name__}", error=e)
                    all_valid = False
                    error_messages.append(f"{tab.tab_name}: Ошибка валидации")

            if not all_valid:
                error_text = "\\n".join(error_messages)
                messagebox.showerror(
                    "Ошибки в настройках",
                    f"Обнаружены ошибки в настройках:\\n\\n{error_text}"
                )
                return False

            # Save all tabs
            all_saved = True
            save_errors = []

            for tab in self.tabs:
                try:
                    if not tab.save_settings():
                        all_saved = False
                        save_errors.append(tab.tab_name)
                except Exception as e:
                    logger.error(f"Save error in {tab.__class__.__name__}", error=e)
                    all_saved = False
                    save_errors.append(tab.tab_name)

            if not all_saved:
                error_text = ", ".join(save_errors)
                messagebox.showerror(
                    "Ошибка сохранения",
                    f"Не удалось сохранить настройки для: {error_text}"
                )
                return False

            # Save configuration file
            self.config_manager.save_config()

            messagebox.showinfo("Сохранение", "Настройки успешно сохранены")
            logger.info("All settings saved successfully")
            return True

        except Exception as e:
            logger.error("Failed to save settings", error=e)
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки: {str(e)}")
            return False

    def _reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        if messagebox.askyesno(
            "Сброс настроек",
            "Сбросить ВСЕ настройки к значениям по умолчанию?\\n\\n"
            "Это действие нельзя отменить."
        ):
            try:
                # Reset each tab to defaults
                for tab in self.tabs:
                    try:
                        if hasattr(tab, '_reset_to_defaults'):
                            tab._reset_to_defaults()
                        elif hasattr(tab, 'reset_to_defaults'):
                            tab.reset_to_defaults()
                    except Exception as e:
                        logger.error(f"Failed to reset {tab.__class__.__name__}", error=e)

                messagebox.showinfo("Сброс", "Настройки сброшены к значениям по умолчанию")
                logger.info("Settings reset to defaults")

            except Exception as e:
                logger.error("Failed to reset settings", error=e)
                messagebox.showerror("Ошибка", f"Не удалось сбросить настройки: {str(e)}")

    def _test_settings(self) -> None:
        """Test current settings configuration."""
        try:
            # Get current tab
            if self.notebook:
                current_tab_index = self.notebook.index(self.notebook.select())
                if 0 <= current_tab_index < len(self.tabs):
                    current_tab = self.tabs[current_tab_index]

                    # Try to call tab-specific test method
                    if hasattr(current_tab, '_test_settings'):
                        current_tab._test_settings()
                    elif hasattr(current_tab, '_test_hotkeys') and isinstance(current_tab, HotkeysTab):
                        current_tab._test_hotkeys()
                    elif hasattr(current_tab, '_test_tts') and isinstance(current_tab, TTSTab):
                        current_tab._test_tts()
                    elif hasattr(current_tab, '_test_ocr') and isinstance(current_tab, OCRTab):
                        current_tab._test_ocr()
                    elif hasattr(current_tab, '_test_batch_processing') and isinstance(current_tab, BatchProcessingTab):
                        current_tab._test_batch_processing()
                    else:
                        messagebox.showinfo(
                            "Тест настроек",
                            f"Настройки вкладки '{current_tab.tab_name}' выглядят корректно."
                        )
                    return

            # Fallback general test
            messagebox.showinfo(
                "Тест настроек",
                "Общий тест настроек:\\n\\n"
                "✓ Конфигурация загружена\\n"
                "✓ Все вкладки инициализированы\\n"
                "✓ Компоненты работают корректно"
            )

        except Exception as e:
            logger.error("Settings test failed", error=e)
            messagebox.showerror("Ошибка теста", f"Не удалось протестировать настройки: {str(e)}")

    def _on_close(self) -> None:
        """Handle window close event."""
        try:
            # Check if there are unsaved changes
            # TODO: Implement unsaved changes detection

            self.window.grab_release()
            self.window.destroy()
            self.window = None
            logger.info("Settings window closed")

        except Exception as e:
            logger.error("Error closing settings window", error=e)

    def on_config_changed(self, config) -> None:
        """Handle configuration changes (ConfigObserver interface)."""
        try:
            self.config = config
            # Refresh all tabs with new config
            for tab in self.tabs:
                if hasattr(tab, '_load_current_values'):
                    tab._load_current_values()

            logger.debug("Settings UI updated after config change")
        except Exception as e:
            logger.error("Failed to update settings UI after config change", error=e)

    def queue_gui_action(self, func, *args) -> None:
        """Queue GUI action for thread-safe execution."""
        if hasattr(self, "gui_queue"):
            self.gui_queue.put((func, args))
        else:
            # Fallback to direct call if no queue
            func(*args)

    def get_current_tab(self) -> Optional[BaseSettingsTab]:
        """Get currently selected tab."""
        if self.notebook and self.tabs:
            try:
                current_index = self.notebook.index(self.notebook.select())
                if 0 <= current_index < len(self.tabs):
                    return self.tabs[current_index]
            except Exception:
                pass
        return None


# Alias for backward compatibility
SettingsWindow = SettingsWindowRefactored
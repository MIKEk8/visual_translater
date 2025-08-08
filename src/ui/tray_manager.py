import json
import os
import queue
import threading

try:
    from tkinter import messagebox
except ImportError:
    print(f"tkinter недоступен в {__name__}")
    # Используем заглушки для импортированных компонентов
    from src.utils.mock_gui import messagebox

from typing import TYPE_CHECKING

try:
    import pystray
except ImportError:
    print(f"pystray недоступен в данной среде")
    # Используем mock
    from src.utils.mock_pystray import *

from PIL import Image

# Avoid circular import
if TYPE_CHECKING:
    from src.core.application import ScreenTranslatorApp  # noqa: F401 - Used in type hints

from src.utils.logger import logger


class TrayManager:
    """System tray manager for Screen Translator"""

    def __init__(self, app: "ScreenTranslatorApp"):
        self.app = app
        self.icon = None
        self.gui_queue = queue.Queue()
        self.is_running = False

        logger.debug("Tray manager initialized")

    def start(self):
        """Start tray manager"""
        if self.is_running:
            return

        self.setup_tray()
        self.start_message_processing()
        self.is_running = True

        logger.info("Tray manager started")

    def stop(self):
        """Stop tray manager"""
        self.is_running = False
        try:
            if self.icon:
                self.icon.stop()
        except Exception as e:
            logger.warning(f"Error stopping tray icon: {e}")
        logger.info("Tray manager stopped")

    def setup_tray(self):
        """Setup system tray icon and menu"""
        menu = pystray.Menu(
            pystray.MenuItem("Сделать скриншот", self._activate_capture, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Быстрые области",
                pystray.Menu(
                    pystray.MenuItem("📱 Центр экрана", self._quick_center),
                    pystray.MenuItem("📺 Субтитры (низ)", self._quick_bottom),
                ),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("История", self._show_history),
            pystray.MenuItem("Настройки", self._open_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Лог", self._show_log),
            pystray.MenuItem("Информация", self._show_info),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", self._exit_app),
        )

        self.icon = pystray.Icon(
            "screen_translator", self._load_icon(), "Screen Translator v2.0", menu=menu
        )

        # Run icon in separate thread
        threading.Thread(target=self.icon.run, daemon=True).start()

    def _load_icon(self) -> Image.Image:
        """Load tray icon"""
        try:
            icon_path = "icon.ico"
            if os.path.exists(icon_path):
                return Image.open(icon_path)
            else:
                # Create default icon
                return Image.new("RGB", (64, 64), color="blue")
        except Exception as e:
            logger.error("Failed to load tray icon", error=e)
            return Image.new("RGB", (64, 64), color="red")

    def start_message_processing(self):
        """Start processing GUI messages"""
        self._check_messages()

    def _check_messages(self):
        """Check and process GUI messages"""
        try:
            while not self.gui_queue.empty():
                func, args = self.gui_queue.get_nowait()
                logger.debug(
                    f"Tray: Processing GUI action: {func.__name__ if hasattr(func, '__name__') else str(func)}"
                )
                func(*args)
        except Exception as e:
            logger.error("Error in GUI message queue", error=e)

        # Schedule next check (only if app is still running)
        if self.is_running:
            try:
                if self.app and hasattr(self.app, "root") and self.app.root:
                    self.app.root.after(100, self._check_messages)
                else:
                    # If no root window available, schedule with threading
                    threading.Timer(0.1, self._check_messages).start()
            except Exception as e:
                logger.debug(f"Could not schedule next message check: {e}")
                # Fallback to direct threading
                if self.is_running:
                    threading.Timer(0.1, self._check_messages).start()

    # Menu event handlers
    def _activate_capture(self, icon=None, item=None):
        """Activate area capture"""
        if self.app:
            self.gui_queue.put((self.app.capture_area, ()))

    def _quick_center(self, icon=None, item=None):
        """Quick capture center area"""
        if self.app:
            self.gui_queue.put((self.app.capture_center, ()))

    def _quick_bottom(self, icon=None, item=None):
        """Quick capture bottom area (subtitles)"""
        if self.app:
            self.gui_queue.put((self.app.capture_subtitles, ()))

    def _show_history(self, icon=None, item=None):
        """Show translation history"""
        if self.app:
            self.gui_queue.put((self.app.show_history, ()))

    def _open_settings(self, icon=None, item=None):
        """Open settings window"""
        if self.app:
            self.gui_queue.put((self.app.open_settings, ()))

    def _show_log(self, icon=None, item=None):
        """Show application log"""
        log_path = "screen_translator.log"
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    log_content = f.read()

                # Show last 100 lines
                lines = log_content.split("\n")
                recent_lines = lines[-100:] if len(lines) > 100 else lines
                recent_content = "\n".join(recent_lines)

                self.gui_queue.put((messagebox.showinfo, ("Лог приложения", recent_content)))
            except Exception as e:
                self.gui_queue.put(
                    (
                        messagebox.showerror,
                        ("Ошибка", f"Не удалось загрузить лог: {str(e)}"),
                    )
                )
        else:
            self.gui_queue.put((messagebox.showwarning, ("Предупреждение", "Лог файл не найден")))

    def _show_info(self, icon=None, item=None):
        """Show about information"""
        info_text = """Screen Translator v2.0

Переводчик экрана в реальном времени

Особенности:
• OCR распознавание текста
• Машинный перевод Google Translate  
• Озвучка переводов (TTS)
• Гибкие горячие клавиши
• Модульная архитектура

Разработано для личного использования"""

        self.gui_queue.put((messagebox.showinfo, ("О программе", info_text)))

    def _exit_app(self, icon=None, item=None):
        """Exit application"""
        if self.app:
            logger.info("Tray: Exit requested")
            self.gui_queue.put((self.app.shutdown, ()))

    def show_notification(self, title: str, message: str, duration: int = 3):
        """Show system notification"""
        if self.icon:
            try:
                self.icon.notify(message, title)
            except Exception as e:
                logger.error("Failed to show notification", error=e, title=title)

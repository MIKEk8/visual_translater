"""
SystemIntegration - System-level operations coordinator

Single Responsibility: Manages system-level operations, cleanup procedures,
and integration with OS components.

Responsibilities:
- Application shutdown procedures
- System tray manager integration
- Keyboard hooks cleanup
- Thread management and cleanup
- Event bus shutdown
"""

import asyncio
import threading
from typing import TYPE_CHECKING, Optional

# Import keyboard only when available
try:
    import keyboard
except ImportError:
    keyboard = None
    print("keyboard недоступен в данной среде")
    
    # Create mock keyboard module for compatibility
    class MockKeyboard:
        def add_hotkey(self, *args, **kwargs):
            pass
        def remove_hotkey(self, *args, **kwargs):
            pass
        def is_pressed(self, *args, **kwargs):
            return False
            
    keyboard = MockKeyboard()
    print("Mock keyboard модуль загружен")

from src.core.events import EventType, get_event_bus, publish_event
from src.services.task_queue import get_task_queue
from src.ui.tray_manager import TrayManager
from src.utils.logger import logger

if TYPE_CHECKING:
    import tkinter as tk

    from src.core.tts_engine import TTSProcessor


class SystemIntegration:
    """Coordinates system-level operations and cleanup"""

    def __init__(
        self,
        root: "tk.Tk",
        tts_processor: Optional["TTSProcessor"] = None,
        tray_manager: Optional[TrayManager] = None,
    ):
        self.root = root
        self.tts_processor = tts_processor
        self.tray_manager = tray_manager
        self._lock = threading.Lock()

        # System components
        self.task_queue = get_task_queue()
        self.event_bus = get_event_bus()

    def shutdown(self) -> None:
        """Complete application shutdown procedure"""
        logger.info("SystemIntegration: Starting application shutdown")

        # Publish shutdown event first
        publish_event(EventType.APPLICATION_SHUTDOWN, source="system_integration")
        logger.log_shutdown()

        # Shutdown components in proper order
        self._shutdown_tray_manager()
        self._shutdown_task_queue()
        self._shutdown_event_bus()
        self._cleanup_keyboard_hooks()
        self._shutdown_tts_processor()
        self._destroy_gui()

        logger.info("SystemIntegration: Application shutdown completed")

    def _shutdown_tray_manager(self) -> None:
        """Stop system tray manager"""
        try:
            if self.tray_manager:
                with self._lock:
                    self.tray_manager.stop()
                logger.debug("Tray manager stopped")
        except Exception as e:
            logger.warning(f"Error stopping system tray: {e}")

    def _shutdown_task_queue(self) -> None:
        """Stop task queue processing"""
        try:
            if hasattr(self, "task_queue") and self.task_queue:
                with self._lock:
                    self.task_queue.stop(wait=True, timeout=3.0)
                logger.debug("Task queue stopped")
        except Exception as e:
            logger.warning(f"Error stopping task queue: {e}")

    def _shutdown_event_bus(self) -> None:
        """Shutdown event bus"""
        try:
            if hasattr(self, "event_bus") and self.event_bus:
                with self._lock:
                    asyncio.run(self.event_bus.shutdown())
                logger.debug("Event bus shut down")
        except Exception as e:
            logger.warning(f"Error shutting down event bus: {e}")

    def _cleanup_keyboard_hooks(self) -> None:
        """Cleanup keyboard hooks"""
        try:
            keyboard.unhook_all()
            logger.debug("Keyboard hooks cleaned up")
        except (ImportError, Exception) as e:
            logger.debug(f"Keyboard hooks cleanup: {e}")

    def _shutdown_tts_processor(self) -> None:
        """Stop TTS processor"""
        try:
            if self.tts_processor:
                with self._lock:
                    self.tts_processor.stop_speaking()
                logger.debug("TTS processor stopped")
        except Exception as e:
            logger.warning(f"Error stopping TTS processor: {e}")

    def _destroy_gui(self) -> None:
        """Destroy GUI components"""
        try:
            with self._lock:
                self.root.destroy()
            logger.debug("GUI destroyed")
        except Exception as e:
            logger.warning(f"Error destroying GUI: {e}")

    def start_tray_manager(self) -> bool:
        """Start system tray manager"""
        if self.tray_manager:
            try:
                with self._lock:
                    self.tray_manager.start()
                logger.info("System tray started")
                return True
            except Exception as e:
                logger.warning(f"Could not start system tray (running in headless mode?): {e}")
                return False
        else:
            logger.info("Running without system tray (headless mode)")
            return False

    def is_tray_available(self) -> bool:
        """Check if system tray is available"""
        return self.tray_manager is not None

    def get_system_info(self) -> dict:
        """Get system information for diagnostics"""
        import platform
        import sys

        return {
            "platform": platform.platform(),
            "python_version": sys.version,
            "architecture": platform.architecture(),
            "processor": platform.processor(),
            "tray_available": self.is_tray_available(),
            "task_queue_active": hasattr(self, "task_queue") and self.task_queue is not None,
            "event_bus_active": hasattr(self, "event_bus") and self.event_bus is not None,
        }

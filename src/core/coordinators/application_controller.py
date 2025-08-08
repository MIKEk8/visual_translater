"""
ApplicationController - Main application coordination controller

Single Responsibility: Serves as the main coordinator for the entire application,
managing component lifecycle, dependency injection, and high-level orchestration.

This is the new, much smaller main class that replaces the original God Class.
It coordinates between all the specialized coordinators.

Responsibilities:
- Application initialization and DI setup
- Component coordination and lifecycle
- Configuration observer implementation
- Main application loop management
- High-level event coordination
"""

import threading

try:
    import tkinter as tk
except ImportError:
    print(f"tkinter недоступен в {__name__}")
    # Используем заглушку
    from src.utils.mock_gui import tk

from typing import TYPE_CHECKING, Optional

from src.core.coordinators.batch_export_manager import BatchExportManager
from src.core.coordinators.capture_orchestrator import CaptureOrchestrator
from src.core.coordinators.system_integration import SystemIntegration
from src.core.coordinators.translation_workflow import TranslationWorkflow
from src.core.coordinators.ui_coordinator import UICoordinator
from src.core.event_handlers import setup_event_handlers
from src.core.events import EventType, get_event_bus, publish_event
from src.core.ocr_engine import OCRProcessor
from src.core.screenshot_engine import ScreenshotEngine
from src.core.translation_engine import TranslationProcessor
from src.core.tts_engine import TTSProcessor
from src.plugins.base_plugin import PluginType
from src.services.config_manager import ConfigManager, ConfigObserver
from src.services.container import container, setup_default_services
from src.services.plugin_service import PluginService
from src.ui.tray_manager import TrayManager
from src.utils.logger import logger

if TYPE_CHECKING:
    from src.services.container import DIContainer


class ApplicationController(ConfigObserver):
    """Main application controller - coordinates all components"""

    def __init__(self, di_container: Optional["DIContainer"] = None):
        # Thread safety
        self._lock = threading.Lock()

        # GUI initialization
        self.root = tk.Tk()
        self.root.withdraw()  # Hide main window

        # Use provided container or global one
        self.container = di_container or container

        # Setup services in the target container
        if di_container:
            setup_default_services(di_container)

        # Get core services from DI container
        self.config_manager = self.container.get(ConfigManager)
        self.screenshot_engine = self.container.get(ScreenshotEngine)
        self.plugin_service = self.container.get(PluginService)

        # Get engines (with plugin support)
        self.ocr_processor = self._get_ocr_engine()
        self.translation_processor = self._get_translation_engine()
        self.tts_processor = self._get_tts_engine()

        # Initialize specialized coordinators
        self._setup_coordinators()

        # Initialize tray manager (optional in headless environments)
        self._setup_tray_manager()

        # Event-driven architecture setup
        self.event_bus = get_event_bus()
        self._setup_event_system()

        # Register as config observer
        self.config_manager.add_observer(self)

        logger.log_startup("2.0.0")
        logger.info("ApplicationController initialized with modular architecture")

        # Publish application started event
        publish_event(EventType.APPLICATION_STARTED, source="application_controller")

    def _setup_coordinators(self) -> None:
        """Initialize all specialized coordinators"""

        # UI Coordinator
        self.ui_coordinator = UICoordinator(self.root, self.config_manager, self.tts_processor)

        # Translation Workflow
        self.translation_workflow = TranslationWorkflow(
            self.ocr_processor, self.translation_processor, self.tts_processor, self.config_manager
        )

        # Capture Orchestrator with callbacks
        self.capture_orchestrator = CaptureOrchestrator(
            self.root,
            self.screenshot_engine,
            self.ui_coordinator.progress_manager,
            on_area_captured=self._on_area_captured,
            on_capture_error=self._on_capture_error,
        )

        # Batch Export Manager
        self.batch_export_manager = BatchExportManager(
            self.screenshot_engine,
            self.ocr_processor,
            self.translation_processor,
            self.ui_coordinator.progress_manager,
        )

        # System Integration
        self.system_integration = SystemIntegration(
            self.root, self.tts_processor, getattr(self, "tray_manager", None)
        )

    def _setup_tray_manager(self) -> None:
        """Setup system tray manager"""
        try:
            self.tray_manager = TrayManager(self)
            # Update system integration with tray manager
            if hasattr(self, "system_integration"):
                self.system_integration.tray_manager = self.tray_manager
        except Exception as e:
            logger.warning(f"Could not initialize tray manager: {e}")
            self.tray_manager = None

    def _get_ocr_engine(self):
        """Get OCR engine from plugins or fallback"""
        try:
            ocr_plugin = self.plugin_service.get_active_plugin(PluginType.OCR)
            if ocr_plugin:
                return ocr_plugin
        except Exception as e:
            logger.warning(f"Failed to get OCR plugin: {e}")
        return self.container.get(OCRProcessor)

    def _get_translation_engine(self):
        """Get translation engine from plugins or fallback"""
        try:
            translation_plugin = self.plugin_service.get_active_plugin(PluginType.TRANSLATION)
            if translation_plugin:
                return translation_plugin
        except Exception as e:
            logger.warning(f"Failed to get translation plugin: {e}")
        return self.container.get(TranslationProcessor)

    def _get_tts_engine(self):
        """Get TTS engine from plugins or fallback"""
        try:
            tts_plugin = self.plugin_service.get_active_plugin(PluginType.TTS)
            if tts_plugin:
                return tts_plugin
        except Exception as e:
            logger.warning(f"Failed to get TTS plugin: {e}")
        return self.container.get(TTSProcessor)

    def _setup_event_system(self) -> None:
        """Setup event-driven architecture components"""
        app_components = {
            "ocr_processor": self.ocr_processor,
            "translation_processor": self.translation_processor,
            "tts_processor": self.tts_processor,
            "config_manager": self.config_manager,
            "performance_monitor": self.batch_export_manager.performance_monitor,
        }

        self.event_handlers = setup_event_handlers(app_components)
        logger.info("Event-driven architecture initialized")

    def _on_area_captured(self, screenshot_data) -> None:
        """Handle successful area capture"""
        # Process through translation workflow
        translation = self.translation_workflow.process_screenshot_translation(screenshot_data)
        if translation:
            self.ui_coordinator.handle_translation_success(translation)

    def _on_capture_error(self, error: Exception) -> None:
        """Handle capture errors"""
        self.ui_coordinator.handle_translation_error(error)

    # Public API methods delegated to coordinators
    def capture_area(self) -> None:
        """Start area selection"""
        self.capture_orchestrator.capture_area()

    def quick_translate_center(self) -> None:
        """Quick translate center area"""
        self.capture_orchestrator.quick_translate_center()

    def quick_translate_bottom(self) -> None:
        """Quick translate bottom area"""
        self.capture_orchestrator.quick_translate_bottom()

    def repeat_last_translation(self) -> None:
        """Repeat last translation"""
        self.translation_workflow.repeat_last_translation()

    def switch_language(self) -> str:
        """Switch target language"""
        return self.translation_workflow.switch_language()

    def show_translation_history(self) -> None:
        """Show translation history"""
        history = self.translation_workflow.get_translation_history()
        self.ui_coordinator.show_translation_history(history)

    def show_batch_history(self) -> None:
        """Show batch history"""
        jobs = self.batch_export_manager.get_active_batch_jobs()
        self.ui_coordinator.show_batch_history(jobs)

    def open_settings(self) -> None:
        """Open settings window"""
        self.ui_coordinator.open_settings()

    def export_translation_history(self, format_type: str = "json") -> Optional[str]:
        """Export translation history"""
        history = self.translation_workflow.get_translation_history()
        return self.batch_export_manager.export_translation_history(history, format_type)

    def export_performance_metrics(self, file_path: Optional[str] = None) -> Optional[str]:
        """Export performance metrics"""
        return self.batch_export_manager.export_performance_metrics(file_path)

    def run(self) -> None:
        """Run the application"""
        logger.info("Starting application main loop")

        # Start system tray
        self.system_integration.start_tray_manager()

        with self._lock:
            self.root.mainloop()

    def shutdown(self) -> None:
        """Shutdown application"""
        self.system_integration.shutdown()

    # ConfigObserver implementation
    def on_config_changed(self, key: str, old_value, new_value) -> None:
        """Handle configuration changes"""
        logger.debug(f"ApplicationController received config change: {key}")

        if key.startswith("languages.default_target"):
            # Update translation workflow
            with self._lock:
                self.translation_workflow.current_language_index = new_value

        elif key.startswith("tts."):
            # Update TTS processor with new config
            if self.tts_processor:
                with self._lock:
                    self.tts_processor.update_config(self.config_manager.get_config().tts)

        elif key.startswith("features.cache_translations"):
            # Update translation processor cache setting
            if self.translation_processor and hasattr(self.translation_processor, "enable_cache"):
                with self._lock:
                    self.translation_processor.enable_cache(new_value)

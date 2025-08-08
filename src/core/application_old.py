import asyncio
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import TclError, filedialog, messagebox
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import keyboard
import pyperclip

from src.core.ocr_engine import OCRProcessor
from src.core.translation_engine import TranslationProcessor
from src.core.tts_engine import TTSProcessor
from src.plugins.base_plugin import PluginType
from src.services.container import setup_default_services
from src.services.plugin_service import PluginService

if TYPE_CHECKING:
    from src.services.container import DIContainer

from src.core.batch_processor import BatchJob, BatchProcessor, BatchStatus
from src.core.event_handlers import setup_event_handlers

# Event-driven architecture imports
from src.core.events import EventType, get_event_bus, publish_event
from src.core.screenshot_engine import ScreenshotEngine
from src.models.translation import Translation
from src.services.config_manager import ConfigManager, ConfigObserver
from src.services.container import container
from src.services.task_queue import TaskPriority, get_task_queue
from src.ui.progress_indicator import ProgressInfo, ProgressManager
from src.ui.settings_window import SettingsWindow
from src.ui.tray_manager import TrayManager
from src.utils.exceptions import (
    InvalidAreaError,
    OCRError,
    ScreenshotCaptureError,
    TranslationFailedError,
    TTSError,
)
from src.utils.export_manager import ExportManager
from src.utils.logger import logger
from src.utils.performance_monitor import get_performance_monitor


class ScreenTranslatorApp(ConfigObserver):
    """Main application class coordinating all components"""

    def __init__(self, di_container: Optional["DIContainer"] = None):
        # Thread safety - create lock FIRST
        self._lock = threading.Lock()

        # GUI initialization (tkinter is not thread-safe, no locking needed)
        self.root = tk.Tk()
        self.root.withdraw()  # Hide main window

        # Task queue for async processing
        self.task_queue = get_task_queue()

        # Use provided container or global one
        self.container = di_container or container

        # Setup services in the target container
        if di_container:
            setup_default_services(di_container)

        # Get core services (DI container is thread-safe)
        self.config_manager = self.container.get(ConfigManager)
        self.screenshot_engine = self.container.get(ScreenshotEngine)
        self.plugin_service = self.container.get(PluginService)

        # Get engines from plugins (with fallback to direct instances)
        self.ocr_processor = self._get_ocr_engine()
        self.translation_processor = self._get_translation_engine()
        self.tts_processor = self._get_tts_engine()

        # UI components (no locking needed for simple assignments)
        self.settings_window = None
        self.progress_manager = ProgressManager(self.root)

        # Initialize tray manager (optional in headless environments)
        try:
            self.tray_manager = TrayManager(self)
        except Exception as e:
            logger.warning(f"Could not initialize tray manager: {e}")
            self.tray_manager = None

        # Batch processing
        self.batch_processor = BatchProcessor(
            self.ocr_processor, self.translation_processor, max_concurrent=3
        )

        # Export manager
        self.export_manager = ExportManager()

        # Performance monitoring
        self.performance_monitor = get_performance_monitor()
        self._setup_performance_alerts()

        # Event-driven architecture setup
        self.event_bus = get_event_bus()
        self._setup_event_system()

        # State (these need thread-safe access)
        with self._lock:
            self.current_language_index = self.config_manager.get_config().languages.default_target
            self.last_translation = ""
            self.translation_history = []

        # Register as config observer
        self.config_manager.add_observer(self)

        # Setup GUI
        self._setup_capture_overlay()

        logger.log_startup("2.0.0")
        logger.info("Screen Translator application initialized")

        # Publish application started event
        publish_event(EventType.APPLICATION_STARTED, source="application")

    def _get_ocr_engine(self) -> Any:
        """Get OCR engine from plugins or fallback"""
        try:
            ocr_plugin = self.plugin_service.get_active_plugin(PluginType.OCR)
            if ocr_plugin:
                return ocr_plugin
        except Exception as e:
            logger.warning(f"Failed to get OCR plugin: {e}")

        # Fallback to direct engine
        return self.container.get(OCRProcessor)

    def _get_translation_engine(self) -> Any:
        """Get translation engine from plugins or fallback"""
        try:
            translation_plugin = self.plugin_service.get_active_plugin(PluginType.TRANSLATION)
            if translation_plugin:
                return translation_plugin
        except Exception as e:
            logger.warning(f"Failed to get translation plugin: {e}")

        # Fallback to direct engine
        return self.container.get(TranslationProcessor)

    def _get_tts_engine(self) -> Any:
        """Get TTS engine from plugins or fallback"""
        try:
            tts_plugin = self.plugin_service.get_active_plugin(PluginType.TTS)
            if tts_plugin:
                return tts_plugin
        except Exception as e:
            logger.warning(f"Failed to get TTS plugin: {e}")

        # Fallback to direct engine
        return self.container.get(TTSProcessor)

    def _setup_event_system(self) -> None:
        """Setup event-driven architecture components."""
        # Setup event handlers with dependencies
        app_components = {
            "ocr_processor": self.ocr_processor,
            "translation_processor": self.translation_processor,
            "tts_processor": self.tts_processor,
            "config_manager": self.config_manager,
            "performance_monitor": self.performance_monitor,
        }

        self.event_handlers = setup_event_handlers(app_components)
        logger.info("Event-driven architecture initialized")

    def _setup_capture_overlay(self) -> None:
        """Setup screenshot capture overlay"""
        # GUI operations don't need locking (tkinter not thread-safe anyway)
        self.root.attributes("-alpha", 0.3)
        self.root.configure(background="black")
        self.root.attributes("-fullscreen", True)
        self.root.overrideredirect(True)

        self.canvas = tk.Canvas(self.root, cursor="cross", bg="grey11")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Bind events
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        self.root.withdraw()
        self.root.protocol("WM_DELETE_WINDOW", self._hide_overlay)

    def _on_press(self, event: tk.Event) -> None:
        """Handle mouse press for area selection"""
        # GUI event handlers run in main thread, minimal locking needed
        self.start_x = event.x_root
        self.start_y = event.y_root

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        self.rect = self.canvas.create_rectangle(
            canvas_x, canvas_y, canvas_x, canvas_y, outline="red", width=2
        )

    def _on_drag(self, event: tk.Event) -> None:
        """Handle mouse drag for area selection"""
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, canvas_x, canvas_y)

    def _on_release(self, event: tk.Event) -> None:
        """Handle mouse release to complete area selection"""
        self.canvas.delete(self.rect)
        self._hide_overlay()

        x1 = min(self.start_x, event.x_root)
        y1 = min(self.start_y, event.y_root)
        x2 = max(self.start_x, event.x_root)
        y2 = max(self.start_y, event.y_root)

        # Show progress indicator
        with self._lock:
            _ = self.progress_manager.show_progress(
                title="Screen Translation",
                message="Capturing and processing screen area...",
                is_indeterminate=True,
            )

        # Process asynchronously using task queue
        with self._lock:
            task_id = self.task_queue.submit(
                func=self._process_area_screenshot,
                args=(x1, y1, x2, y2),
                name="process_area_screenshot",
                priority=TaskPriority.HIGH,
                callback=self._on_translation_success,
                error_callback=self._on_translation_error,
            )
        logger.debug(f"Area screenshot task queued: {task_id}")

    def _hide_overlay(self) -> None:
        """Hide capture overlay"""
        self.root.withdraw()

    def capture_area(self) -> None:
        """Show area selection overlay"""
        logger.info("App: Capture area method called")
        self.root.deiconify()
        self.root.attributes("-topmost", True)
        self.root.focus_force()

    def quick_translate_center(self) -> None:
        """Translate center area of screen"""
        logger.info("App: Quick translate center method called")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Show progress indicator
        with self._lock:
            _ = self.progress_manager.show_progress(
                title="Quick Translation",
                message="Translating center area...",
                is_indeterminate=True,
            )

        # Process asynchronously
        with self._lock:
            task_id = self.task_queue.submit(
                func=self._process_center_screenshot,
                args=(screen_width, screen_height),
                name="quick_translate_center",
                priority=TaskPriority.HIGH,
                callback=self._on_translation_success,
                error_callback=self._on_translation_error,
            )
        logger.debug(f"Center translation task queued: {task_id}")

    def quick_translate_bottom(self) -> None:
        """Translate bottom area of screen"""
        with self._lock:
            screen_width = self.root.winfo_screenwidth()
        with self._lock:
            screen_height = self.root.winfo_screenheight()

        # Show progress indicator
        with self._lock:
            _ = self.progress_manager.show_progress(
                title="Quick Translation",
                message="Translating bottom area...",
                is_indeterminate=True,
            )

        # Process asynchronously
        with self._lock:
            task_id = self.task_queue.submit(
                func=self._process_bottom_screenshot,
                args=(screen_width, screen_height),
                name="quick_translate_bottom",
                priority=TaskPriority.HIGH,
                callback=self._on_translation_success,
                error_callback=self._on_translation_error,
            )
        logger.debug(f"Bottom translation task queued: {task_id}")

    def repeat_last_translation(self) -> None:
        """Repeat last translation"""
        with self._lock:
            translation = self.last_translation

        if translation:
            # Check if using plugin or direct processor
            if hasattr(self.tts_processor, "speak"):
                # Plugin interface
                current_lang = self.get_current_target_language()
                with self._lock:
                    self.tts_processor.speak(translation, current_lang)
            else:
                # Direct processor
                with self._lock:
                    self.tts_processor.speak_text(translation)

    def switch_language(self):
        """Switch target language"""
        with self._lock:
            languages = self.config_manager.get_config().languages.target_languages

        with self._lock:
            self.current_language_index = (self.current_language_index + 1) % len(languages)
            current_lang = languages[self.current_language_index]

        logger.info(f"Switched to language: {current_lang}")

    def get_current_target_language(self) -> str:
        """Get current target language"""
        with self._lock:
            languages = self.config_manager.get_config().languages.target_languages

        with self._lock:
            index = self.current_language_index

        if index < len(languages):
            return languages[index]
        return languages[0] if languages else "en"

    def _process_area_screenshot(self, x1: int, y1: int, x2: int, y2: int):
        """Process screenshot of selected area using event-driven approach"""
        try:
            # Publish screenshot request event
            publish_event(
                EventType.SCREENSHOT_REQUESTED,
                data={"coordinates": (x1, y1, x2, y2)},
                source="application",
            )

            # Capture screenshot
            with self._lock:
                screenshot_data = self.screenshot_engine.capture_area(x1, y1, x2, y2)
            if not screenshot_data:
                publish_event(
                    EventType.SCREENSHOT_FAILED,
                    data={"error": "Failed to capture screenshot", "coordinates": (x1, y1, x2, y2)},
                    source="application",
                )
                return

            # Save debug screenshot if enabled
            if self.config_manager.get_config().features.save_debug_screenshots:
                self.screenshot_engine.save_debug_screenshot(screenshot_data)

            # Publish successful screenshot capture event
            # The event handlers will take over from here
            publish_event(EventType.SCREENSHOT_CAPTURED, data=screenshot_data, source="application")

            # Extract text using OCR
            with self._lock:
                config = self.config_manager.get_config()
            if hasattr(self.ocr_processor, "extract_text"):
                # Plugin interface
                with self._lock:
                    text, ocr_confidence = self.ocr_processor.extract_text(
                        screenshot_data.image_bytes, config.languages.ocr_languages
                    )
            else:
                # Direct processor
                with self._lock:
                    text, ocr_confidence = self.ocr_processor.process_screenshot(
                        screenshot_data, config.languages.ocr_languages
                    )

            if not text.strip():
                logger.warning("No text extracted from screenshot")
                return

            target_lang = self.get_current_target_language()

            # Check if using plugin or direct processor
            if hasattr(self.translation_processor, "translate"):
                # Plugin interface
                with self._lock:
                    translated_text, confidence = self.translation_processor.translate(
                        text, "auto", target_lang  # auto-detect source language
                    )
                # Create Translation object for consistency
                from src.models.translation import Translation

                translation = Translation(
                    original_text=text,
                    translated_text=translated_text,
                    source_language="auto",
                    target_language=target_lang,
                    confidence=confidence,
                )
            else:
                # Direct processor
                with self._lock:
                    translation = self.translation_processor.translate_text(text, target_lang)

            if not translation:
                logger.error("Translation failed")
                return

            # Return result for async callback
            return translation

        except Exception as e:
            logger.error("Error processing area screenshot", error=e)
            raise  # Re-raise for error callback

    def _process_center_screenshot(self, screen_width: int, screen_height: int):
        """Process center area screenshot"""
        try:
            with self._lock:
                screenshot_data = self.screenshot_engine.capture_center_area(
                    screen_width, screen_height
                )
            if screenshot_data:
                return self._process_screenshot_data(screenshot_data)
        except Exception as e:
            logger.error("Error processing center screenshot", error=e)
            raise

    def _process_bottom_screenshot(self, screen_width: int, screen_height: int):
        """Process bottom area screenshot"""
        try:
            with self._lock:
                screenshot_data = self.screenshot_engine.capture_bottom_area(
                    screen_width, screen_height
                )
            if screenshot_data:
                return self._process_screenshot_data(screenshot_data)
        except Exception as e:
            logger.error("Error processing bottom screenshot", error=e)
            raise

    def _process_screenshot_data(self, screenshot_data):
        """Process screenshot data through the pipeline"""
        with self._lock:
            config = self.config_manager.get_config()

        # Extract text
        with self.performance_monitor.measure_operation("ocr_extraction"):
            if hasattr(self.ocr_processor, "extract_text"):
                # Plugin interface
                text, confidence = self.ocr_processor.extract_text(
                    screenshot_data.image_bytes, config.languages.ocr_languages
                )
            else:
                # Direct processor
                text, confidence = self.ocr_processor.process_screenshot(
                    screenshot_data, config.languages.ocr_languages
                )

        if text.strip():
            # Translate
            target_lang = self.get_current_target_language()

            # Check if using plugin or direct processor
            with self.performance_monitor.measure_operation(
                "translation", {"target_lang": target_lang, "text_length": len(text)}
            ):
                if hasattr(self.translation_processor, "translate"):
                    # Plugin interface
                    translated_text, confidence = self.translation_processor.translate(
                        text, "auto", target_lang  # auto-detect source language
                    )
                    # Create Translation object for consistency
                    from src.models.translation import Translation

                    translation = Translation(
                        original_text=text,
                        translated_text=translated_text,
                        source_language="auto",
                        target_language=target_lang,
                        confidence=confidence,
                    )
                else:
                    # Direct processor
                    translation = self.translation_processor.translate_text(text, target_lang)

            if translation:
                return translation

    def _handle_translation_result(self, translation: Translation):
        """Handle successful translation result"""
        # Store for history and repeat (thread-safe)
        with self._lock:
            self.last_translation = translation.translated_text
            self._add_to_history_unsafe(translation)

        # Copy to clipboard if enabled
        if self.config_manager.get_config().features.copy_to_clipboard:
            self._copy_to_clipboard(translation.translated_text)

        # Speak translation if TTS enabled
        if self.config_manager.get_config().tts.enabled:
            # Check if using plugin or direct processor
            if hasattr(self.tts_processor, "speak"):
                # Plugin interface
                self.tts_processor.speak(translation.translated_text, translation.target_language)
            else:
                # Direct processor
                with self._lock:
                    self.tts_processor.speak_text(translation.translated_text)

    def _add_to_history_unsafe(self, translation: Translation):
        """Add translation to history (must be called with lock held)"""
        with self._lock:
            self.translation_history.append(translation)

        # Limit history size
        if len(self.translation_history) > 50:
            with self._lock:
                self.translation_history = self.translation_history[-50:]

    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard"""
        try:

            pyperclip.copy(text)
        except ImportError:
            logger.warning("pyperclip not available for clipboard operations")
        except Exception as e:
            logger.error("Failed to copy to clipboard", error=e)

    def show_translation_history(self):
        """Show translation history dialog"""
        logger.info("App: Show translation history method called")
        with self._lock:
            history_copy = list(self.translation_history)

        if not history_copy:

            messagebox.showinfo("История", "История переводов пуста")
            return

        # Create history display
        history_text = "\n\n".join(
            [
                f"[{t.timestamp.strftime('%H:%M:%S')}] {t.target_language.upper()}\n{t.original_text}\n→ {t.translated_text}"
                for t in history_copy[-10:]  # Last 10
            ]
        )

        messagebox.showinfo("История переводов", history_text)

    def open_settings(self):
        """Open settings window"""
        logger.info("App: Open settings method called")
        # Check if window exists and is valid
        if self.settings_window is None:
            with self._lock:
                self.settings_window = SettingsWindow(self.config_manager, self.tts_processor)
        else:
            try:
                # Check if window still exists
                if not self.settings_window.window.winfo_exists():
                    self.settings_window = SettingsWindow(self.config_manager, self.tts_processor)
            except (AttributeError, TclError):
                # Window was destroyed, create new one
                with self._lock:
                    self.settings_window = SettingsWindow(self.config_manager, self.tts_processor)

        with self._lock:
            self.settings_window.show()

    def shutdown(self):
        """Shutdown application"""
        # Publish shutdown event first
        publish_event(EventType.APPLICATION_SHUTDOWN, source="application")
        logger.log_shutdown()

        # Shutdown components in order
        self._shutdown_tray_manager()
        self._shutdown_task_queue()
        self._shutdown_event_bus()
        self._cleanup_keyboard_hooks()
        self._shutdown_tts_processor()
        self._destroy_gui()

    def _shutdown_tray_manager(self):
        """Stop system tray manager"""
        try:
            if hasattr(self, "tray_manager") and self.tray_manager:
                with self._lock:
                    self.tray_manager.stop()
        except Exception as e:
            logger.warning(f"Error stopping system tray: {e}")

    def _shutdown_task_queue(self):
        """Stop task queue processing"""
        if hasattr(self, "task_queue"):
            with self._lock:
                self.task_queue.stop(wait=True, timeout=3.0)

    def _shutdown_event_bus(self):
        """Shutdown event bus"""
        if hasattr(self, "event_bus"):
            try:
                with self._lock:
                    asyncio.run(self.event_bus.shutdown())
            except Exception as e:
                logger.warning(f"Error shutting down event bus: {e}")

    def _cleanup_keyboard_hooks(self):
        """Cleanup keyboard hooks"""
        try:
            keyboard.unhook_all()
        except (ImportError, Exception):
            pass

    def _shutdown_tts_processor(self):
        """Stop TTS processor"""
        if self.tts_processor:
            with self._lock:
                self.tts_processor.stop_speaking()

    def _destroy_gui(self):
        """Destroy GUI components"""
        with self._lock:
            self.root.destroy()

    def run(self):
        """Run the application"""
        logger.info("Starting application main loop")

        # Start system tray (optional for headless environments)
        if self.tray_manager:
            try:
                with self._lock:
                    self.tray_manager.start()
                logger.info("System tray started")
            except Exception as e:
                logger.warning(f"Could not start system tray (running in headless mode?): {e}")
                # Continue without tray in headless environments
        else:
            logger.info("Running without system tray (headless mode)")

        with self._lock:
            self.root.mainloop()

    # ConfigObserver implementation
    def on_config_changed(self, key: str, old_value, new_value) -> None:
        """Handle configuration changes"""
        logger.debug(f"App received config change: {key}")

        if key.startswith("languages.default_target"):
            with self._lock:
                self.current_language_index = new_value

        elif key.startswith("tts."):
            # Update TTS processor with new config
            if self.tts_processor:
                with self._lock:
                    self.tts_processor.update_config(self.config_manager.get_config().tts)

        elif key.startswith("features.cache_translations"):
            # Update translation processor cache setting
            if self.translation_processor:
                with self._lock:
                    self.translation_processor.enable_cache(new_value)

    def _on_translation_success(self, translation: Translation):
        """Callback for successful translation (runs in main thread)"""
        # Hide progress indicator
        with self._lock:
            self.progress_manager.hide_progress()

        if translation:
            # Show success toast
            with self._lock:
                self.progress_manager.show_success(
                    f"Translated: {translation.translated_text[:50]}{'...' if len(translation.translated_text) > 50 else ''}"
                )

            # Schedule UI update in main thread
            with self._lock:
                self.root.after(0, lambda: self._handle_translation_result(translation))

    def _on_translation_error(self, error: Exception):
        """Callback for translation error (runs in main thread)"""
        # Hide progress indicator
        with self._lock:
            self.progress_manager.hide_progress()

        # Show error-specific messages
        if isinstance(error, InvalidAreaError):
            logger.warning(f"Invalid area selected: {error.coordinates}")
            with self._lock:
                self.progress_manager.show_warning("Please select a larger area with text")
        elif isinstance(error, ScreenshotCaptureError):
            logger.error(f"Screenshot capture failed: {error.reason}")
            with self._lock:
                self.progress_manager.show_error("Failed to capture screen area")
        elif isinstance(error, TranslationFailedError):
            logger.error(f"Translation failed: {error.reason}")
            with self._lock:
                self.progress_manager.show_error("Translation service unavailable")
        elif isinstance(error, OCRError):
            logger.error(f"OCR failed: {error}")
            with self._lock:
                self.progress_manager.show_warning("Could not extract text from image")
        elif isinstance(error, TTSError):
            logger.error(f"TTS failed: {error}")
            with self._lock:
                self.progress_manager.show_warning("Text-to-speech not available")
        else:
            logger.error(f"Unexpected translation task error: {error}")
            with self._lock:
                self.progress_manager.show_error(f"Translation failed: {str(error)}")

    # Batch processing methods
    def process_multiple_areas(
        self, areas_coordinates: List[Tuple[int, int, int, int]], job_name: str = "Multiple Areas"
    ) -> str:
        """Process multiple screen areas in batch"""
        try:
            # Capture screenshots for all areas
            screenshots = []
            for x1, y1, x2, y2 in areas_coordinates:
                with self._lock:
                    screenshot_data = self.screenshot_engine.capture_area(x1, y1, x2, y2)
                if screenshot_data:
                    screenshots.append(screenshot_data)

            if not screenshots:
                with self._lock:
                    self.progress_manager.show_error("No valid screenshots captured")
                return ""

            # Create and start batch job
            with self._lock:
                job_id = self.batch_processor.create_batch_job(
                    name=job_name, screenshots=screenshots, coordinates_list=areas_coordinates
                )

            # Show progress indicator for batch job
            with self._lock:
                _ = self.progress_manager.show_progress(
                    title="Batch Processing",
                    message=f"Processing {len(screenshots)} areas...",
                    is_indeterminate=False,
                )

            # Start batch processing with callbacks
            with self._lock:
                success = self.batch_processor.start_batch_job(
                    job_id,
                    progress_callback=self._on_batch_progress,
                    completion_callback=self._on_batch_completion,
                )

            if not success:
                with self._lock:
                    self.progress_manager.show_error("Failed to start batch processing")
                return ""

            logger.info(f"Started batch processing job: {job_id}")
            return job_id

        except Exception as e:
            logger.error("Error starting batch processing", error=e)
            with self._lock:
                self.progress_manager.show_error(f"Batch processing failed: {str(e)}")
            return ""

    def get_batch_job_status(self, job_id: str) -> Optional[BatchJob]:
        """Get status of a batch job"""
        with self._lock:
            return self.batch_processor.get_batch_job(job_id)

    def cancel_batch_job(self, job_id: str) -> bool:
        """Cancel a running batch job"""
        with self._lock:
            return self.batch_processor.cancel_batch_job(job_id)

    def get_batch_results(self, job_id: str) -> List[Translation]:
        """Get results from completed batch job"""
        with self._lock:
            return self.batch_processor.get_job_results(job_id)

    def _on_batch_progress(self, job_id: str, progress: int, message: str) -> None:
        """Callback for batch processing progress"""
        if (
            hasattr(self.progress_manager, "current_progress")
            and self.progress_manager.current_progress
        ):
            progress_info = ProgressInfo(
                current=progress, total=100, message=message, is_indeterminate=False
            )
            with self._lock:
                self.progress_manager.current_progress.update(progress_info)

    def _on_batch_completion(self, job_id: str, job: BatchJob) -> None:
        """Callback for batch processing completion"""
        # Hide progress indicator
        with self._lock:
            self.progress_manager.hide_progress()

        # Show completion notification
        if job.status == BatchStatus.COMPLETED:
            success_msg = f"Batch completed: {job.completed_items}/{job.total_items} successful"
            if job.failed_items > 0:
                success_msg.append(f" ({job.failed_items} failed)")
            with self._lock:
                self.progress_manager.show_success(success_msg)
        elif job.status == BatchStatus.CANCELLED:
            with self._lock:
                self.progress_manager.show_warning("Batch processing cancelled")
        else:
            with self._lock:
                self.progress_manager.show_error(
                    f"Batch processing failed: {job.failed_items}/{job.total_items} items failed"
                )

        logger.info(f"Batch job {job_id} completed with status: {job.status}")

    def show_batch_history(self) -> None:
        """Show dialog with batch processing history"""
        with self._lock:
            jobs = self.batch_processor.get_active_jobs()
        if not jobs:

            messagebox.showinfo("Batch History", "No active batch jobs")
            return

        # Create history display
        history_text = "\n\n".join(
            [
                f"[{job.created_at.strftime('%H:%M:%S')}] {job.name}\n"
                f"Status: {job.status.value.title()}\n"
                f"Progress: {job.progress}% ({job.completed_items}/{job.total_items})\n"
                f"Success Rate: {job.success_rate:.1f}%"
                for job in jobs[-5:]  # Last 5 jobs
            ]
        )

        messagebox.showinfo("Batch Processing History", history_text)

    # Export methods
    def export_translation_history(self, format_type: str = "json") -> Optional[str]:
        """Export translation history to file"""
        try:
            with self._lock:
                history_copy = list(self.translation_history)

            if not history_copy:
                self.progress_manager.show_warning("No translation history to export")
                return None

            # Show file dialog

            file_types = [
                ("JSON files", "*.json"),
                ("CSV files", "*.csv"),
                ("Text files", "*.txt"),
                ("HTML files", "*.html"),
                ("XML files", "*.xml"),
                ("All files", "*.*"),
            ]

            with self._lock:
                suggested_name = self.export_manager.suggest_filename(
                    "translation_history", format_type
                )
            file_path = filedialog.asksaveasfilename(
                title="Export Translation History",
                defaultextension=f".{format_type}",
                filetypes=file_types,
                initialvalue=suggested_name,
            )

            if not file_path:
                return None

            # Determine format from file extension if not specified
            if file_path.endswith(".csv"):
                format_type = "csv"
            elif file_path.endswith(".txt"):
                format_type = "txt"
            elif file_path.endswith(".html"):
                format_type = "html"
            elif file_path.endswith(".xml"):
                format_type = "xml"
            else:
                format_type = "json"

            # Export
            if self.export_manager.export_translations(history_copy, file_path, format_type):
                self.progress_manager.show_success(f"History exported to {Path(file_path).name}")
                return file_path
            else:
                self.progress_manager.show_error("Export failed")
                return None

        except Exception as e:
            logger.error("Error exporting translation history", error=e)
            with self._lock:
                self.progress_manager.show_error(f"Export failed: {str(e)}")
            return None

    def export_batch_results(self, job_id: str, format_type: str = "html") -> Optional[str]:
        """Export batch job results to file"""
        try:
            with self._lock:
                job = self.batch_processor.get_batch_job(job_id)
            if not job:
                with self._lock:
                    self.progress_manager.show_error("Batch job not found")
                return None

            # Show file dialog

            file_types = [
                ("HTML files", "*.html"),
                ("JSON files", "*.json"),
                ("CSV files", "*.csv"),
                ("Text files", "*.txt"),
                ("XML files", "*.xml"),
                ("All files", "*.*"),
            ]

            safe_name = "".join(c for c in job.name if c.isalnum() or c in (" ", "-", "_")).strip()
            with self._lock:
                suggested_name = self.export_manager.suggest_filename(
                    f"batch_{safe_name}", format_type
                )

            file_path = filedialog.asksaveasfilename(
                title="Export Batch Results",
                defaultextension=f".{format_type}",
                filetypes=file_types,
                initialvalue=suggested_name,
            )

            if not file_path:
                return None

            # Determine format from file extension
            if file_path.endswith(".csv"):
                format_type = "csv"
            elif file_path.endswith(".txt"):
                format_type = "txt"
            elif file_path.endswith(".html"):
                format_type = "html"
            elif file_path.endswith(".xml"):
                format_type = "xml"
            else:
                format_type = "json"

            # Export
            if self.export_manager.export_batch_job(
                job, file_path, format_type, include_metadata=True
            ):
                self.progress_manager.show_success(
                    f"Batch results exported to {Path(file_path).name}"
                )
                return file_path
            else:
                with self._lock:
                    self.progress_manager.show_error("Batch export failed")
                return None

        except Exception as e:
            logger.error("Error exporting batch results", error=e)
            with self._lock:
                self.progress_manager.show_error(f"Batch export failed: {str(e)}")
            return None

    def _setup_performance_alerts(self) -> None:
        """Setup performance monitoring alerts"""

        def performance_alert_handler(alert_type: str, alert_data: Dict) -> None:
            """Handle performance alerts with toast notifications"""
            message = alert_data.get("message", f"Performance alert: {alert_type}")

            if alert_type in ["cpu_high", "memory_high"]:
                with self._lock:
                    self.progress_manager.show_warning(message)
            elif alert_type in ["operation_slow", "error_rate_high"]:
                with self._lock:
                    self.progress_manager.show_warning(message)

            logger.warning(f"Performance alert: {alert_type} - {message}")

        with self._lock:
            self.performance_monitor.add_alert_callback(performance_alert_handler)
        logger.info("Performance alerts configured")

    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        with self._lock:
            return self.performance_monitor.get_performance_report()

    def export_performance_metrics(self, file_path: Optional[str] = None) -> Optional[str]:
        """Export performance metrics to file"""
        try:
            if not file_path:

                file_path = filedialog.asksaveasfilename(
                    title="Export Performance Metrics",
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                    initialvalue=f"performance_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                )

            if not file_path:
                return None

            if self.performance_monitor.export_metrics(file_path):
                self.progress_manager.show_success(
                    f"Performance metrics exported to {Path(file_path).name}"
                )
                return file_path
            else:
                with self._lock:
                    self.progress_manager.show_error("Failed to export performance metrics")
                return None

        except Exception as e:
            logger.error("Error exporting performance metrics", error=e)
            with self._lock:
                self.progress_manager.show_error(f"Metrics export failed: {str(e)}")
            return None

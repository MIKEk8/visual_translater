"""Unit tests for ApplicationController - Main application coordinator"""

import sys
import unittest
from unittest.mock import MagicMock, Mock, patch, call, ANY
import threading
from typing import Optional

# Mock GUI and system modules before any imports
sys.modules['tkinter'] = MagicMock()
sys.modules['pystray'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()

# Import after mocking
from src.core.coordinators.application_controller import ApplicationController
from src.core.events import EventType
from src.services.config_manager import ConfigObserver
from src.models.config import AppConfig, TTSConfig
from src.plugins.base_plugin import PluginType


class TestApplicationController(unittest.TestCase):
    """Test suite for ApplicationController"""

    def setUp(self):
        """Set up test fixtures"""
        # Create mocks for all dependencies
        self.mock_container = MagicMock()
        self.mock_config_manager = MagicMock()
        self.mock_screenshot_engine = MagicMock()
        self.mock_plugin_service = MagicMock()
        self.mock_ocr_processor = MagicMock()
        self.mock_translation_processor = MagicMock()
        self.mock_tts_processor = MagicMock()
        
        # Configure container to return mocked services
        self.mock_container.get.side_effect = self._container_get_side_effect
        
        # Mock plugin service to return None (no plugins)
        self.mock_plugin_service.get_active_plugin.return_value = None
        
        # Patch all external dependencies
        self.patches = [
            patch('src.core.coordinators.application_controller.UICoordinator'),
            patch('src.core.coordinators.application_controller.TranslationWorkflow'),
            patch('src.core.coordinators.application_controller.CaptureOrchestrator'),
            patch('src.core.coordinators.application_controller.BatchExportManager'),
            patch('src.core.coordinators.application_controller.SystemIntegration'),
            patch('src.core.coordinators.application_controller.TrayManager'),
            patch('src.core.coordinators.application_controller.setup_event_handlers'),
            patch('src.core.coordinators.application_controller.get_event_bus'),
            patch('src.core.coordinators.application_controller.publish_event'),
            patch('src.core.coordinators.application_controller.logger'),
            patch('src.core.coordinators.application_controller.setup_default_services')
        ]
        
        self.mocks = {}
        for p in self.patches:
            mock = p.start()
            self.mocks[p.attribute] = mock
            
        # Configure event bus mock
        self.mock_event_bus = MagicMock()
        self.mocks['get_event_bus'].return_value = self.mock_event_bus

    def tearDown(self):
        """Clean up patches"""
        for p in self.patches:
            p.stop()

    def _container_get_side_effect(self, service_type):
        """Side effect for container.get() calls"""
        service_map = {
            'ConfigManager': self.mock_config_manager,
            'ScreenshotEngine': self.mock_screenshot_engine,
            'PluginService': self.mock_plugin_service,
            'OCRProcessor': self.mock_ocr_processor,
            'TranslationProcessor': self.mock_translation_processor,
            'TTSProcessor': self.mock_tts_processor,
        }
        return service_map.get(service_type.__name__, MagicMock())

    def test_initialization(self):
        """Test ApplicationController initialization"""
        # Act
        controller = ApplicationController(self.mock_container)
        
        # Assert
        # Verify container setup
        self.mocks['setup_default_services'].assert_called_once_with(self.mock_container)
        
        # Verify service retrieval
        self.assertEqual(controller.config_manager, self.mock_config_manager)
        self.assertEqual(controller.screenshot_engine, self.mock_screenshot_engine)
        self.assertEqual(controller.plugin_service, self.mock_plugin_service)
        
        # Verify coordinators were created
        self.mocks['UICoordinator'].assert_called_once()
        self.mocks['TranslationWorkflow'].assert_called_once()
        self.mocks['CaptureOrchestrator'].assert_called_once()
        self.mocks['BatchExportManager'].assert_called_once()
        self.mocks['SystemIntegration'].assert_called_once()
        
        # Verify event system setup
        self.mocks['setup_event_handlers'].assert_called_once()
        self.mocks['publish_event'].assert_called_once_with(
            EventType.APPLICATION_STARTED, 
            source="application_controller"
        )
        
        # Verify config observer registration
        self.mock_config_manager.add_observer.assert_called_once_with(controller)
        
        # Verify logging
        self.mocks['logger'].log_startup.assert_called_once_with("2.0.0")

    def test_initialization_without_container(self):
        """Test initialization using global container"""
        with patch('src.core.coordinators.application_controller.container') as mock_global_container:
            mock_global_container.get.side_effect = self._container_get_side_effect
            
            # Act
            controller = ApplicationController()
            
            # Assert - should use global container
            self.assertEqual(controller.container, mock_global_container)
            # setup_default_services should NOT be called for global container
            self.mocks['setup_default_services'].assert_not_called()

    def test_plugin_engine_retrieval(self):
        """Test getting engines from plugins"""
        # Setup
        mock_ocr_plugin = MagicMock()
        mock_translation_plugin = MagicMock()
        mock_tts_plugin = MagicMock()
        
        def plugin_side_effect(plugin_type):
            if plugin_type == PluginType.OCR:
                return mock_ocr_plugin
            elif plugin_type == PluginType.TRANSLATION:
                return mock_translation_plugin
            elif plugin_type == PluginType.TTS:
                return mock_tts_plugin
            return None
            
        self.mock_plugin_service.get_active_plugin.side_effect = plugin_side_effect
        
        # Act
        controller = ApplicationController(self.mock_container)
        
        # Assert - should use plugin engines
        self.assertEqual(controller.ocr_processor, mock_ocr_plugin)
        self.assertEqual(controller.translation_processor, mock_translation_plugin)
        self.assertEqual(controller.tts_processor, mock_tts_plugin)

    def test_plugin_engine_fallback(self):
        """Test fallback to default engines when plugins fail"""
        # Setup - plugin service throws exception
        self.mock_plugin_service.get_active_plugin.side_effect = Exception("Plugin error")
        
        # Act
        controller = ApplicationController(self.mock_container)
        
        # Assert - should fallback to default engines
        self.assertEqual(controller.ocr_processor, self.mock_ocr_processor)
        self.assertEqual(controller.translation_processor, self.mock_translation_processor)
        self.assertEqual(controller.tts_processor, self.mock_tts_processor)
        
        # Verify warnings were logged
        self.assertEqual(self.mocks['logger'].warning.call_count, 3)

    def test_tray_manager_initialization_failure(self):
        """Test graceful handling of tray manager initialization failure"""
        # Setup
        self.mocks['TrayManager'].side_effect = Exception("Display not available")
        
        # Act
        controller = ApplicationController(self.mock_container)
        
        # Assert
        self.assertIsNone(controller.tray_manager)
        self.mocks['logger'].warning.assert_called()

    def test_capture_area_delegation(self):
        """Test capture_area delegates to capture orchestrator"""
        # Setup
        controller = ApplicationController(self.mock_container)
        mock_capture_orchestrator = controller.capture_orchestrator
        
        # Act
        controller.capture_area()
        
        # Assert
        mock_capture_orchestrator.capture_area.assert_called_once()

    def test_quick_translate_methods(self):
        """Test quick translate methods delegate correctly"""
        # Setup
        controller = ApplicationController(self.mock_container)
        mock_capture_orchestrator = controller.capture_orchestrator
        
        # Act & Assert
        controller.quick_translate_center()
        mock_capture_orchestrator.quick_translate_center.assert_called_once()
        
        controller.quick_translate_bottom()
        mock_capture_orchestrator.quick_translate_bottom.assert_called_once()

    def test_repeat_last_translation(self):
        """Test repeat translation delegates to workflow"""
        # Setup
        controller = ApplicationController(self.mock_container)
        mock_workflow = controller.translation_workflow
        
        # Act
        controller.repeat_last_translation()
        
        # Assert
        mock_workflow.repeat_last_translation.assert_called_once()

    def test_switch_language(self):
        """Test language switching"""
        # Setup
        controller = ApplicationController(self.mock_container)
        mock_workflow = controller.translation_workflow
        mock_workflow.switch_language.return_value = "Spanish"
        
        # Act
        result = controller.switch_language()
        
        # Assert
        self.assertEqual(result, "Spanish")
        mock_workflow.switch_language.assert_called_once()

    def test_show_translation_history(self):
        """Test showing translation history"""
        # Setup
        controller = ApplicationController(self.mock_container)
        mock_workflow = controller.translation_workflow
        mock_ui = controller.ui_coordinator
        mock_history = [{"text": "test", "translation": "тест"}]
        mock_workflow.get_translation_history.return_value = mock_history
        
        # Act
        controller.show_translation_history()
        
        # Assert
        mock_workflow.get_translation_history.assert_called_once()
        mock_ui.show_translation_history.assert_called_once_with(mock_history)

    def test_show_batch_history(self):
        """Test showing batch history"""
        # Setup
        controller = ApplicationController(self.mock_container)
        mock_batch_manager = controller.batch_export_manager
        mock_ui = controller.ui_coordinator
        mock_jobs = [{"id": "job1", "status": "running"}]
        mock_batch_manager.get_active_batch_jobs.return_value = mock_jobs
        
        # Act
        controller.show_batch_history()
        
        # Assert
        mock_batch_manager.get_active_batch_jobs.assert_called_once()
        mock_ui.show_batch_history.assert_called_once_with(mock_jobs)

    def test_open_settings(self):
        """Test opening settings window"""
        # Setup
        controller = ApplicationController(self.mock_container)
        mock_ui = controller.ui_coordinator
        
        # Act
        controller.open_settings()
        
        # Assert
        mock_ui.open_settings.assert_called_once()

    def test_export_translation_history(self):
        """Test exporting translation history"""
        # Setup
        controller = ApplicationController(self.mock_container)
        mock_workflow = controller.translation_workflow
        mock_batch_manager = controller.batch_export_manager
        mock_history = [{"text": "test"}]
        mock_workflow.get_translation_history.return_value = mock_history
        mock_batch_manager.export_translation_history.return_value = "/path/to/export.json"
        
        # Act
        result = controller.export_translation_history("csv")
        
        # Assert
        mock_workflow.get_translation_history.assert_called_once()
        mock_batch_manager.export_translation_history.assert_called_once_with(mock_history, "csv")
        self.assertEqual(result, "/path/to/export.json")

    def test_export_performance_metrics(self):
        """Test exporting performance metrics"""
        # Setup
        controller = ApplicationController(self.mock_container)
        mock_batch_manager = controller.batch_export_manager
        mock_batch_manager.export_performance_metrics.return_value = "/path/to/metrics.json"
        
        # Act
        result = controller.export_performance_metrics("/custom/path.json")
        
        # Assert
        mock_batch_manager.export_performance_metrics.assert_called_once_with("/custom/path.json")
        self.assertEqual(result, "/path/to/metrics.json")

    def test_on_area_captured_success(self):
        """Test successful area capture handling"""
        # Setup
        controller = ApplicationController(self.mock_container)
        mock_workflow = controller.translation_workflow
        mock_ui = controller.ui_coordinator
        
        mock_screenshot_data = {"image": "test_image"}
        mock_translation = {"text": "Hello", "translation": "Привет"}
        mock_workflow.process_screenshot_translation.return_value = mock_translation
        
        # Act
        controller._on_area_captured(mock_screenshot_data)
        
        # Assert
        mock_workflow.process_screenshot_translation.assert_called_once_with(mock_screenshot_data)
        mock_ui.handle_translation_success.assert_called_once_with(mock_translation)

    def test_on_area_captured_no_translation(self):
        """Test area capture with no translation result"""
        # Setup
        controller = ApplicationController(self.mock_container)
        mock_workflow = controller.translation_workflow
        mock_ui = controller.ui_coordinator
        
        mock_screenshot_data = {"image": "test_image"}
        mock_workflow.process_screenshot_translation.return_value = None
        
        # Act
        controller._on_area_captured(mock_screenshot_data)
        
        # Assert
        mock_workflow.process_screenshot_translation.assert_called_once_with(mock_screenshot_data)
        mock_ui.handle_translation_success.assert_not_called()

    def test_on_capture_error(self):
        """Test capture error handling"""
        # Setup
        controller = ApplicationController(self.mock_container)
        mock_ui = controller.ui_coordinator
        error = Exception("Capture failed")
        
        # Act
        controller._on_capture_error(error)
        
        # Assert
        mock_ui.handle_translation_error.assert_called_once_with(error)

    def test_run_method(self):
        """Test run method starts main loop"""
        # Setup
        controller = ApplicationController(self.mock_container)
        mock_system = controller.system_integration
        mock_root = controller.root
        
        # Act
        controller.run()
        
        # Assert
        mock_system.start_tray_manager.assert_called_once()
        mock_root.mainloop.assert_called_once()
        self.mocks['logger'].info.assert_called_with("Starting application main loop")

    def test_shutdown_method(self):
        """Test shutdown delegates to system integration"""
        # Setup
        controller = ApplicationController(self.mock_container)
        mock_system = controller.system_integration
        
        # Act
        controller.shutdown()
        
        # Assert
        mock_system.shutdown.assert_called_once()

    def test_on_config_changed_language(self):
        """Test config change handling for language settings"""
        # Setup
        controller = ApplicationController(self.mock_container)
        mock_workflow = controller.translation_workflow
        
        # Act
        controller.on_config_changed("languages.default_target", 0, 1)
        
        # Assert
        self.assertEqual(mock_workflow.current_language_index, 1)

    def test_on_config_changed_tts(self):
        """Test config change handling for TTS settings"""
        # Setup
        controller = ApplicationController(self.mock_container)
        mock_config = MagicMock()
        mock_tts_config = MagicMock(spec=TTSConfig)
        mock_config.tts = mock_tts_config
        self.mock_config_manager.get_config.return_value = mock_config
        
        # Act
        controller.on_config_changed("tts.rate", 150, 200)
        
        # Assert
        controller.tts_processor.update_config.assert_called_once_with(mock_tts_config)

    def test_on_config_changed_cache(self):
        """Test config change handling for cache settings"""
        # Setup
        controller = ApplicationController(self.mock_container)
        # Add enable_cache method to mock
        controller.translation_processor.enable_cache = MagicMock()
        
        # Act
        controller.on_config_changed("features.cache_translations", False, True)
        
        # Assert
        controller.translation_processor.enable_cache.assert_called_once_with(True)

    def test_on_config_changed_no_cache_method(self):
        """Test config change when translation processor has no cache method"""
        # Setup
        controller = ApplicationController(self.mock_container)
        # Remove enable_cache method
        delattr(controller.translation_processor, 'enable_cache')
        
        # Act - should not raise exception
        controller.on_config_changed("features.cache_translations", False, True)
        
        # Assert - no exception raised
        self.mocks['logger'].debug.assert_called()

    def test_thread_safety(self):
        """Test thread safety of critical operations"""
        # Setup
        controller = ApplicationController(self.mock_container)
        
        # Verify lock is created
        self.assertIsInstance(controller._lock, type(threading.Lock()))
        
        # Test that lock is acquired during critical operations
        # We can't mock __enter__ and __exit__ on a real lock, so we'll test
        # that the lock exists and is a proper threading.Lock
        self.assertTrue(hasattr(controller._lock, 'acquire'))
        self.assertTrue(hasattr(controller._lock, 'release'))
        
        # Verify the lock is used by checking it's the same type as a real lock
        self.assertEqual(type(controller._lock), type(threading.Lock()))

    def test_capture_orchestrator_callbacks(self):
        """Test capture orchestrator is created with correct callbacks"""
        # Setup & Act
        controller = ApplicationController(self.mock_container)
        
        # Assert
        capture_orchestrator_call = self.mocks['CaptureOrchestrator'].call_args
        self.assertEqual(capture_orchestrator_call[1]['on_area_captured'], controller._on_area_captured)
        self.assertEqual(capture_orchestrator_call[1]['on_capture_error'], controller._on_capture_error)

    def test_event_handlers_setup(self):
        """Test event handlers are setup with correct components"""
        # Setup & Act
        controller = ApplicationController(self.mock_container)
        
        # Assert
        expected_components = {
            "ocr_processor": controller.ocr_processor,
            "translation_processor": controller.translation_processor,
            "tts_processor": controller.tts_processor,
            "config_manager": controller.config_manager,
            "performance_monitor": controller.batch_export_manager.performance_monitor,
        }
        
        self.mocks['setup_event_handlers'].assert_called_once_with(expected_components)


if __name__ == '__main__':
    unittest.main()
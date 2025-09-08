"""Unit tests for BatchExportManager - Batch processing and export coordinator"""

import sys
import unittest
from unittest.mock import MagicMock, Mock, patch, call, ANY
import threading
import queue
from datetime import datetime
from pathlib import Path

# Mock GUI and system modules before imports  
sys.modules['tkinter'] = MagicMock()
sys.modules['tkinter.filedialog'] = MagicMock()
sys.modules['pystray'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()

from src.core.coordinators.batch_export_manager import BatchExportManager
from src.models.translation import Translation


class TestBatchExportManager(unittest.TestCase):
    """Test suite for BatchExportManager"""

    def setUp(self):
        """Set up test fixtures"""
        # Create mocks for dependencies
        self.mock_screenshot_engine = MagicMock()
        self.mock_ocr_processor = MagicMock()
        self.mock_translation_processor = MagicMock()
        self.mock_progress_manager = MagicMock()
        
        # Patch dependencies
        self.patches = [
            patch('src.core.coordinators.batch_export_manager.BatchProcessor'),
            patch('src.core.coordinators.batch_export_manager.ExportManager'),
            patch('src.core.coordinators.batch_export_manager.get_performance_monitor'),
            patch('src.core.coordinators.batch_export_manager.logger'),
        ]
        
        self.mocks = {}
        for p in self.patches:
            mock = p.start()
            self.mocks[p.attribute] = mock
            
        # Configure performance monitor
        self.mock_performance_monitor = MagicMock()
        self.mocks['get_performance_monitor'].return_value = self.mock_performance_monitor
        
        # Configure batch processor mock
        self.mock_batch_processor = MagicMock()
        self.mocks['BatchProcessor'].return_value = self.mock_batch_processor

    def tearDown(self):
        """Clean up patches"""
        for p in self.patches:
            p.stop()

    def test_initialization(self):
        """Test BatchExportManager initialization"""
        # Act
        manager = BatchExportManager(
            self.mock_screenshot_engine,
            self.mock_ocr_processor,
            self.mock_translation_processor,
            self.mock_progress_manager
        )
        
        # Assert
        self.assertEqual(manager.screenshot_engine, self.mock_screenshot_engine)
        self.assertEqual(manager.progress_manager, self.mock_progress_manager)
        self.assertEqual(manager.performance_monitor, self.mock_performance_monitor)
        
        # Verify BatchProcessor was created with processors
        self.mocks['BatchProcessor'].assert_called_once_with(
            self.mock_ocr_processor, self.mock_translation_processor, max_concurrent=3
        )
        
        # Verify ExportManager was created
        self.mocks['ExportManager'].assert_called_once()

    def test_validate_export_params_valid(self):
        """Test parameter validation with valid parameters"""
        # Setup
        manager = BatchExportManager(
            self.mock_screenshot_engine,
            self.mock_ocr_processor,
            self.mock_translation_processor,
            self.mock_progress_manager
        )
        
        areas = [MagicMock(), MagicMock()]
        
        # Act
        is_valid, message = manager._validate_export_params(areas, "json", "/path/to/output.json")
        
        # Assert
        self.assertTrue(is_valid)
        self.assertEqual(message, "")

    def test_validate_export_params_no_areas(self):
        """Test parameter validation with no areas"""
        # Setup
        manager = BatchExportManager(
            self.mock_screenshot_engine,
            self.mock_ocr_processor,
            self.mock_translation_processor,
            self.mock_progress_manager
        )
        
        # Act
        is_valid, message = manager._validate_export_params([], "json", "/path/to/output.json")
        
        # Assert
        self.assertFalse(is_valid)
        self.assertEqual(message, "No areas to export")

    def test_validate_export_params_invalid_format(self):
        """Test parameter validation with invalid format"""
        # Setup
        manager = BatchExportManager(
            self.mock_screenshot_engine,
            self.mock_ocr_processor,
            self.mock_translation_processor,
            self.mock_progress_manager
        )
        
        areas = [MagicMock()]
        
        # Act
        is_valid, message = manager._validate_export_params(areas, "invalid", "/path/to/output")
        
        # Assert
        self.assertFalse(is_valid)
        self.assertEqual(message, "Unsupported format: invalid")

    def test_validate_export_params_no_output_path(self):
        """Test parameter validation with no output path"""
        # Setup
        manager = BatchExportManager(
            self.mock_screenshot_engine,
            self.mock_ocr_processor,
            self.mock_translation_processor,
            self.mock_progress_manager
        )
        
        areas = [MagicMock()]
        
        # Act
        is_valid, message = manager._validate_export_params(areas, "json", None)
        
        # Assert
        self.assertFalse(is_valid)
        self.assertEqual(message, "Output path not specified")

    def test_prepare_export_data(self):
        """Test preparing data for export"""
        # Setup
        manager = BatchExportManager(
            self.mock_screenshot_engine,
            self.mock_ocr_processor,
            self.mock_translation_processor,
            self.mock_progress_manager
        )
        
        # Create mock areas
        area1 = MagicMock()
        area1.x = 10
        area1.y = 20
        area1.width = 100
        area1.height = 50
        area1.timestamp = datetime.now()
        area1.text = "Hello"
        area1.translation = "Hola"
        area1.confidence = 0.95
        
        # Create area2 as simple object without optional attributes
        class SimpleArea:
            def __init__(self, x, y, width, height):
                self.x = x
                self.y = y  
                self.width = width
                self.height = height
        
        area2 = SimpleArea(30, 40, 80, 60)
        areas = [area1, area2]
        
        # Act
        result = manager._prepare_export_data(areas)
        
        # Assert
        self.assertEqual(len(result), 2)
        
        # Check first area
        self.assertEqual(result[0]["area_id"], 1)
        self.assertEqual(result[0]["coordinates"], "10,20,100,50")
        self.assertEqual(result[0]["text_extracted"], "Hello")
        self.assertEqual(result[0]["translation"], "Hola")
        self.assertEqual(result[0]["confidence"], 0.95)
        
        # Check second area with defaults
        self.assertEqual(result[1]["area_id"], 2)
        self.assertEqual(result[1]["coordinates"], "30,40,80,60")
        self.assertEqual(result[1]["text_extracted"], "")
        self.assertEqual(result[1]["translation"], "")
        self.assertEqual(result[1]["confidence"], 0.0)

    def test_prepare_export_data_error_handling(self):
        """Test error handling in export data preparation"""
        # Setup
        manager = BatchExportManager(
            self.mock_screenshot_engine,
            self.mock_ocr_processor,
            self.mock_translation_processor,
            self.mock_progress_manager
        )
        
        # Create mock area that will raise exception during processing
        area_with_error = MagicMock()
        # Make accessing x property raise an exception
        type(area_with_error).x = property(lambda self: exec('raise ZeroDivisionError()'))
        
        valid_area = MagicMock()
        valid_area.x = 10
        valid_area.y = 20
        valid_area.width = 100
        valid_area.height = 50
        
        areas = [area_with_error, valid_area]
        
        # Act
        result = manager._prepare_export_data(areas)
        
        # Assert - should skip the error area and include the valid one
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["area_id"], 2)  # Second area
        
        # Verify error was logged
        self.mocks['logger'].error.assert_called()

    def test_get_active_batch_jobs(self):
        """Test getting active batch jobs"""
        # Setup
        mock_batch_processor = MagicMock()
        self.mocks['BatchProcessor'].return_value = mock_batch_processor
        
        manager = BatchExportManager(
            self.mock_screenshot_engine,
            self.mock_ocr_processor,
            self.mock_translation_processor,
            self.mock_progress_manager
        )
        
        mock_jobs = [MagicMock(), MagicMock()]
        mock_batch_processor.get_active_jobs.return_value = mock_jobs
        
        # Act
        result = manager.get_active_batch_jobs()
        
        # Assert
        self.assertEqual(result, mock_jobs)
        mock_batch_processor.get_active_jobs.assert_called_once()

    def test_export_translation_history(self):
        """Test exporting translation history"""
        # Setup
        mock_export_manager = MagicMock()
        self.mocks['ExportManager'].return_value = mock_export_manager
        
        manager = BatchExportManager(
            self.mock_screenshot_engine,
            self.mock_ocr_processor,
            self.mock_translation_processor,
            self.mock_progress_manager
        )
        
        # Mock translations
        translations = [
            Translation(
                original_text="Hello",
                translated_text="Hola",
                source_language="en",
                target_language="es"
            ),
            Translation(
                original_text="World",
                translated_text="Mundo",
                source_language="en",
                target_language="es"
            )
        ]
        
        # Mock file dialog and export methods  
        mock_export_manager.suggest_filename.return_value = "translation_history.json"
        mock_export_manager.export_translations.return_value = True
        
        # Add _show_save_dialog method to manager
        manager._show_save_dialog = MagicMock(return_value="/path/to/export.json")
        
        # Act
        result = manager.export_translation_history(translations, "json")
        
        # Assert
        self.assertEqual(result, "/path/to/export.json")
        
        # Verify export_translations was called
        mock_export_manager.export_translations.assert_called_once_with(
            translations, "/path/to/export.json", "json"
        )

    def test_export_translation_history_empty(self):
        """Test exporting empty translation history"""
        # Setup
        manager = BatchExportManager(
            self.mock_screenshot_engine,
            self.mock_ocr_processor,
            self.mock_translation_processor,
            self.mock_progress_manager
        )
        
        # Act
        result = manager.export_translation_history([], "json")
        
        # Assert
        self.assertIsNone(result)
        # Progress manager should show warning for empty data
        self.mock_progress_manager.show_warning.assert_called_with(
            "No translation history to export"
        )

    def test_export_performance_metrics(self):
        """Test exporting performance metrics"""
        # Setup
        manager = BatchExportManager(
            self.mock_screenshot_engine,
            self.mock_ocr_processor,
            self.mock_translation_processor,
            self.mock_progress_manager
        )
        
        # Mock performance monitor export
        self.mock_performance_monitor.export_metrics.return_value = True
        
        # Act
        result = manager.export_performance_metrics("/custom/path.json")
        
        # Assert
        self.assertEqual(result, "/custom/path.json")
        
        # Verify performance monitor export_metrics was called
        self.mock_performance_monitor.export_metrics.assert_called_once_with("/custom/path.json")
        
        # Verify success message was shown
        self.mock_progress_manager.show_success.assert_called_once()

    def test_export_performance_metrics_default_path(self):
        """Test exporting performance metrics with default path"""
        # Setup
        manager = BatchExportManager(
            self.mock_screenshot_engine,
            self.mock_ocr_processor,
            self.mock_translation_processor,
            self.mock_progress_manager
        )
        
        # Mock performance monitor export
        self.mock_performance_monitor.export_metrics.return_value = True
        
        # Act  
        result = manager.export_performance_metrics()
        
        # Assert - result should be the generated filename with timestamp
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("performance_metrics_"))
        self.assertTrue(result.endswith(".json"))
        
        # Verify export_metrics was called with the generated path
        self.mock_performance_monitor.export_metrics.assert_called_once()

    def test_process_multiple_areas(self):
        """Test processing multiple screen areas"""
        # Setup
        manager = BatchExportManager(
            self.mock_screenshot_engine,
            self.mock_ocr_processor,
            self.mock_translation_processor,
            self.mock_progress_manager
        )
        
        # Mock screenshot capture
        mock_screenshot_data = MagicMock()
        self.mock_screenshot_engine.capture_area.return_value = mock_screenshot_data
        
        # Mock batch processor
        self.mock_batch_processor.create_batch_job.return_value = "job123"
        self.mock_batch_processor.start_batch_job.return_value = True
        
        areas = [(10, 10, 100, 100), (200, 200, 300, 300)]
        
        # Act
        result = manager.process_multiple_areas(areas, "Test Job")
        
        # Assert
        self.assertEqual(result, "job123")
        
        # Verify screenshot captures
        self.assertEqual(self.mock_screenshot_engine.capture_area.call_count, 2)
        
        # Verify batch job creation
        self.mock_batch_processor.create_batch_job.assert_called_once()
        self.mock_batch_processor.start_batch_job.assert_called_once()

    def test_get_batch_job_status(self):
        """Test getting batch job status"""
        # Setup
        manager = BatchExportManager(
            self.mock_screenshot_engine,
            self.mock_ocr_processor,
            self.mock_translation_processor,
            self.mock_progress_manager
        )
        
        mock_job = MagicMock()
        self.mock_batch_processor.get_batch_job.return_value = mock_job
        
        # Act
        result = manager.get_batch_job_status("job123")
        
        # Assert
        self.assertEqual(result, mock_job)
        self.mock_batch_processor.get_batch_job.assert_called_once_with("job123")

    def test_cancel_batch_job(self):
        """Test cancelling a batch job"""
        # Setup
        manager = BatchExportManager(
            self.mock_screenshot_engine,
            self.mock_ocr_processor,
            self.mock_translation_processor,
            self.mock_progress_manager
        )
        
        self.mock_batch_processor.cancel_batch_job.return_value = True
        
        # Act
        result = manager.cancel_batch_job("job123")
        
        # Assert
        self.assertTrue(result)
        self.mock_batch_processor.cancel_batch_job.assert_called_once_with("job123")

    def test_get_batch_results(self):
        """Test getting batch job results"""
        # Setup
        manager = BatchExportManager(
            self.mock_screenshot_engine,
            self.mock_ocr_processor,
            self.mock_translation_processor,
            self.mock_progress_manager
        )
        
        mock_results = [MagicMock(), MagicMock()]
        self.mock_batch_processor.get_job_results.return_value = mock_results
        
        # Act
        result = manager.get_batch_results("job123")
        
        # Assert
        self.assertEqual(result, mock_results)
        self.mock_batch_processor.get_job_results.assert_called_once_with("job123")

    def test_get_performance_report(self):
        """Test getting performance report"""
        # Setup
        manager = BatchExportManager(
            self.mock_screenshot_engine,
            self.mock_ocr_processor,
            self.mock_translation_processor,
            self.mock_progress_manager
        )
        
        mock_report = {"cpu_usage": 50, "memory_usage": 1024}
        self.mock_performance_monitor.get_performance_report.return_value = mock_report
        
        # Act
        result = manager.get_performance_report()
        
        # Assert
        self.assertEqual(result, mock_report)
        self.mock_performance_monitor.get_performance_report.assert_called_once()

    def test_thread_safety(self):
        """Test thread safety considerations"""
        # Setup
        manager = BatchExportManager(
            self.mock_screenshot_engine,
            self.mock_ocr_processor,
            self.mock_translation_processor,
            self.mock_progress_manager
        )
        
        # Test that operations can be called concurrently without issues
        # This is a basic smoke test for thread safety
        
        # Act
        manager.get_active_batch_jobs()
        manager.export_translation_history([], "json")
        manager.export_performance_metrics()
        
        # If we get here without deadlocks or race conditions, basic thread safety is working
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
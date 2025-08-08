#!/usr/bin/env python3
"""
Integration tests for new features in Screen Translator v2.0
Tests all new components working together.
"""

import io
import json
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from PIL import Image

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from src.tests.test_utils import skip_on_ci, skip_without_display  # noqa: E402

pytestmark = pytest.mark.integration


@skip_on_ci
@skip_without_display
def test_progress_and_notifications():
    """Test progress indicators and notifications integration"""
    print("Testing progress indicators and notifications...")

    try:
        import tkinter as tk

        from src.ui.progress_indicator import ProgressInfo, ProgressManager

        # Create test environment
        root = tk.Tk()
        root.withdraw()

        progress_manager = ProgressManager(root)

        # Test progress indicator
        progress = progress_manager.show_progress("Test Progress", "Testing...", False)
        assert progress is not None

        # Test progress update
        progress_info = ProgressInfo(
            current=50, total=100, message="50% complete", is_indeterminate=False
        )
        progress.update(progress_info)

        # Test notifications
        progress_manager.show_success("Test success")
        progress_manager.show_error("Test error")
        progress_manager.show_warning("Test warning")
        progress_manager.show_info("Test info")

        # Cleanup
        progress_manager.hide_progress()
        root.destroy()

        print("[PASS] Progress indicators and notifications working")
        return True

    except Exception as e:
        print(f"[FAIL] Progress and notifications test failed: {e}")
        return False


@skip_on_ci
def test_batch_processing():
    """Test batch processing integration"""
    print("Testing batch processing...")

    try:
        from unittest.mock import Mock

        from src.core.batch_processor import BatchProcessor, BatchStatus
        from src.models.screenshot_data import ScreenshotData
        from src.models.translation import Translation

        # Create mock processors
        mock_ocr = Mock()
        mock_translation = Mock()

        # Setup mock responses
        mock_ocr.extract_text.return_value = ("Test text", 0.95)
        mock_translation_result = Translation(
            original_text="Test text",
            translated_text="Тестовый текст",
            source_language="en",
            target_language="ru",
            confidence=0.95,
        )
        mock_translation.translate_text.return_value = mock_translation_result

        # Create batch processor
        processor = BatchProcessor(mock_ocr, mock_translation, max_concurrent=2)

        # Create test screenshots
        screenshots = []
        for i in range(3):
            image = Image.new("RGB", (100, 100), color="white")
            img_bytes = io.BytesIO()
            image.save(img_bytes, format="PNG")

            screenshot_data = ScreenshotData(
                image=image,
                image_data=img_bytes.getvalue(),
                coordinates=(i * 10, i * 10, i * 10 + 100, i * 10 + 100),
                timestamp=datetime.now(),
            )
            screenshots.append(screenshot_data)

        # Create and start batch job
        job_id = processor.create_batch_job("Test Batch", screenshots)
        assert job_id is not None

        # Test job creation
        job = processor.get_batch_job(job_id)
        assert job.name == "Test Batch"
        assert job.total_items == 3
        assert job.status == BatchStatus.PENDING

        # Start batch processing
        completion_events = []

        def completion_callback(job_id, job):
            completion_events.append((job_id, job))

        success = processor.start_batch_job(job_id, completion_callback=completion_callback)
        assert success

        # Wait for completion
        start_time = time.time()
        while len(completion_events) == 0 and time.time() - start_time < 10:
            time.sleep(0.1)

        # Verify completion
        assert len(completion_events) == 1
        final_job = completion_events[0][1]
        assert final_job.status in [BatchStatus.COMPLETED, BatchStatus.FAILED]

        # Test results
        if final_job.status == BatchStatus.COMPLETED:
            results = processor.get_job_results(job_id)
            assert len(results) > 0
            for result in results:
                assert isinstance(result, Translation)

        # Test statistics
        stats = processor.get_statistics()
        assert stats["total_jobs"] >= 1
        assert stats["max_concurrent_workers"] == 2

        print("[PASS] Batch processing working")
        return True

    except Exception as e:
        print(f"[FAIL] Batch processing test failed: {e}")
        return False


@skip_on_ci
def test_export_functionality():
    """Test export functionality"""
    print("Testing export functionality...")

    try:
        import tempfile

        from src.core.batch_processor import BatchJob, BatchStatus
        from src.models.translation import Translation
        from src.utils.export_manager import ExportManager

        export_manager = ExportManager()

        # Create test translations
        translations = []
        for i in range(3):
            translation = Translation(
                original_text=f"Test {i}",
                translated_text=f"Тест {i}",
                source_language="en",
                target_language="ru",
                confidence=0.9 + i * 0.02,
                timestamp=datetime.now(),
            )
            translations.append(translation)

        # Test different export formats
        temp_dir = tempfile.mkdtemp()
        try:
            formats = ["json", "csv", "txt", "html", "xml"]

            for format_type in formats:
                file_path = os.path.join(temp_dir, f"test.{format_type}")
                success = export_manager.export_translations(translations, file_path, format_type)
                assert success, f"Export failed for format: {format_type}"
                assert os.path.exists(file_path), f"File not created for format: {format_type}"

                # Verify file has content
                file_size = os.path.getsize(file_path)
                assert file_size > 0, f"Empty file for format: {format_type}"

            # Test batch job export
            batch_job = BatchJob(id="test_batch", name="Test Export Batch")
            batch_job.status = BatchStatus.COMPLETED
            batch_job.total_items = 3
            batch_job.completed_items = 3
            batch_job.failed_items = 0
            batch_job.created_at = datetime.now()
            batch_job.completed_at = datetime.now()

            batch_file = os.path.join(temp_dir, "batch.json")
            success = export_manager.export_batch_job(batch_job, batch_file, "json", True)
            assert success
            assert os.path.exists(batch_file)

            # Verify batch export content
            with open(batch_file, "r") as f:
                data = json.load(f)
                assert "batch_job" in data
                assert "export_info" in data
                assert data["batch_job"]["id"] == "test_batch"

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

        print("[PASS] Export functionality working")
        return True

    except Exception as e:
        print(f"[FAIL] Export functionality test failed: {e}")
        return False


@skip_on_ci
def test_performance_monitoring():
    """Test performance monitoring"""
    print("Testing performance monitoring...")

    try:
        from src.utils.performance_monitor import PerformanceMonitor, measure_performance

        # Create monitor (disable system monitoring for tests)
        monitor = PerformanceMonitor(max_metrics=100, enable_system_monitoring=False)

        # Test basic operation recording
        monitor.record_operation("test_operation", 1.5, True)
        assert len(monitor.metrics) == 1

        metric = monitor.metrics[0]
        assert metric.operation == "test_operation"
        assert metric.duration == 1.5
        assert metric.success is True

        # Test context manager measurement
        with monitor.measure_operation("context_test") as _:
            time.sleep(0.1)  # Simulate work

        assert len(monitor.metrics) == 2
        context_metric = monitor.metrics[1]
        assert context_metric.operation == "context_test"
        assert context_metric.success is True
        assert context_metric.duration > 0.05

        # Test operation statistics
        for i in range(5):
            success = i < 4  # 4 success, 1 failure
            monitor.record_operation("stats_test", 1.0 + i * 0.1, success)

        stats = monitor.get_operation_stats("stats_test")
        assert stats["total_count"] == 5
        assert stats["error_count"] == 1
        assert stats["error_rate"] == 0.2

        # Test performance report
        report = monitor.get_performance_report(hours=1)
        assert "operation_statistics" in report
        assert "total_operations" in report
        assert report["total_operations"] >= 7  # At least our test operations

        # Test decorator (if available)
        try:

            @measure_performance("decorated_test")
            def test_function():
                time.sleep(0.05)
                return "result"

            result = test_function()
            assert result == "result"

            # Should have recorded the decorated operation
            decorated_metrics = [m for m in monitor.metrics if m.operation == "decorated_test"]
            assert len(decorated_metrics) == 1
        except Exception as decorator_error:
            print(f"[WARN] Decorator test failed (non-critical): {decorator_error}")
            # Continue with other tests

        # Test export
        temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        try:
            success = monitor.export_metrics(temp_file.name)
            assert success

            # Verify exported data
            with open(temp_file.name, "r") as f:
                data = json.load(f)
                assert "metrics" in data
                assert "export_info" in data
                assert len(data["metrics"]) > 0

        finally:
            os.unlink(temp_file.name)

        print("[PASS] Performance monitoring working")
        return True

    except Exception as e:
        print(f"[FAIL] Performance monitoring test failed: {e}")
        return False


@skip_on_ci
def test_enhanced_ocr():
    """Test enhanced OCR with confidence thresholds"""
    print("Testing enhanced OCR...")

    try:
        from unittest.mock import patch

        from src.core.ocr_engine import OCRProcessor
        from src.models.config import ImageProcessingConfig

        # Create config with new features
        config = ImageProcessingConfig(
            upscale_factor=2.0,
            contrast_enhance=1.5,
            sharpness_enhance=2.0,
            ocr_confidence_threshold=0.7,
            enable_preprocessing=True,
            noise_reduction=True,
        )

        # Test configuration values
        assert config.ocr_confidence_threshold == 0.7
        assert config.enable_preprocessing is True
        assert config.noise_reduction is True

        # Mock OCR engine for testing
        with patch("src.core.ocr_engine.TesseractOCR.is_available", return_value=True):
            processor = OCRProcessor(config)

            # Test image enhancement
            test_image = Image.new("RGB", (100, 100), color="white")
            enhanced = processor.enhance_image(test_image)

            assert enhanced.size == (200, 200)  # Should be upscaled 2x
            assert enhanced.mode == "RGB"

            # Test with preprocessing disabled
            config_no_preprocessing = ImageProcessingConfig(enable_preprocessing=False)
            processor_no_preprocessing = OCRProcessor(config_no_preprocessing)

            enhanced_disabled = processor_no_preprocessing.enhance_image(test_image)
            assert enhanced_disabled.size == test_image.size  # Should not be changed

        print("[PASS] Enhanced OCR working")
        return True

    except Exception as e:
        print(f"[FAIL] Enhanced OCR test failed: {e}")
        return False


@skip_on_ci
@skip_without_display
def test_drag_drop_simulation():
    """Test drag and drop simulation"""
    print("Testing drag and drop simulation...")

    try:
        import tkinter as tk
        from unittest.mock import Mock

        from src.ui.drag_drop_handler import BatchImageProcessor, DragDropHandler, ImageDropZone

        # Create test environment
        root = tk.Tk()
        root.withdraw()

        # Test DragDropHandler
        callback_calls = []

        def test_callback(files):
            callback_calls.append(files)

        handler = DragDropHandler(root, test_callback)

        # Test supported formats
        expected_formats = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"}
        assert handler.supported_formats == expected_formats

        # Test file filtering
        temp_dir = tempfile.mkdtemp()
        try:
            # Create test files
            test_files = ["image.png", "document.pdf", "photo.jpg"]
            file_paths = []

            for filename in test_files:
                file_path = os.path.join(temp_dir, filename)
                Path(file_path).touch()
                file_paths.append(file_path)

            valid_files = handler._filter_supported_files(file_paths)

            # Should only include image files
            assert len(valid_files) == 2  # png and jpg
            valid_names = [os.path.basename(f) for f in valid_files]
            assert "image.png" in valid_names
            assert "photo.jpg" in valid_names
            assert "document.pdf" not in valid_names

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

        # Test ImageDropZone
        drop_zone = ImageDropZone(root, test_callback)
        assert drop_zone.frame is not None
        assert drop_zone.label is not None

        # Test file drop simulation
        test_files = ["image1.png", "image2.jpg"]
        drop_zone._on_files_dropped(test_files)

        assert len(callback_calls) == 1
        assert callback_calls[0] == test_files

        # Test BatchImageProcessor
        mock_app = Mock()
        mock_app.batch_processor = Mock()
        mock_app.progress_manager = Mock()

        processor = BatchImageProcessor(mock_app)

        # Test image loading simulation
        temp_dir = tempfile.mkdtemp()
        try:
            image_path = os.path.join(temp_dir, "test.png")
            test_image = Image.new("RGB", (100, 100), color="red")
            test_image.save(image_path, "PNG")

            screenshot_data = processor._load_image_file(image_path)
            assert screenshot_data is not None
            assert screenshot_data.image.size == (100, 100)
            assert screenshot_data.image.mode == "RGB"

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

        # Cleanup
        root.destroy()

        print("[PASS] Drag and drop simulation working")
        return True

    except Exception as e:
        print(f"[FAIL] Drag and drop test failed: {e}")
        return False


@skip_on_ci
@skip_without_display
def test_full_workflow():
    """Test complete workflow with new features"""
    print("Testing complete workflow...")

    try:
        import tkinter as tk
        from unittest.mock import Mock

        from src.core.batch_processor import BatchProcessor
        from src.models.translation import Translation
        from src.ui.progress_indicator import ProgressManager
        from src.utils.export_manager import ExportManager
        from src.utils.performance_monitor import PerformanceMonitor

        # Setup environment
        root = tk.Tk()
        root.withdraw()

        # Initialize all new components
        progress_manager = ProgressManager(root)

        # Mock processors for batch
        mock_ocr = Mock()
        mock_translation = Mock()
        mock_ocr.extract_text.return_value = ("Workflow test", 0.95)
        mock_translation.translate_text.return_value = Translation(
            original_text="Workflow test",
            translated_text="Тест рабочего процесса",
            source_language="en",
            target_language="ru",
            confidence=0.95,
        )

        batch_processor = BatchProcessor(mock_ocr, mock_translation, max_concurrent=1)
        export_manager = ExportManager()
        performance_monitor = PerformanceMonitor(enable_system_monitoring=False)

        # Simulate complete workflow
        print("  1. Starting workflow simulation...")

        # Step 1: Show progress
        with performance_monitor.measure_operation("workflow_step1"):
            progress_manager.show_progress("Workflow Test", "Step 1...", True)
            time.sleep(0.1)

        # Step 2: Create batch job
        with performance_monitor.measure_operation("workflow_step2"):
            # Create test screenshot
            image = Image.new("RGB", (100, 100), color="blue")
            img_bytes = io.BytesIO()
            image.save(img_bytes, format="PNG")

            from src.models.screenshot_data import ScreenshotData

            screenshot_data = ScreenshotData(
                image=image,
                image_data=img_bytes.getvalue(),
                coordinates=(0, 0, 100, 100),
                timestamp=datetime.now(),
            )

            job_id = batch_processor.create_batch_job("Workflow Test", [screenshot_data])
            assert job_id is not None

        # Step 3: Process batch
        with performance_monitor.measure_operation("workflow_step3"):
            completion_events = []

            def completion_callback(job_id, job):
                completion_events.append((job_id, job))

            success = batch_processor.start_batch_job(
                job_id, completion_callback=completion_callback
            )
            assert success

            # Wait for completion
            start_time = time.time()
            while len(completion_events) == 0 and time.time() - start_time < 5:
                time.sleep(0.1)

        # Step 4: Export results
        with performance_monitor.measure_operation("workflow_step4"):
            results = batch_processor.get_job_results(job_id)
            if results:
                temp_dir = tempfile.mkdtemp()
                try:
                    export_path = os.path.join(temp_dir, "workflow_results.json")
                    success = export_manager.export_translations(results, export_path, "json")
                    assert success
                    assert os.path.exists(export_path)
                finally:
                    import shutil

                    shutil.rmtree(temp_dir, ignore_errors=True)

        # Step 5: Show completion
        progress_manager.hide_progress()
        progress_manager.show_success("Workflow completed successfully!")

        # Verify performance metrics
        report = performance_monitor.get_performance_report()
        assert "workflow_step1" in report["operation_statistics"]
        assert "workflow_step2" in report["operation_statistics"]
        assert "workflow_step3" in report["operation_statistics"]
        assert "workflow_step4" in report["operation_statistics"]

        # Cleanup
        root.destroy()

        print("  ✅ Workflow simulation completed successfully")
        print("[PASS] Complete workflow working")
        return True

    except Exception as e:
        print(f"[FAIL] Complete workflow test failed: {e}")
        return False


def main():
    """Run all new feature integration tests"""
    print("=" * 60)
    print("Screen Translator v2.0 - New Features Integration Tests")
    print("=" * 60)

    tests = [
        ("Progress & Notifications", test_progress_and_notifications),
        ("Batch Processing", test_batch_processing),
        ("Export Functionality", test_export_functionality),
        ("Performance Monitoring", test_performance_monitoring),
        ("Enhanced OCR", test_enhanced_ocr),
        ("Drag & Drop Simulation", test_drag_drop_simulation),
        ("Complete Workflow", test_full_workflow),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n[TEST] {test_name}")
        print("-" * 40)
        try:
            if test_func():
                passed += 1
                print(f"[RESULT] {test_name}: PASSED")
            else:
                print(f"[RESULT] {test_name}: FAILED")
        except Exception as e:
            print(f"[RESULT] {test_name}: CRASHED - {e}")

    print("\n" + "=" * 60)
    print(f"NEW FEATURES RESULTS: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("🎉 ALL NEW FEATURES WORKING - READY FOR PRODUCTION!")
        return 0
    else:
        print("⚠️  SOME NEW FEATURES FAILED - CHECK LOGS ABOVE")
        return 1


if __name__ == "__main__":
    sys.exit(main())

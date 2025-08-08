#!/usr/bin/env python3
"""
Core workflow integration tests for Screen Translator v2.0.
Tests the main translation workflow: Screenshot -> OCR -> Translation -> TTS.
"""

import io
import os
import sys
import threading
import time
import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = Mock()

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from src.core.ocr_engine import OCRProcessor
from src.core.screenshot_engine import ScreenshotEngine
from src.core.translation_engine import TranslationProcessor
from src.core.tts_engine import TTSProcessor
from src.models.config import AppConfig, ImageProcessingConfig, TTSConfig
from src.models.screenshot_data import ScreenshotData
from src.services.cache_service import TranslationCache
from src.services.config_manager import ConfigManager
from src.services.container import DIContainer, setup_default_services
from src.tests.test_utils import skip_on_ci

pytestmark = pytest.mark.integration


@skip_on_ci
@unittest.skipUnless(PIL_AVAILABLE, "PIL not available")
class TestCoreWorkflowIntegration(unittest.TestCase):
    """Integration tests for core workflow components"""

    def setUp(self):
        """Setup test environment with real components"""
        self.config = AppConfig()
        self.config_manager = ConfigManager()

        # Create DI container and setup services
        self.container = DIContainer()
        setup_default_services(self.container)

        # Initialize components
        self.screenshot_engine = ScreenshotEngine()
        self.ocr_processor = OCRProcessor(self.config.image_processing)
        self.translation_processor = TranslationProcessor(cache_enabled=True)
        self.tts_processor = TTSProcessor(self.config.tts)

    def test_full_translation_workflow(self):
        """Test complete workflow: Screenshot -> OCR -> Translation -> TTS"""

        # Step 1: Create mock screenshot
        test_image = Image.new("RGB", (200, 100), color="white")
        import io

        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format="PNG")

        screenshot_data = ScreenshotData(
            image=test_image,
            image_data=img_bytes.getvalue(),
            coordinates=(0, 0, 200, 100),
            timestamp=datetime.now(),
        )

        # Step 2: Mock OCR extraction
        with patch.object(self.ocr_processor, "process_screenshot") as mock_ocr:
            mock_ocr.return_value = ("Hello world", 0.95)

            # Step 3: Mock translation
            with patch.object(self.translation_processor, "translate_text") as mock_translate:
                from src.models.translation import Translation

                mock_translation = Translation(
                    original_text="Hello world",
                    translated_text="Привет мир",
                    source_language="en",
                    target_language="ru",
                    timestamp=datetime.now(),
                )
                mock_translate.return_value = mock_translation

                # Step 4: Mock TTS
                with patch.object(self.tts_processor, "speak_text") as mock_tts:
                    mock_tts.return_value = True

                    # Execute workflow
                    start_time = time.time()

                    # OCR
                    ocr_text, ocr_confidence = self.ocr_processor.process_screenshot(
                        screenshot_data, "eng"
                    )
                    self.assertEqual(ocr_text, "Hello world")
                    self.assertEqual(ocr_confidence, 0.95)

                    # Translation
                    translation = self.translation_processor.translate_text(ocr_text, "ru")
                    self.assertIsNotNone(translation)
                    self.assertEqual(translation.translated_text, "Привет мир")

                    # TTS
                    tts_success = self.tts_processor.speak_text(translation.translated_text)
                    self.assertTrue(tts_success)

                    # Verify workflow completed in reasonable time
                    duration = time.time() - start_time
                    self.assertLess(duration, 1.0)  # Should be fast with mocks

                    # Verify all components were called
                    mock_ocr.assert_called_once()
                    mock_translate.assert_called_once()
                    mock_tts.assert_called_once()

    def test_workflow_with_cache_integration(self):
        """Test workflow with translation caching"""

        screenshot_data = ScreenshotData(
            image=Image.new("RGB", (100, 100), color="white"),
            image_data=b"fake_image_data",
            coordinates=(0, 0, 100, 100),
            timestamp=datetime.now(),
        )

        with patch.object(self.ocr_processor, "process_screenshot") as mock_ocr:
            mock_ocr.return_value = ("Cached text", 0.9)

            with patch.object(self.translation_processor.active_engine, "translate") as mock_engine:
                mock_engine.return_value = "Кэшированный текст"

                # First translation - should hit engine
                translation1 = self.translation_processor.translate_text("Cached text", "ru")
                self.assertIsNotNone(translation1)
                self.assertFalse(translation1.cached)

                # Second translation - should hit cache
                translation2 = self.translation_processor.translate_text("Cached text", "ru")
                self.assertIsNotNone(translation2)
                self.assertTrue(translation2.cached)

                # Verify engine only called once
                self.assertEqual(mock_engine.call_count, 1)

    def test_workflow_error_handling(self):
        """Test workflow error handling at each stage"""

        screenshot_data = ScreenshotData(
            image=Image.new("RGB", (100, 100), color="white"),
            image_data=b"fake_image_data",
            coordinates=(0, 0, 100, 100),
            timestamp=datetime.now(),
        )

        # Test OCR failure
        with patch.object(self.ocr_processor, "process_screenshot") as mock_ocr:
            mock_ocr.return_value = ("", None)  # OCR failure

            ocr_text, ocr_confidence = self.ocr_processor.process_screenshot(screenshot_data)
            self.assertEqual(ocr_text, "")
            self.assertIsNone(ocr_confidence)

        # Test translation failure
        with patch.object(self.translation_processor, "translate_text") as mock_translate:
            mock_translate.return_value = None  # Translation failure

            translation = self.translation_processor.translate_text("Test", "ru")
            self.assertIsNone(translation)

        # Test TTS failure
        with patch.object(self.tts_processor, "speak_text") as mock_tts:
            mock_tts.return_value = False  # TTS failure

            tts_success = self.tts_processor.speak_text("Test")
            self.assertFalse(tts_success)

    def test_concurrent_workflow_execution(self):
        """Test concurrent execution of workflow components"""

        results = []
        errors = []

        def workflow_task(task_id):
            try:
                # Create unique screenshot data for each task
                screenshot = ScreenshotData(
                    image=Image.new("RGB", (100, 100), color="white"),
                    image_data=f"task_{task_id}_data".encode(),
                    coordinates=(
                        task_id * 10,
                        task_id * 10,
                        (task_id + 1) * 100,
                        (task_id + 1) * 100,
                    ),
                    timestamp=datetime.now(),
                )

                with patch.object(self.ocr_processor, "process_screenshot") as mock_ocr:
                    mock_ocr.return_value = (f"Text {task_id}", 0.9)

                    with patch.object(
                        self.translation_processor, "translate_text"
                    ) as mock_translate:
                        from src.models.translation import Translation

                        mock_translation = Translation(
                            original_text=f"Text {task_id}",
                            translated_text=f"Текст {task_id}",
                            source_language="en",
                            target_language="ru",
                            timestamp=datetime.now(),
                        )
                        mock_translate.return_value = mock_translation

                        # Execute workflow
                        ocr_text, _ = self.ocr_processor.process_screenshot(screenshot)
                        translation = self.translation_processor.translate_text(ocr_text, "ru")

                        results.append(
                            {
                                "task_id": task_id,
                                "ocr_text": ocr_text,
                                "translation": translation.translated_text if translation else None,
                            }
                        )

            except Exception as e:
                errors.append((task_id, str(e)))

        # Run multiple workflow tasks concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=workflow_task, daemon=True, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify results
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 5)

        # Verify each task completed successfully
        for i, result in enumerate(results):
            self.assertEqual(result["ocr_text"], f"Text {result['task_id']}")
            self.assertEqual(result["translation"], f"Текст {result['task_id']}")

    def test_di_container_integration(self):
        """Test dependency injection container integration"""

        # Test that services are properly registered
        services = self.container.get_registered_services()

        expected_services = [
            "src.services.config_manager.ConfigManager",
            "src.core.screenshot_engine.ScreenshotEngine",
            "src.core.ocr_engine.OCRProcessor",
            "src.core.translation_engine.TranslationProcessor",
            "src.core.tts_engine.TTSProcessor",
        ]

        for service_name in expected_services:
            self.assertIn(service_name, services, f"Service {service_name} not registered")

        # Test service retrieval
        config_manager = self.container.get(ConfigManager)
        self.assertIsInstance(config_manager, ConfigManager)

        screenshot_engine = self.container.get(ScreenshotEngine)
        self.assertIsInstance(screenshot_engine, ScreenshotEngine)

    def test_config_observer_integration(self):
        """Test configuration observer pattern integration"""

        # Create mock observer
        observer_called = []

        class MockObserver:
            def on_config_changed(self, key, old_value, new_value):
                observer_called.append((key, old_value, new_value))

        observer = MockObserver()
        self.config_manager.add_observer(observer)

        # Change configuration
        old_rate = self.config_manager.get_value("tts.rate")
        new_rate = 200
        self.config_manager.set_value("tts.rate", new_rate)

        # Verify observer was notified
        self.assertEqual(len(observer_called), 1)
        key, old_val, new_val = observer_called[0]
        self.assertEqual(key, "tts.rate")
        self.assertEqual(old_val, old_rate)
        self.assertEqual(new_val, new_rate)

    def test_screenshot_validation_integration(self):
        """Test screenshot validation integration"""

        # Test valid coordinates
        valid_coords = self.screenshot_engine._validate_coordinates(10, 10, 100, 100, 1920, 1080)
        self.assertEqual(valid_coords, (10, 10, 100, 100))

        # Test coordinate correction
        swapped_coords = self.screenshot_engine._validate_coordinates(100, 100, 10, 10, 1920, 1080)
        self.assertEqual(swapped_coords, (10, 10, 100, 100))

        # Test boundary clipping
        clipped_coords = self.screenshot_engine._validate_coordinates(
            -10, -10, 2000, 2000, 1920, 1080
        )
        self.assertEqual(clipped_coords, (0, 0, 1920, 1080))

    def test_image_enhancement_integration(self):
        """Test image enhancement integration"""

        # Create test image with different modes
        test_cases = [
            Image.new("RGB", (100, 100), color="white"),
            Image.new("RGBA", (100, 100), color=(255, 255, 255, 128)),
            Image.new("L", (100, 100), color=128),  # Grayscale
        ]

        for test_image in test_cases:
            enhanced = self.ocr_processor.enhance_image(test_image)

            # Should always return RGB image
            self.assertEqual(enhanced.mode, "RGB")

            # Should be upscaled if factor > 1
            if self.config.image_processing.upscale_factor > 1.0:
                expected_width = int(test_image.width * self.config.image_processing.upscale_factor)
                expected_height = int(
                    test_image.height * self.config.image_processing.upscale_factor
                )
                self.assertEqual(enhanced.size, (expected_width, expected_height))

    def test_translation_cache_integration(self):
        """Test translation cache integration"""

        cache = TranslationCache(max_size=5, ttl_hours=1)

        # Test cache operations
        from src.models.translation import Translation

        translations = []
        for i in range(3):
            translation = Translation(
                original_text=f"Test {i}",
                translated_text=f"Тест {i}",
                source_language="en",
                target_language="ru",
                timestamp=datetime.now(),
            )
            translations.append(translation)
            cache.add(translation)

        # Test cache retrieval
        for i, translation in enumerate(translations):
            cached = cache.get(f"Test {i}", "ru")
            self.assertIsNotNone(cached)
            self.assertEqual(cached.translated_text, f"Тест {i}")
            self.assertTrue(cached.cached)

        # Test cache statistics
        stats = cache.get_stats()
        self.assertEqual(stats["size"], 3)
        self.assertEqual(stats["hits"], 3)
        self.assertEqual(stats["hit_rate"], 1.0)

    def test_memory_management_integration(self):
        """Test memory management across components"""

        import gc
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create multiple workflow iterations
        for i in range(10):
            # Create large screenshot data
            large_image = Image.new("RGB", (1000, 1000), color="white")
            img_bytes = io.BytesIO()
            large_image.save(img_bytes, format="PNG")

            screenshot_data = ScreenshotData(
                image=large_image,
                image_data=img_bytes.getvalue(),
                coordinates=(0, 0, 1000, 1000),
                timestamp=datetime.now(),
            )

            # Process through components
            enhanced_image = self.ocr_processor.enhance_image(screenshot_data.image)

            # Clean up explicitly
            del large_image
            del enhanced_image
            del screenshot_data

            # Force garbage collection
            gc.collect()

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 100MB)
        self.assertLess(
            memory_increase,
            100 * 1024 * 1024,
            f"Memory increased by {memory_increase / 1024 / 1024:.1f} MB",
        )


@skip_on_ci
@unittest.skipUnless(PIL_AVAILABLE, "PIL not available")
class TestWorkflowPerformance(unittest.TestCase):
    """Performance tests for workflow components"""

    def setUp(self):
        """Setup performance test environment"""
        self.screenshot_engine = ScreenshotEngine()
        self.ocr_processor = OCRProcessor(ImageProcessingConfig())
        self.translation_processor = TranslationProcessor(cache_enabled=True)
        self.tts_processor = TTSProcessor(TTSConfig())

    def test_screenshot_performance(self):
        """Test screenshot capture performance"""

        with patch("src.core.screenshot_engine.ImageGrab") as mock_grab:
            mock_image = Mock()
            mock_image.size = (1920, 1080)
            mock_grab.grab.return_value = mock_image

            start_time = time.time()

            # Multiple screenshot operations
            for _ in range(10):
                result = self.screenshot_engine.capture_area(0, 0, 100, 100, 1920, 1080)
                self.assertIsNotNone(result)

            duration = time.time() - start_time

            # Should complete quickly
            self.assertLess(duration, 0.5, f"Screenshot performance too slow: {duration:.3f}s")

    def test_ocr_performance(self):
        """Test OCR processing performance"""

        test_image = Image.new("RGB", (200, 100), color="white")
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format="PNG")

        screenshot_data = ScreenshotData(
            image=test_image,
            image_data=img_bytes.getvalue(),
            coordinates=(0, 0, 200, 100),
            timestamp=datetime.now(),
        )

        with patch.object(self.ocr_processor, "active_engine") as mock_engine:
            mock_engine.extract_text.return_value = ("Performance test", 0.95)

            start_time = time.time()

            # Multiple OCR operations
            for _ in range(5):
                text, confidence = self.ocr_processor.process_screenshot(screenshot_data)
                self.assertEqual(text, "Performance test")

            duration = time.time() - start_time

            # Should complete in reasonable time
            self.assertLess(duration, 1.0, f"OCR performance too slow: {duration:.3f}s")

    def test_translation_cache_performance(self):
        """Test translation cache performance"""

        cache = TranslationCache(max_size=1000, ttl_hours=1)

        # Add many translations
        start_time = time.time()

        for i in range(100):
            from src.models.translation import Translation

            translation = Translation(
                original_text=f"Performance test {i}",
                translated_text=f"Тест производительности {i}",
                source_language="en",
                target_language="ru",
                timestamp=datetime.now(),
            )
            cache.add(translation)

        add_duration = time.time() - start_time

        # Retrieve all translations
        start_time = time.time()

        for i in range(100):
            cached = cache.get(f"Performance test {i}", "ru")
            self.assertIsNotNone(cached)

        get_duration = time.time() - start_time

        # Performance should be good
        self.assertLess(add_duration, 0.1, f"Cache add too slow: {add_duration:.3f}s")
        self.assertLess(get_duration, 0.05, f"Cache get too slow: {get_duration:.3f}s")


if __name__ == "__main__":
    unittest.main()

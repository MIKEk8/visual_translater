"""
Integration Tests for Main Scenarios - Screen Translator v2.0
Тестирует основные сценарии использования приложения
"""

import queue
import threading
import time
import unittest
from typing import Dict
from unittest.mock import Mock

import pytest

from src.models.config import HotkeyConfig
from src.services.container import DIContainer

# Импорт основных компонентов
from src.services.task_queue import TaskPriority, TaskQueue
from src.services.translation_cache import TranslationCache
from src.tests.test_utils import skip_on_ci

pytestmark = pytest.mark.integration


@skip_on_ci
class TestMainScenarios(unittest.TestCase):
    """Интеграционные тесты основных сценариев"""

    def setUp(self):
        """Настройка тестового окружения"""
        self.container = DIContainer()
        self.task_queue = TaskQueue(num_workers=2)
        self.task_queue.start()
        self.translation_cache = TranslationCache()

    def tearDown(self):
        """Очистка после тестов"""
        self.task_queue.stop()
        self.container.clear()

    def test_scenario_screenshot_to_translation(self):
        """Тест сценария: Скриншот -> OCR -> Перевод -> TTS"""
        print("\n🧪 Testing: Screenshot -> OCR -> Translation -> TTS")

        # Моки для компонентов
        mock_screenshot = Mock(return_value={"image": "test_image", "bounds": (0, 0, 100, 100)})
        mock_ocr = Mock(return_value=("Hello world", 0.95))
        mock_translate = Mock(return_value="Привет мир")
        mock_tts = Mock()

        # Создаем интерфейсы для сервисов
        class ScreenshotEngine:
            pass

        class OCRProcessor:
            pass

        class Translator:
            pass

        class TTSProcessor:
            pass

        # Регистрация в контейнере
        self.container.register_instance(ScreenshotEngine, mock_screenshot)
        self.container.register_instance(OCRProcessor, mock_ocr)
        self.container.register_instance(Translator, mock_translate)
        self.container.register_instance(TTSProcessor, mock_tts)

        # Симуляция workflow
        results = queue.Queue()

        def screenshot_workflow():
            try:
                # 1. Захват скриншота
                screenshot = self.container.get(ScreenshotEngine)()

                # 2. OCR обработка
                text, confidence = self.container.get(OCRProcessor)(screenshot["image"])

                # 3. Перевод
                translation = self.container.get(Translator)(text)

                # 4. TTS озвучка
                self.container.get(TTSProcessor)(translation)

                results.put(
                    {
                        "success": True,
                        "text": text,
                        "translation": translation,
                        "confidence": confidence,
                    }
                )

            except Exception as e:
                results.put({"success": False, "error": str(e)})

        # Запуск через TaskQueue
        task_id = self.task_queue.submit(screenshot_workflow, name="screenshot_workflow")

        # Ожидание результата
        success = self.task_queue.wait_for_task(task_id, timeout=5)
        self.assertTrue(success)

        # Проверка результатов
        result = results.get(timeout=1)
        self.assertTrue(result["success"])
        self.assertEqual(result["text"], "Hello world")
        self.assertEqual(result["translation"], "Привет мир")
        self.assertEqual(result["confidence"], 0.95)

        # Проверка вызовов
        mock_screenshot.assert_called_once()
        mock_ocr.assert_called_once()
        mock_translate.assert_called_once_with("Hello world")
        mock_tts.assert_called_once_with("Привет мир")

    def test_scenario_hotkey_quick_translate(self):
        """Тест сценария: Горячая клавиша -> Быстрый перевод области"""
        print("\n🧪 Testing: Hotkey -> Quick Translate")

        # Конфигурация горячих клавиш
        hotkey_config = HotkeyConfig(area_select="ctrl+shift+a", quick_center="ctrl+shift+q")

        # Мок обработчика горячих клавиш
        captured_hotkeys = []

        def mock_hotkey_handler(hotkey: str):
            captured_hotkeys.append(hotkey)

            if hotkey == hotkey_config.quick_center:
                # Симуляция быстрого перевода
                task_id = self.task_queue.submit(
                    lambda: {"translated": "Quick translation result"},
                    name="quick_translate",
                    priority=TaskPriority.HIGH,
                )
                return task_id

        # Симуляция нажатия горячей клавиши
        task_id = mock_hotkey_handler("ctrl+shift+q")

        # Проверка
        self.assertIn("ctrl+shift+q", captured_hotkeys)
        self.assertIsNotNone(task_id)

        # Ожидание выполнения
        success = self.task_queue.wait_for_task(task_id, timeout=2)
        self.assertTrue(success)

        result = self.task_queue.get_task_result(task_id)
        self.assertEqual(result["translated"], "Quick translation result")

    def test_scenario_batch_image_processing(self):
        """Тест сценария: Пакетная обработка изображений"""
        print("\n🧪 Testing: Batch Image Processing")

        # Список изображений для обработки
        test_images = [f"image_{i}.png" for i in range(5)]

        # Результаты обработки
        processed_results = []

        def process_image(image_path: str) -> Dict:
            """Обработка одного изображения"""
            # Симуляция обработки
            time.sleep(0.1)  # Имитация времени обработки

            result = {
                "image": image_path,
                "text": f"Text from {image_path}",
                "translation": f"Перевод из {image_path}",
                "timestamp": time.time(),
            }

            return result

        # Отправка задач в очередь
        task_ids = []
        for image in test_images:
            task_id = self.task_queue.submit(
                process_image, args=(image,), name=f"process_{image}", priority=TaskPriority.NORMAL
            )
            task_ids.append(task_id)

        # Ожидание завершения всех задач
        start_time = time.time()

        for task_id in task_ids:
            success = self.task_queue.wait_for_task(task_id, timeout=5)
            self.assertTrue(success)

            result = self.task_queue.get_task_result(task_id)
            processed_results.append(result)

        end_time = time.time()

        # Проверка результатов
        self.assertEqual(len(processed_results), 5)

        for i, result in enumerate(processed_results):
            self.assertEqual(result["image"], f"image_{i}.png")
            self.assertIn("Text from", result["text"])
            self.assertIn("Перевод из", result["translation"])

        # Проверка параллельной обработки
        total_time = end_time - start_time
        print(f"   ⏱️ Total processing time: {total_time:.2f}s")

        # С 2 воркерами должно быть быстрее чем последовательно
        self.assertLess(total_time, 0.5 * len(test_images))

    def test_scenario_translation_with_cache(self):
        """Тест сценария: Перевод с использованием кэша"""
        print("\n🧪 Testing: Translation with Cache")

        # Счетчики вызовов
        translation_calls = 0

        def mock_translate(text: str) -> str:
            nonlocal translation_calls
            translation_calls += 1
            time.sleep(0.1)  # Имитация сетевого запроса
            return f"Translated: {text}"

        # Тексты для перевода (с повторами)
        texts = ["Hello", "World", "Hello", "Test", "World", "Hello"]
        results = []

        # Первый проход - кэш пустой
        for text in texts:
            # Проверка кэша
            cached = self.translation_cache.get(text, "en", "ru")

            if cached:
                results.append(cached)
            else:
                # Перевод и сохранение в кэш
                translation = mock_translate(text)
                self.translation_cache.add(text, translation, "en", "ru")
                results.append(translation)

        # Проверка результатов
        self.assertEqual(len(results), 6)
        self.assertEqual(translation_calls, 3)  # Только уникальные тексты

        # Второй проход - всё должно быть в кэше
        translation_calls = 0
        cached_results = []

        for text in texts:
            cached = self.translation_cache.get(text, "en", "ru")
            self.assertIsNotNone(cached)
            cached_results.append(cached)

        self.assertEqual(translation_calls, 0)  # Все из кэша
        self.assertEqual(results, cached_results)

    def test_scenario_error_recovery(self):
        """Тест сценария: Восстановление после ошибок"""
        print("\n🧪 Testing: Error Recovery")

        # Функция с периодическими сбоями
        attempt_count = 0

        def unreliable_service():
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count < 3:
                raise Exception(f"Service failed (attempt {attempt_count})")

            return "Success after retries"

        # Функция с retry логикой
        def with_retry(func, max_attempts=3):
            for attempt in range(max_attempts):
                try:
                    return func()
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff

        # Запуск через TaskQueue
        task_id = self.task_queue.submit(
            lambda: with_retry(unreliable_service), name="unreliable_task"
        )

        # Ожидание результата
        success = self.task_queue.wait_for_task(task_id, timeout=5)
        self.assertTrue(success)

        result = self.task_queue.get_task_result(task_id)
        self.assertEqual(result, "Success after retries")
        self.assertEqual(attempt_count, 3)

    def test_scenario_concurrent_users(self):
        """Тест сценария: Одновременные запросы"""
        print("\n🧪 Testing: Concurrent Requests")

        # Счетчик активных запросов
        active_requests = 0
        max_concurrent = 0
        lock = threading.Lock()

        def simulate_request(request_id: int):
            nonlocal active_requests, max_concurrent

            with lock:
                active_requests += 1
                max_concurrent = max(max_concurrent, active_requests)

            # Симуляция обработки
            time.sleep(0.2)

            with lock:
                active_requests -= 1

            return f"Request {request_id} completed"

        # Запуск множества одновременных запросов
        num_requests = 10
        task_ids = []

        for i in range(num_requests):
            task_id = self.task_queue.submit(
                simulate_request, args=(i,), name=f"request_{i}", priority=TaskPriority.NORMAL
            )
            task_ids.append(task_id)

        # Ожидание завершения
        results = []
        for task_id in task_ids:
            success = self.task_queue.wait_for_task(task_id, timeout=10)
            self.assertTrue(success)
            results.append(self.task_queue.get_task_result(task_id))

        # Проверка результатов
        self.assertEqual(len(results), num_requests)
        print(f"   🔄 Max concurrent requests: {max_concurrent}")

        # С 2 воркерами должно быть не более 2 одновременных запросов
        self.assertLessEqual(max_concurrent, 2)

    def test_scenario_memory_efficiency(self):
        """Тест сценария: Эффективность использования памяти"""
        print("\n🧪 Testing: Memory Efficiency")

        # Создание большого количества задач
        num_tasks = 100

        # Функция, генерирующая данные
        def generate_data(size_kb: int):
            # Генерация строки заданного размера
            data = "x" * (size_kb * 1024)
            # Возвращаем только размер, не храним данные
            return len(data)

        # Отправка задач
        task_ids = []
        for i in range(num_tasks):
            task_id = self.task_queue.submit(
                generate_data, args=(10,), name=f"memory_test_{i}"  # 10KB на задачу
            )
            task_ids.append(task_id)

        # Проверка что очередь не переполнена
        queue_size = self.task_queue.get_queue_size()
        print(f"   📊 Queue size during processing: {queue_size}")

        # Ожидание завершения
        completed = 0
        for task_id in task_ids:
            if self.task_queue.wait_for_task(task_id, timeout=0.1):
                completed += 1

        print(f"   ✅ Completed tasks: {completed}/{num_tasks}")

        # Проверка статистики
        stats = self.task_queue.get_stats()
        print(f"   📊 Queue stats: {stats}")

        self.assertGreater(completed, 0)
        self.assertEqual(stats["total_tasks"], num_tasks)


@skip_on_ci
class TestPerformanceScenarios(unittest.TestCase):
    """Тесты производительности основных сценариев"""

    def setUp(self):
        """Настройка тестового окружения"""
        self.task_queue = TaskQueue(num_workers=4)
        self.task_queue.start()

    def tearDown(self):
        """Очистка после тестов"""
        self.task_queue.stop()

    def test_performance_high_load(self):
        """Тест производительности под высокой нагрузкой"""
        print("\n🧪 Testing: High Load Performance")

        # Параметры теста
        num_tasks = 1000
        results = []

        def cpu_bound_task(n):
            """CPU-intensive задача"""
            return sum(i * i for i in range(n))

        # Измерение времени
        start_time = time.time()

        # Отправка задач
        task_ids = []
        for i in range(num_tasks):
            task_id = self.task_queue.submit(cpu_bound_task, args=(100,), name=f"cpu_task_{i}")
            task_ids.append(task_id)

        submit_time = time.time() - start_time

        # Ожидание выполнения
        completed = 0
        timeout = 30  # 30 секунд максимум

        while completed < len(task_ids) and (time.time() - start_time) < timeout:
            for task_id in task_ids[completed:]:
                if self.task_queue.get_task_status(task_id) == "completed":
                    completed += 1
            time.sleep(0.01)

        execution_time = time.time() - start_time

        # Результаты
        print(f"   📊 Tasks submitted: {num_tasks}")
        print(f"   ⏱️ Submit time: {submit_time:.3f}s ({num_tasks/submit_time:.1f} tasks/sec)")
        print(f"   ⏱️ Total execution time: {execution_time:.3f}s")
        print(f"   ✅ Tasks completed: {completed}")
        print(f"   📈 Throughput: {completed/execution_time:.1f} tasks/sec")

        # Проверки производительности
        self.assertLess(submit_time, 1.0)  # Отправка должна быть быстрой
        self.assertGreater(completed / execution_time, 50)  # Минимум 50 задач/сек
        self.assertGreater(completed, num_tasks * 0.9)  # 90%+ должны завершиться


if __name__ == "__main__":
    unittest.main(verbosity=2)

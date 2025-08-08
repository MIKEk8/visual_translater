#!/usr/bin/env python3
"""
Performance Benchmarks - Screen Translator v2.0
Бенчмарки для критических операций
"""

import json
import threading
import time
from typing import Any, Dict, List

from src.services.container import DIContainer

# Импорт компонентов для тестирования
from src.services.task_queue import TaskPriority, TaskQueue
from src.services.translation_cache import TranslationCache


class PerformanceBenchmark:
    """Класс для бенчмарков производительности"""

    def __init__(self):
        self.results = {}

    def measure(self, name: str, func, *args, **kwargs):
        """Измерить производительность функции"""
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()

        duration = end - start
        self.results[name] = {
            "duration": duration,
            "ops_per_sec": 1 / duration if duration > 0 else float("inf"),
        }

        return result, duration

    def benchmark_task_queue(self):
        """Бенчмарк TaskQueue"""
        print("🔍 Benchmarking TaskQueue...")

        # Создание очереди
        queue = TaskQueue(num_workers=4)
        queue.start()

        # Тест 1: Скорость добавления задач
        def dummy_task(x):
            return x * 2

        start = time.perf_counter()
        task_ids = []
        for i in range(1000):
            task_id = queue.submit(dummy_task, args=(i,))
            task_ids.append(task_id)
        submit_time = time.perf_counter() - start

        self.results["task_queue_submit_1000"] = {
            "duration": submit_time,
            "ops_per_sec": 1000 / submit_time,
        }

        # Тест 2: Скорость выполнения задач
        start = time.perf_counter()
        completed = 0
        timeout = 10  # 10 секунд максимум

        while completed < len(task_ids) and (time.perf_counter() - start) < timeout:
            for task_id in task_ids:
                if queue.get_task_status(task_id) == "completed":
                    completed += 1
            time.sleep(0.01)

        execution_time = time.perf_counter() - start

        self.results["task_queue_execute_1000"] = {
            "duration": execution_time,
            "ops_per_sec": completed / execution_time,
        }

        queue.stop()

        print(f"   ✅ Submit 1000 tasks: {submit_time:.3f}s ({1000/submit_time:.1f} ops/sec)")
        print(
            f"   ✅ Execute {completed} tasks: {execution_time:.3f}s ({completed/execution_time:.1f} ops/sec)"
        )

    def benchmark_di_container(self):
        """Бенчмарк DI Container"""
        print("\n🔍 Benchmarking DI Container...")

        container = DIContainer()

        # Тест регистрации
        class TestService:
            def __init__(self):
                self.value = 42

        start = time.perf_counter()
        for i in range(1000):
            container.register_singleton(f"service_{i}", TestService)
        register_time = time.perf_counter() - start

        self.results["di_register_1000"] = {
            "duration": register_time,
            "ops_per_sec": 1000 / register_time,
        }

        # Тест получения
        start = time.perf_counter()
        for i in range(1000):
            service = container.get(f"service_{i}")
        get_time = time.perf_counter() - start

        self.results["di_get_1000"] = {"duration": get_time, "ops_per_sec": 1000 / get_time}

        print(
            f"   ✅ Register 1000 services: {register_time:.3f}s ({1000/register_time:.1f} ops/sec)"
        )
        print(f"   ✅ Get 1000 services: {get_time:.3f}s ({1000/get_time:.1f} ops/sec)")

    def benchmark_translation_cache(self):
        """Бенчмарк Translation Cache"""
        print("\n🔍 Benchmarking Translation Cache...")

        cache = TranslationCache(max_size=1000)

        # Тест добавления в кэш
        start = time.perf_counter()
        for i in range(1000):
            cache.add(f"text_{i}", f"translation_{i}", "en", "ru")
        add_time = time.perf_counter() - start

        self.results["cache_add_1000"] = {"duration": add_time, "ops_per_sec": 1000 / add_time}

        # Тест поиска в кэше
        start = time.perf_counter()
        hits = 0
        for i in range(1000):
            result = cache.get(f"text_{i}", "en", "ru")
            if result:
                hits += 1
        lookup_time = time.perf_counter() - start

        self.results["cache_lookup_1000"] = {
            "duration": lookup_time,
            "ops_per_sec": 1000 / lookup_time,
            "hit_rate": hits / 1000,
        }

        print(f"   ✅ Add 1000 entries: {add_time:.3f}s ({1000/add_time:.1f} ops/sec)")
        print(f"   ✅ Lookup 1000 entries: {lookup_time:.3f}s ({1000/lookup_time:.1f} ops/sec)")
        print(f"   ✅ Cache hit rate: {hits/10:.1f}%")

    def benchmark_threading(self):
        """Бенчмарк многопоточности"""
        print("\n🔍 Benchmarking Threading...")

        # Тест создания потоков
        def worker_thread(result_queue, work_items):
            for item in work_items:
                result = item * 2
                result_queue.put(result)

        work_items = list(range(1000))
        result_queue = queue.Queue()

        # Однопоточное выполнение
        start = time.perf_counter()
        for item in work_items:
            result = item * 2
            result_queue.put(result)
        single_thread_time = time.perf_counter() - start

        # Очистка очереди
        while not result_queue.empty():
            result_queue.get()

        # Многопоточное выполнение (4 потока)
        start = time.perf_counter()
        threads = []
        items_per_thread = len(work_items) // 4

        for i in range(4):
            start_idx = i * items_per_thread
            end_idx = start_idx + items_per_thread if i < 3 else len(work_items)
            thread_items = work_items[start_idx:end_idx]

            thread = threading.Thread(target=worker_thread, args=(result_queue, thread_items))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        multi_thread_time = time.perf_counter() - start

        self.results["single_thread_1000"] = {
            "duration": single_thread_time,
            "ops_per_sec": 1000 / single_thread_time,
        }

        self.results["multi_thread_1000"] = {
            "duration": multi_thread_time,
            "ops_per_sec": 1000 / multi_thread_time,
            "speedup": single_thread_time / multi_thread_time,
        }

        print(
            f"   ✅ Single thread: {single_thread_time:.3f}s ({1000/single_thread_time:.1f} ops/sec)"
        )
        print(
            f"   ✅ Multi thread (4): {multi_thread_time:.3f}s ({1000/multi_thread_time:.1f} ops/sec)"
        )
        print(f"   ✅ Speedup: {single_thread_time/multi_thread_time:.2f}x")

    def run_all_benchmarks(self):
        """Запустить все бенчмарки"""
        print("🚀 RUNNING PERFORMANCE BENCHMARKS")
        print("=" * 60)

        self.benchmark_task_queue()
        self.benchmark_di_container()
        self.benchmark_translation_cache()
        self.benchmark_threading()

        # Сохранение результатов
        with open("benchmark_results.json", "w") as f:
            json.dump(self.results, f, indent=2)

        print("\n✅ Benchmark results saved to benchmark_results.json")

        # Анализ производительности
        print("\n📊 PERFORMANCE ANALYSIS")
        print("=" * 60)

        critical_thresholds = {
            "task_queue_submit_1000": 1.0,  # Должно быть < 1 секунды
            "di_get_1000": 0.1,  # Должно быть < 100ms
            "cache_lookup_1000": 0.01,  # Должно быть < 10ms
        }

        issues = []
        for metric, threshold in critical_thresholds.items():
            if metric in self.results:
                duration = self.results[metric]["duration"]
                if duration > threshold:
                    issues.append(f"{metric}: {duration:.3f}s (threshold: {threshold}s)")

        if issues:
            print("⚠️ Performance issues detected:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ All critical paths perform within acceptable thresholds")

        return len(issues) == 0


if __name__ == "__main__":
    benchmark = PerformanceBenchmark()
    success = benchmark.run_all_benchmarks()
    exit(0 if success else 1)

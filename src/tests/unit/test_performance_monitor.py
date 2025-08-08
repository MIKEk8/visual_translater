import json
import tempfile
import time
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from src.utils.performance_monitor import (
    PerformanceMetric,
    PerformanceMonitor,
    SystemStats,
    get_performance_monitor,
    measure_performance,
)


class TestPerformanceMonitor(unittest.TestCase):
    """Test PerformanceMonitor functionality"""

    def setUp(self):
        """Setup test environment"""
        self.monitor = PerformanceMonitor(
            max_metrics=100, enable_system_monitoring=False  # Disable for tests
        )

    def tearDown(self):
        """Cleanup test environment"""
        self.monitor.stop_system_monitoring()

    def test_record_operation(self):
        """Test recording operation metrics"""
        self.monitor.record_operation("test_operation", 1.5, True)

        self.assertEqual(len(self.monitor.metrics), 1)

        metric = self.monitor.metrics[0]
        self.assertEqual(metric.operation, "test_operation")
        self.assertEqual(metric.duration, 1.5)
        self.assertTrue(metric.success)
        self.assertIsNone(metric.error_message)

    def test_record_failed_operation(self):
        """Test recording failed operation"""
        self.monitor.record_operation(
            "failed_operation", 2.0, False, "Test error", {"key": "value"}
        )

        metric = self.monitor.metrics[0]
        self.assertFalse(metric.success)
        self.assertEqual(metric.error_message, "Test error")
        self.assertEqual(metric.metadata["key"], "value")

    def test_operation_stats(self):
        """Test operation statistics"""
        # Record multiple operations
        for i in range(5):
            success = i < 4  # 4 success, 1 failure
            self.monitor.record_operation("test_op", 1.0 + i * 0.1, success)

        stats = self.monitor.get_operation_stats("test_op")

        self.assertEqual(stats["total_count"], 5)
        self.assertEqual(stats["error_count"], 1)
        self.assertEqual(stats["error_rate"], 0.2)
        self.assertAlmostEqual(stats["average_time"], 1.2, places=1)

    def test_measure_operation_context_manager(self):
        """Test operation measurement context manager"""
        with self.monitor.measure_operation("context_test") as _:
            time.sleep(0.1)  # Simulate work
            # Operation should be successful by default

        self.assertEqual(len(self.monitor.metrics), 1)
        metric = self.monitor.metrics[0]
        self.assertEqual(metric.operation, "context_test")
        self.assertTrue(metric.success)
        self.assertGreater(metric.duration, 0.05)

    def test_measure_operation_with_exception(self):
        """Test operation measurement with exception"""
        try:
            with self.monitor.measure_operation("exception_test") as _:
                raise ValueError("Test exception")
        except ValueError:
            pass

        metric = self.monitor.metrics[0]
        self.assertFalse(metric.success)
        self.assertEqual(metric.error_message, "Test exception")

    def test_measure_operation_manual_error(self):
        """Test manual error marking"""
        with self.monitor.measure_operation("manual_error_test") as measurer:
            measurer.mark_error("Manual error")

        metric = self.monitor.metrics[0]
        self.assertFalse(metric.success)
        self.assertEqual(metric.error_message, "Manual error")

    def test_max_metrics_limit(self):
        """Test metrics limit enforcement"""
        monitor = PerformanceMonitor(max_metrics=3, enable_system_monitoring=False)

        # Add more metrics than limit
        for i in range(5):
            monitor.record_operation(f"op_{i}", 1.0, True)

        # Should only keep last 3
        self.assertEqual(len(monitor.metrics), 3)

        # Should have newest metrics
        operations = [m.operation for m in monitor.metrics]
        self.assertIn("op_4", operations)
        self.assertIn("op_3", operations)
        self.assertIn("op_2", operations)
        self.assertNotIn("op_0", operations)

    @patch("src.utils.performance_monitor.psutil")
    def test_get_system_performance(self, mock_psutil):
        """Test system performance monitoring"""
        # Mock psutil calls
        mock_psutil.cpu_percent.return_value = 45.0
        mock_psutil.virtual_memory.return_value.percent = 60.0
        mock_psutil.virtual_memory.return_value.used = 8 * 1024**3  # 8GB
        mock_psutil.virtual_memory.return_value.available = 4 * 1024**3  # 4GB
        mock_psutil.disk_usage.return_value.percent = 70.0

        # Mock process info
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 512 * 1024**2  # 512MB
        mock_process.num_threads.return_value = 5
        mock_process.cpu_percent.return_value = 15.0
        mock_psutil.Process.return_value = mock_process

        perf = self.monitor.get_system_performance()

        self.assertEqual(perf["system"]["cpu_percent"], 45.0)
        self.assertEqual(perf["system"]["memory_percent"], 60.0)
        self.assertEqual(perf["process"]["threads"], 5)

    def test_get_performance_report(self):
        """Test performance report generation"""
        # Add some test metrics
        operations = ["ocr", "translation", "screenshot"]
        for op in operations:
            for i in range(3):
                success = i < 2  # 2 success, 1 failure per operation
                self.monitor.record_operation(op, 1.0 + i * 0.5, success)

        report = self.monitor.get_performance_report(hours=1)

        self.assertIn("operation_statistics", report)
        self.assertIn("total_operations", report)
        self.assertEqual(report["total_operations"], 9)
        self.assertEqual(report["unique_operations"], 3)

        # Check operation stats
        for op in operations:
            self.assertIn(op, report["operation_statistics"])
            op_stats = report["operation_statistics"][op]
            self.assertEqual(op_stats["count"], 3)
            self.assertAlmostEqual(op_stats["success_rate"], 2 / 3, places=2)

    def test_export_metrics(self):
        """Test metrics export"""
        # Add test metrics
        self.monitor.record_operation("test", 1.0, True, metadata={"test": "data"})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            success = self.monitor.export_metrics(temp_path, "json")
            self.assertTrue(success)

            # Verify exported data
            with open(temp_path, "r") as f:
                data = json.load(f)

            self.assertIn("export_info", data)
            self.assertIn("metrics", data)
            self.assertEqual(len(data["metrics"]), 1)

            metric = data["metrics"][0]
            self.assertEqual(metric["operation"], "test")
            self.assertEqual(metric["duration"], 1.0)
            self.assertTrue(metric["success"])
            self.assertEqual(metric["metadata"]["test"], "data")

        finally:
            import os

            os.unlink(temp_path)

    def test_alert_system(self):
        """Test performance alert system"""
        alert_calls = []

        def alert_handler(alert_type, alert_data):
            alert_calls.append((alert_type, alert_data))

        self.monitor.add_alert_callback(alert_handler)
        self.monitor.set_alert_threshold("operation_slow", 2.0)

        # Record slow operation
        self.monitor.record_operation("slow_op", 3.0, True)

        # Should trigger alert
        self.assertEqual(len(alert_calls), 1)
        alert_type, alert_data = alert_calls[0]
        self.assertEqual(alert_type, "operation_slow")
        self.assertIn("Slow operation detected", alert_data["message"])

    @patch("src.utils.performance_monitor.psutil")
    def test_system_monitoring_thread(self, mock_psutil):
        """Test system monitoring background thread"""
        # Mock system stats
        mock_psutil.cpu_percent.return_value = 50.0
        mock_psutil.virtual_memory.return_value.percent = 60.0
        mock_psutil.virtual_memory.return_value.used = 8 * 1024**2
        mock_psutil.virtual_memory.return_value.available = 4 * 1024**2
        mock_psutil.disk_usage.return_value.percent = 70.0

        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 512 * 1024**2
        mock_psutil.Process.return_value = mock_process

        # Start monitoring
        monitor = PerformanceMonitor(enable_system_monitoring=True)
        monitor.start_system_monitoring(interval=0.1)

        # Wait for some data
        time.sleep(0.3)

        # Should have collected some system stats
        self.assertGreater(len(monitor.system_stats), 0)

        monitor.stop_system_monitoring()

    def test_insights_generation(self):
        """Test performance insights generation"""
        # Add operations with different characteristics
        self.monitor.record_operation("fast_op", 0.1, True)
        self.monitor.record_operation("slow_op", 5.0, True)  # Slow

        # Add error-prone operation
        for i in range(10):
            success = i < 6  # 60% success rate
            self.monitor.record_operation("error_prone", 1.0, success)

        report = self.monitor.get_performance_report()
        insights = report.get("insights", [])

        # Should identify slow operation
        slow_insight = any("slow_op" in insight for insight in insights)
        self.assertTrue(slow_insight)

    def test_recommendations_generation(self):
        """Test performance recommendations"""
        # Add slow operation
        self.monitor.record_operation("optimize_me", 3.0, True)

        # Add error-prone operation
        for i in range(20):
            success = i < 15  # 75% success rate (below 95% threshold)
            self.monitor.record_operation("unreliable_op", 1.0, success)

        report = self.monitor.get_performance_report()
        recommendations = report.get("recommendations", [])

        # Should recommend optimization
        optimize_rec = any("optimize_me" in rec for rec in recommendations)
        self.assertTrue(optimize_rec)

        # Should recommend investigating errors
        error_rec = any("unreliable_op" in rec for rec in recommendations)
        self.assertTrue(error_rec)


class TestGlobalMonitor(unittest.TestCase):
    """Test global monitor functions"""

    def test_get_performance_monitor(self):
        """Test global monitor singleton"""
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()

        # Should be same instance
        self.assertIs(monitor1, monitor2)

    def test_measure_performance_decorator(self):
        """Test performance measurement decorator"""
        monitor = get_performance_monitor()
        initial_count = len(monitor.metrics)

        @measure_performance("decorated_operation")
        def test_function():
            time.sleep(0.1)
            return "result"

        result = test_function()

        self.assertEqual(result, "result")
        self.assertEqual(len(monitor.metrics), initial_count + 1)

        # Find the metric for our operation
        metric = next(m for m in monitor.metrics if m.operation == "decorated_operation")
        self.assertTrue(metric.success)
        self.assertGreater(metric.duration, 0.05)

    def test_measure_performance_decorator_with_exception(self):
        """Test decorator with exception"""
        monitor = get_performance_monitor()
        initial_count = len(monitor.metrics)

        @measure_performance("failing_operation")
        def failing_function():
            raise ValueError("Test error")

        with self.assertRaises(ValueError):
            failing_function()

        self.assertEqual(len(monitor.metrics), initial_count + 1)

        # Find the metric for our operation
        metric = next(m for m in monitor.metrics if m.operation == "failing_operation")
        self.assertFalse(metric.success)
        self.assertEqual(metric.error_message, "Test error")


class TestPerformanceMetric(unittest.TestCase):
    """Test PerformanceMetric data model"""

    def test_metric_creation(self):
        """Test creating performance metric"""
        timestamp = datetime.now()
        metric = PerformanceMetric(
            timestamp=timestamp,
            operation="test_op",
            duration=1.5,
            memory_used=100.0,
            cpu_percent=50.0,
            success=True,
            metadata={"key": "value"},
        )

        self.assertEqual(metric.timestamp, timestamp)
        self.assertEqual(metric.operation, "test_op")
        self.assertEqual(metric.duration, 1.5)
        self.assertTrue(metric.success)
        self.assertEqual(metric.metadata["key"], "value")


class TestSystemStats(unittest.TestCase):
    """Test SystemStats data model"""

    def test_system_stats_creation(self):
        """Test creating system stats"""
        timestamp = datetime.now()
        stats = SystemStats(
            timestamp=timestamp,
            cpu_percent=45.0,
            memory_percent=60.0,
            memory_used_mb=8192.0,
            memory_available_mb=4096.0,
            disk_usage_percent=70.0,
            active_threads=10,
            python_memory_mb=512.0,
        )

        self.assertEqual(stats.timestamp, timestamp)
        self.assertEqual(stats.cpu_percent, 45.0)
        self.assertEqual(stats.memory_percent, 60.0)
        self.assertEqual(stats.active_threads, 10)


if __name__ == "__main__":
    unittest.main()

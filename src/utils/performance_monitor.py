"""
Performance monitoring and metrics collection system
"""

import json
import platform
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import psutil

from src.utils.logger import logger


@dataclass
class PerformanceMetric:
    """Single performance measurement"""

    timestamp: datetime
    operation: str
    duration: float  # in seconds
    memory_used: float  # in MB
    cpu_percent: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemStats:
    """System resource statistics"""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    active_threads: int
    python_memory_mb: float


class PerformanceMonitor:
    """Monitor and collect performance metrics"""

    def __init__(self, max_metrics: int = 1000, enable_system_monitoring: bool = True):
        self.max_metrics = max_metrics
        self.enable_system_monitoring = enable_system_monitoring

        # Metrics storage
        self.metrics: deque = deque(maxlen=max_metrics)
        self.system_stats: deque = deque(maxlen=max_metrics // 10)  # Less frequent

        # Operation counters
        self.operation_counts: defaultdict[str, int] = defaultdict(int)
        self.operation_total_time: defaultdict[str, float] = defaultdict(float)
        self.operation_errors: defaultdict[str, int] = defaultdict(int)

        # Thread safety
        self._lock = threading.Lock()

        # System monitoring
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None

        # Performance alerts
        self.alert_callbacks: List[Callable[[str, Dict], None]] = []
        self.alert_thresholds = {
            "cpu_high": 80.0,  # %
            "memory_high": 85.0,  # %
            "operation_slow": 5.0,  # seconds
            "error_rate_high": 0.1,  # 10%
        }

        if enable_system_monitoring:
            self.start_system_monitoring()

        logger.info("Performance monitor initialized")

    def start_system_monitoring(self, interval: float = 10.0) -> None:
        """Start background system monitoring"""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._system_monitor_loop, args=(interval,), daemon=True
        )
        self._monitor_thread.start()
        logger.info(f"System monitoring started (interval: {interval}s)")

    def stop_system_monitoring(self) -> None:
        """Stop background system monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
        logger.info("System monitoring stopped")

    def record_operation(
        self,
        operation: str,
        duration: float,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a performance metric for an operation"""
        try:
            # Get current system stats
            cpu_percent = psutil.cpu_percent(interval=None)
            memory_info = psutil.virtual_memory()
            psutil.Process()

            metric = PerformanceMetric(
                timestamp=datetime.now(),
                operation=operation,
                duration=duration,
                memory_used=memory_info.used / (1024 * 1024),  # MB
                cpu_percent=cpu_percent,
                success=success,
                error_message=error_message,
                metadata=metadata or {},
            )

            with self._lock:
                self.metrics.append(metric)

                # Update counters
                self.operation_counts[operation] += 1
                self.operation_total_time[operation] += duration
                if not success:
                    self.operation_errors[operation] += 1

            # Check for performance alerts
            self._check_alerts(metric)

        except Exception as e:
            logger.error(f"Failed to record performance metric: {e}")

    def measure_operation(self, operation_name: str, metadata: Optional[Dict] = None):
        """Decorator/context manager for measuring operation performance"""
        return OperationMeasurer(self, operation_name, metadata)

    def get_operation_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistics for a specific operation"""
        with self._lock:
            count = self.operation_counts.get(operation, 0)
            total_time = self.operation_total_time.get(operation, 0.0)
            errors = self.operation_errors.get(operation, 0)

        if count == 0:
            return {"operation": operation, "count": 0}

        # Get recent metrics for this operation
        recent_metrics = [
            m
            for m in self.metrics
            if m.operation == operation and m.timestamp > datetime.now() - timedelta(hours=1)
        ]

        durations = [m.duration for m in recent_metrics]

        return {
            "operation": operation,
            "total_count": count,
            "total_time": total_time,
            "average_time": total_time / count,
            "error_count": errors,
            "error_rate": errors / count,
            "recent_count": len(recent_metrics),
            "recent_avg_time": sum(durations) / len(durations) if durations else 0,
            "recent_min_time": min(durations) if durations else 0,
            "recent_max_time": max(durations) if durations else 0,
        }

    def get_all_operation_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all operations"""
        operations = list(self.operation_counts.keys())
        return [self.get_operation_stats(op) for op in operations]

    def get_system_performance(self) -> Dict[str, Any]:
        """Get current system performance overview"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Current process info
            process = psutil.Process()
            process_memory = process.memory_info().rss / (1024 * 1024)  # MB
            thread_count = process.num_threads()

            # Recent metrics summary
            recent_time = datetime.now() - timedelta(minutes=5)
            recent_metrics = [m for m in self.metrics if m.timestamp > recent_time]

            total_operations = len(recent_metrics)
            successful_operations = len([m for m in recent_metrics if m.success])
            avg_operation_time = (
                sum(m.duration for m in recent_metrics) / total_operations
                if total_operations
                else 0
            )

            return {
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_used_gb": memory.used / (1024**3),
                    "memory_available_gb": memory.available / (1024**3),
                    "disk_usage_percent": disk.percent,
                    "platform": platform.system(),
                    "architecture": platform.architecture()[0],
                },
                "process": {
                    "memory_mb": process_memory,
                    "threads": thread_count,
                    "cpu_percent": process.cpu_percent(),
                },
                "operations": {
                    "recent_count": total_operations,
                    "success_rate": (
                        successful_operations / total_operations if total_operations else 1.0
                    ),
                    "average_duration": avg_operation_time,
                    "total_operations": sum(self.operation_counts.values()),
                    "total_errors": sum(self.operation_errors.values()),
                },
            }

        except Exception as e:
            logger.error(f"Failed to get system performance: {e}")
            return {"error": str(e)}

    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            # Filter metrics by time period
            period_metrics = [m for m in self.metrics if m.timestamp > cutoff_time]

            if not period_metrics:
                return {"message": f"No metrics available for the last {hours} hours"}

            # Group by operation
            by_operation = defaultdict(list)
            for metric in period_metrics:
                by_operation[metric.operation].append(metric)

            # Calculate statistics per operation
            operation_stats = {}
            for operation, metrics in by_operation.items():
                durations = [m.duration for m in metrics]
                success_count = len([m for m in metrics if m.success])

                operation_stats[operation] = {
                    "count": len(metrics),
                    "success_rate": success_count / len(metrics),
                    "avg_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                    "total_duration": sum(durations),
                    "error_count": len(metrics) - success_count,
                }

            # System resource analysis
            system_data = list(self.system_stats)
            if system_data:
                cpu_values = [s.cpu_percent for s in system_data]
                memory_values = [s.memory_percent for s in system_data]

                system_analysis = {
                    "avg_cpu": sum(cpu_values) / len(cpu_values),
                    "max_cpu": max(cpu_values),
                    "avg_memory": sum(memory_values) / len(memory_values),
                    "max_memory": max(memory_values),
                    "samples": len(system_data),
                }
            else:
                system_analysis = {"message": "No system stats available"}

            # Performance insights
            insights = self._generate_insights(operation_stats, system_analysis)

            return {
                "report_period": f"{hours} hours",
                "generated_at": datetime.now().isoformat(),
                "total_operations": len(period_metrics),
                "unique_operations": len(by_operation),
                "overall_success_rate": len([m for m in period_metrics if m.success])
                / len(period_metrics),
                "operation_statistics": operation_stats,
                "system_analysis": system_analysis,
                "insights": insights,
                "recommendations": self._generate_recommendations(operation_stats, system_analysis),
            }

        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return {"error": str(e)}

    def export_metrics(self, file_path: str, format_type: str = "json") -> bool:
        """Export performance metrics to file"""
        try:
            data = {
                "export_info": {
                    "timestamp": datetime.now().isoformat(),
                    "format": format_type,
                    "total_metrics": len(self.metrics),
                    "system_stats": len(self.system_stats),
                },
                "metrics": [
                    {
                        "timestamp": m.timestamp.isoformat(),
                        "operation": m.operation,
                        "duration": m.duration,
                        "memory_used": m.memory_used,
                        "cpu_percent": m.cpu_percent,
                        "success": m.success,
                        "error_message": m.error_message,
                        "metadata": m.metadata,
                    }
                    for m in self.metrics
                ],
                "system_stats": [
                    {
                        "timestamp": s.timestamp.isoformat(),
                        "cpu_percent": s.cpu_percent,
                        "memory_percent": s.memory_percent,
                        "memory_used_mb": s.memory_used_mb,
                        "memory_available_mb": s.memory_available_mb,
                        "disk_usage_percent": s.disk_usage_percent,
                        "active_threads": s.active_threads,
                        "python_memory_mb": s.python_memory_mb,
                    }
                    for s in self.system_stats
                ],
                "operation_summary": self.get_all_operation_stats(),
            }

            if format_type.lower() == "json":
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                logger.error(f"Unsupported export format: {format_type}")
                return False

            logger.info(f"Performance metrics exported to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            return False

    def add_alert_callback(self, callback: Callable[[str, Dict], None]) -> None:
        """Add callback for performance alerts"""
        self.alert_callbacks.append(callback)

    def set_alert_threshold(self, alert_type: str, threshold: float) -> None:
        """Set threshold for performance alerts"""
        self.alert_thresholds[alert_type] = threshold

    def _system_monitor_loop(self, interval: float) -> None:
        """Background system monitoring loop"""
        while self._monitoring:
            try:
                # Collect system stats
                cpu_percent = psutil.cpu_percent(interval=None)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage("/")

                # Process info
                process = psutil.Process()
                process_memory = process.memory_info().rss / (1024 * 1024)  # MB
                thread_count = threading.active_count()

                stats = SystemStats(
                    timestamp=datetime.now(),
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    memory_used_mb=memory.used / (1024 * 1024),
                    memory_available_mb=memory.available / (1024 * 1024),
                    disk_usage_percent=disk.percent,
                    active_threads=thread_count,
                    python_memory_mb=process_memory,
                )

                with self._lock:
                    self.system_stats.append(stats)

                # Check system alerts
                self._check_system_alerts(stats)

                time.sleep(interval)

            except Exception as e:
                logger.error(f"System monitoring error: {e}")
                time.sleep(interval)

    def _check_alerts(self, metric: PerformanceMetric) -> None:
        """Check for performance alerts"""
        alerts = []

        # Slow operation alert
        if metric.duration > self.alert_thresholds["operation_slow"]:
            alerts.append(
                {
                    "type": "operation_slow",
                    "message": f"Slow operation detected: {metric.operation} took {metric.duration:.2f}s",
                    "metric": metric,
                }
            )

        # Operation error alert
        if not metric.success:
            # Check error rate for this operation
            operation_metrics = [m for m in self.metrics if m.operation == metric.operation]
            recent_metrics = [
                m for m in operation_metrics if m.timestamp > datetime.now() - timedelta(minutes=10)
            ]

            if len(recent_metrics) >= 5:  # Need some data
                error_rate = len([m for m in recent_metrics if not m.success]) / len(recent_metrics)
                if error_rate > self.alert_thresholds["error_rate_high"]:
                    alerts.append(
                        {
                            "type": "error_rate_high",
                            "message": f"High error rate for {metric.operation}: {error_rate:.1%}",
                            "metric": metric,
                        }
                    )

        # Fire alerts
        for alert in alerts:
            for callback in self.alert_callbacks:
                try:
                    callback(alert["type"], alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")

    def _check_system_alerts(self, stats: SystemStats) -> None:
        """Check for system-level alerts"""
        alerts = []

        if stats.cpu_percent > self.alert_thresholds["cpu_high"]:
            alerts.append(
                {
                    "type": "cpu_high",
                    "message": f"High CPU usage: {stats.cpu_percent:.1f}%",
                    "stats": stats,
                }
            )

        if stats.memory_percent > self.alert_thresholds["memory_high"]:
            alerts.append(
                {
                    "type": "memory_high",
                    "message": f"High memory usage: {stats.memory_percent:.1f}%",
                    "stats": stats,
                }
            )

        # Fire alerts
        for alert in alerts:
            for callback in self.alert_callbacks:
                try:
                    callback(alert["type"], alert)
                except Exception as e:
                    logger.error(f"System alert callback failed: {e}")

    def _generate_insights(self, operation_stats: Dict, system_analysis: Dict) -> List[str]:
        """Generate performance insights"""
        insights = []

        # Find slowest operations
        if operation_stats:
            slowest = max(operation_stats.items(), key=lambda x: x[1]["avg_duration"])
            insights.append(
                f"Slowest operation: {slowest[0]} ({slowest[1]['avg_duration']:.2f}s avg)"
            )

            # Find operations with high error rates
            high_error_ops = [
                op
                for op, stats in operation_stats.items()
                if stats["success_rate"] < 0.9 and stats["count"] >= 5
            ]
            if high_error_ops:
                insights.append(f"Operations with high error rates: {', '.join(high_error_ops)}")

        # System resource insights
        if "avg_cpu" in system_analysis:
            if system_analysis["avg_cpu"] > 70:
                insights.append(f"High average CPU usage: {system_analysis['avg_cpu']:.1f}%")
            if system_analysis["avg_memory"] > 80:
                insights.append(f"High average memory usage: {system_analysis['avg_memory']:.1f}%")

        return insights

    def _generate_recommendations(self, operation_stats: Dict, system_analysis: Dict) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []

        # Operation-specific recommendations
        for operation, stats in operation_stats.items():
            if stats["avg_duration"] > 2.0:
                recommendations.append(
                    f"Consider optimizing {operation} - average duration is {stats['avg_duration']:.2f}s"
                )

            if stats["success_rate"] < 0.95 and stats["count"] >= 10:
                recommendations.append(
                    f"Investigate errors in {operation} - success rate is {stats['success_rate']:.1%}"
                )

        # System recommendations
        if "avg_memory" in system_analysis and system_analysis["avg_memory"] > 75:
            recommendations.append(
                "Consider increasing available memory or optimizing memory usage"
            )

        if "avg_cpu" in system_analysis and system_analysis["avg_cpu"] > 80:
            recommendations.append(
                "High CPU usage detected - consider optimizing computationally intensive operations"
            )

        return recommendations


class OperationMeasurer:
    """Context manager for measuring operation performance"""

    def __init__(
        self, monitor: PerformanceMonitor, operation_name: str, metadata: Optional[Dict] = None
    ):
        self.monitor = monitor
        self.operation_name = operation_name
        self.metadata = metadata or {}
        self.start_time: Optional[float] = None
        self.success = True
        self.error_message: Optional[str] = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _ = exc_tb  # Unused parameter - not needed for basic error handling
        duration = time.time() - (self.start_time or 0)

        if exc_type is not None:
            self.success = False
            self.error_message = str(exc_val)

        self.monitor.record_operation(
            self.operation_name, duration, self.success, self.error_message, self.metadata
        )

        return False  # Don't suppress exceptions

    def mark_error(self, error_message: str):
        """Mark operation as failed with error message"""
        self.success = False
        self.error_message = error_message


# Global performance monitor instance
_global_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def measure_performance(operation_name: str, metadata: Optional[Dict] = None):
    """Decorator for measuring function performance"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            with monitor.measure_operation(operation_name, metadata):
                return func(*args, **kwargs)

        return wrapper

    return decorator

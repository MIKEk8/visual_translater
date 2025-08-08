"""
Enhanced metrics system integrating all application components.

This module provides comprehensive metrics collection, aggregation,
and reporting for the Screen Translator application.
"""

import asyncio
import json
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.services.circuit_breaker import get_circuit_breaker_manager
from src.utils.circuit_breaker_monitor import get_circuit_breaker_monitor
from src.utils.logger import logger
from src.utils.performance_monitor import get_performance_monitor


class MetricType(Enum):
    """Types of metrics collected."""

    COUNTER = "counter"  # Incrementing values
    GAUGE = "gauge"  # Point-in-time values
    HISTOGRAM = "histogram"  # Distribution of values
    SUMMARY = "summary"  # Statistical summaries
    HEALTH = "health"  # Service health indicators


@dataclass
class MetricPoint:
    """Single metric data point."""

    timestamp: datetime
    metric_name: str
    metric_type: MetricType
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthMetrics:
    """Service health metrics."""

    service_name: str
    is_healthy: bool
    health_score: float  # 0-100
    last_check: datetime
    response_time_ms: float
    error_rate: float
    uptime_percent: float
    alerts: List[str] = field(default_factory=list)


@dataclass
class ApplicationMetrics:
    """Comprehensive application metrics."""

    timestamp: datetime

    # Performance metrics
    avg_translation_time: float
    avg_ocr_time: float
    avg_screenshot_time: float

    # Usage metrics
    total_translations: int
    successful_translations: int
    failed_translations: int

    # Circuit breaker metrics
    circuit_breaker_states: Dict[str, str]
    service_health_scores: Dict[str, float]

    # System metrics
    cpu_usage: float
    memory_usage: float
    disk_usage: float

    # Repository metrics
    translation_cache_size: int
    screenshot_cache_size: int

    # Event system metrics
    events_published: int
    events_processed: int

    # Overall health
    overall_health_score: float
    critical_issues: List[str] = field(default_factory=list)


class EnhancedMetricsCollector:
    """Enhanced metrics collection and analysis system."""

    def __init__(self, data_dir: str = "data", max_metrics: int = 10000):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.metrics_file = self.data_dir / "metrics.json"

        # Metrics storage
        self.metrics: deque[MetricPoint] = deque(maxlen=max_metrics)
        self.health_metrics: Dict[str, HealthMetrics] = {}
        self.application_snapshots: deque[ApplicationMetrics] = deque(maxlen=100)

        # Aggregation counters
        self.counters: defaultdict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: defaultdict[str, List[float]] = defaultdict(list)

        # Component references
        self.performance_monitor = get_performance_monitor()
        self.circuit_breaker_manager = get_circuit_breaker_manager()
        self.circuit_breaker_monitor = get_circuit_breaker_monitor()

        # Collection state
        self._collecting = False
        self._collection_task: Optional[asyncio.Task] = None

        logger.info("Enhanced metrics collector initialized")

    async def start_collection(self, interval: float = 30.0) -> None:
        """Start automated metrics collection."""
        if self._collecting:
            return

        self._collecting = True
        self._collection_task = asyncio.create_task(self._collection_loop(interval))
        logger.info(f"Enhanced metrics collection started (interval: {interval}s)")

    async def stop_collection(self) -> None:
        """Stop automated metrics collection."""
        self._collecting = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        logger.info("Enhanced metrics collection stopped")

    async def _collection_loop(self, interval: float) -> None:
        """Main collection loop."""
        while self._collecting:
            try:
                await self.collect_all_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(interval)

    async def collect_all_metrics(self) -> ApplicationMetrics:
        """Collect comprehensive application metrics."""
        timestamp = datetime.now()

        # Collect performance metrics
        perf_data = self.performance_monitor.get_performance_report()

        # Collect circuit breaker metrics
        cb_health = self.circuit_breaker_monitor.get_overall_health()
        cb_details = self.circuit_breaker_monitor.get_service_details()

        # Calculate derived metrics
        translation_stats = self.performance_monitor.get_operation_stats("translation")
        ocr_stats = self.performance_monitor.get_operation_stats("ocr_extraction")
        screenshot_stats = self.performance_monitor.get_operation_stats("screenshot_capture")

        # Build comprehensive metrics snapshot
        app_metrics = ApplicationMetrics(
            timestamp=timestamp,
            # Performance metrics
            avg_translation_time=translation_stats.get("recent_avg_time", 0.0),
            avg_ocr_time=ocr_stats.get("recent_avg_time", 0.0),
            avg_screenshot_time=screenshot_stats.get("recent_avg_time", 0.0),
            # Usage metrics
            total_translations=translation_stats.get("total_count", 0),
            successful_translations=translation_stats.get("total_count", 0)
            - translation_stats.get("error_count", 0),
            failed_translations=translation_stats.get("error_count", 0),
            # Circuit breaker metrics
            circuit_breaker_states={name: details["state"] for name, details in cb_details.items()},
            service_health_scores={
                name: details["health_score"] for name, details in cb_details.items()
            },
            # System metrics
            cpu_usage=perf_data.get("current_cpu_percent", 0.0),
            memory_usage=perf_data.get("current_memory_percent", 0.0),
            disk_usage=perf_data.get("disk_usage_percent", 0.0),
            # Repository metrics (placeholder - would integrate with repositories)
            translation_cache_size=0,  # Would get from repository
            screenshot_cache_size=0,  # Would get from repository
            # Event system metrics (placeholder - would integrate with event bus)
            events_published=0,  # Would get from event bus
            events_processed=0,  # Would get from event bus
            # Overall health calculation
            overall_health_score=self._calculate_overall_health(cb_health, perf_data),
            critical_issues=cb_health.get("issues", []),
        )

        # Store snapshot
        self.application_snapshots.append(app_metrics)

        # Record individual metrics
        await self._record_metrics_from_snapshot(app_metrics)

        return app_metrics

    def _calculate_overall_health(self, cb_health: Dict, perf_data: Dict) -> float:
        """Calculate overall application health score (0-100)."""
        health_score = 100.0

        # Circuit breaker impact
        failed_services = cb_health.get("failed_services", 0)
        degraded_services = cb_health.get("degraded_services", 0)
        total_services = cb_health.get("total_services", 1)

        if total_services > 0:
            service_health = (
                total_services - failed_services - degraded_services * 0.5
            ) / total_services
            health_score *= service_health

        # Performance impact
        cpu_usage = perf_data.get("current_cpu_percent", 0)
        memory_usage = perf_data.get("current_memory_percent", 0)

        if cpu_usage > 80:
            health_score *= 0.8
        elif cpu_usage > 90:
            health_score *= 0.6

        if memory_usage > 85:
            health_score *= 0.8
        elif memory_usage > 95:
            health_score *= 0.5

        return max(0.0, min(100.0, health_score))

    async def _record_metrics_from_snapshot(self, snapshot: ApplicationMetrics) -> None:
        """Record individual metrics from application snapshot."""
        timestamp = snapshot.timestamp

        # Performance metrics
        self.record_metric(
            "translation_time", MetricType.HISTOGRAM, snapshot.avg_translation_time, timestamp
        )
        self.record_metric("ocr_time", MetricType.HISTOGRAM, snapshot.avg_ocr_time, timestamp)
        self.record_metric(
            "screenshot_time", MetricType.HISTOGRAM, snapshot.avg_screenshot_time, timestamp
        )

        # Usage counters
        self.record_metric(
            "translations_total", MetricType.COUNTER, snapshot.total_translations, timestamp
        )
        self.record_metric(
            "translations_failed", MetricType.COUNTER, snapshot.failed_translations, timestamp
        )

        # System gauges
        self.record_metric("cpu_usage_percent", MetricType.GAUGE, snapshot.cpu_usage, timestamp)
        self.record_metric(
            "memory_usage_percent", MetricType.GAUGE, snapshot.memory_usage, timestamp
        )
        self.record_metric("disk_usage_percent", MetricType.GAUGE, snapshot.disk_usage, timestamp)

        # Health score
        self.record_metric(
            "overall_health_score", MetricType.GAUGE, snapshot.overall_health_score, timestamp
        )

        # Service health scores
        for service, score in snapshot.service_health_scores.items():
            self.record_metric(
                "service_health_score",
                MetricType.GAUGE,
                score,
                timestamp,
                labels={"service": service},
            )

    def record_metric(
        self,
        name: str,
        metric_type: MetricType,
        value: float,
        timestamp: Optional[datetime] = None,
        labels: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a single metric point."""
        if timestamp is None:
            timestamp = datetime.now()

        metric = MetricPoint(
            timestamp=timestamp,
            metric_name=name,
            metric_type=metric_type,
            value=value,
            labels=labels or {},
            metadata=metadata or {},
        )

        self.metrics.append(metric)

        # Update aggregations
        if metric_type == MetricType.COUNTER:
            self.counters[name] += value
        elif metric_type == MetricType.GAUGE:
            self.gauges[name] = value
        elif metric_type == MetricType.HISTOGRAM:
            self.histograms[name].append(value)
            # Keep histogram size manageable
            if len(self.histograms[name]) > 1000:
                self.histograms[name] = self.histograms[name][-1000:]

    def get_metric_summary(self, metric_name: str, hours: int = 1) -> Dict[str, Any]:
        """Get statistical summary for a metric over time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        # Get metrics for the time period
        matching_metrics = [
            m for m in self.metrics if m.metric_name == metric_name and m.timestamp > cutoff_time
        ]

        if not matching_metrics:
            return {"metric": metric_name, "count": 0, "period_hours": hours}

        values = [m.value for m in matching_metrics]

        return {
            "metric": metric_name,
            "count": len(values),
            "period_hours": hours,
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1] if values else 0,
            "first_timestamp": matching_metrics[0].timestamp.isoformat(),
            "last_timestamp": matching_metrics[-1].timestamp.isoformat(),
        }

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for metrics dashboard."""
        latest_snapshot = self.application_snapshots[-1] if self.application_snapshots else None

        if not latest_snapshot:
            return {"error": "No metrics data available"}

        # Get trends over last hour
        trends = {
            "translation_time": self.get_metric_summary("translation_time"),
            "cpu_usage": self.get_metric_summary("cpu_usage_percent"),
            "memory_usage": self.get_metric_summary("memory_usage_percent"),
            "health_score": self.get_metric_summary("overall_health_score"),
        }

        return {
            "timestamp": latest_snapshot.timestamp.isoformat(),
            "current_metrics": asdict(latest_snapshot),
            "trends": trends,
            "alerts": latest_snapshot.critical_issues,
            "service_status": {
                name: {
                    "state": state,
                    "health_score": latest_snapshot.service_health_scores.get(name, 0),
                }
                for name, state in latest_snapshot.circuit_breaker_states.items()
            },
        }

    async def export_metrics(self, file_path: Optional[str] = None) -> str:
        """Export all metrics to JSON file."""
        if file_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = str(self.data_dir / f"metrics_export_{timestamp}.json")

        # Prepare export data
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "metrics_count": len(self.metrics),
            "snapshots_count": len(self.application_snapshots),
            "latest_snapshot": (
                asdict(self.application_snapshots[-1]) if self.application_snapshots else None
            ),
            "metric_summaries": {
                name: self.get_metric_summary(name, hours=24)
                for name in set(m.metric_name for m in self.metrics)
            },
            "counters": dict(self.counters),
            "gauges": self.gauges,
            "histogram_stats": {
                name: {
                    "count": len(values),
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0,
                    "avg": sum(values) / len(values) if values else 0,
                }
                for name, values in self.histograms.items()
            },
        }

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info(f"Metrics exported to {file_path}")
        return file_path

    def get_performance_insights(self) -> List[Dict[str, Any]]:
        """Generate performance insights and recommendations."""
        insights = []

        if not self.application_snapshots:
            return insights

        latest = self.application_snapshots[-1]

        # Translation performance insights
        if latest.avg_translation_time > 5.0:
            insights.append(
                {
                    "type": "performance",
                    "severity": "warning",
                    "component": "translation",
                    "message": f"Translation time is high ({latest.avg_translation_time:.2f}s)",
                    "recommendation": "Check network connectivity and Google Translate API status",
                }
            )

        # System resource insights
        if latest.cpu_usage > 80:
            insights.append(
                {
                    "type": "resource",
                    "severity": "warning",
                    "component": "system",
                    "message": f"High CPU usage ({latest.cpu_usage:.1f}%)",
                    "recommendation": "Consider reducing concurrent operations or optimizing algorithms",
                }
            )

        if latest.memory_usage > 85:
            insights.append(
                {
                    "type": "resource",
                    "severity": "critical",
                    "component": "system",
                    "message": f"High memory usage ({latest.memory_usage:.1f}%)",
                    "recommendation": "Check for memory leaks or increase available memory",
                }
            )

        # Service health insights
        for service, score in latest.service_health_scores.items():
            if score < 50:
                insights.append(
                    {
                        "type": "service",
                        "severity": "critical",
                        "component": service,
                        "message": f"Service health is poor ({score:.1f}%)",
                        "recommendation": f"Investigate {service} service issues and consider circuit breaker reset",
                    }
                )

        # Success rate insights
        if latest.total_translations > 0:
            success_rate = latest.successful_translations / latest.total_translations
            if success_rate < 0.9:
                insights.append(
                    {
                        "type": "reliability",
                        "severity": "warning",
                        "component": "translation",
                        "message": f"Translation success rate is low ({success_rate:.1%})",
                        "recommendation": "Review error logs and check external service dependencies",
                    }
                )

        return insights


# Singleton instance for global access
_enhanced_metrics_collector: Optional[EnhancedMetricsCollector] = None


def get_enhanced_metrics_collector(data_dir: str = "data") -> EnhancedMetricsCollector:
    """Get global enhanced metrics collector instance."""
    global _enhanced_metrics_collector
    if _enhanced_metrics_collector is None:
        _enhanced_metrics_collector = EnhancedMetricsCollector(data_dir)
    return _enhanced_metrics_collector

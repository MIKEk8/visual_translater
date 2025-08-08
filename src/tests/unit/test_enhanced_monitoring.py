"""
Unit tests for enhanced monitoring system.
"""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.utils.alert_system import (
    Alert,
    AlertCategory,
    AlertManager,
    AlertRule,
    AlertSeverity,
    AlertStatus,
    FileNotificationChannel,
    LogNotificationChannel,
)
from src.utils.enhanced_metrics import (
    ApplicationMetrics,
    EnhancedMetricsCollector,
    MetricType,
)
from src.utils.monitoring_dashboard import MonitoringDashboard


class TestEnhancedMetricsCollector:
    """Test EnhancedMetricsCollector functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def metrics_collector(self, temp_dir):
        """Create metrics collector for testing."""
        return EnhancedMetricsCollector(temp_dir, max_metrics=100)

    def test_metric_recording(self, metrics_collector):
        """Test recording individual metrics."""
        # Record different metric types
        metrics_collector.record_metric("test_counter", MetricType.COUNTER, 5.0)
        metrics_collector.record_metric("test_gauge", MetricType.GAUGE, 75.5)
        metrics_collector.record_metric("test_histogram", MetricType.HISTOGRAM, 1.23)

        # Verify metrics are stored
        assert len(metrics_collector.metrics) == 3

        # Verify aggregations
        assert metrics_collector.counters["test_counter"] == 5.0
        assert metrics_collector.gauges["test_gauge"] == 75.5
        assert len(metrics_collector.histograms["test_histogram"]) == 1
        assert metrics_collector.histograms["test_histogram"][0] == 1.23

    def test_metric_summary(self, metrics_collector):
        """Test getting metric summaries."""
        # Record some test data
        test_values = [1.0, 2.0, 3.0, 4.0, 5.0]
        for value in test_values:
            metrics_collector.record_metric("test_metric", MetricType.HISTOGRAM, value)

        # Get summary
        summary = metrics_collector.get_metric_summary("test_metric")

        assert summary["count"] == 5
        assert summary["min"] == 1.0
        assert summary["max"] == 5.0
        assert summary["avg"] == 3.0
        assert summary["latest"] == 5.0

    @pytest.mark.asyncio
    async def test_collection_loop(self, metrics_collector):
        """Test automated collection loop."""
        # Mock the collection method
        metrics_collector.collect_all_metrics = AsyncMock()

        # Start collection for short duration
        await metrics_collector.start_collection(0.1)
        await asyncio.sleep(0.25)  # Let it run for 2-3 cycles
        await metrics_collector.stop_collection()

        # Verify collection was called multiple times
        assert metrics_collector.collect_all_metrics.call_count >= 2

    @pytest.mark.asyncio
    async def test_export_metrics(self, metrics_collector, temp_dir):
        """Test metrics export functionality."""
        # Add some test data
        metrics_collector.record_metric("test_export", MetricType.COUNTER, 42.0)

        # Export metrics
        export_path = await metrics_collector.export_metrics()

        # Verify file was created
        assert Path(export_path).exists()

        # Verify content
        import json

        with open(export_path, "r") as f:
            data = json.load(f)

        assert "export_timestamp" in data
        assert "counters" in data
        assert data["counters"]["test_export"] == 42.0


class TestAlertSystem:
    """Test alert system functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def alert_manager(self, temp_dir):
        """Create alert manager for testing."""
        return AlertManager(temp_dir)

    @pytest.fixture
    def sample_alert(self):
        """Create sample alert for testing."""
        return Alert(
            id="test-alert-123",
            title="Test Alert",
            description="This is a test alert",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.PERFORMANCE,
            source="test",
            timestamp=datetime.now(),
        )

    def test_alert_rule_creation(self, alert_manager):
        """Test creating alert rules."""
        rule = AlertRule(
            name="test_rule",
            description="Test rule",
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.SYSTEM,
            metric_name="test_metric",
            condition="gt",
            threshold=100.0,
        )

        alert_manager.add_alert_rule(rule)

        assert "test_rule" in alert_manager.alert_rules
        assert alert_manager.alert_rules["test_rule"].threshold == 100.0

    @pytest.mark.asyncio
    async def test_alert_firing(self, alert_manager, sample_alert):
        """Test firing alerts."""
        # Fire alert
        await alert_manager.fire_alert(sample_alert)

        # Verify alert is active
        assert sample_alert.id in alert_manager.active_alerts
        assert len(alert_manager.alert_history) == 1

        # Verify statistics
        assert alert_manager.stats["total_alerts"] == 1
        assert alert_manager.stats["alerts_by_severity"]["warning"] == 1

    @pytest.mark.asyncio
    async def test_alert_acknowledgment(self, alert_manager, sample_alert):
        """Test acknowledging alerts."""
        # Fire and acknowledge alert
        await alert_manager.fire_alert(sample_alert)
        success = await alert_manager.acknowledge_alert(sample_alert.id, "test_user")

        assert success is True
        assert alert_manager.active_alerts[sample_alert.id].status == AlertStatus.ACKNOWLEDGED
        assert alert_manager.active_alerts[sample_alert.id].acknowledged_by == "test_user"

    @pytest.mark.asyncio
    async def test_alert_resolution(self, alert_manager, sample_alert):
        """Test resolving alerts."""
        # Fire and resolve alert
        await alert_manager.fire_alert(sample_alert)
        success = await alert_manager.resolve_alert(sample_alert.id)

        assert success is True
        assert sample_alert.id not in alert_manager.active_alerts
        assert alert_manager.alert_history[-1].status == AlertStatus.RESOLVED

    @pytest.mark.asyncio
    async def test_metric_alert_checking(self, alert_manager):
        """Test checking metrics against alert rules."""
        # Add rule that should trigger
        rule = AlertRule(
            name="high_cpu",
            description="CPU too high",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.RESOURCE,
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            notification_channels=["log"],
        )
        alert_manager.add_alert_rule(rule)

        # Check metric that should trigger alert
        alerts = await alert_manager.check_metric_alerts("cpu_usage", 90.0)

        assert len(alerts) == 1
        assert alerts[0].metric_name == "cpu_usage"
        assert alerts[0].metric_value == 90.0
        assert alerts[0].severity == AlertSeverity.WARNING

    def test_notification_channels(self, alert_manager, temp_dir):
        """Test notification channels."""
        # Test log channel
        log_channel = LogNotificationChannel("WARNING")
        alert_manager.add_notification_channel("test_log", log_channel)

        assert "test_log" in alert_manager.notification_channels

        # Test file channel
        test_file = Path(temp_dir) / "alerts.log"
        file_channel = FileNotificationChannel(str(test_file))
        alert_manager.add_notification_channel("test_file", file_channel)

        assert "test_file" in alert_manager.notification_channels

    @pytest.mark.asyncio
    async def test_alert_export(self, alert_manager, sample_alert, temp_dir):
        """Test exporting alert data."""
        # Fire an alert
        await alert_manager.fire_alert(sample_alert)

        # Export alerts
        export_path = await alert_manager.export_alerts()

        # Verify file exists and contains data
        assert Path(export_path).exists()

        import json

        with open(export_path, "r") as f:
            data = json.load(f)

        assert "active_alerts" in data
        assert len(data["active_alerts"]) == 1
        assert data["active_alerts"][0]["id"] == sample_alert.id


class TestMonitoringDashboard:
    """Test monitoring dashboard functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def dashboard(self, temp_dir):
        """Create monitoring dashboard for testing."""
        return MonitoringDashboard(temp_dir)

    def test_dashboard_initialization(self, dashboard):
        """Test dashboard initialization."""
        assert dashboard.metrics_collector is not None
        assert dashboard.alert_manager is not None
        assert dashboard.circuit_monitor is not None
        assert dashboard.performance_monitor is not None

    @patch("src.utils.monitoring_dashboard.get_enhanced_metrics_collector")
    @patch("src.utils.monitoring_dashboard.get_alert_manager")
    @patch("src.utils.monitoring_dashboard.get_circuit_breaker_monitor")
    def test_dashboard_overview(self, mock_cb_monitor, mock_alert_manager, mock_metrics, dashboard):
        """Test getting dashboard overview."""
        # Mock component responses
        mock_metrics.return_value.get_dashboard_data.return_value = {
            "current_metrics": {"overall_health_score": 85.0}
        }
        mock_alert_manager.return_value.get_alert_summary.return_value = {
            "active_alerts_count": 2,
            "active_by_severity": {"warning": 2},
        }
        mock_cb_monitor.return_value.get_overall_health.return_value = {
            "healthy_services": 3,
            "total_services": 3,
            "failed_services": 0,
            "degraded_services": 0,
        }

        # Get overview
        overview = dashboard.get_dashboard_overview()

        assert "status" in overview
        assert "metrics" in overview
        assert "alerts" in overview
        assert "circuit_breakers" in overview

    def test_health_check(self, dashboard):
        """Test quick health check."""
        with patch.object(dashboard, "get_dashboard_overview") as mock_overview:
            mock_overview.return_value = {
                "status": {"overall": "healthy", "health_score": 95.0},
                "alerts": {"active_alerts_count": 0},
                "circuit_breakers": {"service_status": {"service1": "closed"}},
            }

            health = dashboard.get_health_check()

            assert health["status"] == "healthy"
            assert health["health_score"] == 95.0
            assert "timestamp" in health

    def test_status_summary_generation(self, dashboard):
        """Test generating human-readable status summary."""
        with patch.object(dashboard, "get_dashboard_overview") as mock_overview:
            mock_overview.return_value = {
                "status": {
                    "overall": "warning",
                    "health_score": 75.0,
                    "issues": ["High CPU usage", "Service degraded"],
                    "last_updated": "2023-01-01T12:00:00",
                },
                "alerts": {"active_alerts_count": 1, "active_by_severity": {"warning": 1}},
                "circuit_breakers": {"healthy_services": 2, "total_services": 3},
            }

            summary = dashboard.generate_status_summary()

            assert "Screen Translator Monitoring Summary" in summary
            assert "WARNING" in summary
            assert "Health Score: 75.0%" in summary
            assert "High CPU usage" in summary

    @pytest.mark.asyncio
    async def test_monitoring_lifecycle(self, dashboard):
        """Test starting and stopping monitoring."""
        # Mock the collection method to avoid actual monitoring
        dashboard.metrics_collector.start_collection = AsyncMock()
        dashboard.metrics_collector.stop_collection = AsyncMock()

        # Start monitoring
        await dashboard.start_monitoring(0.1)
        assert dashboard._auto_refresh is True

        # Stop monitoring
        await dashboard.stop_monitoring()
        assert dashboard._auto_refresh is False

        # Verify collection methods were called
        dashboard.metrics_collector.start_collection.assert_called_once()
        dashboard.metrics_collector.stop_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_dashboard_export(self, dashboard, temp_dir):
        """Test exporting dashboard report."""
        with patch.object(dashboard, "get_detailed_report") as mock_report:
            mock_report.return_value = {
                "timestamp": "2023-01-01T12:00:00",
                "status": "healthy",
                "test_data": "sample",
            }

            # Export report
            export_path = await dashboard.export_dashboard_report()

            # Verify file exists
            assert Path(export_path).exists()

            # Verify content
            import json

            with open(export_path, "r") as f:
                data = json.load(f)

            assert "export_info" in data
            assert data["test_data"] == "sample"


class TestMonitoringIntegration:
    """Integration tests for monitoring system."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.mark.asyncio
    async def test_end_to_end_monitoring(self, temp_dir):
        """Test complete monitoring workflow."""
        # Create dashboard first (which creates other components via singletons)
        dashboard = MonitoringDashboard(temp_dir)

        # Get the same instances dashboard is using
        metrics_collector = dashboard.metrics_collector
        alert_manager = dashboard.alert_manager

        # Record some metrics that should trigger alerts
        metrics_collector.record_metric("cpu_usage_percent", MetricType.GAUGE, 95.0)

        # Check for alerts
        alerts = await alert_manager.check_metric_alerts("cpu_usage_percent", 95.0)

        # Verify alert was created
        assert len(alerts) > 0
        high_cpu_alert = next((a for a in alerts if "cpu" in a.title.lower()), None)
        assert high_cpu_alert is not None
        assert high_cpu_alert.severity == AlertSeverity.CRITICAL

        # Get dashboard overview
        overview = dashboard.get_dashboard_overview()

        # Verify dashboard reflects the alert
        assert overview["alerts"]["active_alerts_count"] > 0

    @pytest.mark.asyncio
    async def test_performance_insights_generation(self, temp_dir):
        """Test generation of performance insights."""
        metrics_collector = EnhancedMetricsCollector(temp_dir)

        # Record metrics that should generate insights
        metrics_collector.record_metric("translation_time", MetricType.HISTOGRAM, 8.0)  # Slow
        metrics_collector.record_metric("cpu_usage_percent", MetricType.GAUGE, 85.0)  # High

        # Mock the application snapshot
        snapshot = ApplicationMetrics(
            timestamp=datetime.now(),
            avg_translation_time=8.0,
            avg_ocr_time=2.0,
            avg_screenshot_time=1.0,
            total_translations=100,
            successful_translations=90,
            failed_translations=10,
            circuit_breaker_states={"google_translate": "closed"},
            service_health_scores={"google_translate": 75.0},
            cpu_usage=85.0,
            memory_usage=70.0,
            disk_usage=50.0,
            translation_cache_size=50,
            screenshot_cache_size=20,
            events_published=200,
            events_processed=198,
            overall_health_score=75.0,
            critical_issues=[],
        )

        metrics_collector.application_snapshots.append(snapshot)

        # Generate insights
        insights = metrics_collector.get_performance_insights()

        # Verify insights were generated
        assert len(insights) > 0

        # Check for expected insights
        translation_insight = next(
            (i for i in insights if "translation" in i["message"].lower()), None
        )
        assert translation_insight is not None
        assert translation_insight["severity"] == "warning"

        cpu_insight = next((i for i in insights if "cpu" in i["message"].lower()), None)
        assert cpu_insight is not None

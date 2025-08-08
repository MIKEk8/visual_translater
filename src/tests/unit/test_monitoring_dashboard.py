"""Unit tests for monitoring dashboard utils module"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.utils.monitoring_dashboard import MonitoringDashboard


@pytest.fixture
def mock_metrics_collector():
    """Create mock metrics collector"""
    collector = Mock()
    collector.start_collection = AsyncMock()
    collector.stop_collection = AsyncMock()
    collector.get_current_metrics = Mock(
        return_value={
            "translation_count": 100,
            "ocr_count": 105,
            "tts_count": 80,
            "error_count": 5,
            "avg_response_time": 1.2,
        }
    )
    return collector


@pytest.fixture
def mock_alert_manager():
    """Create mock alert manager"""
    manager = Mock()
    manager.get_active_alerts = Mock(return_value=[])
    manager.get_statistics = Mock(
        return_value={
            "total_alerts": 10,
            "active_alerts": 2,
            "resolved_alerts": 8,
            "by_severity": {"warning": 6, "critical": 2, "emergency": 2},
        }
    )
    return manager


@pytest.fixture
def mock_circuit_monitor():
    """Create mock circuit breaker monitor"""
    monitor = Mock()
    monitor.get_circuit_states = Mock(
        return_value={
            "translation_service": {"state": "CLOSED", "failure_count": 0},
            "ocr_service": {"state": "HALF_OPEN", "failure_count": 3},
            "tts_service": {"state": "OPEN", "failure_count": 10},
        }
    )
    return monitor


@pytest.fixture
def mock_performance_monitor():
    """Create mock performance monitor"""
    monitor = Mock()
    monitor.get_current_stats = Mock(
        return_value={
            "cpu_usage": 65.2,
            "memory_usage": 78.5,
            "disk_usage": 45.0,
            "network_io": {"bytes_sent": 1024000, "bytes_recv": 2048000},
        }
    )
    monitor.get_performance_history = Mock(return_value=[])
    return monitor


@pytest.fixture
def monitoring_dashboard(tmp_path):
    """Create MonitoringDashboard instance with mocked dependencies"""
    data_dir = str(tmp_path / "monitoring_data")

    with patch(
        "src.utils.monitoring_dashboard.get_enhanced_metrics_collector"
    ) as mock_metrics, patch(
        "src.utils.monitoring_dashboard.get_alert_manager"
    ) as mock_alerts, patch(
        "src.utils.monitoring_dashboard.get_circuit_breaker_monitor"
    ) as mock_circuit, patch(
        "src.utils.monitoring_dashboard.get_performance_monitor"
    ) as mock_perf:

        # Configure mocks
        mock_metrics.return_value = Mock()
        mock_alerts.return_value = Mock()
        mock_circuit.return_value = Mock()
        mock_perf.return_value = Mock()

        dashboard = MonitoringDashboard(data_dir)
        return dashboard


class TestMonitoringDashboard:
    """Test MonitoringDashboard class"""

    def test_initialization(self, monitoring_dashboard, tmp_path):
        """Test dashboard initialization"""
        assert monitoring_dashboard.data_dir.exists()
        assert monitoring_dashboard.metrics_collector is not None
        assert monitoring_dashboard.alert_manager is not None
        assert monitoring_dashboard.circuit_monitor is not None
        assert monitoring_dashboard.performance_monitor is not None
        assert monitoring_dashboard._auto_refresh is False
        assert monitoring_dashboard._refresh_task is None

    @pytest.mark.asyncio
    async def test_start_monitoring(self, monitoring_dashboard):
        """Test starting monitoring"""
        refresh_interval = 10.0

        with patch.object(monitoring_dashboard, "_refresh_loop") as mock_refresh_loop:
            await monitoring_dashboard.start_monitoring(refresh_interval)

            # Should start metrics collection
            monitoring_dashboard.metrics_collector.start_collection.assert_called_once_with(
                refresh_interval
            )

            # Should enable auto-refresh
            assert monitoring_dashboard._auto_refresh is True
            assert monitoring_dashboard._refresh_task is not None

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, monitoring_dashboard):
        """Test stopping monitoring"""
        # Mock running state
        monitoring_dashboard._auto_refresh = True
        mock_task = Mock()
        monitoring_dashboard._refresh_task = mock_task

        await monitoring_dashboard.stop_monitoring()

        # Should stop metrics collection
        monitoring_dashboard.metrics_collector.stop_collection.assert_called_once()

        # Should disable auto-refresh
        assert monitoring_dashboard._auto_refresh is False
        mock_task.cancel.assert_called_once()

    def test_get_system_overview(self, monitoring_dashboard):
        """Test getting system overview"""
        # Mock component data
        monitoring_dashboard.metrics_collector.get_current_metrics.return_value = {
            "translation_count": 500,
            "error_rate": 0.02,
        }

        monitoring_dashboard.performance_monitor.get_current_stats.return_value = {
            "cpu_usage": 45.0,
            "memory_usage": 68.5,
        }

        monitoring_dashboard.alert_manager.get_statistics.return_value = {
            "active_alerts": 3,
            "total_alerts": 15,
        }

        overview = monitoring_dashboard.get_system_overview()

        assert "metrics" in overview
        assert "performance" in overview
        assert "alerts" in overview
        assert "circuits" in overview
        assert "timestamp" in overview
        assert overview["metrics"]["translation_count"] == 500

    def test_get_detailed_metrics(self, monitoring_dashboard):
        """Test getting detailed metrics"""
        # Mock historical data
        monitoring_dashboard.metrics_collector.get_historical_data.return_value = [
            {"timestamp": 1234567890, "translation_count": 450},
            {"timestamp": 1234567950, "translation_count": 475},
            {"timestamp": 1234568010, "translation_count": 500},
        ]

        time_range = timedelta(hours=1)
        detailed_metrics = monitoring_dashboard.get_detailed_metrics(time_range)

        assert "historical_data" in detailed_metrics
        assert "summary" in detailed_metrics
        assert len(detailed_metrics["historical_data"]) == 3

    def test_get_alert_summary(self, monitoring_dashboard):
        """Test getting alert summary"""
        # Mock alert data
        mock_alerts = [
            Mock(
                id="alert1",
                title="High CPU",
                severity=Mock(value="warning"),
                category=Mock(value="performance"),
                status=Mock(value="active"),
                timestamp=datetime.now().timestamp(),
            ),
            Mock(
                id="alert2",
                title="Service Down",
                severity=Mock(value="critical"),
                category=Mock(value="service"),
                status=Mock(value="active"),
                timestamp=datetime.now().timestamp(),
            ),
        ]

        monitoring_dashboard.alert_manager.get_active_alerts.return_value = mock_alerts
        monitoring_dashboard.alert_manager.get_statistics.return_value = {
            "total_alerts": 10,
            "active_alerts": 2,
            "by_severity": {"warning": 1, "critical": 1},
        }

        alert_summary = monitoring_dashboard.get_alert_summary()

        assert "active_alerts" in alert_summary
        assert "statistics" in alert_summary
        assert len(alert_summary["active_alerts"]) == 2
        assert alert_summary["statistics"]["active_alerts"] == 2

    def test_get_performance_summary(self, monitoring_dashboard):
        """Test getting performance summary"""
        # Mock performance data
        monitoring_dashboard.performance_monitor.get_current_stats.return_value = {
            "cpu_usage": 75.2,
            "memory_usage": 85.7,
            "disk_usage": 45.0,
        }

        monitoring_dashboard.performance_monitor.get_performance_history.return_value = [
            {"timestamp": 1234567890, "cpu_usage": 70.0},
            {"timestamp": 1234567950, "cpu_usage": 72.5},
            {"timestamp": 1234568010, "cpu_usage": 75.2},
        ]

        perf_summary = monitoring_dashboard.get_performance_summary()

        assert "current_stats" in perf_summary
        assert "history" in perf_summary
        assert "trends" in perf_summary
        assert perf_summary["current_stats"]["cpu_usage"] == 75.2

    def test_get_circuit_breaker_status(self, monitoring_dashboard):
        """Test getting circuit breaker status"""
        # Mock circuit breaker data
        monitoring_dashboard.circuit_monitor.get_circuit_states.return_value = {
            "translation_service": {
                "state": "CLOSED",
                "failure_count": 0,
                "success_count": 1000,
                "last_failure": None,
            },
            "ocr_service": {
                "state": "HALF_OPEN",
                "failure_count": 3,
                "success_count": 500,
                "last_failure": datetime.now().timestamp(),
            },
        }

        circuit_status = monitoring_dashboard.get_circuit_breaker_status()

        assert "circuits" in circuit_status
        assert "summary" in circuit_status
        assert len(circuit_status["circuits"]) == 2
        assert circuit_status["circuits"]["translation_service"]["state"] == "CLOSED"

    def test_generate_health_report(self, monitoring_dashboard):
        """Test generating comprehensive health report"""
        # Mock all component data
        monitoring_dashboard.metrics_collector.get_current_metrics.return_value = {
            "translation_count": 1000,
            "error_rate": 0.01,
        }

        monitoring_dashboard.performance_monitor.get_current_stats.return_value = {
            "cpu_usage": 60.0,
            "memory_usage": 70.0,
        }

        monitoring_dashboard.alert_manager.get_active_alerts.return_value = []

        monitoring_dashboard.circuit_monitor.get_circuit_states.return_value = {
            "service1": {"state": "CLOSED"}
        }

        health_report = monitoring_dashboard.generate_health_report()

        assert "overall_health" in health_report
        assert "components" in health_report
        assert "recommendations" in health_report
        assert "timestamp" in health_report
        assert health_report["overall_health"] in ["healthy", "warning", "critical"]

    def test_export_dashboard_data(self, monitoring_dashboard, tmp_path):
        """Test exporting dashboard data"""
        # Mock data for export
        monitoring_dashboard.get_system_overview = Mock(return_value={"test": "data"})

        export_file = tmp_path / "dashboard_export.json"

        monitoring_dashboard.export_dashboard_data(str(export_file))

        assert export_file.exists()

        # Verify exported data
        with open(export_file) as f:
            exported_data = json.load(f)

        assert "export_timestamp" in exported_data
        assert "system_overview" in exported_data

    def test_import_dashboard_data(self, monitoring_dashboard, tmp_path):
        """Test importing dashboard data"""
        # Create test import data
        import_data = {
            "export_timestamp": datetime.now().isoformat(),
            "system_overview": {"test": "imported_data"},
            "metrics": {"translation_count": 123},
        }

        import_file = tmp_path / "dashboard_import.json"
        with open(import_file, "w") as f:
            json.dump(import_data, f)

        result = monitoring_dashboard.import_dashboard_data(str(import_file))

        assert result is True

    def test_create_custom_dashboard(self, monitoring_dashboard):
        """Test creating custom dashboard configuration"""
        config = {
            "name": "Custom Dashboard",
            "widgets": [
                {"type": "metric", "title": "Translations", "metric": "translation_count"},
                {"type": "chart", "title": "CPU Usage", "metric": "cpu_usage", "timerange": "1h"},
                {
                    "type": "alert_list",
                    "title": "Active Alerts",
                    "severities": ["critical", "warning"],
                },
            ],
            "refresh_interval": 15,
            "auto_refresh": True,
        }

        dashboard_id = monitoring_dashboard.create_custom_dashboard(config)

        assert dashboard_id is not None
        assert len(dashboard_id) > 0

    def test_get_dashboard_config(self, monitoring_dashboard):
        """Test getting dashboard configuration"""
        # Create a custom dashboard first
        config = {"name": "Test Dashboard", "widgets": []}
        dashboard_id = monitoring_dashboard.create_custom_dashboard(config)

        retrieved_config = monitoring_dashboard.get_dashboard_config(dashboard_id)

        assert retrieved_config is not None
        assert retrieved_config["name"] == "Test Dashboard"

    def test_calculate_system_health_score(self, monitoring_dashboard):
        """Test calculating overall system health score"""
        # Mock component scores
        with patch.object(
            monitoring_dashboard, "_calculate_metrics_score", return_value=0.9
        ), patch.object(
            monitoring_dashboard, "_calculate_performance_score", return_value=0.8
        ), patch.object(
            monitoring_dashboard, "_calculate_alert_score", return_value=0.7
        ), patch.object(
            monitoring_dashboard, "_calculate_circuit_score", return_value=0.95
        ):

            health_score = monitoring_dashboard.calculate_system_health_score()

            # Should be weighted average of component scores
            assert 0.0 <= health_score <= 1.0
            assert health_score > 0.7  # Should be reasonable given mock scores

    def test_get_trending_metrics(self, monitoring_dashboard):
        """Test getting trending metrics"""
        # Mock trending data
        monitoring_dashboard.metrics_collector.get_trending_metrics.return_value = {
            "translation_count": {"trend": "increasing", "change_percent": 15.5},
            "error_rate": {"trend": "decreasing", "change_percent": -8.2},
            "response_time": {"trend": "stable", "change_percent": 1.1},
        }

        trending = monitoring_dashboard.get_trending_metrics()

        assert "translation_count" in trending
        assert trending["translation_count"]["trend"] == "increasing"

    @pytest.mark.asyncio
    async def test_refresh_loop(self, monitoring_dashboard):
        """Test dashboard refresh loop"""
        monitoring_dashboard._auto_refresh = True
        refresh_count = 0

        async def mock_refresh():
            nonlocal refresh_count
            refresh_count += 1
            if refresh_count >= 3:  # Stop after 3 refreshes
                monitoring_dashboard._auto_refresh = False

        with patch.object(
            monitoring_dashboard, "_refresh_dashboard_data", side_effect=mock_refresh
        ):
            await monitoring_dashboard._refresh_loop(0.1)  # Very short interval for testing

            assert refresh_count >= 3

    def test_set_alert_thresholds(self, monitoring_dashboard):
        """Test setting custom alert thresholds"""
        thresholds = {
            "cpu_usage": {"warning": 70, "critical": 90},
            "memory_usage": {"warning": 80, "critical": 95},
            "error_rate": {"warning": 0.05, "critical": 0.1},
        }

        monitoring_dashboard.set_alert_thresholds(thresholds)

        # Should update alert manager with new thresholds
        monitoring_dashboard.alert_manager.update_thresholds.assert_called_once_with(thresholds)

    def test_get_component_dependencies(self, monitoring_dashboard):
        """Test getting component dependency map"""
        dependencies = monitoring_dashboard.get_component_dependencies()

        assert "services" in dependencies
        assert "dependencies" in dependencies

        # Should show relationships between components
        services = dependencies["services"]
        assert any("translation" in service.lower() for service in services)

    def test_simulate_load_test(self, monitoring_dashboard):
        """Test simulating load test scenario"""
        load_config = {
            "duration": 60,  # seconds
            "concurrent_users": 10,
            "requests_per_second": 5,
            "scenario": "translation_stress_test",
        }

        with patch.object(monitoring_dashboard, "_execute_load_test") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "total_requests": 300,
                "failed_requests": 5,
                "avg_response_time": 1.2,
            }

            result = monitoring_dashboard.simulate_load_test(load_config)

            assert result["success"] is True
            assert result["total_requests"] == 300

    def test_generate_sla_report(self, monitoring_dashboard):
        """Test generating SLA compliance report"""
        sla_config = {
            "availability_target": 99.9,
            "response_time_target": 2.0,
            "error_rate_target": 0.01,
            "reporting_period": "monthly",
        }

        with patch.object(monitoring_dashboard, "_calculate_sla_metrics") as mock_calculate:
            mock_calculate.return_value = {
                "availability": 99.95,
                "avg_response_time": 1.8,
                "error_rate": 0.008,
            }

            sla_report = monitoring_dashboard.generate_sla_report(sla_config)

            assert "compliance" in sla_report
            assert "metrics" in sla_report
            assert sla_report["metrics"]["availability"] == 99.95

    def test_dashboard_permissions(self, monitoring_dashboard):
        """Test dashboard access permissions"""
        user_roles = ["admin", "operator", "viewer"]

        for role in user_roles:
            permissions = monitoring_dashboard.get_user_permissions(role)

            assert "read" in permissions

            if role == "admin":
                assert "write" in permissions
                assert "configure" in permissions
            elif role == "operator":
                assert "acknowledge_alerts" in permissions
            else:  # viewer
                assert len(permissions) == 1  # only read

"""
Integrated monitoring dashboard for Screen Translator.

This module provides a comprehensive monitoring interface that integrates
all monitoring components into a unified dashboard view.
"""

import asyncio
import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.alert_system import get_alert_manager
from src.utils.circuit_breaker_monitor import get_circuit_breaker_monitor
from src.utils.enhanced_metrics import get_enhanced_metrics_collector
from src.utils.logger import logger
from src.utils.performance_monitor import get_performance_monitor


class MonitoringDashboard:
    """Comprehensive monitoring dashboard."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Component references
        self.metrics_collector = get_enhanced_metrics_collector(data_dir)
        self.alert_manager = get_alert_manager(data_dir)
        self.circuit_monitor = get_circuit_breaker_monitor()
        self.performance_monitor = get_performance_monitor()

        # Dashboard state
        self._auto_refresh = False
        self._refresh_task: Optional[asyncio.Task] = None

        logger.info("Monitoring dashboard initialized")

    async def start_monitoring(self, refresh_interval: float = 30.0) -> None:
        """Start comprehensive monitoring with auto-refresh."""
        # Start metrics collection
        await self.metrics_collector.start_collection(refresh_interval)

        # Start dashboard refresh
        self._auto_refresh = True
        self._refresh_task = asyncio.create_task(self._refresh_loop(refresh_interval))

        logger.info(f"Monitoring dashboard started (refresh: {refresh_interval}s)")

    async def stop_monitoring(self) -> None:
        """Stop monitoring and cleanup."""
        # Stop auto-refresh
        self._auto_refresh = False
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

        # Stop metrics collection
        await self.metrics_collector.stop_collection()

        logger.info("Monitoring dashboard stopped")

    async def _refresh_loop(self, interval: float) -> None:
        """Dashboard refresh loop."""
        while self._auto_refresh:
            try:
                # Collect fresh metrics
                latest_metrics = await self.metrics_collector.collect_all_metrics()

                # Check for metric-based alerts
                await self._check_metric_alerts(latest_metrics)

                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in dashboard refresh loop: {e}")
                await asyncio.sleep(interval)

    async def _check_metric_alerts(self, metrics) -> None:
        """Check metrics against alert rules."""
        try:
            # Check key metrics for alerts
            metrics_to_check = [
                ("cpu_usage_percent", metrics.cpu_usage),
                ("memory_usage_percent", metrics.memory_usage),
                ("overall_health_score", metrics.overall_health_score),
                ("translation_time", metrics.avg_translation_time),
            ]

            for metric_name, value in metrics_to_check:
                await self.alert_manager.check_metric_alerts(metric_name, value)

            # Check service health scores
            for service, score in metrics.service_health_scores.items():
                await self.alert_manager.check_metric_alerts(
                    "service_health_score", score, labels={"service": service}
                )

        except Exception as e:
            logger.error(f"Error checking metric alerts: {e}")

    def get_dashboard_overview(self) -> Dict[str, Any]:
        """Get comprehensive dashboard overview."""
        try:
            # Get latest metrics
            dashboard_data = self.metrics_collector.get_dashboard_data()

            # Get alert summary
            alert_summary = self.alert_manager.get_alert_summary()

            # Get circuit breaker health
            cb_health = self.circuit_monitor.get_overall_health()

            # Get performance insights
            insights = self.metrics_collector.get_performance_insights()

            # Calculate overall status
            overall_status = self._calculate_overall_status(
                dashboard_data, alert_summary, cb_health
            )

            return {
                "timestamp": datetime.now().isoformat(),
                "status": overall_status,
                "metrics": dashboard_data,
                "alerts": alert_summary,
                "circuit_breakers": cb_health,
                "insights": insights,
                "component_status": {
                    "metrics_collector": (
                        "active" if self.metrics_collector._collecting else "inactive"
                    ),
                    "alert_manager": "active",
                    "circuit_monitor": "active",
                    "performance_monitor": "active",
                },
            }

        except Exception as e:
            logger.error(f"Error generating dashboard overview: {e}")
            return {"timestamp": datetime.now().isoformat(), "status": "error", "error": str(e)}

    def _calculate_overall_status(
        self, metrics_data: Dict, alert_data: Dict, cb_data: Dict
    ) -> Dict[str, Any]:
        """Calculate overall system status."""
        status = "healthy"
        issues = []

        # Check alerts
        critical_alerts = alert_data.get("active_by_severity", {}).get("critical", 0)
        warning_alerts = alert_data.get("active_by_severity", {}).get("warning", 0)

        if critical_alerts > 0:
            status = "critical"
            issues.append(f"{critical_alerts} critical alert(s)")
        elif warning_alerts > 0:
            status = "warning"
            issues.append(f"{warning_alerts} warning alert(s)")

        # Check circuit breakers
        failed_services = cb_data.get("failed_services", 0)
        degraded_services = cb_data.get("degraded_services", 0)

        if failed_services > 0:
            if status != "critical":
                status = "degraded"
            issues.append(f"{failed_services} service(s) failed")

        if degraded_services > 0:
            if status == "healthy":
                status = "degraded"
            issues.append(f"{degraded_services} service(s) degraded")

        # Check health score
        current_metrics = metrics_data.get("current_metrics", {})
        health_score = current_metrics.get("overall_health_score", 100)

        if health_score < 50 and status == "healthy":
            status = "degraded"
            issues.append(f"Low health score ({health_score:.1f}%)")

        return {
            "overall": status,
            "health_score": health_score,
            "issues": issues,
            "last_updated": datetime.now().isoformat(),
        }

    def get_detailed_report(self) -> Dict[str, Any]:
        """Generate detailed monitoring report."""
        try:
            # Get base overview
            overview = self.get_dashboard_overview()

            # Add detailed components
            detailed_report = {
                **overview,
                "detailed_metrics": {
                    "performance_stats": self.performance_monitor.get_all_operation_stats(),
                    "system_performance": self.performance_monitor.get_system_performance(),
                    "circuit_breaker_details": self.circuit_monitor.get_service_details(),
                    "metric_summaries": self._get_metric_summaries(),
                },
                "active_alerts": [
                    asdict(alert) for alert in self.alert_manager.get_active_alerts()
                ],
                "recent_events": self._get_recent_events(),
                "recommendations": self._generate_recommendations(),
            }

            return detailed_report

        except Exception as e:
            logger.error(f"Error generating detailed report: {e}")
            return {"error": str(e)}

    def _get_metric_summaries(self) -> Dict[str, Any]:
        """Get summaries for key metrics."""
        key_metrics = [
            "translation_time",
            "ocr_time",
            "screenshot_time",
            "cpu_usage_percent",
            "memory_usage_percent",
            "overall_health_score",
        ]

        summaries = {}
        for metric in key_metrics:
            try:
                summaries[metric] = self.metrics_collector.get_metric_summary(metric, hours=1)
            except Exception as e:
                logger.warning(f"Failed to get summary for {metric}: {e}")
                summaries[metric] = {"error": str(e)}

        return summaries

    def _get_recent_events(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get recent significant events."""
        events = []
        cutoff_time = datetime.now() - timedelta(hours=hours)

        # Recent alerts
        for alert in self.alert_manager.alert_history:
            if alert.timestamp > cutoff_time:
                events.append(
                    {
                        "timestamp": alert.timestamp.isoformat(),
                        "type": "alert",
                        "severity": alert.severity.value,
                        "message": f"Alert: {alert.title}",
                        "details": alert.description,
                    }
                )

        # Circuit breaker state changes (would need to track these)
        # For now, just current unhealthy services
        unhealthy_services = self.circuit_monitor.manager.get_unhealthy_services()
        for service, status in unhealthy_services.items():
            events.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "type": "service_issue",
                    "severity": "warning",
                    "message": f"Service {service} is unhealthy",
                    "details": status,
                }
            )

        # Sort by timestamp descending
        events.sort(key=lambda x: x["timestamp"], reverse=True)
        return events[:20]  # Last 20 events

    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate system recommendations based on current status."""
        recommendations = []

        try:
            # Get current data
            dashboard_data = self.metrics_collector.get_dashboard_data()
            current_metrics = dashboard_data.get("current_metrics", {})

            # Performance recommendations
            if current_metrics.get("avg_translation_time", 0) > 5.0:
                recommendations.append(
                    {
                        "priority": "medium",
                        "category": "performance",
                        "title": "Optimize Translation Performance",
                        "description": "Translation times are higher than optimal",
                        "action": "Check network connectivity and consider caching strategies",
                    }
                )

            # Resource recommendations
            cpu_usage = current_metrics.get("cpu_usage", 0)
            memory_usage = current_metrics.get("memory_usage", 0)

            if cpu_usage > 80:
                recommendations.append(
                    {
                        "priority": "high",
                        "category": "resources",
                        "title": "High CPU Usage",
                        "description": f"CPU usage is at {cpu_usage:.1f}%",
                        "action": "Consider reducing concurrent operations or optimizing algorithms",
                    }
                )

            if memory_usage > 85:
                recommendations.append(
                    {
                        "priority": "high",
                        "category": "resources",
                        "title": "High Memory Usage",
                        "description": f"Memory usage is at {memory_usage:.1f}%",
                        "action": "Check for memory leaks and consider increasing available memory",
                    }
                )

            # Service health recommendations
            service_health = current_metrics.get("service_health_scores", {})
            for service, score in service_health.items():
                if score < 70:
                    recommendations.append(
                        {
                            "priority": "high" if score < 50 else "medium",
                            "category": "service",
                            "title": f"Service Health Issue: {service}",
                            "description": f"Health score is {score:.1f}%",
                            "action": f"Investigate {service} service issues and check logs",
                        }
                    )

            # Alert recommendations
            active_alerts = len(self.alert_manager.get_active_alerts())
            if active_alerts > 5:
                recommendations.append(
                    {
                        "priority": "medium",
                        "category": "alerts",
                        "title": "Multiple Active Alerts",
                        "description": f"{active_alerts} alerts are currently active",
                        "action": "Review and acknowledge alerts to reduce noise",
                    }
                )

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            recommendations.append(
                {
                    "priority": "low",
                    "category": "system",
                    "title": "Monitoring System Issue",
                    "description": f"Error generating recommendations: {e}",
                    "action": "Check monitoring system logs",
                }
            )

        return recommendations

    async def export_dashboard_report(self, file_path: Optional[str] = None) -> str:
        """Export comprehensive dashboard report."""
        if file_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = str(self.data_dir / f"dashboard_report_{timestamp}.json")

        # Generate comprehensive report
        report = self.get_detailed_report()

        # Add export metadata
        report["export_info"] = {
            "exported_at": datetime.now().isoformat(),
            "export_type": "comprehensive_dashboard_report",
            "version": "2.0",
        }

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Dashboard report exported to {file_path}")
        return file_path

    def get_health_check(self) -> Dict[str, Any]:
        """Quick health check for external monitoring."""
        try:
            overview = self.get_dashboard_overview()
            status_info = overview.get("status", {})

            return {
                "status": status_info.get("overall", "unknown"),
                "health_score": status_info.get("health_score", 0),
                "timestamp": datetime.now().isoformat(),
                "services_healthy": len(
                    [
                        s
                        for s, state in overview.get("circuit_breakers", {})
                        .get("service_status", {})
                        .items()
                        if state != "open"
                    ]
                ),
                "active_alerts": overview.get("alerts", {}).get("active_alerts_count", 0),
                "uptime": "monitoring_active" if self._auto_refresh else "monitoring_inactive",
            }

        except Exception as e:
            return {"status": "error", "error": str(e), "timestamp": datetime.now().isoformat()}

    def generate_status_summary(self) -> str:
        """Generate human-readable status summary."""
        try:
            overview = self.get_dashboard_overview()
            status = overview.get("status", {})

            lines = []
            lines.append("=== Screen Translator Monitoring Summary ===")
            lines.append(f"Status: {status.get('overall', 'unknown').upper()}")
            lines.append(f"Health Score: {status.get('health_score', 0):.1f}%")
            lines.append(f"Last Updated: {status.get('last_updated', 'unknown')}")

            # Issues
            issues = status.get("issues", [])
            if issues:
                lines.append("\nCurrent Issues:")
                for issue in issues:
                    lines.append(f"  ⚠️  {issue}")
            else:
                lines.append("\n✅ No current issues detected")

            # Active alerts
            alerts = overview.get("alerts", {})
            alert_count = alerts.get("active_alerts_count", 0)
            if alert_count > 0:
                lines.append(f"\n🚨 Active Alerts: {alert_count}")
                by_severity = alerts.get("active_by_severity", {})
                for severity, count in by_severity.items():
                    if count > 0:
                        lines.append(f"  {severity.upper()}: {count}")

            # Service status
            cb_status = overview.get("circuit_breakers", {})
            healthy_services = cb_status.get("healthy_services", 0)
            total_services = cb_status.get("total_services", 0)
            lines.append(f"\n🔧 Services: {healthy_services}/{total_services} healthy")

            return "\n".join(lines)

        except Exception as e:
            return f"Error generating status summary: {e}"


# Singleton instance for global access
_monitoring_dashboard: Optional[MonitoringDashboard] = None


def get_monitoring_dashboard(data_dir: str = "data") -> MonitoringDashboard:
    """Get global monitoring dashboard instance."""
    global _monitoring_dashboard
    if _monitoring_dashboard is None:
        _monitoring_dashboard = MonitoringDashboard(data_dir)
    return _monitoring_dashboard

"""
Circuit Breaker monitoring and health check utilities.

This module provides monitoring capabilities for circuit breakers
and health status reporting.
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.services.circuit_breaker import CircuitState, get_circuit_breaker_manager
from src.utils.logger import logger


class CircuitBreakerMonitor:
    """Monitor for circuit breaker health and statistics."""

    def __init__(self):
        self.manager = get_circuit_breaker_manager()
        self._health_history: List[Dict[str, Any]] = []
        self._alert_callbacks: List[callable] = []

    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health based on circuit breakers."""
        metrics = self.manager.get_all_metrics()

        if not metrics:
            return {
                "status": "unknown",
                "healthy_services": 0,
                "total_services": 0,
                "issues": ["No circuit breakers registered"],
            }

        healthy_count = 0
        degraded_count = 0
        failed_count = 0
        issues = []

        for name, data in metrics.items():
            state = data["state"]
            if state == CircuitState.CLOSED.value:
                healthy_count += 1
            elif state == CircuitState.HALF_OPEN.value:
                degraded_count += 1
                issues.append(f"{name} is recovering (HALF_OPEN)")
            else:  # OPEN
                failed_count += 1
                issues.append(f"{name} is failing (OPEN)")

        total_services = len(metrics)

        # Determine overall status
        if failed_count > 0:
            status = "critical"
        elif degraded_count > 0:
            status = "degraded"
        else:
            status = "healthy"

        health_data = {
            "status": status,
            "healthy_services": healthy_count,
            "degraded_services": degraded_count,
            "failed_services": failed_count,
            "total_services": total_services,
            "issues": issues,
            "timestamp": datetime.now().isoformat(),
        }

        # Record in history
        self._health_history.append(health_data)

        # Keep only last 100 entries
        if len(self._health_history) > 100:
            self._health_history = self._health_history[-100:]

        # Check for alerts
        self._check_alerts(health_data)

        return health_data

    def get_service_details(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed information for each service."""
        metrics = self.manager.get_all_metrics()
        details = {}

        for name, data in metrics.items():
            state = data["state"]
            failure_count = data["failure_count"]
            last_failure_time = data["last_failure_time"]
            last_success_time = data["last_success_time"]

            # Calculate health score (0-100)
            health_score = self._calculate_health_score(data)

            # Determine status message
            if state == CircuitState.CLOSED.value:
                status_msg = "Healthy - All operations successful"
            elif state == CircuitState.HALF_OPEN.value:
                status_msg = f"Recovering - Testing service availability"
            else:  # OPEN
                time_since_failure = time.time() - last_failure_time if last_failure_time else 0
                status_msg = f"Failed - Circuit open for {int(time_since_failure)}s"

            details[name] = {
                "state": state,
                "health_score": health_score,
                "status_message": status_msg,
                "failure_count": failure_count,
                "success_count": data.get("success_count", 0),
                "last_failure": (
                    datetime.fromtimestamp(last_failure_time).isoformat()
                    if last_failure_time
                    else None
                ),
                "last_success": (
                    datetime.fromtimestamp(last_success_time).isoformat()
                    if last_success_time
                    else None
                ),
                "config": data["config"],
            }

        return details

    def _calculate_health_score(self, metrics: Dict[str, Any]) -> int:
        """Calculate health score (0-100) based on circuit breaker metrics."""
        state = metrics["state"]
        failure_count = metrics["failure_count"]
        failure_threshold = metrics["config"]["failure_threshold"]

        if state == CircuitState.CLOSED.value:
            # Health decreases with failure count
            failure_ratio = min(failure_count / failure_threshold, 1.0)
            return int(100 * (1 - failure_ratio * 0.5))  # Min 50% for closed circuit
        elif state == CircuitState.HALF_OPEN.value:
            return 30  # Moderate health while testing
        else:  # OPEN
            return 0  # Critical health for open circuit

    def get_health_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent health history."""
        return self._health_history[-limit:] if self._health_history else []

    def add_alert_callback(self, callback: callable) -> None:
        """Add callback for health alerts."""
        self._alert_callbacks.append(callback)

    def _check_alerts(self, health_data: Dict[str, Any]) -> None:
        """Check if alerts should be triggered."""
        status = health_data["status"]
        failed_services = health_data["failed_services"]
        degraded_services = health_data["degraded_services"]

        # Trigger alerts for critical issues
        if status == "critical" and failed_services > 0:
            alert_data = {
                "type": "service_failure",
                "severity": "critical",
                "message": f"{failed_services} service(s) have failed",
                "details": health_data["issues"],
                "timestamp": health_data["timestamp"],
            }
            self._trigger_alert(alert_data)

        # Trigger alerts for degraded services
        elif status == "degraded" and degraded_services > 0:
            alert_data = {
                "type": "service_degradation",
                "severity": "warning",
                "message": f"{degraded_services} service(s) are recovering",
                "details": health_data["issues"],
                "timestamp": health_data["timestamp"],
            }
            self._trigger_alert(alert_data)

    def _trigger_alert(self, alert_data: Dict[str, Any]) -> None:
        """Trigger alert callbacks."""
        logger.warning(f"Circuit breaker alert: {alert_data['message']}")

        for callback in self._alert_callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

    def generate_health_report(self) -> str:
        """Generate human-readable health report."""
        health = self.get_overall_health()
        details = self.get_service_details()

        report = []
        report.append("=== Circuit Breaker Health Report ===")
        report.append(f"Overall Status: {health['status'].upper()}")
        report.append(f"Timestamp: {health['timestamp']}")
        report.append(f"Services: {health['healthy_services']}/{health['total_services']} healthy")

        if health["issues"]:
            report.append("\nIssues:")
            for issue in health["issues"]:
                report.append(f"  ⚠️  {issue}")

        report.append("\nService Details:")
        for name, data in details.items():
            status_icon = (
                "✅" if data["state"] == "closed" else "⚠️" if data["state"] == "half_open" else "❌"
            )
            report.append(
                f"  {status_icon} {name} ({data['health_score']}%): {data['status_message']}"
            )

            if data["failure_count"] > 0:
                report.append(f"    Failures: {data['failure_count']}")
            if data["last_failure"]:
                report.append(f"    Last failure: {data['last_failure']}")

        return "\n".join(report)

    def reset_all_circuits(self) -> Dict[str, bool]:
        """Reset all circuit breakers (for emergency recovery)."""
        results = {}

        for name in self.manager._circuit_breakers:
            try:
                breaker = self.manager.get_circuit_breaker(name)
                if breaker:
                    breaker.reset()
                    results[name] = True
                    logger.info(f"Reset circuit breaker: {name}")
            except Exception as e:
                results[name] = False
                logger.error(f"Failed to reset circuit breaker {name}: {e}")

        return results


# Singleton instance for global access
_circuit_breaker_monitor: Optional[CircuitBreakerMonitor] = None


def get_circuit_breaker_monitor() -> CircuitBreakerMonitor:
    """Get global circuit breaker monitor instance."""
    global _circuit_breaker_monitor
    if _circuit_breaker_monitor is None:
        _circuit_breaker_monitor = CircuitBreakerMonitor()
    return _circuit_breaker_monitor

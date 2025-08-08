"""
Comprehensive alert system for application monitoring.

This module provides alert management, notification delivery,
and escalation policies for critical system events.
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.utils.logger import logger


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertCategory(Enum):
    """Alert categories."""

    PERFORMANCE = "performance"
    RESOURCE = "resource"
    SERVICE = "service"
    SECURITY = "security"
    DATA = "data"
    SYSTEM = "system"


class AlertStatus(Enum):
    """Alert status states."""

    ACTIVE = "active"  # Alert is currently firing
    ACKNOWLEDGED = "acknowledged"  # Alert acknowledged by user
    RESOLVED = "resolved"  # Alert condition resolved
    SUPPRESSED = "suppressed"  # Alert temporarily suppressed


@dataclass
class Alert:
    """Individual alert instance."""

    id: str
    title: str
    description: str
    severity: AlertSeverity
    category: AlertCategory
    source: str
    timestamp: datetime
    status: AlertStatus = AlertStatus.ACTIVE

    # Alert details
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None

    # Metadata
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Status tracking
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None

    # Related alerts
    related_alerts: List[str] = field(default_factory=list)


@dataclass
class AlertRule:
    """Alert rule configuration."""

    name: str
    description: str
    severity: AlertSeverity
    category: AlertCategory

    # Condition
    metric_name: str
    condition: str  # "gt", "lt", "eq", "ne"
    threshold: float
    duration_seconds: int = 0  # How long condition must persist

    # Notification settings
    enabled: bool = True
    notification_channels: List[str] = field(default_factory=list)

    # Rate limiting
    cooldown_seconds: int = 300  # 5 minutes default
    max_alerts_per_hour: int = 10

    # Labels and metadata
    labels: Dict[str, str] = field(default_factory=dict)


class NotificationChannel(ABC):
    """Abstract notification channel."""

    @abstractmethod
    async def send_notification(self, alert: Alert) -> bool:
        """Send alert notification. Returns True if successful."""

    @abstractmethod
    def get_channel_info(self) -> Dict[str, Any]:
        """Get channel configuration info."""


class LogNotificationChannel(NotificationChannel):
    """Log-based notification channel."""

    def __init__(self, log_level: str = "ERROR"):
        self.log_level = log_level.upper()

    async def send_notification(self, alert: Alert) -> bool:
        """Send notification via logging."""
        try:
            message = (
                f"ALERT [{alert.severity.value.upper()}] {alert.title}: " f"{alert.description}"
            )

            if self.log_level == "ERROR":
                logger.error(message)
            elif self.log_level == "WARNING":
                logger.warning(message)
            else:
                logger.info(message)

            return True
        except Exception as e:
            logger.error(f"Failed to send log notification: {e}")
            return False

    def get_channel_info(self) -> Dict[str, Any]:
        return {"type": "log", "log_level": self.log_level}


class FileNotificationChannel(NotificationChannel):
    """File-based notification channel."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    async def send_notification(self, alert: Alert) -> bool:
        """Send notification to file."""
        try:
            alert_data = {
                "timestamp": alert.timestamp.isoformat(),
                "severity": alert.severity.value,
                "title": alert.title,
                "description": alert.description,
                "source": alert.source,
                "labels": alert.labels,
                "metadata": alert.metadata,
            }

            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(alert_data) + "\n")

            return True
        except Exception as e:
            logger.error(f"Failed to send file notification: {e}")
            return False

    def get_channel_info(self) -> Dict[str, Any]:
        return {"type": "file", "file_path": str(self.file_path)}


class CallbackNotificationChannel(NotificationChannel):
    """Callback-based notification channel."""

    def __init__(self, callback: Callable[[Alert], bool], name: str = "callback"):
        self.callback = callback
        self.name = name

    async def send_notification(self, alert: Alert) -> bool:
        """Send notification via callback."""
        try:
            result = self.callback(alert)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to send callback notification: {e}")
            return False

    def get_channel_info(self) -> Dict[str, Any]:
        return {"type": "callback", "name": self.name}


class AlertManager:
    """Central alert management system."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.alerts_file = self.data_dir / "alerts.json"

        # Alert storage
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque[Alert] = deque(maxlen=1000)
        self.alert_rules: Dict[str, AlertRule] = {}

        # Notification channels
        self.notification_channels: Dict[str, NotificationChannel] = {}

        # Rate limiting
        self.alert_counts: defaultdict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.last_alert_time: Dict[str, datetime] = {}

        # Processing state
        self._processing = False
        self._processing_task: Optional[asyncio.Task] = None

        # Statistics
        self.stats = {
            "total_alerts": 0,
            "alerts_by_severity": defaultdict(int),
            "alerts_by_category": defaultdict(int),
            "notifications_sent": 0,
            "notifications_failed": 0,
        }

        # Setup default channels
        self._setup_default_channels()

        # Setup default rules
        self._setup_default_rules()

        logger.info("Alert manager initialized")

    def _setup_default_channels(self) -> None:
        """Setup default notification channels."""
        # Log channel for all alerts
        self.add_notification_channel("log", LogNotificationChannel())

        # File channel for critical alerts
        alerts_file = self.data_dir / "critical_alerts.jsonl"
        self.add_notification_channel("file", FileNotificationChannel(str(alerts_file)))

    def _setup_default_rules(self) -> None:
        """Setup default alert rules."""
        rules = [
            AlertRule(
                name="high_cpu_usage",
                description="CPU usage is critically high",
                severity=AlertSeverity.CRITICAL,
                category=AlertCategory.RESOURCE,
                metric_name="cpu_usage_percent",
                condition="gt",
                threshold=90.0,
                duration_seconds=60,
                notification_channels=["log", "file"],
            ),
            AlertRule(
                name="high_memory_usage",
                description="Memory usage is critically high",
                severity=AlertSeverity.CRITICAL,
                category=AlertCategory.RESOURCE,
                metric_name="memory_usage_percent",
                condition="gt",
                threshold=95.0,
                duration_seconds=30,
                notification_channels=["log", "file"],
            ),
            AlertRule(
                name="service_circuit_open",
                description="Service circuit breaker is open",
                severity=AlertSeverity.WARNING,
                category=AlertCategory.SERVICE,
                metric_name="service_health_score",
                condition="lt",
                threshold=10.0,
                duration_seconds=0,
                notification_channels=["log"],
            ),
            AlertRule(
                name="translation_slow",
                description="Translation response time is slow",
                severity=AlertSeverity.WARNING,
                category=AlertCategory.PERFORMANCE,
                metric_name="translation_time",
                condition="gt",
                threshold=10.0,
                duration_seconds=0,
                notification_channels=["log"],
            ),
            AlertRule(
                name="low_health_score",
                description="Overall application health is low",
                severity=AlertSeverity.WARNING,
                category=AlertCategory.SYSTEM,
                metric_name="overall_health_score",
                condition="lt",
                threshold=50.0,
                duration_seconds=60,
                notification_channels=["log", "file"],
            ),
        ]

        for rule in rules:
            self.add_alert_rule(rule)

    def add_notification_channel(self, name: str, channel: NotificationChannel) -> None:
        """Add a notification channel."""
        self.notification_channels[name] = channel
        logger.info(f"Added notification channel: {name}")

    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self.alert_rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")

    async def check_metric_alerts(
        self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> List[Alert]:
        """Check if metric value triggers any alerts."""
        triggered_alerts = []

        for rule_name, rule in self.alert_rules.items():
            if not rule.enabled or rule.metric_name != metric_name:
                continue

            # Check condition
            if not self._evaluate_condition(value, rule.condition, rule.threshold):
                continue

            # Check rate limiting
            if not self._check_rate_limit(rule):
                continue

            # Create alert
            alert_id = f"{rule_name}_{int(time.time())}"
            alert = Alert(
                id=alert_id,
                title=f"{rule.name.replace('_', ' ').title()}",
                description=rule.description,
                severity=rule.severity,
                category=rule.category,
                source="metric_monitor",
                timestamp=datetime.now(),
                metric_name=metric_name,
                metric_value=value,
                threshold=rule.threshold,
                labels=dict(rule.labels, **(labels or {})),
            )

            triggered_alerts.append(alert)
            await self.fire_alert(alert, rule.notification_channels)

        return triggered_alerts

    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Evaluate alert condition."""
        if condition == "gt":
            return value > threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "eq":
            return abs(value - threshold) < 0.001
        elif condition == "ne":
            return abs(value - threshold) >= 0.001
        else:
            logger.warning(f"Unknown condition: {condition}")
            return False

    def _check_rate_limit(self, rule: AlertRule) -> bool:
        """Check if alert rule is rate limited."""
        now = datetime.now()
        rule_key = rule.name

        # Check cooldown
        if rule_key in self.last_alert_time:
            time_since_last = (now - self.last_alert_time[rule_key]).total_seconds()
            if time_since_last < rule.cooldown_seconds:
                return False

        # Check hourly limit
        hour_ago = now - timedelta(hours=1)
        recent_alerts = [t for t in self.alert_counts[rule_key] if t > hour_ago]

        if len(recent_alerts) >= rule.max_alerts_per_hour:
            return False

        return True

    async def fire_alert(self, alert: Alert, channels: Optional[List[str]] = None) -> None:
        """Fire an alert and send notifications."""
        # Store alert
        self.active_alerts[alert.id] = alert
        self.alert_history.append(alert)

        # Update statistics
        self.stats["total_alerts"] += 1
        self.stats["alerts_by_severity"][alert.severity.value] += 1
        self.stats["alerts_by_category"][alert.category.value] += 1

        # Update rate limiting
        rule_key = f"{alert.metric_name}_{alert.source}"
        self.alert_counts[rule_key].append(alert.timestamp)
        self.last_alert_time[rule_key] = alert.timestamp

        # Send notifications
        channels = channels or ["log"]
        for channel_name in channels:
            if channel_name in self.notification_channels:
                try:
                    success = await self.notification_channels[channel_name].send_notification(
                        alert
                    )
                    if success:
                        self.stats["notifications_sent"] += 1
                    else:
                        self.stats["notifications_failed"] += 1
                except Exception as e:
                    logger.error(f"Failed to send notification via {channel_name}: {e}")
                    self.stats["notifications_failed"] += 1

        logger.warning(f"Alert fired: {alert.title} [{alert.severity.value}]")

    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system") -> bool:
        """Acknowledge an active alert."""
        if alert_id not in self.active_alerts:
            return False

        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now()
        alert.acknowledged_by = acknowledged_by

        logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
        return True

    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an active alert."""
        if alert_id not in self.active_alerts:
            return False

        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now()

        # Remove from active alerts
        del self.active_alerts[alert_id]

        logger.info(f"Alert resolved: {alert_id}")
        return True

    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get list of active alerts, optionally filtered by severity."""
        alerts = list(self.active_alerts.values())

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        # Sort by severity and timestamp
        severity_order = {
            AlertSeverity.EMERGENCY: 0,
            AlertSeverity.CRITICAL: 1,
            AlertSeverity.WARNING: 2,
            AlertSeverity.INFO: 3,
        }

        alerts.sort(key=lambda a: (severity_order[a.severity], a.timestamp), reverse=True)
        return alerts

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alert system status."""
        active_by_severity = defaultdict(int)
        for alert in self.active_alerts.values():
            active_by_severity[alert.severity.value] += 1

        return {
            "timestamp": datetime.now().isoformat(),
            "active_alerts_count": len(self.active_alerts),
            "active_by_severity": dict(active_by_severity),
            "total_rules": len(self.alert_rules),
            "enabled_rules": len([r for r in self.alert_rules.values() if r.enabled]),
            "notification_channels": len(self.notification_channels),
            "statistics": dict(self.stats),
        }

    async def export_alerts(self, file_path: Optional[str] = None) -> str:
        """Export alert data to JSON file."""
        if file_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = str(self.data_dir / f"alerts_export_{timestamp}.json")

        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "active_alerts": [asdict(alert) for alert in self.active_alerts.values()],
            "recent_history": [asdict(alert) for alert in list(self.alert_history)[-100:]],
            "alert_rules": [asdict(rule) for rule in self.alert_rules.values()],
            "statistics": dict(self.stats),
            "summary": self.get_alert_summary(),
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info(f"Alerts exported to {file_path}")
        return file_path


# Singleton instance for global access
_alert_manager: Optional[AlertManager] = None


def get_alert_manager(data_dir: str = "data") -> AlertManager:
    """Get global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager(data_dir)
    return _alert_manager

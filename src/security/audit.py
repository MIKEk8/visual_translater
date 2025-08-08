"""
Security audit logging for monitoring and compliance.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.logger import logger


class SecurityEventType(Enum):
    """Types of security events."""

    # Authentication events
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILURE = "auth.login.failure"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_CREATED = "auth.token.created"  # nosec B105 - This is an event type, not a password
    AUTH_TOKEN_EXPIRED = "auth.token.expired"  # nosec B105 - This is an event type, not a password

    # Data access events
    DATA_READ = "data.read"
    DATA_WRITE = "data.write"
    DATA_DELETE = "data.delete"
    DATA_EXPORT = "data.export"
    DATA_IMPORT = "data.import"

    # Configuration events
    CONFIG_CHANGE = "config.change"
    CONFIG_RESET = "config.reset"

    # API events
    API_KEY_CREATED = "api.key.created"
    API_KEY_USED = "api.key.used"
    API_KEY_REVOKED = "api.key.revoked"
    API_RATE_LIMIT_EXCEEDED = "api.rate_limit.exceeded"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"

    # Security events
    SECURITY_SCAN = "security.scan"
    SECURITY_VIOLATION = "security.violation"
    ENCRYPTION_KEY_GENERATED = "encryption.key.generated"
    ENCRYPTION_KEY_LOADED = "encryption.key.loaded"

    # Privacy events
    PRIVACY_DATA_COLLECTED = "privacy.data.collected"
    PRIVACY_DATA_ANONYMIZED = "privacy.data.anonymized"
    PRIVACY_CONSENT_GIVEN = "privacy.consent.given"
    PRIVACY_CONSENT_REVOKED = "privacy.consent.revoked"


class SecurityLevel(Enum):
    """Security event severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class SecurityEvent:
    """Security audit event."""

    event_type: SecurityEventType
    timestamp: datetime = field(default_factory=datetime.now)
    level: SecurityLevel = SecurityLevel.INFO
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Event details
    description: str = ""
    resource: Optional[str] = None
    action: Optional[str] = None
    result: str = "success"  # "success", "failure", "blocked"

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # System context
    process_id: Optional[int] = None
    thread_id: Optional[int] = None
    component: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "description": self.description,
            "resource": self.resource,
            "action": self.action,
            "result": self.result,
            "metadata": self.metadata,
            "process_id": self.process_id,
            "thread_id": self.thread_id,
            "component": self.component,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SecurityEvent":
        """Create event from dictionary."""
        return cls(
            event_type=SecurityEventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            level=SecurityLevel(data["level"]),
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            description=data.get("description", ""),
            resource=data.get("resource"),
            action=data.get("action"),
            result=data.get("result", "success"),
            metadata=data.get("metadata", {}),
            process_id=data.get("process_id"),
            thread_id=data.get("thread_id"),
            component=data.get("component"),
        )


class AuditLogger:
    """Security audit logging system."""

    def __init__(self, log_dir: str = "data/audit", max_file_size: int = 10 * 1024 * 1024):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = max_file_size

        # Current log file
        self.current_log_file = self._get_current_log_file()

        # Event counters
        self.event_counts = {level: 0 for level in SecurityLevel}
        self.total_events = 0

        # High-severity events buffer
        self.critical_events: List[SecurityEvent] = []
        self.max_critical_events = 1000

        logger.info(f"Security audit logger initialized: {self.log_dir}")

        # Log audit system startup
        self.log_event(
            SecurityEvent(
                event_type=SecurityEventType.SYSTEM_STARTUP,
                description="Security audit logging started",
                component="audit_logger",
            )
        )

    def _get_current_log_file(self) -> Path:
        """Get current log file path."""
        timestamp = datetime.now().strftime("%Y%m%d")
        return self.log_dir / f"security_audit_{timestamp}.jsonl"

    def _rotate_log_file_if_needed(self) -> None:
        """Rotate log file if it's too large."""
        if (
            self.current_log_file.exists()
            and self.current_log_file.stat().st_size > self.max_file_size
        ):
            # Rename current file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_file = self.log_dir / f"security_audit_{timestamp}_rotated.jsonl"
            self.current_log_file.rename(rotated_file)

            # Create new log file
            self.current_log_file = self._get_current_log_file()
            logger.info(f"Security audit log rotated: {rotated_file}")

    def log_event(self, event: SecurityEvent) -> None:
        """Log security audit event."""
        try:
            # Rotate log file if needed
            self._rotate_log_file_if_needed()

            # Add system context
            import os
            import threading

            event.process_id = os.getpid()
            event.thread_id = threading.get_ident()

            # Write event to log file
            with open(self.current_log_file, "a", encoding="utf-8") as f:
                json.dump(event.to_dict(), f, ensure_ascii=False)
                f.write("\n")

            # Update counters
            self.event_counts[event.level] += 1
            self.total_events += 1

            # Store critical events in memory
            if event.level in [SecurityLevel.CRITICAL, SecurityLevel.EMERGENCY]:
                self.critical_events.append(event)
                if len(self.critical_events) > self.max_critical_events:
                    self.critical_events = self.critical_events[-self.max_critical_events :]

            # Log to main logger based on severity
            if event.level == SecurityLevel.EMERGENCY:
                logger.critical(f"SECURITY EMERGENCY: {event.description}")
            elif event.level == SecurityLevel.CRITICAL:
                logger.error(f"SECURITY CRITICAL: {event.description}")
            elif event.level == SecurityLevel.WARNING:
                logger.warning(f"SECURITY WARNING: {event.description}")
            else:
                logger.debug(f"SECURITY INFO: {event.description}")

        except Exception as e:
            logger.error(f"Failed to log security event: {e}")

    def log_authentication(
        self, success: bool, user_id: Optional[str] = None, ip_address: Optional[str] = None
    ) -> None:
        """Log authentication event."""
        event = SecurityEvent(
            event_type=(
                SecurityEventType.AUTH_LOGIN_SUCCESS
                if success
                else SecurityEventType.AUTH_LOGIN_FAILURE
            ),
            level=SecurityLevel.INFO if success else SecurityLevel.WARNING,
            user_id=user_id,
            ip_address=ip_address,
            description=f"Authentication {'successful' if success else 'failed'}",
            result="success" if success else "failure",
            component="authentication",
        )
        self.log_event(event)

    def log_data_access(
        self, action: str, resource: str, user_id: Optional[str] = None, success: bool = True
    ) -> None:
        """Log data access event."""
        event = SecurityEvent(
            event_type=(
                SecurityEventType.DATA_READ if action == "read" else SecurityEventType.DATA_WRITE
            ),
            level=SecurityLevel.INFO,
            user_id=user_id,
            description=f"Data {action} on {resource}",
            resource=resource,
            action=action,
            result="success" if success else "failure",
            component="data_access",
        )
        self.log_event(event)

    def log_config_change(
        self,
        config_key: str,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """Log configuration change."""
        event = SecurityEvent(
            event_type=SecurityEventType.CONFIG_CHANGE,
            level=SecurityLevel.WARNING,
            user_id=user_id,
            description=f"Configuration changed: {config_key}",
            resource=config_key,
            action="change",
            metadata={
                "old_value": str(old_value) if old_value is not None else None,
                "new_value": str(new_value) if new_value is not None else None,
            },
            component="configuration",
        )
        self.log_event(event)

    def log_api_access(
        self, api_key_id: str, endpoint: str, success: bool = True, ip_address: Optional[str] = None
    ) -> None:
        """Log API access event."""
        event = SecurityEvent(
            event_type=SecurityEventType.API_KEY_USED,
            level=SecurityLevel.INFO,
            ip_address=ip_address,
            description=f"API access to {endpoint}",
            resource=endpoint,
            action="api_call",
            result="success" if success else "failure",
            metadata={"api_key_id": api_key_id},
            component="api",
        )
        self.log_event(event)

    def log_rate_limit_exceeded(
        self, identifier: str, limit: int, ip_address: Optional[str] = None
    ) -> None:
        """Log rate limit exceeded event."""
        event = SecurityEvent(
            event_type=SecurityEventType.API_RATE_LIMIT_EXCEEDED,
            level=SecurityLevel.WARNING,
            ip_address=ip_address,
            description=f"Rate limit exceeded for {identifier}",
            resource=identifier,
            action="rate_limit_check",
            result="blocked",
            metadata={"limit": limit},
            component="rate_limiter",
        )
        self.log_event(event)

    def log_security_violation(
        self,
        violation_type: str,
        description: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Log security violation."""
        event = SecurityEvent(
            event_type=SecurityEventType.SECURITY_VIOLATION,
            level=SecurityLevel.CRITICAL,
            user_id=user_id,
            ip_address=ip_address,
            description=f"Security violation: {description}",
            action=violation_type,
            result="blocked",
            component="security",
        )
        self.log_event(event)

    def get_recent_events(
        self, limit: int = 100, level: Optional[SecurityLevel] = None
    ) -> List[SecurityEvent]:
        """Get recent audit events."""
        try:
            events = []

            if self.current_log_file.exists():
                with open(self.current_log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for line in reversed(lines[-limit:]):
                    try:
                        event_data = json.loads(line.strip())
                        event = SecurityEvent.from_dict(event_data)

                        if level is None or event.level == level:
                            events.append(event)

                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

            return events[:limit]

        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            return []

    def get_critical_events(self) -> List[SecurityEvent]:
        """Get recent critical events."""
        return self.critical_events.copy()

    def get_audit_summary(self) -> Dict[str, Any]:
        """Get audit logging summary."""
        return {
            "total_events": self.total_events,
            "event_counts_by_level": {
                level.value: count for level, count in self.event_counts.items()
            },
            "current_log_file": str(self.current_log_file),
            "log_directory": str(self.log_dir),
            "critical_events_count": len(self.critical_events),
            "max_file_size": self.max_file_size,
        }

    def export_audit_log(
        self,
        output_file: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> bool:
        """Export audit log to file."""
        try:
            events = []

            # Read all log files in directory
            for log_file in self.log_dir.glob("security_audit_*.jsonl"):
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            event_data = json.loads(line.strip())
                            event_timestamp = datetime.fromisoformat(event_data["timestamp"])

                            # Filter by date range
                            if date_from and event_timestamp < date_from:
                                continue
                            if date_to and event_timestamp > date_to:
                                continue

                            events.append(event_data)

                        except (json.JSONDecodeError, KeyError, ValueError):
                            continue

            # Export events
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "export_timestamp": datetime.now().isoformat(),
                        "date_range": {
                            "from": date_from.isoformat() if date_from else None,
                            "to": date_to.isoformat() if date_to else None,
                        },
                        "total_events": len(events),
                        "events": events,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            logger.info(f"Audit log exported: {output_file} ({len(events)} events)")
            return True

        except Exception as e:
            logger.error(f"Failed to export audit log: {e}")
            return False


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance."""
    global _audit_logger

    if _audit_logger is None:
        _audit_logger = AuditLogger()

    return _audit_logger

"""
Application state definition and state snapshots.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from src.models.config import AppConfig
from src.models.translation import Translation


class CaptureMode(Enum):
    """Screen capture modes."""

    AREA_SELECT = "area_select"
    CENTER_AREA = "center_area"
    BOTTOM_AREA = "bottom_area"
    FULL_SCREEN = "full_screen"


class AppStatus(Enum):
    """Application status states."""

    INITIALIZING = "initializing"
    READY = "ready"
    CAPTURING = "capturing"
    PROCESSING = "processing"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


@dataclass
class UIState:
    """User interface state."""

    settings_window_open: bool = False
    history_window_open: bool = False
    overlay_visible: bool = False
    progress_visible: bool = False
    progress_message: str = ""
    progress_value: float = 0.0
    toast_message: str = ""
    toast_visible: bool = False
    toast_type: str = "info"  # "info", "success", "warning", "error"


@dataclass
class ProcessingState:
    """Current processing operation state."""

    is_processing: bool = False
    operation_type: str = ""  # "ocr", "translation", "tts", "batch"
    current_step: str = ""
    progress_percentage: float = 0.0
    start_time: Optional[float] = None
    estimated_completion: Optional[float] = None


@dataclass
class PerformanceMetrics:
    """Performance metrics state."""

    avg_ocr_time_ms: float = 0.0
    avg_translation_time_ms: float = 0.0
    avg_total_time_ms: float = 0.0
    success_rate: float = 1.0
    total_operations: int = 0
    failed_operations: int = 0
    cache_hit_rate: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0


@dataclass
class ServiceHealth:
    """External service health state."""

    ocr_service_healthy: bool = True
    translation_service_healthy: bool = True
    tts_service_healthy: bool = True
    circuit_breaker_states: Dict[str, str] = field(default_factory=dict)
    last_health_check: Optional[datetime] = None


@dataclass
class AppState:
    """Complete application state."""

    # Core state
    status: AppStatus = AppStatus.INITIALIZING
    version: str = "2.0.0"
    last_updated: datetime = field(default_factory=datetime.now)

    # Configuration
    config: Optional[AppConfig] = None

    # Language and translation
    current_target_language: str = "en"
    available_languages: List[str] = field(default_factory=list)
    last_translation: Optional[Translation] = None
    translation_history: List[Translation] = field(default_factory=list)

    # Screen capture
    capture_mode: CaptureMode = CaptureMode.AREA_SELECT
    last_capture_area: Optional[tuple] = None
    screenshot_history: List[dict] = field(default_factory=list)

    # UI state
    ui: UIState = field(default_factory=UIState)

    # Processing state
    processing: ProcessingState = field(default_factory=ProcessingState)

    # Performance metrics
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)

    # Service health
    service_health: ServiceHealth = field(default_factory=ServiceHealth)

    # Cache and temporary data
    ocr_cache: Dict[str, Any] = field(default_factory=dict)
    translation_cache: Dict[str, Any] = field(default_factory=dict)

    # Feature flags
    features: Dict[str, bool] = field(
        default_factory=lambda: {
            "real_time_overlay": False,
            "smart_area_detection": False,
            "batch_processing": True,
            "voice_commands": False,
            "cloud_sync": False,
        }
    )

    # User preferences
    preferences: Dict[str, Any] = field(
        default_factory=lambda: {
            "auto_copy_to_clipboard": True,
            "show_confidence_scores": False,
            "dark_mode": False,
            "minimize_to_tray": True,
            "auto_language_detection": True,
        }
    )

    def copy(self) -> "AppState":
        """Create a deep copy of the state."""
        import copy

        return copy.deepcopy(self)

    def get_translation_count(self) -> int:
        """Get total translation count."""
        return len(self.translation_history)

    def get_success_rate(self) -> float:
        """Get overall success rate."""
        return self.performance.success_rate

    def is_healthy(self) -> bool:
        """Check if all services are healthy."""
        return (
            self.service_health.ocr_service_healthy
            and self.service_health.translation_service_healthy
            and self.service_health.tts_service_healthy
        )

    def get_active_capture_coordinates(self) -> Optional[tuple]:
        """Get coordinates for current capture mode."""
        if self.capture_mode == CaptureMode.AREA_SELECT:
            return self.last_capture_area
        return None


@dataclass
class StateSnapshot:
    """Immutable snapshot of application state at a point in time."""

    timestamp: float = field(default_factory=time.time)
    state: AppState = field(default_factory=AppState)
    action_id: Optional[str] = None
    action_type: Optional[str] = None

    @classmethod
    def create(
        cls, state: AppState, action_id: Optional[str] = None, action_type: Optional[str] = None
    ) -> "StateSnapshot":
        """Create a new state snapshot."""
        return cls(
            timestamp=time.time(), state=state.copy(), action_id=action_id, action_type=action_type
        )

    def get_age_seconds(self) -> float:
        """Get age of snapshot in seconds."""
        return time.time() - self.timestamp

    def is_expired(self, max_age_seconds: float) -> bool:
        """Check if snapshot has expired."""
        return self.get_age_seconds() > max_age_seconds

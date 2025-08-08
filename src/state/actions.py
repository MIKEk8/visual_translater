"""
State actions for Redux-like state management.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from src.models.translation import Translation
from src.state.app_state import AppStatus, CaptureMode


class ActionType(Enum):
    """Available action types."""

    # Application lifecycle
    APP_INITIALIZE = "app/initialize"
    APP_READY = "app/ready"
    APP_SHUTDOWN = "app/shutdown"
    APP_ERROR = "app/error"

    # Configuration
    CONFIG_LOAD = "config/load"
    CONFIG_UPDATE = "config/update"
    CONFIG_RESET = "config/reset"

    # Language and translation
    LANGUAGE_CHANGE = "language/change"
    LANGUAGE_LIST_UPDATE = "language/list_update"
    TRANSLATION_START = "translation/start"
    TRANSLATION_SUCCESS = "translation/success"
    TRANSLATION_FAILURE = "translation/failure"
    TRANSLATION_HISTORY_ADD = "translation/history_add"
    TRANSLATION_HISTORY_CLEAR = "translation/history_clear"

    # Screen capture
    CAPTURE_MODE_CHANGE = "capture/mode_change"
    CAPTURE_START = "capture/start"
    CAPTURE_SUCCESS = "capture/success"
    CAPTURE_FAILURE = "capture/failure"
    CAPTURE_AREA_SET = "capture/area_set"

    # UI state
    UI_SETTINGS_OPEN = "ui/settings_open"
    UI_SETTINGS_CLOSE = "ui/settings_close"
    UI_HISTORY_OPEN = "ui/history_open"
    UI_HISTORY_CLOSE = "ui/history_close"
    UI_OVERLAY_SHOW = "ui/overlay_show"
    UI_OVERLAY_HIDE = "ui/overlay_hide"
    UI_PROGRESS_SHOW = "ui/progress_show"
    UI_PROGRESS_UPDATE = "ui/progress_update"
    UI_PROGRESS_HIDE = "ui/progress_hide"
    UI_TOAST_SHOW = "ui/toast_show"
    UI_TOAST_HIDE = "ui/toast_hide"

    # Processing state
    PROCESSING_START = "processing/start"
    PROCESSING_UPDATE = "processing/update"
    PROCESSING_COMPLETE = "processing/complete"
    PROCESSING_ERROR = "processing/error"

    # Performance metrics
    METRICS_UPDATE = "metrics/update"
    METRICS_RESET = "metrics/reset"

    # Service health
    SERVICE_HEALTH_UPDATE = "service/health_update"
    CIRCUIT_BREAKER_STATE_CHANGE = "service/circuit_breaker_change"

    # Cache operations
    CACHE_UPDATE = "cache/update"
    CACHE_CLEAR = "cache/clear"

    # Feature flags
    FEATURE_TOGGLE = "feature/toggle"
    FEATURE_UPDATE = "feature/update"

    # User preferences
    PREFERENCE_UPDATE = "preference/update"
    PREFERENCE_RESET = "preference/reset"


@dataclass
class Action(ABC):
    """Base class for all state actions."""

    type: ActionType
    timestamp: datetime = field(default_factory=datetime.now)
    action_id: str = field(default_factory=lambda: f"action_{int(time.time() * 1000)}")
    metadata: Dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    def get_payload(self) -> Dict[str, Any]:
        """Get action payload for state reduction."""
        pass


# Application lifecycle actions
@dataclass
class AppInitializeAction(Action):
    """Initialize application."""

    type: ActionType = ActionType.APP_INITIALIZE
    version: str = "2.0.0"

    def get_payload(self) -> Dict[str, Any]:
        return {"version": self.version}


@dataclass
class AppReadyAction(Action):
    """Application ready for use."""

    type: ActionType = ActionType.APP_READY

    def get_payload(self) -> Dict[str, Any]:
        return {}


@dataclass
class AppErrorAction(Action):
    """Application error occurred."""

    type: ActionType = ActionType.APP_ERROR
    error_message: str = ""
    error_type: str = "unknown"

    def get_payload(self) -> Dict[str, Any]:
        return {"error_message": self.error_message, "error_type": self.error_type}


# Language and translation actions
@dataclass
class LanguageChangeAction(Action):
    """Change target language."""

    type: ActionType = ActionType.LANGUAGE_CHANGE
    target_language: str = ""

    def get_payload(self) -> Dict[str, Any]:
        return {"target_language": self.target_language}


@dataclass
class TranslationStartedAction(Action):
    """Translation started."""

    type: ActionType = ActionType.TRANSLATION_START
    original_text: str = ""
    target_language: str = ""

    def get_payload(self) -> Dict[str, Any]:
        return {"original_text": self.original_text, "target_language": self.target_language}


@dataclass
class TranslationSuccessAction(Action):
    """Translation completed successfully."""

    type: ActionType = ActionType.TRANSLATION_SUCCESS
    translation: Optional[Translation] = None
    execution_time_ms: float = 0.0

    def get_payload(self) -> Dict[str, Any]:
        return {"translation": self.translation, "execution_time_ms": self.execution_time_ms}


@dataclass
class TranslationFailureAction(Action):
    """Translation failed."""

    type: ActionType = ActionType.TRANSLATION_FAILURE
    error_message: str = ""
    original_text: str = ""

    def get_payload(self) -> Dict[str, Any]:
        return {"error_message": self.error_message, "original_text": self.original_text}


# Screen capture actions
@dataclass
class CaptureModeChangeAction(Action):
    """Change capture mode."""

    type: ActionType = ActionType.CAPTURE_MODE_CHANGE
    capture_mode: CaptureMode = CaptureMode.AREA_SELECT

    def get_payload(self) -> Dict[str, Any]:
        return {"capture_mode": self.capture_mode}


@dataclass
class CaptureAreaSetAction(Action):
    """Set capture area coordinates."""

    type: ActionType = ActionType.CAPTURE_AREA_SET
    coordinates: Tuple[int, int, int, int] = (0, 0, 0, 0)

    def get_payload(self) -> Dict[str, Any]:
        return {"coordinates": self.coordinates}


# UI state actions
@dataclass
class UIProgressShowAction(Action):
    """Show progress indicator."""

    type: ActionType = ActionType.UI_PROGRESS_SHOW
    message: str = ""
    is_indeterminate: bool = True

    def get_payload(self) -> Dict[str, Any]:
        return {"message": self.message, "is_indeterminate": self.is_indeterminate}


@dataclass
class UIProgressUpdateAction(Action):
    """Update progress indicator."""

    type: ActionType = ActionType.UI_PROGRESS_UPDATE
    progress_value: float = 0.0
    message: str = ""

    def get_payload(self) -> Dict[str, Any]:
        return {"progress_value": self.progress_value, "message": self.message}


@dataclass
class UIToastShowAction(Action):
    """Show toast notification."""

    type: ActionType = ActionType.UI_TOAST_SHOW
    message: str = ""
    toast_type: str = "info"  # "info", "success", "warning", "error"
    duration_ms: int = 3000

    def get_payload(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "toast_type": self.toast_type,
            "duration_ms": self.duration_ms,
        }


# Processing state actions
@dataclass
class ProcessingStartAction(Action):
    """Start processing operation."""

    type: ActionType = ActionType.PROCESSING_START
    operation_type: str = ""
    estimated_duration_ms: Optional[float] = None

    def get_payload(self) -> Dict[str, Any]:
        return {
            "operation_type": self.operation_type,
            "estimated_duration_ms": self.estimated_duration_ms,
        }


@dataclass
class ProcessingUpdateAction(Action):
    """Update processing progress."""

    type: ActionType = ActionType.PROCESSING_UPDATE
    current_step: str = ""
    progress_percentage: float = 0.0

    def get_payload(self) -> Dict[str, Any]:
        return {"current_step": self.current_step, "progress_percentage": self.progress_percentage}


# Performance metrics actions
@dataclass
class MetricsUpdateAction(Action):
    """Update performance metrics."""

    type: ActionType = ActionType.METRICS_UPDATE
    ocr_time_ms: Optional[float] = None
    translation_time_ms: Optional[float] = None
    total_time_ms: Optional[float] = None
    success: bool = True
    cache_hit: bool = False

    def get_payload(self) -> Dict[str, Any]:
        return {
            "ocr_time_ms": self.ocr_time_ms,
            "translation_time_ms": self.translation_time_ms,
            "total_time_ms": self.total_time_ms,
            "success": self.success,
            "cache_hit": self.cache_hit,
        }


# Service health actions
@dataclass
class ServiceHealthUpdateAction(Action):
    """Update service health status."""

    type: ActionType = ActionType.SERVICE_HEALTH_UPDATE
    service_name: str = ""
    is_healthy: bool = True
    error_message: Optional[str] = None

    def get_payload(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "is_healthy": self.is_healthy,
            "error_message": self.error_message,
        }


# Feature flag actions
@dataclass
class FeatureToggleAction(Action):
    """Toggle feature flag."""

    type: ActionType = ActionType.FEATURE_TOGGLE
    feature_name: str = ""
    enabled: bool = False

    def get_payload(self) -> Dict[str, Any]:
        return {"feature_name": self.feature_name, "enabled": self.enabled}


# User preference actions
@dataclass
class PreferenceUpdateAction(Action):
    """Update user preference."""

    type: ActionType = ActionType.PREFERENCE_UPDATE
    preference_name: str = ""
    preference_value: Any = None

    def get_payload(self) -> Dict[str, Any]:
        return {"preference_name": self.preference_name, "preference_value": self.preference_value}


# Type alias for convenience
StateAction = Action

# Backwards compatibility aliases
TranslationCompletedAction = TranslationSuccessAction
TranslationFailedAction = TranslationFailureAction
SettingsUpdatedAction = PreferenceUpdateAction
UIStateChangeAction = UIProgressShowAction
ResetStateAction = AppInitializeAction

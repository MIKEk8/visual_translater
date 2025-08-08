"""
State reducers for Redux-like state management.
"""

import time
from datetime import datetime
from typing import Callable, Dict

from src.state.actions import Action, ActionType
from src.state.app_state import AppState, AppStatus, PerformanceMetrics, ProcessingState
from src.utils.logger import logger


class RootReducer:
    """Root reducer that combines all state reducers."""

    def __init__(self):
        self.reducers = {
            # Application lifecycle
            ActionType.APP_INITIALIZE: self._reduce_app_initialize,
            ActionType.APP_READY: self._reduce_app_ready,
            ActionType.APP_SHUTDOWN: self._reduce_app_shutdown,
            ActionType.APP_ERROR: self._reduce_app_error,
            # Language and translation
            ActionType.LANGUAGE_CHANGE: self._reduce_language_change,
            ActionType.TRANSLATION_SUCCESS: self._reduce_translation_success,
            ActionType.TRANSLATION_FAILURE: self._reduce_translation_failure,
            ActionType.TRANSLATION_HISTORY_ADD: self._reduce_translation_history_add,
            ActionType.TRANSLATION_HISTORY_CLEAR: self._reduce_translation_history_clear,
            # Screen capture
            ActionType.CAPTURE_MODE_CHANGE: self._reduce_capture_mode_change,
            ActionType.CAPTURE_AREA_SET: self._reduce_capture_area_set,
            # UI state
            ActionType.UI_SETTINGS_OPEN: self._reduce_ui_settings_open,
            ActionType.UI_SETTINGS_CLOSE: self._reduce_ui_settings_close,
            ActionType.UI_PROGRESS_SHOW: self._reduce_ui_progress_show,
            ActionType.UI_PROGRESS_UPDATE: self._reduce_ui_progress_update,
            ActionType.UI_PROGRESS_HIDE: self._reduce_ui_progress_hide,
            ActionType.UI_TOAST_SHOW: self._reduce_ui_toast_show,
            ActionType.UI_TOAST_HIDE: self._reduce_ui_toast_hide,
            # Processing state
            ActionType.PROCESSING_START: self._reduce_processing_start,
            ActionType.PROCESSING_UPDATE: self._reduce_processing_update,
            ActionType.PROCESSING_COMPLETE: self._reduce_processing_complete,
            ActionType.PROCESSING_ERROR: self._reduce_processing_error,
            # Performance metrics
            ActionType.METRICS_UPDATE: self._reduce_metrics_update,
            ActionType.METRICS_RESET: self._reduce_metrics_reset,
            # Service health
            ActionType.SERVICE_HEALTH_UPDATE: self._reduce_service_health_update,
            # Feature flags
            ActionType.FEATURE_TOGGLE: self._reduce_feature_toggle,
            # User preferences
            ActionType.PREFERENCE_UPDATE: self._reduce_preference_update,
        }

    def reduce(self, state: AppState, action: Action) -> AppState:
        """Reduce action to new state."""
        try:
            # Get reducer for action type
            reducer = self.reducers.get(action.type)
            if not reducer:
                logger.warning(f"No reducer found for action type: {action.type}")
                return state

            # Create new state
            new_state = state.copy()
            new_state.last_updated = datetime.now()

            # Apply reducer
            new_state = reducer(new_state, action)

            logger.debug(f"State reduced: {action.type}", action_id=action.action_id)
            return new_state

        except Exception as e:
            logger.error(f"Error reducing state: {e}", action_type=action.type, error=e)
            return state

    # Application lifecycle reducers
    def _reduce_app_initialize(self, state: AppState, action: Action) -> AppState:
        """Handle app initialization."""
        payload = action.get_payload()
        state.status = AppStatus.INITIALIZING
        state.version = payload.get("version", "2.0.0")
        return state

    def _reduce_app_ready(self, state: AppState, action: Action) -> AppState:
        """Handle app ready."""
        state.status = AppStatus.READY
        return state

    def _reduce_app_shutdown(self, state: AppState, action: Action) -> AppState:
        """Handle app shutdown."""
        state.status = AppStatus.SHUTTING_DOWN
        return state

    def _reduce_app_error(self, state: AppState, action: Action) -> AppState:
        """Handle app error."""
        payload = action.get_payload()
        state.status = AppStatus.ERROR
        # Could store error details in state if needed
        return state

    # Language and translation reducers
    def _reduce_language_change(self, state: AppState, action: Action) -> AppState:
        """Handle language change."""
        payload = action.get_payload()
        state.current_target_language = payload.get("target_language", "en")
        return state

    def _reduce_translation_success(self, state: AppState, action: Action) -> AppState:
        """Handle successful translation."""
        payload = action.get_payload()
        translation = payload.get("translation")

        if translation:
            state.last_translation = translation
            # Don't add to history here - use separate action for that

        return state

    def _reduce_translation_failure(self, state: AppState, action: Action) -> AppState:
        """Handle translation failure."""
        payload = action.get_payload()
        # Could store error info in state if needed
        return state

    def _reduce_translation_history_add(self, state: AppState, action: Action) -> AppState:
        """Add translation to history."""
        payload = action.get_payload()
        translation = payload.get("translation")

        if translation:
            state.translation_history.append(translation)

            # Limit history size
            max_history = 1000
            if len(state.translation_history) > max_history:
                state.translation_history = state.translation_history[-max_history:]

        return state

    def _reduce_translation_history_clear(self, state: AppState, action: Action) -> AppState:
        """Clear translation history."""
        state.translation_history = []
        return state

    # Screen capture reducers
    def _reduce_capture_mode_change(self, state: AppState, action: Action) -> AppState:
        """Handle capture mode change."""
        payload = action.get_payload()
        state.capture_mode = payload.get("capture_mode")
        return state

    def _reduce_capture_area_set(self, state: AppState, action: Action) -> AppState:
        """Handle capture area setting."""
        payload = action.get_payload()
        state.last_capture_area = payload.get("coordinates")
        return state

    # UI state reducers
    def _reduce_ui_settings_open(self, state: AppState, action: Action) -> AppState:
        """Handle settings window open."""
        state.ui.settings_window_open = True
        return state

    def _reduce_ui_settings_close(self, state: AppState, action: Action) -> AppState:
        """Handle settings window close."""
        state.ui.settings_window_open = False
        return state

    def _reduce_ui_progress_show(self, state: AppState, action: Action) -> AppState:
        """Handle progress show."""
        payload = action.get_payload()
        state.ui.progress_visible = True
        state.ui.progress_message = payload.get("message", "")
        state.ui.progress_value = 0.0
        return state

    def _reduce_ui_progress_update(self, state: AppState, action: Action) -> AppState:
        """Handle progress update."""
        payload = action.get_payload()
        state.ui.progress_value = payload.get("progress_value", 0.0)
        state.ui.progress_message = payload.get("message", state.ui.progress_message)
        return state

    def _reduce_ui_progress_hide(self, state: AppState, action: Action) -> AppState:
        """Handle progress hide."""
        state.ui.progress_visible = False
        state.ui.progress_message = ""
        state.ui.progress_value = 0.0
        return state

    def _reduce_ui_toast_show(self, state: AppState, action: Action) -> AppState:
        """Handle toast show."""
        payload = action.get_payload()
        state.ui.toast_visible = True
        state.ui.toast_message = payload.get("message", "")
        state.ui.toast_type = payload.get("toast_type", "info")
        return state

    def _reduce_ui_toast_hide(self, state: AppState, action: Action) -> AppState:
        """Handle toast hide."""
        state.ui.toast_visible = False
        state.ui.toast_message = ""
        return state

    # Processing state reducers
    def _reduce_processing_start(self, state: AppState, action: Action) -> AppState:
        """Handle processing start."""
        payload = action.get_payload()
        state.processing.is_processing = True
        state.processing.operation_type = payload.get("operation_type", "")
        state.processing.current_step = "Starting..."
        state.processing.progress_percentage = 0.0
        state.processing.start_time = time.time()

        estimated_duration = payload.get("estimated_duration_ms")
        if estimated_duration:
            state.processing.estimated_completion = time.time() + (estimated_duration / 1000)

        return state

    def _reduce_processing_update(self, state: AppState, action: Action) -> AppState:
        """Handle processing update."""
        payload = action.get_payload()
        state.processing.current_step = payload.get("current_step", "")
        state.processing.progress_percentage = payload.get("progress_percentage", 0.0)
        return state

    def _reduce_processing_complete(self, state: AppState, action: Action) -> AppState:
        """Handle processing complete."""
        state.processing.is_processing = False
        state.processing.operation_type = ""
        state.processing.current_step = ""
        state.processing.progress_percentage = 100.0
        state.processing.start_time = None
        state.processing.estimated_completion = None
        return state

    def _reduce_processing_error(self, state: AppState, action: Action) -> AppState:
        """Handle processing error."""
        state.processing.is_processing = False
        state.processing.operation_type = ""
        state.processing.current_step = "Error occurred"
        state.processing.start_time = None
        state.processing.estimated_completion = None
        return state

    # Performance metrics reducers
    def _reduce_metrics_update(self, state: AppState, action: Action) -> AppState:
        """Handle metrics update."""
        payload = action.get_payload()

        # Update running averages
        total_ops = state.performance.total_operations

        # OCR time
        ocr_time = payload.get("ocr_time_ms")
        if ocr_time is not None:
            current_avg = state.performance.avg_ocr_time_ms
            state.performance.avg_ocr_time_ms = (current_avg * total_ops + ocr_time) / (
                total_ops + 1
            )

        # Translation time
        translation_time = payload.get("translation_time_ms")
        if translation_time is not None:
            current_avg = state.performance.avg_translation_time_ms
            state.performance.avg_translation_time_ms = (
                current_avg * total_ops + translation_time
            ) / (total_ops + 1)

        # Total time
        total_time = payload.get("total_time_ms")
        if total_time is not None:
            current_avg = state.performance.avg_total_time_ms
            state.performance.avg_total_time_ms = (current_avg * total_ops + total_time) / (
                total_ops + 1
            )

        # Update counters
        state.performance.total_operations += 1

        if not payload.get("success", True):
            state.performance.failed_operations += 1

        # Update success rate
        state.performance.success_rate = (
            state.performance.total_operations - state.performance.failed_operations
        ) / state.performance.total_operations

        # Update cache hit rate if provided
        if payload.get("cache_hit", False):
            # Simplified cache hit rate calculation
            state.performance.cache_hit_rate = min(state.performance.cache_hit_rate + 0.01, 1.0)

        return state

    def _reduce_metrics_reset(self, state: AppState, action: Action) -> AppState:
        """Handle metrics reset."""
        state.performance = PerformanceMetrics()
        return state

    # Service health reducers
    def _reduce_service_health_update(self, state: AppState, action: Action) -> AppState:
        """Handle service health update."""
        payload = action.get_payload()
        service_name = payload.get("service_name", "")
        is_healthy = payload.get("is_healthy", True)

        if service_name == "ocr":
            state.service_health.ocr_service_healthy = is_healthy
        elif service_name == "translation":
            state.service_health.translation_service_healthy = is_healthy
        elif service_name == "tts":
            state.service_health.tts_service_healthy = is_healthy

        state.service_health.last_health_check = datetime.now()
        return state

    # Feature flag reducers
    def _reduce_feature_toggle(self, state: AppState, action: Action) -> AppState:
        """Handle feature toggle."""
        payload = action.get_payload()
        feature_name = payload.get("feature_name", "")
        enabled = payload.get("enabled", False)

        if feature_name:
            state.features[feature_name] = enabled

        return state

    # User preference reducers
    def _reduce_preference_update(self, state: AppState, action: Action) -> AppState:
        """Handle preference update."""
        payload = action.get_payload()
        preference_name = payload.get("preference_name", "")
        preference_value = payload.get("preference_value")

        if preference_name:
            state.preferences[preference_name] = preference_value

        return state


def create_root_reducer() -> RootReducer:
    """Create and return root reducer instance."""
    return RootReducer()

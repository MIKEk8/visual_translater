"""
Middleware for state store with logging, validation, and performance monitoring.
"""

import time
from abc import ABC, abstractmethod
from typing import Optional

from src.state.actions import Action
from src.state.app_state import AppState
from src.utils.logger import logger


class Middleware(ABC):
    """Abstract base class for state store middleware."""

    @abstractmethod
    def before_dispatch(self, action: Action, current_state: AppState) -> Optional[Action]:
        """
        Process action before dispatch.
        Return None to block the action, or modified action to continue.
        """
        pass

    @abstractmethod
    def after_dispatch(self, action: Action, old_state: AppState, new_state: AppState) -> None:
        """Process after state has been updated."""
        pass


class LoggingMiddleware(Middleware):
    """Middleware for logging state changes."""

    def __init__(self, log_level: str = "DEBUG"):
        self.log_level = log_level.upper()
        self.action_count = 0

    def before_dispatch(self, action: Action, current_state: AppState) -> Optional[Action]:
        """Log action before dispatch."""
        self.action_count += 1

        if self.log_level == "DEBUG":
            logger.debug(
                f"Dispatching action: {action.type.value}",
                action_id=action.action_id,
                action_count=self.action_count,
            )
        elif self.log_level == "INFO":
            logger.info(f"Action: {action.type.value}", action_id=action.action_id)

        return action

    def after_dispatch(self, action: Action, old_state: AppState, new_state: AppState) -> None:
        """Log state change after dispatch."""
        if self.log_level == "DEBUG":
            state_changed = old_state != new_state
            logger.debug(
                f"Action processed: {action.type.value}",
                action_id=action.action_id,
                state_changed=state_changed,
                new_status=new_state.status.value,
            )


class PerformanceMiddleware(Middleware):
    """Middleware for monitoring state performance."""

    def __init__(self):
        self.action_times = {}
        self.slow_actions = []
        self.slow_threshold_ms = 100.0  # Consider actions > 100ms as slow

    def before_dispatch(self, action: Action, current_state: AppState) -> Optional[Action]:
        """Record action start time."""
        self.action_times[action.action_id] = time.time()
        return action

    def after_dispatch(self, action: Action, old_state: AppState, new_state: AppState) -> None:
        """Calculate and log action execution time."""
        start_time = self.action_times.pop(action.action_id, None)
        if start_time is None:
            return

        execution_time_ms = (time.time() - start_time) * 1000

        # Log slow actions
        if execution_time_ms > self.slow_threshold_ms:
            self.slow_actions.append(
                {
                    "action_type": action.type.value,
                    "action_id": action.action_id,
                    "execution_time_ms": execution_time_ms,
                    "timestamp": time.time(),
                }
            )

            # Keep only last 50 slow actions
            if len(self.slow_actions) > 50:
                self.slow_actions = self.slow_actions[-50:]

            logger.warning(
                f"Slow state action: {action.type.value}",
                action_id=action.action_id,
                execution_time_ms=execution_time_ms,
            )

        # Log performance metrics
        logger.debug(
            f"Action performance: {action.type.value}",
            action_id=action.action_id,
            execution_time_ms=execution_time_ms,
        )

    def get_slow_actions(self) -> list:
        """Get list of slow actions."""
        return self.slow_actions.copy()

    def get_performance_summary(self) -> dict:
        """Get performance summary."""
        if not self.slow_actions:
            return {"slow_actions_count": 0}

        total_slow_time = sum(action["execution_time_ms"] for action in self.slow_actions)
        avg_slow_time = total_slow_time / len(self.slow_actions)

        return {
            "slow_actions_count": len(self.slow_actions),
            "total_slow_time_ms": total_slow_time,
            "avg_slow_time_ms": avg_slow_time,
            "slowest_action": max(self.slow_actions, key=lambda x: x["execution_time_ms"]),
        }


class ValidationMiddleware(Middleware):
    """Middleware for validating actions and state transitions."""

    def __init__(self):
        self.validation_errors = []
        self.blocked_actions = 0

    def before_dispatch(self, action: Action, current_state: AppState) -> Optional[Action]:
        """Validate action before dispatch."""
        try:
            # Basic action validation
            if not hasattr(action, "type") or not action.type:
                self._add_validation_error(f"Invalid action type: {action}")
                return None

            # State-specific validations
            validation_result = self._validate_action_for_state(action, current_state)
            if not validation_result:
                self.blocked_actions += 1
                return None

            return action

        except Exception as e:
            self._add_validation_error(f"Validation error: {e}")
            return None

    def after_dispatch(self, action: Action, old_state: AppState, new_state: AppState) -> None:
        """Validate state after dispatch."""
        try:
            # Validate state consistency
            self._validate_state_consistency(new_state)

        except Exception as e:
            self._add_validation_error(f"State validation error after {action.type.value}: {e}")

    def _validate_action_for_state(self, action: Action, state: AppState) -> bool:
        """Validate if action is allowed in current state."""
        from src.state.actions import ActionType

        # Don't allow certain actions during shutdown
        if state.status.value == "shutting_down":
            forbidden_during_shutdown = [
                ActionType.TRANSLATION_START,
                ActionType.CAPTURE_START,
                ActionType.PROCESSING_START,
            ]
            if action.type in forbidden_during_shutdown:
                self._add_validation_error(
                    f"Action {action.type.value} not allowed during shutdown"
                )
                return False

        # Don't allow multiple processing operations
        if state.processing.is_processing and action.type == ActionType.PROCESSING_START:
            self._add_validation_error("Cannot start processing while already processing")
            return False

        return True

    def _validate_state_consistency(self, state: AppState) -> None:
        """Validate state internal consistency."""
        # Check that processing state is consistent
        if state.processing.is_processing:
            if not state.processing.operation_type:
                raise ValueError("Processing is active but no operation type set")

        # Check that translation history is reasonable
        if len(state.translation_history) > 10000:
            logger.warning(f"Translation history very large: {len(state.translation_history)}")

        # Check performance metrics are valid
        if state.performance.success_rate < 0 or state.performance.success_rate > 1:
            raise ValueError(f"Invalid success rate: {state.performance.success_rate}")

    def _add_validation_error(self, error_message: str) -> None:
        """Add validation error to log."""
        self.validation_errors.append({"error": error_message, "timestamp": time.time()})

        # Keep only last 100 errors
        if len(self.validation_errors) > 100:
            self.validation_errors = self.validation_errors[-100:]

        logger.warning(f"State validation error: {error_message}")

    def get_validation_errors(self) -> list:
        """Get recent validation errors."""
        return self.validation_errors.copy()

    def get_validation_summary(self) -> dict:
        """Get validation summary."""
        return {
            "total_errors": len(self.validation_errors),
            "blocked_actions": self.blocked_actions,
            "recent_errors": self.validation_errors[-10:] if self.validation_errors else [],
        }


class DevToolsMiddleware(Middleware):
    """Middleware for development tools and debugging."""

    def __init__(self):
        self.action_log = []
        self.state_snapshots = {}
        self.max_log_size = 1000

    def before_dispatch(self, action: Action, current_state: AppState) -> Optional[Action]:
        """Record action for dev tools."""
        action_record = {
            "action_id": action.action_id,
            "action_type": action.type.value,
            "timestamp": time.time(),
            "payload": action.get_payload(),
            "state_before": current_state.copy(),
        }

        self.action_log.append(action_record)

        # Keep log size manageable
        if len(self.action_log) > self.max_log_size:
            self.action_log = self.action_log[-self.max_log_size :]

        return action

    def after_dispatch(self, action: Action, old_state: AppState, new_state: AppState) -> None:
        """Record state change for dev tools."""
        # Update last action record with new state
        if self.action_log:
            self.action_log[-1]["state_after"] = new_state.copy()
            self.action_log[-1]["state_changed"] = old_state != new_state

        # Store state snapshot
        self.state_snapshots[action.action_id] = {
            "old_state": old_state.copy(),
            "new_state": new_state.copy(),
            "timestamp": time.time(),
        }

        # Keep snapshots manageable
        if len(self.state_snapshots) > 100:
            # Remove oldest snapshots
            oldest_keys = sorted(self.state_snapshots.keys())[:50]
            for key in oldest_keys:
                del self.state_snapshots[key]

    def get_action_log(self) -> list:
        """Get action log for debugging."""
        return self.action_log.copy()

    def get_state_snapshot(self, action_id: str) -> dict:
        """Get state snapshot for specific action."""
        return self.state_snapshots.get(action_id, {})

    def export_debug_data(self) -> dict:
        """Export all debug data."""
        return {
            "action_log": self.action_log,
            "state_snapshots": self.state_snapshots,
            "export_timestamp": time.time(),
        }

"""
State store implementation for Redux-like state management.
"""

import asyncio
import threading
import time
from collections import deque
from typing import Callable, Dict, List, Optional

from src.state.actions import Action
from src.state.app_state import AppState, StateSnapshot
from src.state.middleware import Middleware
from src.state.reducers import RootReducer, create_root_reducer
from src.utils.logger import logger


class StateStore:
    """Central state store with Redux-like functionality."""

    def __init__(
        self, initial_state: Optional[AppState] = None, reducer: Optional[RootReducer] = None
    ):
        self._state = initial_state or AppState()
        self._reducer = reducer or create_root_reducer()
        self._subscribers: List[Callable[[AppState], None]] = []
        self._middleware: List[Middleware] = []
        self._history: deque[StateSnapshot] = deque(maxlen=100)  # Keep last 100 states
        self._lock = threading.RLock()  # Thread-safe state updates
        self._is_dispatching = False

        # Performance metrics
        self._dispatch_count = 0
        self._total_dispatch_time = 0.0
        self._subscriber_count = 0

        # Store initial state snapshot
        self._history.append(StateSnapshot.create(self._state))

        logger.info("State store initialized")

    def get_state(self) -> AppState:
        """Get current application state (immutable copy)."""
        with self._lock:
            return self._state.copy()

    def dispatch(self, action: Action) -> None:
        """Dispatch action to update state."""
        start_time = time.time()

        with self._lock:
            if self._is_dispatching:
                raise RuntimeError("Cannot dispatch action while already dispatching")

            try:
                self._is_dispatching = True

                # Apply middleware (pre-dispatch)
                processed_action = action
                for middleware in self._middleware:
                    processed_action = middleware.before_dispatch(processed_action, self._state)
                    if processed_action is None:
                        logger.debug(f"Action blocked by middleware: {action.type}")
                        return

                # Apply reducer to get new state
                old_state = self._state
                new_state = self._reducer.reduce(self._state, processed_action)

                # Update state if changed
                if new_state != old_state:
                    self._state = new_state

                    # Store state snapshot
                    snapshot = StateSnapshot.create(
                        new_state, processed_action.action_id, processed_action.type.value
                    )
                    self._history.append(snapshot)

                    # Apply middleware (post-dispatch)
                    for middleware in self._middleware:
                        middleware.after_dispatch(processed_action, old_state, new_state)

                    # Notify subscribers
                    self._notify_subscribers(new_state)

                    logger.debug(
                        f"State updated: {processed_action.type.value}",
                        action_id=processed_action.action_id,
                    )
                else:
                    logger.debug(f"State unchanged: {processed_action.type.value}")

                # Update metrics
                execution_time = (time.time() - start_time) * 1000
                self._dispatch_count += 1
                self._total_dispatch_time += execution_time

            except Exception as e:
                logger.error(
                    f"Error dispatching action: {action.type.value}",
                    action_id=action.action_id,
                    error=e,
                )
                raise
            finally:
                self._is_dispatching = False

    async def dispatch_async(self, action: Action) -> None:
        """Dispatch action asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.dispatch, action)

    def subscribe(self, callback: Callable[[AppState], None]) -> Callable[[], None]:
        """Subscribe to state changes. Returns unsubscribe function."""
        with self._lock:
            self._subscribers.append(callback)
            self._subscriber_count = len(self._subscribers)

            logger.debug(f"State subscriber added, total: {self._subscriber_count}")

            # Return unsubscribe function
            def unsubscribe():
                self.unsubscribe(callback)

            return unsubscribe

    def unsubscribe(self, callback: Callable[[AppState], None]) -> None:
        """Unsubscribe from state changes."""
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)
                self._subscriber_count = len(self._subscribers)
                logger.debug(f"State subscriber removed, total: {self._subscriber_count}")

    def _notify_subscribers(self, new_state: AppState) -> None:
        """Notify all subscribers of state change."""
        for callback in self._subscribers[:]:  # Copy list to avoid modification during iteration
            try:
                callback(new_state)
            except Exception as e:
                logger.error(f"Error in state subscriber: {e}", error=e)

    def add_middleware(self, middleware: Middleware) -> None:
        """Add middleware to the store."""
        with self._lock:
            self._middleware.append(middleware)
            logger.info(f"Middleware added: {middleware.__class__.__name__}")

    def remove_middleware(self, middleware: Middleware) -> None:
        """Remove middleware from the store."""
        with self._lock:
            if middleware in self._middleware:
                self._middleware.remove(middleware)
                logger.info(f"Middleware removed: {middleware.__class__.__name__}")

    def get_history(self, limit: int = 10) -> List[StateSnapshot]:
        """Get state history snapshots."""
        with self._lock:
            return list(self._history)[-limit:]

    def get_state_at_time(self, timestamp: float) -> Optional[StateSnapshot]:
        """Get state snapshot closest to the given timestamp."""
        with self._lock:
            closest_snapshot = None
            min_diff = float("inf")

            for snapshot in self._history:
                time_diff = abs(snapshot.timestamp - timestamp)
                if time_diff < min_diff:
                    min_diff = time_diff
                    closest_snapshot = snapshot

            return closest_snapshot

    def clear_history(self) -> None:
        """Clear state history."""
        with self._lock:
            self._history.clear()
            # Keep current state
            self._history.append(StateSnapshot.create(self._state))
            logger.info("State history cleared")

    def get_metrics(self) -> Dict[str, any]:
        """Get store performance metrics."""
        with self._lock:
            avg_dispatch_time = (
                self._total_dispatch_time / self._dispatch_count if self._dispatch_count > 0 else 0
            )

            return {
                "dispatch_count": self._dispatch_count,
                "total_dispatch_time_ms": self._total_dispatch_time,
                "avg_dispatch_time_ms": avg_dispatch_time,
                "subscriber_count": self._subscriber_count,
                "middleware_count": len(self._middleware),
                "history_size": len(self._history),
                "current_state_size": len(str(self._state)),  # Rough size estimate
            }

    def reset_state(self, new_state: Optional[AppState] = None) -> None:
        """Reset state to initial or provided state."""
        with self._lock:
            old_state = self._state
            self._state = new_state or AppState()

            # Clear history and add new initial state
            self._history.clear()
            self._history.append(StateSnapshot.create(self._state))

            # Notify subscribers
            self._notify_subscribers(self._state)

            logger.info("State reset")


# Global state store instance
_state_store: Optional[StateStore] = None
_store_lock = threading.Lock()


def get_state_store() -> StateStore:
    """Get global state store instance (singleton)."""
    global _state_store

    if _state_store is None:
        with _store_lock:
            if _state_store is None:
                _state_store = StateStore()

    return _state_store


def reset_state_store() -> None:
    """Reset global state store (mainly for testing)."""
    global _state_store

    with _store_lock:
        _state_store = None

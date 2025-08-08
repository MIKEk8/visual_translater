"""
State Management System for centralized application state.

This module implements Redux-like state management with actions,
reducers, and reactive subscriptions to state changes.
"""

from .actions import Action, ActionType, StateAction
from .app_state import AppState, StateSnapshot
from .middleware import LoggingMiddleware, PerformanceMiddleware, ValidationMiddleware
from .reducers import RootReducer, create_root_reducer
from .store import StateStore, get_state_store

__all__ = [
    "AppState",
    "StateSnapshot",
    "Action",
    "ActionType",
    "StateAction",
    "RootReducer",
    "create_root_reducer",
    "StateStore",
    "get_state_store",
    "LoggingMiddleware",
    "PerformanceMiddleware",
    "ValidationMiddleware",
]

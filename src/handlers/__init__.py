"""
Command and Query handlers for CQRS architecture.

This module provides handlers that execute commands and queries,
implementing the separation of concerns between read and write operations.
"""

from .base_handler import CommandHandler, QueryHandler
from .command_handlers import (
    AppCommandHandler,
    ScreenshotCommandHandler,
    TranslationCommandHandler,
    TTSCommandHandler,
)
from .query_handlers import (
    ConfigQueryHandler,
    PerformanceQueryHandler,
    TranslationQueryHandler,
)

__all__ = [
    "CommandHandler",
    "QueryHandler",
    "ScreenshotCommandHandler",
    "TranslationCommandHandler",
    "TTSCommandHandler",
    "AppCommandHandler",
    "TranslationQueryHandler",
    "PerformanceQueryHandler",
    "ConfigQueryHandler",
]

"""
Query pattern implementations for CQRS architecture.

This module provides query objects that represent requests
for data without modifying application state.
"""

from .base_query import Query, QueryResult
from .config_queries import (
    GetAvailableLanguagesQuery,
    GetConfigQuery,
    GetHotkeyConfigQuery,
)
from .performance_queries import (
    GetPerformanceMetricsQuery,
    GetSystemHealthQuery,
    GetUsageStatsQuery,
)
from .screenshot_queries import (
    GetScreenshotByIdQuery,
    GetScreenshotHistoryQuery,
)
from .translation_queries import (
    GetTranslationHistoryQuery,
    GetTranslationStatsQuery,
    SearchTranslationsQuery,
)

__all__ = [
    "Query",
    "QueryResult",
    "GetTranslationHistoryQuery",
    "SearchTranslationsQuery",
    "GetTranslationStatsQuery",
    "GetScreenshotHistoryQuery",
    "GetScreenshotByIdQuery",
    "GetPerformanceMetricsQuery",
    "GetSystemHealthQuery",
    "GetUsageStatsQuery",
    "GetConfigQuery",
    "GetAvailableLanguagesQuery",
    "GetHotkeyConfigQuery",
]

"""
Translation-related queries for CQRS pattern.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from .base_query import Query


@dataclass
class GetTranslationHistoryQuery(Query):
    """Query to get translation history."""

    limit: int = 100
    include_failed: bool = False
    language_filter: Optional[str] = None

    def validate(self) -> bool:
        """Validate history query."""
        if self.limit < 1 or self.limit > 1000:
            return False

        # Validate pagination if present
        if self.pagination and not self.pagination.validate():
            return False

        # Validate sorting if present
        if self.sorting and not self.sorting.validate():
            return False

        # Validate supported sort fields
        if self.sorting:
            valid_sort_fields = ["timestamp", "confidence", "duration", "text_length"]
            if self.sorting.field not in valid_sort_fields:
                return False

        return True


@dataclass
class SearchTranslationsQuery(Query):
    """Query to search translations by text content."""

    search_text: str = ""
    search_in: str = "both"  # "original", "translated", "both"
    case_sensitive: bool = False
    exact_match: bool = False
    min_confidence: Optional[float] = None

    def validate(self) -> bool:
        """Validate search query."""
        if not self.search_text or not self.search_text.strip():
            return False

        if len(self.search_text) > 500:  # Max search text length
            return False

        valid_search_in = ["original", "translated", "both"]
        if self.search_in not in valid_search_in:
            return False

        if self.min_confidence is not None:
            if not (0.0 <= self.min_confidence <= 1.0):
                return False

        # Validate pagination if present
        if self.pagination and not self.pagination.validate():
            return False

        return True

    @property
    def normalized_search_text(self) -> str:
        """Get normalized search text."""
        text = self.search_text.strip()
        if not self.case_sensitive:
            text = text.lower()
        return text


@dataclass
class GetTranslationStatsQuery(Query):
    """Query to get translation statistics."""

    time_range_days: int = 30
    group_by: str = "day"  # "hour", "day", "week", "month"
    include_performance: bool = True
    include_languages: bool = True

    def validate(self) -> bool:
        """Validate stats query."""
        if self.time_range_days < 1 or self.time_range_days > 365:
            return False

        valid_group_by = ["hour", "day", "week", "month"]
        if self.group_by not in valid_group_by:
            return False

        return True

    @property
    def start_date(self) -> datetime:
        """Get start date for statistics."""
        return datetime.now() - timedelta(days=self.time_range_days)


@dataclass
class GetTranslationByIdQuery(Query):
    """Query to get specific translation by ID."""

    translation_id: str = ""
    include_metadata: bool = True

    def validate(self) -> bool:
        """Validate get by ID query."""
        if not self.translation_id:
            return False

        return True


@dataclass
class GetTopTranslationsQuery(Query):
    """Query to get most frequently translated texts."""

    limit: int = 50
    time_range_days: Optional[int] = None
    min_occurrences: int = 2

    def validate(self) -> bool:
        """Validate top translations query."""
        if self.limit < 1 or self.limit > 500:
            return False

        if self.min_occurrences < 1:
            return False

        if self.time_range_days is not None:
            if self.time_range_days < 1 or self.time_range_days > 365:
                return False

        return True


@dataclass
class GetTranslationLanguagePairsQuery(Query):
    """Query to get available language pairs with usage statistics."""

    include_usage_stats: bool = True
    min_usage_count: int = 1

    def validate(self) -> bool:
        """Validate language pairs query."""
        if self.min_usage_count < 0:
            return False

        return True


@dataclass
class GetTranslationPerformanceQuery(Query):
    """Query to get translation performance metrics."""

    time_range_days: int = 7
    include_breakdown: bool = True  # OCR vs Translation time
    percentiles: Optional[List[float]] = None  # e.g., [50, 90, 95, 99]

    def __post_init__(self):
        """Set default percentiles if none provided."""
        if self.percentiles is None:
            self.percentiles = [50.0, 90.0, 95.0, 99.0]

    def validate(self) -> bool:
        """Validate performance query."""
        if self.time_range_days < 1 or self.time_range_days > 90:
            return False

        if self.percentiles:
            for p in self.percentiles:
                if not (0.0 <= p <= 100.0):
                    return False

        return True


@dataclass
class GetFailedTranslationsQuery(Query):
    """Query to get failed translation attempts."""

    time_range_days: int = 7
    error_type_filter: Optional[str] = None
    include_retry_info: bool = True

    def validate(self) -> bool:
        """Validate failed translations query."""
        if self.time_range_days < 1 or self.time_range_days > 90:
            return False

        if self.error_type_filter:
            valid_error_types = [
                "network_error",
                "api_error",
                "rate_limit",
                "invalid_language",
                "text_too_long",
                "unknown",
            ]
            if self.error_type_filter not in valid_error_types:
                return False

        return True


@dataclass
class GetCacheStatsQuery(Query):
    """Query to get translation cache statistics."""

    include_hit_rate: bool = True
    include_size_info: bool = True
    include_top_cached: bool = False
    top_cached_limit: int = 20

    def validate(self) -> bool:
        """Validate cache stats query."""
        if self.top_cached_limit < 1 or self.top_cached_limit > 100:
            return False

        return True

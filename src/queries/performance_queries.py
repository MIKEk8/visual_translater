"""
Performance-related queries for CQRS pattern.
"""

from dataclasses import dataclass
from typing import List, Optional

from .base_query import Query


@dataclass
class GetPerformanceMetricsQuery(Query):
    """Query to get performance metrics."""

    time_range_days: int = 7
    metric_types: Optional[List[str]] = None
    include_breakdown: bool = True

    def __post_init__(self):
        """Set default metric types if none provided."""
        if self.metric_types is None:
            self.metric_types = ["ocr", "translation", "tts", "overall"]

    def validate(self) -> bool:
        """Validate performance metrics query."""
        if self.time_range_days < 1 or self.time_range_days > 90:
            return False

        valid_metrics = ["ocr", "translation", "tts", "screenshot", "overall"]
        if self.metric_types:
            for metric in self.metric_types:
                if metric not in valid_metrics:
                    return False

        return True


@dataclass
class GetSystemHealthQuery(Query):
    """Query to get system health information."""

    include_performance: bool = True
    include_resources: bool = True
    include_errors: bool = True

    def validate(self) -> bool:
        """Always valid query."""
        return True


@dataclass
class GetUsageStatsQuery(Query):
    """Query to get usage statistics."""

    time_range_days: int = 30
    group_by: str = "day"  # "hour", "day", "week", "month"
    include_features: bool = True

    def validate(self) -> bool:
        """Validate usage stats query."""
        if self.time_range_days < 1 or self.time_range_days > 365:
            return False

        valid_group_by = ["hour", "day", "week", "month"]
        if self.group_by not in valid_group_by:
            return False

        return True

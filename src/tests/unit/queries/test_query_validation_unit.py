from datetime import datetime, timedelta

from src.queries.base_query import PaginationParams, SortParams, FilterParams
from src.queries.translation_queries import (
    GetTranslationHistoryQuery,
    SearchTranslationsQuery,
    GetTranslationStatsQuery,
)
from src.queries.screenshot_queries import GetScreenshotHistoryQuery
from src.queries.performance_queries import GetPerformanceMetricsQuery, GetUsageStatsQuery
from src.queries.config_queries import GetConfigQuery


def test_pagination_sort_filter_validation():
    assert PaginationParams(page=1, page_size=50).validate() is True
    assert PaginationParams(page=0).validate() is False
    assert SortParams(field="name", direction="asc").validate() is True
    assert SortParams(field="", direction="asc").validate() is False
    assert FilterParams(date_from=datetime.now(), date_to=datetime.now()).validate() is True
    assert FilterParams(date_from=datetime.now(), date_to=datetime.now() - timedelta(days=1)).validate() is False


def test_config_query_sections():
    assert GetConfigQuery(section=None).validate() is True
    assert GetConfigQuery(section="languages").validate() is True
    assert GetConfigQuery(section="invalid").validate() is False


def test_history_and_screenshot_queries():
    assert GetTranslationHistoryQuery(limit=10).validate() is True
    assert GetTranslationHistoryQuery(limit=0).validate() is False
    assert GetScreenshotHistoryQuery(limit=100).validate() is True
    assert GetScreenshotHistoryQuery(limit=0).validate() is False


def test_search_query_validation():
    assert SearchTranslationsQuery(search_text="hello").validate() is True
    assert SearchTranslationsQuery(search_text="").validate() is False
    assert SearchTranslationsQuery(search_text="a" * 501).validate() is False
    assert SearchTranslationsQuery(search_text="hi", search_in="both").validate() is True
    assert SearchTranslationsQuery(search_text="hi", search_in="x").validate() is False
    assert SearchTranslationsQuery(search_text="hi", min_confidence=1.1).validate() is False
    assert SearchTranslationsQuery(search_text="hi", min_confidence=0.5).validate() is True


def test_stats_and_usage_queries():
    assert GetTranslationStatsQuery(time_range_days=30, group_by="day").validate() is True
    assert GetTranslationStatsQuery(time_range_days=0).validate() is False
    assert GetUsageStatsQuery(time_range_days=30, group_by="day").validate() is True
    assert GetUsageStatsQuery(group_by="year").validate() is False
    assert GetPerformanceMetricsQuery(time_range_days=7).validate() is True
    assert GetPerformanceMetricsQuery(time_range_days=0).validate() is False



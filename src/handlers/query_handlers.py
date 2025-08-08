"""Query handlers for CQRS pattern."""

from src.handlers.base_handler import QueryHandler
from src.queries.base_query import Query, QueryResult


class TranslationQueryHandler(QueryHandler):
    """Handler for translation-related queries."""

    def __init__(self):
        super().__init__("TranslationQueryHandler")

    async def _execute(self, query: Query) -> QueryResult:
        """Execute translation queries."""
        # Mock implementation for testing
        return QueryResult.success_result(data=[{"translation": "data"}], total_count=1)


class PerformanceQueryHandler(QueryHandler):
    """Handler for performance-related queries."""

    def __init__(self):
        super().__init__("PerformanceQueryHandler")

    async def _execute(self, query: Query) -> QueryResult:
        """Execute performance queries."""
        # Mock implementation for testing
        return QueryResult.success_result(data=[{"performance": "metrics"}], total_count=1)


class ConfigQueryHandler(QueryHandler):
    """Handler for configuration-related queries."""

    def __init__(self):
        super().__init__("ConfigQueryHandler")

    async def _execute(self, query: Query) -> QueryResult:
        """Execute config queries."""
        # Mock implementation for testing
        return QueryResult.success_result(data=[{"config": "data"}], total_count=1)

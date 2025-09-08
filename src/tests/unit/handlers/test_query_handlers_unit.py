import pytest

from src.handlers.query_handlers import (
    ConfigQueryHandler,
    PerformanceQueryHandler,
    TranslationQueryHandler,
)
from src.queries.base_query import Query


class ValidQuery(Query):
    def validate(self) -> bool:
        return True


class InvalidQuery(Query):
    def validate(self) -> bool:
        return False


@pytest.mark.asyncio
async def test_translation_query_handler_success_and_invalid():
    h = TranslationQueryHandler()
    ok = await h.handle(ValidQuery())
    assert ok.success and ok.total_count == 1 and ok.data
    bad = await h.handle(InvalidQuery())
    assert bad.success is False


@pytest.mark.asyncio
async def test_performance_query_handler_success():
    h = PerformanceQueryHandler()
    ok = await h.handle(ValidQuery())
    assert ok.success and ok.total_count == 1 and ok.data


@pytest.mark.asyncio
async def test_config_query_handler_success():
    h = ConfigQueryHandler()
    ok = await h.handle(ValidQuery())
    assert ok.success and ok.total_count == 1 and ok.data



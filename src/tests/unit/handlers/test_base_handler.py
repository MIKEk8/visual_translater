import asyncio

import pytest

from src.handlers.base_handler import CommandHandler, QueryHandler
from src.commands.base_command import Command, CommandResult
from src.queries.base_query import Query, QueryResult


class GoodCommand(Command):
    def validate(self) -> bool:
        return True

    def get_command_type(self) -> str:
        return "GOOD"


class BadCommand(Command):
    def validate(self) -> bool:
        return False

    def get_command_type(self) -> str:
        return "BAD"


class FailingCommand(Command):
    def validate(self) -> bool:
        return True

    def get_command_type(self) -> str:
        return "FAIL"


class GoodHandler(CommandHandler[GoodCommand, str]):
    async def _execute(self, command: GoodCommand) -> CommandResult[str]:
        return CommandResult.success_result("ok")


class FailingHandler(CommandHandler[FailingCommand, str]):
    async def _execute(self, command: FailingCommand) -> CommandResult[str]:
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_command_handler_success_and_metrics():
    h = GoodHandler("H")
    res = await h.handle(GoodCommand())
    assert res.success is True and res.data == "ok"
    m = h.get_metrics()
    assert m["execution_count"] == 1 and m["error_count"] == 0
    assert m["avg_execution_time_ms"] >= 0


@pytest.mark.asyncio
async def test_command_handler_invalid_command():
    h = GoodHandler("H")
    res = await h.handle(BadCommand())
    assert res.success is False and "Invalid command" in (res.error or "")
    m = h.get_metrics()
    # invalid не считается выполнением _execute
    assert m["execution_count"] == 0


@pytest.mark.asyncio
async def test_command_handler_exception_flow():
    h = FailingHandler("H")
    res = await h.handle(FailingCommand())
    assert res.success is False and "Command handler error" in (res.error or "")
    m = h.get_metrics()
    assert m["execution_count"] == 1 and m["error_count"] == 1


class GoodQuery(Query):
    def validate(self) -> bool:
        return True

    def get_query_type(self) -> str:
        return "GOODQ"


class BadQuery(Query):
    def validate(self) -> bool:
        return False

    def get_query_type(self) -> str:
        return "BADQ"


class GoodQHandler(QueryHandler[GoodQuery, list]):
    async def _execute(self, query: GoodQuery) -> QueryResult[list]:
        return QueryResult.success_result([1, 2, 3], total_count=3)


@pytest.mark.asyncio
async def test_query_handler_success_and_metrics():
    h = GoodQHandler("QH")
    res = await h.handle(GoodQuery())
    assert res.success is True and res.total_count == 3
    m = h.get_metrics()
    assert m["execution_count"] == 1 and m["error_count"] == 0


@pytest.mark.asyncio
async def test_query_handler_invalid_query():
    h = GoodQHandler("QH")
    res = await h.handle(BadQuery())
    assert res.success is False and "Invalid query" in (res.error or "")
    m = h.get_metrics()
    assert m["execution_count"] == 0



"""
Base handler classes for CQRS architecture.
"""

import asyncio  # noqa: F401
import time
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from src.commands.base_command import Command, CommandResult
from src.queries.base_query import Query, QueryResult
from src.utils.logger import logger

# Type variables for generic handlers
TCommand = TypeVar("TCommand", bound=Command)
TCommandResult = TypeVar("TCommandResult")
TQuery = TypeVar("TQuery", bound=Query)
TQueryResult = TypeVar("TQueryResult")


class CommandHandler(ABC, Generic[TCommand, TCommandResult]):
    """Base class for command handlers."""

    def __init__(self, name: str):
        self.name = name
        self.execution_count = 0
        self.error_count = 0
        self.total_execution_time = 0.0

    async def handle(self, command: TCommand) -> CommandResult[TCommandResult]:
        """Handle command execution with timing and error handling."""
        start_time = time.time()

        try:
            # Validate command
            if not command.validate():
                error_msg = f"Invalid command: {command.get_command_type()}"
                logger.warning(error_msg, command_id=command.command_id)
                return CommandResult.error_result(error_msg)

            # Log command execution
            logger.info(
                f"Executing command: {command.get_command_type()}",
                command_id=command.command_id,
                handler=self.name,
            )

            # Execute command
            result = await self._execute(command)

            # Update metrics
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            result.execution_time_ms = execution_time

            self.execution_count += 1
            self.total_execution_time += execution_time

            if result.success:
                logger.info(
                    f"Command executed successfully: {command.get_command_type()}",
                    command_id=command.command_id,
                    execution_time_ms=execution_time,
                )
            else:
                self.error_count += 1
                logger.error(
                    f"Command execution failed: {command.get_command_type()}",
                    command_id=command.command_id,
                    error=result.error,
                    execution_time_ms=execution_time,
                )

            return result

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self.error_count += 1
            self.execution_count += 1
            self.total_execution_time += execution_time

            error_msg = f"Command handler error: {str(e)}"
            logger.error(
                error_msg,
                command_id=command.command_id,
                handler=self.name,
                error=e,
                execution_time_ms=execution_time,
            )

            result = CommandResult.error_result(error_msg)
            result.execution_time_ms = execution_time
            return result

    @abstractmethod
    async def _execute(self, command: TCommand) -> CommandResult[TCommandResult]:
        """Execute the specific command logic."""
        pass

    def get_metrics(self) -> dict:
        """Get handler performance metrics."""
        avg_execution_time = (
            self.total_execution_time / self.execution_count if self.execution_count > 0 else 0
        )

        return {
            "name": self.name,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "success_count": self.execution_count - self.error_count,
            "error_rate": (
                self.error_count / self.execution_count if self.execution_count > 0 else 0
            ),
            "total_execution_time_ms": self.total_execution_time,
            "avg_execution_time_ms": avg_execution_time,
        }


class QueryHandler(ABC, Generic[TQuery, TQueryResult]):
    """Base class for query handlers."""

    def __init__(self, name: str):
        self.name = name
        self.execution_count = 0
        self.error_count = 0
        self.total_execution_time = 0.0
        self.cache_hits = 0

    async def handle(self, query: TQuery) -> QueryResult[TQueryResult]:
        """Handle query execution with timing and error handling."""
        start_time = time.time()

        try:
            # Validate query
            if not query.validate():
                error_msg = f"Invalid query: {query.get_query_type()}"
                logger.warning(error_msg, query_id=query.query_id)
                return QueryResult.error_result(error_msg)

            # Log query execution
            logger.debug(
                f"Executing query: {query.get_query_type()}",
                query_id=query.query_id,
                handler=self.name,
            )

            # Execute query
            result = await self._execute(query)

            # Update metrics
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            result.execution_time_ms = execution_time

            self.execution_count += 1
            self.total_execution_time += execution_time

            if result.success:
                logger.debug(
                    f"Query executed successfully: {query.get_query_type()}",
                    query_id=query.query_id,
                    execution_time_ms=execution_time,
                    result_count=result.total_count,
                )
            else:
                self.error_count += 1
                logger.error(
                    f"Query execution failed: {query.get_query_type()}",
                    query_id=query.query_id,
                    error=result.error,
                    execution_time_ms=execution_time,
                )

            return result

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self.error_count += 1
            self.execution_count += 1
            self.total_execution_time += execution_time

            error_msg = f"Query handler error: {str(e)}"
            logger.error(
                error_msg,
                query_id=query.query_id,
                handler=self.name,
                error=e,
                execution_time_ms=execution_time,
            )

            result = QueryResult.error_result(error_msg)
            result.execution_time_ms = execution_time
            return result

    @abstractmethod
    async def _execute(self, query: TQuery) -> QueryResult[TQueryResult]:
        """Execute the specific query logic."""
        pass

    def get_metrics(self) -> dict:
        """Get handler performance metrics."""
        avg_execution_time = (
            self.total_execution_time / self.execution_count if self.execution_count > 0 else 0
        )

        cache_hit_rate = self.cache_hits / self.execution_count if self.execution_count > 0 else 0

        return {
            "name": self.name,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "success_count": self.execution_count - self.error_count,
            "error_rate": (
                self.error_count / self.execution_count if self.execution_count > 0 else 0
            ),
            "total_execution_time_ms": self.total_execution_time,
            "avg_execution_time_ms": avg_execution_time,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": cache_hit_rate,
        }

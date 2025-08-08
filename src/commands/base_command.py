"""Base command pattern implementation for CQRS architecture."""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Generic, Optional, TypeVar

# Generic type for command result
T = TypeVar("T")


@dataclass
class CommandResult(Generic[T]):
    """Result of command execution."""

    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success_result(
        cls, data: T, metadata: Optional[Dict[str, Any]] = None
    ) -> "CommandResult[T]":
        """Create successful command result."""
        return cls(success=True, data=data, metadata=metadata or {})

    @classmethod
    def error_result(
        cls, error: str, metadata: Optional[Dict[str, Any]] = None
    ) -> "CommandResult[T]":
        """Create error command result."""
        return cls(success=False, error=error, metadata=metadata or {})


@dataclass
class Command(ABC):
    """Base class for all commands in CQRS pattern."""

    command_id: str = field(default_factory=lambda: f"cmd_{int(time.time() * 1000)}")
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    def validate(self) -> bool:
        """Validate command parameters."""
        pass

    def get_command_type(self) -> str:
        """Get command type for logging and metrics."""
        return self.__class__.__name__

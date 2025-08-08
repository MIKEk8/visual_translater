"""
Base query pattern implementation for CQRS architecture.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Generic, Optional, TypeVar

# Generic type for query result
T = TypeVar("T")


@dataclass
class QueryResult(Generic[T]):
    """Result of query execution."""

    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    total_count: Optional[int] = None  # For paginated results
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success_result(
        cls, data: T, total_count: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None
    ) -> "QueryResult[T]":
        """Create successful query result."""
        return cls(success=True, data=data, total_count=total_count, metadata=metadata or {})

    @classmethod
    def error_result(
        cls, error: str, metadata: Optional[Dict[str, Any]] = None
    ) -> "QueryResult[T]":
        """Create error query result."""
        return cls(success=False, error=error, metadata=metadata or {})


@dataclass
class PaginationParams:
    """Pagination parameters for queries."""

    page: int = 1
    page_size: int = 50
    max_page_size: int = 1000

    def validate(self) -> bool:
        """Validate pagination parameters."""
        if self.page < 1:
            return False

        if self.page_size < 1 or self.page_size > self.max_page_size:
            return False

        return True

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get limit for database queries."""
        return self.page_size


@dataclass
class SortParams:
    """Sorting parameters for queries."""

    field: str
    direction: str = "desc"  # "asc" or "desc"

    def validate(self) -> bool:
        """Validate sort parameters."""
        if not self.field:
            return False

        if self.direction not in ["asc", "desc"]:
            return False

        return True


@dataclass
class FilterParams:
    """Filtering parameters for queries."""

    filters: Dict[str, Any] = field(default_factory=dict)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    def validate(self) -> bool:
        """Validate filter parameters."""
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                return False

        return True

    def has_date_filter(self) -> bool:
        """Check if date filtering is enabled."""
        return self.date_from is not None or self.date_to is not None


@dataclass
class Query(ABC):
    """Base class for all queries in CQRS pattern."""

    query_id: str = field(default_factory=lambda: f"qry_{int(time.time() * 1000)}")
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None
    pagination: Optional[PaginationParams] = None
    sorting: Optional[SortParams] = None
    filtering: Optional[FilterParams] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    def validate(self) -> bool:
        """Validate query parameters."""
        pass

    def get_query_type(self) -> str:
        """Get query type for logging and metrics."""
        return self.__class__.__name__

    def is_paginated(self) -> bool:
        """Check if query uses pagination."""
        return self.pagination is not None

    def is_sorted(self) -> bool:
        """Check if query uses sorting."""
        return self.sorting is not None

    def is_filtered(self) -> bool:
        """Check if query uses filtering."""
        return self.filtering is not None and (
            bool(self.filtering.filters) or self.filtering.has_date_filter()
        )

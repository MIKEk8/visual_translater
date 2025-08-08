"""
Domain ID Value Object - Pure domain abstraction for entity identification
No external dependencies, follows Clean Architecture principles
"""

from typing import Any


class DomainId:
    """Domain-specific identifier - no external dependencies"""

    def __init__(self, value: str):
        if not value or not isinstance(value, str):
            raise ValueError("ID must be non-empty string")
        self._value = value.strip()
        if not self._value:
            raise ValueError("ID cannot be empty or whitespace")

    @classmethod
    def generate(cls) -> "DomainId":
        """Generate new ID - implementation detail hidden"""
        import random
        import time

        timestamp = str(int(time.time() * 1000000))[-10:]
        random_suffix = str(random.randint(100, 999))
        return cls(f"id_{timestamp}_{random_suffix}")

    @classmethod
    def from_string(cls, value: str) -> "DomainId":
        """Create from existing string"""
        return cls(value)

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"DomainId('{self._value}')"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, DomainId):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    @property
    def value(self) -> str:
        """Get the raw string value"""
        return self._value

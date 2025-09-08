"""
Domain ID Value Object - Pure domain abstraction for entity identification
No external dependencies, follows Clean Architecture principles
"""

from typing import Any


class DomainId(str):
    """Domain-specific identifier implemented as a string subclass.

    Behaves like a standard string so it can be passed wherever a string is expected
    (e.g., uuid.UUID()), while still providing a distinct type in the domain layer.
    """

    def __new__(cls, value: str):
        if not value or not isinstance(value, str):
            raise ValueError("ID must be non-empty string")
        normalized = value.strip()
        if not normalized:
            raise ValueError("ID cannot be empty or whitespace")
        return str.__new__(cls, normalized)

    @classmethod
    def generate(cls) -> "DomainId":
        """Generate new ID - implementation detail hidden"""
        import uuid

        return cls(str(uuid.uuid4()))

    @classmethod
    def from_string(cls, value: str) -> "DomainId":
        """Create from existing string"""
        return cls(value)

    def __repr__(self) -> str:
        return f"DomainId('{str(self)}')"

    @property
    def value(self) -> str:
        """Get the raw string value"""
        return str(self)

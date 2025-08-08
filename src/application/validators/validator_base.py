"""
Base validation functionality.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class ValidationResult:
    """Validation result container."""

    is_valid: bool
    errors: List[str] = None

    @classmethod
    def success(cls) -> "ValidationResult":
        """Create success result."""
        return cls(is_valid=True, errors=[])

    @classmethod
    def error(cls, errors: List[str]) -> "ValidationResult":
        """Create error result."""
        return cls(is_valid=False, errors=errors or [])

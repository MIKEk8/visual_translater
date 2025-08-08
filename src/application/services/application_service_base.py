"""
Base application service.
"""

from abc import ABC


class ApplicationServiceBase(ABC):
    """Base class for application services."""

    def __init__(self):
        pass

    def validate_input(self, data: any) -> bool:
        """Validate input data."""
        return data is not None

    def handle_error(self, error: Exception) -> str:
        """Handle service errors."""
        return f"Service error: {str(error)}"

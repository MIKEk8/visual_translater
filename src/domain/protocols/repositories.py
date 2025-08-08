"""
Repository protocols - define interfaces for data access.
"""

from abc import abstractmethod
from typing import List, Optional, Protocol

from ..entities.screenshot import Screenshot
from ..entities.translation import Translation


class TranslationRepository(Protocol):
    """Translation repository protocol."""

    @abstractmethod
    async def save(self, translation: Translation) -> None:
        """Save translation."""
        ...

    @abstractmethod
    async def get_by_id(self, translation_id: str) -> Optional[Translation]:
        """Get translation by ID."""
        ...

    @abstractmethod
    async def get_recent(self, limit: int = 100) -> List[Translation]:
        """Get recent translations."""
        ...

    @abstractmethod
    async def search(self, text: str, limit: int = 50) -> List[Translation]:
        """Search translations by text."""
        ...

    @abstractmethod
    async def clear_all(self) -> int:
        """Clear all translations."""
        ...


class ScreenshotRepository(Protocol):
    """Screenshot repository protocol."""

    @abstractmethod
    async def save(self, screenshot: Screenshot) -> None:
        """Save screenshot."""
        ...

    @abstractmethod
    async def get_by_id(self, screenshot_id: str) -> Optional[Screenshot]:
        """Get screenshot by ID."""
        ...

    @abstractmethod
    async def get_recent(self, limit: int = 50) -> List[Screenshot]:
        """Get recent screenshots."""
        ...

    @abstractmethod
    async def delete_old(self, days: int = 7) -> int:
        """Delete old screenshots."""
        ...

"""
Repository layer for data access abstraction.

This package provides repository interfaces and implementations for
data persistence operations, following the Repository pattern.
"""

from .base_repository import BaseRepository
from .screenshot_repository import FileScreenshotRepository, ScreenshotRepository
from .translation_repository import FileTranslationRepository, TranslationRepository
from .unit_of_work import FileUnitOfWork, RepositoryManager, UnitOfWork, get_repository_manager

__all__ = [
    "BaseRepository",
    "TranslationRepository",
    "FileTranslationRepository",
    "ScreenshotRepository",
    "FileScreenshotRepository",
    "UnitOfWork",
    "FileUnitOfWork",
    "RepositoryManager",
    "get_repository_manager",
]

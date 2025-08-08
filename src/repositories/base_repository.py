"""
Base repository interface and common functionality.

This module provides the abstract base class for all repositories
and common repository operations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

# Generic type for entity
T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Abstract base repository class."""

    @abstractmethod
    async def save(self, entity: T) -> str:
        """
        Save an entity and return its ID.

        Args:
            entity: The entity to save

        Returns:
            The ID of the saved entity
        """

    @abstractmethod
    async def find_by_id(self, entity_id: str) -> Optional[T]:
        """
        Find an entity by its ID.

        Args:
            entity_id: The ID to search for

        Returns:
            The entity if found, None otherwise
        """

    @abstractmethod
    async def find_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """
        Find all entities with optional pagination.

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip

        Returns:
            List of entities
        """

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """
        Delete an entity by ID.

        Args:
            entity_id: The ID of the entity to delete

        Returns:
            True if deleted, False if not found
        """

    @abstractmethod
    async def exists(self, entity_id: str) -> bool:
        """
        Check if an entity exists by ID.

        Args:
            entity_id: The ID to check

        Returns:
            True if exists, False otherwise
        """

    @abstractmethod
    async def count(self) -> int:
        """
        Count total number of entities.

        Returns:
            Total count of entities
        """

    @abstractmethod
    async def search(self, criteria: Dict[str, Any]) -> List[T]:
        """
        Search entities by criteria.

        Args:
            criteria: Search criteria as key-value pairs

        Returns:
            List of matching entities
        """

    async def save_batch(self, entities: List[T]) -> List[str]:
        """
        Save multiple entities in batch.

        Args:
            entities: List of entities to save

        Returns:
            List of entity IDs
        """
        entity_ids = []
        for entity in entities:
            entity_id = await self.save(entity)
            entity_ids.append(entity_id)
        return entity_ids

    async def delete_batch(self, entity_ids: List[str]) -> int:
        """
        Delete multiple entities by IDs.

        Args:
            entity_ids: List of entity IDs to delete

        Returns:
            Number of entities actually deleted
        """
        deleted_count = 0
        for entity_id in entity_ids:
            if await self.delete(entity_id):
                deleted_count += 1
        return deleted_count

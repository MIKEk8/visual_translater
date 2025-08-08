"""
Unit of Work pattern implementation.

This module provides transaction management and coordination across multiple repositories.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.repositories.base_repository import BaseRepository
from src.repositories.screenshot_repository import FileScreenshotRepository, ScreenshotRepository
from src.repositories.translation_repository import FileTranslationRepository, TranslationRepository
from src.utils.logger import logger


class UnitOfWork(ABC):
    """Abstract Unit of Work for transaction management."""

    def __init__(self):
        self._repositories: Dict[str, BaseRepository] = {}
        self._new_entities: List[Any] = []
        self._modified_entities: List[Any] = []
        self._deleted_entities: List[Any] = []
        self._is_committed = False

    @abstractmethod
    async def commit(self) -> bool:
        """Commit all changes within the unit of work."""

    @abstractmethod
    async def rollback(self) -> bool:
        """Rollback all changes within the unit of work."""

    def register_new(self, entity: Any) -> None:
        """Register a new entity for insertion."""
        if entity not in self._new_entities:
            self._new_entities.append(entity)

    def register_modified(self, entity: Any) -> None:
        """Register an entity for update."""
        if entity not in self._modified_entities and entity not in self._new_entities:
            self._modified_entities.append(entity)

    def register_deleted(self, entity: Any) -> None:
        """Register an entity for deletion."""
        if entity not in self._deleted_entities:
            self._deleted_entities.append(entity)
            # Remove from new/modified if present
            if entity in self._new_entities:
                self._new_entities.remove(entity)
            if entity in self._modified_entities:
                self._modified_entities.remove(entity)

    def get_repository(self, repository_name: str) -> Optional[BaseRepository]:
        """Get repository by name."""
        return self._repositories.get(repository_name)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if exc_type is None and not self._is_committed:
            # Auto-commit if no exception and not manually committed
            await self.commit()
        elif exc_type is not None:
            # Rollback on exception
            await self.rollback()


class FileUnitOfWork(UnitOfWork):
    """File-based Unit of Work implementation."""

    def __init__(self, data_dir: str = "data"):
        super().__init__()
        self.data_dir = data_dir

        # Initialize repositories
        self.translations = FileTranslationRepository(data_dir)
        self.screenshots = FileScreenshotRepository(data_dir)

        # Register repositories
        self._repositories["translations"] = self.translations
        self._repositories["screenshots"] = self.screenshots

        # Track original states for rollback
        self._original_states: Dict[str, Any] = {}

    async def _backup_current_state(self) -> None:
        """Backup current repository states for rollback."""
        try:
            # Backup translations
            translations_stats = await self.translations.get_statistics()
            screenshots_stats = await self.screenshots.get_statistics()

            self._original_states = {
                "translations_count": translations_stats.get("total", 0),
                "screenshots_count": screenshots_stats.get("total", 0),
                "backup_timestamp": logger.get_timestamp(),
            }

            logger.debug("Backed up repository states for rollback")

        except Exception as e:
            logger.warning(f"Failed to backup repository states: {e}")

    async def commit(self) -> bool:
        """Commit all changes within the unit of work."""
        if self._is_committed:
            logger.warning("Unit of work already committed")
            return True

        try:
            # Backup current state before making changes
            await self._backup_current_state()

            # Process all registered changes
            success = await self._process_changes()

            if success:
                self._is_committed = True
                logger.info(
                    f"Unit of work committed successfully - "
                    f"New: {len(self._new_entities)}, "
                    f"Modified: {len(self._modified_entities)}, "
                    f"Deleted: {len(self._deleted_entities)}"
                )

                # Clear tracking lists
                self._clear_tracking_lists()
                return True
            else:
                await self.rollback()
                return False

        except Exception as e:
            logger.error(f"Failed to commit unit of work: {e}")
            await self.rollback()
            return False

    async def rollback(self) -> bool:
        """Rollback all changes within the unit of work."""
        try:
            logger.warning("Rolling back unit of work changes")

            # For file-based implementation, we can't easily rollback
            # individual operations, so we log the rollback attempt
            logger.info(
                "File-based repositories don't support atomic rollback. "
                "Changes may have been partially applied."
            )

            # Clear tracking lists
            self._clear_tracking_lists()

            return True

        except Exception as e:
            logger.error(f"Failed to rollback unit of work: {e}")
            return False

    async def _process_changes(self) -> bool:
        """Process all registered changes."""
        try:
            # Process new entities
            await self._process_entity_list(self._new_entities, "insertion", self._save_entity)

            # Process modified entities
            await self._process_entity_list(
                self._modified_entities, "modification", self._save_entity
            )

            # Process deleted entities
            await self._process_entity_list(self._deleted_entities, "deletion", self._delete_entity)

            return True

        except Exception as e:
            logger.error(f"Failed to process unit of work changes: {e}")
            return False

    async def _process_entity_list(self, entities: List[Any], operation: str, handler) -> None:
        """Process a list of entities with the given handler."""
        for entity in entities:
            if hasattr(entity, "__class__"):
                await handler(entity, operation)

    async def _save_entity(self, entity: Any, operation: str) -> None:
        """Save an entity to the appropriate repository."""
        entity_type = entity.__class__.__name__

        if entity_type == "Translation":
            await self.translations.save(entity)
        elif entity_type == "ScreenshotData":
            await self.screenshots.save(entity)
        else:
            logger.warning(f"Unknown entity type for {operation}: {entity_type}")

    async def _delete_entity(self, entity: Any, operation: str) -> None:
        """Delete an entity from the appropriate repository."""
        if not hasattr(entity, "id"):
            logger.warning(f"Entity missing ID for {operation}: {entity.__class__.__name__}")
            return

        entity_type = entity.__class__.__name__

        if entity_type == "Translation":
            await self.translations.delete(entity.id)
        elif entity_type == "ScreenshotData":
            await self.screenshots.delete(entity.id)
        else:
            logger.warning(f"Unknown entity type for {operation}: {entity_type}")

    def _clear_tracking_lists(self) -> None:
        """Clear all entity tracking lists."""
        self._new_entities.clear()
        self._modified_entities.clear()
        self._deleted_entities.clear()

    async def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics across all repositories."""
        try:
            translation_stats = await self.translations.get_statistics()
            screenshot_stats = await self.screenshots.get_statistics()

            return {
                "unit_of_work": {
                    "is_committed": self._is_committed,
                    "pending_new": len(self._new_entities),
                    "pending_modified": len(self._modified_entities),
                    "pending_deleted": len(self._deleted_entities),
                },
                "translations": translation_stats,
                "screenshots": screenshot_stats,
                "total_entities": translation_stats.get("total", 0)
                + screenshot_stats.get("total", 0),
            }

        except Exception as e:
            logger.error(f"Failed to get unit of work statistics: {e}")
            return {"error": str(e)}


class RepositoryManager:
    """Manager for repository instances and unit of work coordination."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self._unit_of_work: Optional[UnitOfWork] = None

    def create_unit_of_work(self) -> UnitOfWork:
        """Create a new unit of work instance."""
        return FileUnitOfWork(self.data_dir)

    def get_translation_repository(self) -> TranslationRepository:
        """Get translation repository instance."""
        if self._unit_of_work:
            return self._unit_of_work.get_repository("translations")
        return FileTranslationRepository(self.data_dir)

    def get_screenshot_repository(self) -> ScreenshotRepository:
        """Get screenshot repository instance."""
        if self._unit_of_work:
            return self._unit_of_work.get_repository("screenshots")
        return FileScreenshotRepository(self.data_dir)

    async def with_transaction(self, operation_func, *args, **kwargs) -> Any:
        """Execute operation within a transaction."""
        async with self.create_unit_of_work() as uow:
            self._unit_of_work = uow
            try:
                result = await operation_func(*args, **kwargs)
                return result
            finally:
                self._unit_of_work = None


# Singleton instance for global access
_repository_manager: Optional[RepositoryManager] = None


def get_repository_manager(data_dir: str = "data") -> RepositoryManager:
    """Get global repository manager instance."""
    global _repository_manager
    if _repository_manager is None:
        _repository_manager = RepositoryManager(data_dir)
    return _repository_manager

"""
Unit tests for repository implementations.
"""

import tempfile
from datetime import datetime

import pytest

from src.models.screenshot_data import ScreenshotData
from src.models.translation import Translation
from src.repositories import (
    FileScreenshotRepository,
    FileTranslationRepository,
    FileUnitOfWork,
    RepositoryManager,
)


class TestFileTranslationRepository:
    """Test FileTranslationRepository implementation."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def repository(self, temp_dir):
        """Create repository instance for testing."""
        return FileTranslationRepository(temp_dir)

    @pytest.fixture
    def sample_translation(self):
        """Create sample translation for testing."""
        return Translation(
            original_text="Hello world",
            translated_text="Hola mundo",
            source_language="en",
            target_language="es",
            confidence=0.95,
            cached=False,
        )

    @pytest.mark.asyncio
    async def test_save_translation(self, repository, sample_translation):
        """Test saving a translation."""
        # Save translation
        saved_id = await repository.save(sample_translation)

        # Verify ID is returned
        assert saved_id is not None

        # Verify translation can be retrieved
        retrieved = await repository.find_by_id(saved_id)
        assert retrieved is not None
        assert retrieved.original_text == sample_translation.original_text
        assert retrieved.translated_text == sample_translation.translated_text

    @pytest.mark.asyncio
    async def test_find_by_text(self, repository, sample_translation):
        """Test finding translation by text."""
        # Save translation
        await repository.save(sample_translation)

        # Find by text
        found = await repository.find_by_text("Hello world", "es")
        assert found is not None
        assert found.original_text == sample_translation.original_text

        # Test not found
        not_found = await repository.find_by_text("Nonexistent", "es")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_find_recent(self, repository):
        """Test finding recent translations."""
        # Create multiple translations
        translations = []
        for i in range(5):
            translation = Translation(
                original_text=f"Text {i}",
                translated_text=f"Translated {i}",
                source_language="en",
                target_language="es",
            )
            translations.append(translation)
            await repository.save(translation)

        # Find recent translations
        recent = await repository.find_recent(3)
        assert len(recent) == 3

        # Should be ordered by timestamp descending
        for i in range(len(recent) - 1):
            assert recent[i].timestamp >= recent[i + 1].timestamp

    @pytest.mark.asyncio
    async def test_search(self, repository, sample_translation):
        """Test searching translations."""
        # Save translation
        await repository.save(sample_translation)

        # Search by source language
        results = await repository.search({"source_language": "en"})
        assert len(results) == 1
        assert results[0].original_text == sample_translation.original_text

        # Search by cached status
        results = await repository.search({"cached": False})
        assert len(results) == 1

        # Search with no matches
        results = await repository.search({"source_language": "fr"})
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_delete(self, repository, sample_translation):
        """Test deleting translation."""
        # Save translation
        saved_id = await repository.save(sample_translation)

        # Verify exists
        assert await repository.exists(saved_id)

        # Delete
        deleted = await repository.delete(saved_id)
        assert deleted is True

        # Verify doesn't exist
        assert not await repository.exists(saved_id)

        # Try to delete non-existent
        deleted = await repository.delete("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_statistics(self, repository):
        """Test getting repository statistics."""
        # Initially empty
        stats = await repository.get_statistics()
        assert stats["total"] == 0

        # Add some translations
        for i in range(3):
            translation = Translation(
                original_text=f"Text {i}",
                translated_text=f"Translated {i}",
                source_language="en",
                target_language="es",
                cached=i % 2 == 0,  # Alternate cached status
            )
            await repository.save(translation)

        # Check statistics
        stats = await repository.get_statistics()
        assert stats["total"] == 3
        assert stats["cached"] == 2  # 2 out of 3 are cached
        assert "es" in stats["target_languages"]
        assert stats["target_languages"]["es"] == 3


class TestFileScreenshotRepository:
    """Test FileScreenshotRepository implementation."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def repository(self, temp_dir):
        """Create repository instance for testing."""
        return FileScreenshotRepository(temp_dir)

    @pytest.fixture
    def sample_screenshot(self):
        """Create sample screenshot for testing."""
        import io

        from PIL import Image

        # Create a fake PIL image
        fake_image = Image.new("RGB", (100, 100), color="white")
        image_buffer = io.BytesIO()
        fake_image.save(image_buffer, format="PNG")
        image_data = image_buffer.getvalue()

        return ScreenshotData(
            image=fake_image,
            image_data=image_data,
            coordinates=(100, 100, 200, 200),
            timestamp=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_save_screenshot(self, repository, sample_screenshot):
        """Test saving a screenshot."""
        # Save screenshot
        saved_id = await repository.save(sample_screenshot)

        # Verify ID is returned
        assert saved_id is not None

        # Verify screenshot can be retrieved
        retrieved = await repository.find_by_id(saved_id)
        assert retrieved is not None
        assert retrieved.coordinates == sample_screenshot.coordinates
        assert retrieved.image_data is not None  # Image should be saved

    @pytest.mark.asyncio
    async def test_find_by_coordinates(self, repository, sample_screenshot):
        """Test finding screenshot by coordinates."""
        # Save screenshot
        await repository.save(sample_screenshot)

        # Find by coordinates
        found = await repository.find_by_coordinates((100, 100, 200, 200))
        assert found is not None
        assert found.coordinates == sample_screenshot.coordinates

        # Test not found
        not_found = await repository.find_by_coordinates((0, 0, 50, 50))
        assert not_found is None

    @pytest.mark.asyncio
    async def test_search_by_size(self, repository):
        """Test searching screenshots by size range."""
        # Create screenshots with different sizes
        import io

        from PIL import Image

        # Small image
        small_image = Image.new("RGB", (50, 50), color="red")
        small_buffer = io.BytesIO()
        small_image.save(small_buffer, format="PNG")
        small_data = small_buffer.getvalue()

        # Large image
        large_image = Image.new("RGB", (200, 200), color="blue")
        large_buffer = io.BytesIO()
        large_image.save(large_buffer, format="PNG")
        large_data = large_buffer.getvalue()

        small_screenshot = ScreenshotData(
            image=small_image,
            image_data=small_data,
            coordinates=(0, 0, 50, 50),
            timestamp=datetime.now(),
        )
        large_screenshot = ScreenshotData(
            image=large_image,
            image_data=large_data,
            coordinates=(0, 0, 200, 200),
            timestamp=datetime.now(),
        )

        await repository.save(small_screenshot)
        await repository.save(large_screenshot)

        # Search by size range (by file size in bytes)
        # Large screenshot should have more bytes than small one
        large_size = len(large_screenshot.image_data)
        small_size = len(small_screenshot.image_data)

        # Find screenshots larger than small size but smaller than large size + buffer
        results = await repository.find_by_size_range(small_size + 1, large_size + 1000)
        assert len(results) == 1
        assert results[0].coordinates == large_screenshot.coordinates

    @pytest.mark.asyncio
    async def test_clear_all(self, repository, sample_screenshot):
        """Test clearing all screenshots."""
        # Save screenshot
        await repository.save(sample_screenshot)

        # Verify exists
        assert await repository.count() == 1

        # Clear all
        cleared_count = await repository.clear_all()
        assert cleared_count == 1
        assert await repository.count() == 0


class TestFileUnitOfWork:
    """Test FileUnitOfWork implementation."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def unit_of_work(self, temp_dir):
        """Create unit of work instance for testing."""
        return FileUnitOfWork(temp_dir)

    @pytest.fixture
    def sample_translation(self):
        """Create sample translation for testing."""
        return Translation(
            original_text="Test text",
            translated_text="Texto de prueba",
            source_language="en",
            target_language="es",
        )

    @pytest.mark.asyncio
    async def test_unit_of_work_context_manager(self, unit_of_work, sample_translation):
        """Test unit of work as context manager."""
        # Use as context manager
        async with unit_of_work as uow:
            # Register new entity
            uow.register_new(sample_translation)

            # Should not be committed yet
            assert not uow._is_committed

        # Should be auto-committed after context exit
        assert unit_of_work._is_committed

        # Verify translation was saved
        saved_translation = await unit_of_work.translations.find_by_text("Test text", "es")
        assert saved_translation is not None

    @pytest.mark.asyncio
    async def test_manual_commit(self, unit_of_work, sample_translation):
        """Test manual commit of unit of work."""
        # Register new entity
        unit_of_work.register_new(sample_translation)

        # Manual commit
        success = await unit_of_work.commit()
        assert success is True
        assert unit_of_work._is_committed

        # Verify translation was saved
        saved_translation = await unit_of_work.translations.find_by_text("Test text", "es")
        assert saved_translation is not None

    @pytest.mark.asyncio
    async def test_rollback(self, unit_of_work, sample_translation):
        """Test rollback functionality."""
        # Register new entity
        unit_of_work.register_new(sample_translation)

        # Rollback
        success = await unit_of_work.rollback()
        assert success is True

        # Tracking lists should be cleared
        assert len(unit_of_work._new_entities) == 0
        assert len(unit_of_work._modified_entities) == 0
        assert len(unit_of_work._deleted_entities) == 0

    @pytest.mark.asyncio
    async def test_get_statistics(self, unit_of_work, sample_translation):
        """Test getting unit of work statistics."""
        # Initial statistics
        stats = await unit_of_work.get_statistics()
        assert stats["unit_of_work"]["pending_new"] == 0
        assert stats["total_entities"] == 0

        # Register entities
        unit_of_work.register_new(sample_translation)

        # Check pending statistics
        stats = await unit_of_work.get_statistics()
        assert stats["unit_of_work"]["pending_new"] == 1
        assert not stats["unit_of_work"]["is_committed"]


class TestRepositoryManager:
    """Test RepositoryManager functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def manager(self, temp_dir):
        """Create repository manager for testing."""
        return RepositoryManager(temp_dir)

    def test_create_unit_of_work(self, manager):
        """Test creating unit of work."""
        uow = manager.create_unit_of_work()
        assert isinstance(uow, FileUnitOfWork)
        assert uow.data_dir == manager.data_dir

    def test_get_repositories(self, manager):
        """Test getting repository instances."""
        translation_repo = manager.get_translation_repository()
        screenshot_repo = manager.get_screenshot_repository()

        assert isinstance(translation_repo, FileTranslationRepository)
        assert isinstance(screenshot_repo, FileScreenshotRepository)

    @pytest.mark.asyncio
    async def test_with_transaction(self, manager):
        """Test transaction execution."""
        sample_translation = Translation(
            original_text="Transaction test",
            translated_text="Prueba de transacción",
            source_language="en",
            target_language="es",
        )

        async def save_translation():
            repo = manager.get_translation_repository()
            return await repo.save(sample_translation)

        # Execute within transaction
        result = await manager.with_transaction(save_translation)
        assert result is not None

        # Verify translation was saved
        repo = manager.get_translation_repository()
        saved = await repo.find_by_id(result)
        assert saved is not None

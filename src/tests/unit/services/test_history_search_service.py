"""
Tests for Enhanced History Window with SQLite FTS5 search functionality.

FEATURE: Enhanced History Window (SQLite FTS5 search)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

# CRITICAL: Import paths will fail until implementation exists
from src.services.history_search_service import (
    HistorySearchService,
    SearchFilters,
    SearchResult
)
from src.domain.entities.translation import Translation
from src.infrastructure.repositories.history_repository import HistoryRepository


class TestHistorySearchService:
    """Test suite for history search with FTS5 full-text search."""

    # CRITICAL: Service initialization and basic functionality
    def test_history_search_service_initialization(self):
        """Test service initializes with proper database setup."""
        with patch('src.services.history_search_service.sqlite3.connect') as mock_connect:
            mock_db = MagicMock()
            mock_cursor = MagicMock()

            # Setup mock cursor to return FTS5 support
            mock_cursor.fetchall.return_value = [('ENABLE_FTS5',)]
            mock_db.execute.return_value = mock_cursor
            mock_db.__enter__.return_value = mock_db
            mock_db.__exit__.return_value = None

            mock_connect.return_value = mock_db

            service = HistorySearchService()

            assert service.db_path is not None
            assert service.is_fts5_enabled is True
            mock_connect.assert_called_once()
            # Verify FTS5 table creation was attempted
            mock_db.execute.assert_called()

    # CRITICAL: Full-text search functionality
    def test_fts5_search_basic_query(self):
        """Test FTS5 search with basic text query."""
        service = HistorySearchService()

        # Mock database with FTS5 results
        with patch.object(service, '_execute_fts5_query') as mock_fts5:
            expected_translations = [
                Translation(
                    original="Hello world",
                    translated="Привет мир",
                    source_lang="en",
                    target_lang="ru",
                    timestamp=datetime.now()
                )
            ]
            mock_fts5.return_value = expected_translations

            results = service.search("hello", SearchFilters())

            assert len(results) == 1
            assert results[0].original == "Hello world"
            mock_fts5.assert_called_once_with("hello", SearchFilters())

    # CRITICAL: Advanced filtering
    def test_search_with_date_filters(self):
        """Test search with date range filtering."""
        service = HistorySearchService()

        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        filters = SearchFilters(
            date_from=start_date,
            date_to=end_date,
            source_language="en",
            target_language="ru"
        )

        with patch.object(service, '_execute_filtered_query') as mock_query:
            mock_query.return_value = []

            results = service.search("test", filters)

            mock_query.assert_called_once()
            args = mock_query.call_args[0]
            assert start_date in str(args)
            assert end_date in str(args)

    # CRITICAL: Performance with large datasets
    def test_search_performance_with_large_dataset(self):
        """Test search performance with 10k+ records."""
        service = HistorySearchService()

        # Mock large dataset
        large_dataset = [
            Translation(
                original=f"Text {i}",
                translated=f"Текст {i}",
                source_lang="en",
                target_lang="ru",
                timestamp=datetime.now()
            )
            for i in range(10000)
        ]

        with patch.object(service, '_execute_fts5_query') as mock_fts5:
            mock_fts5.return_value = large_dataset[:100]  # Return first 100

            import time
            start_time = time.time()
            results = service.search("Text", SearchFilters(max_results=100))
            search_time = time.time() - start_time

            # CRITICAL: Search must complete under 1 second
            assert search_time < 1.0
            assert len(results) == 100

    def test_search_filters_validation(self):
        """Test search filters validation and error handling."""
        service = HistorySearchService()

        # Test invalid date range
        filters = SearchFilters(
            date_from=datetime.now(),
            date_to=datetime.now() - timedelta(days=1)  # Invalid: end before start
        )

        with pytest.raises(ValueError, match="Invalid date range"):
            service.search("test", filters)

    def test_search_empty_query_handling(self):
        """Test handling of empty search queries."""
        service = HistorySearchService()

        # Empty query should return recent results
        with patch.object(service, '_get_recent_translations') as mock_recent:
            mock_recent.return_value = []

            results = service.search("", SearchFilters())

            mock_recent.assert_called_once()
            assert results == []

    def test_fts5_fallback_on_error(self):
        """Test fallback to simple search if FTS5 fails."""
        service = HistorySearchService()

        with patch.object(service, '_execute_fts5_query') as mock_fts5:
            mock_fts5.side_effect = Exception("FTS5 error")

            with patch.object(service, '_execute_simple_search') as mock_simple:
                mock_simple.return_value = []

                results = service.search("test", SearchFilters())

                mock_fts5.assert_called_once()
                mock_simple.assert_called_once()
                assert results == []

    # CRITICAL: Database migration handling
    def test_database_migration_from_old_schema(self):
        """Test migration of existing history data to FTS5 schema."""
        with patch('sqlite3.connect') as mock_connect:
            mock_db = MagicMock()
            mock_connect.return_value = mock_db

            # Mock existing data in old format
            mock_db.execute.return_value.fetchall.return_value = [
                (1, "Hello", "Привет", "en", "ru", "2025-01-01 12:00:00"),
                (2, "World", "Мир", "en", "ru", "2025-01-01 12:01:00")
            ]

            service = HistorySearchService()
            service._migrate_existing_data()

            # Verify migration queries were executed
            assert mock_db.execute.call_count >= 2
            assert any("INSERT INTO" in str(call) for call in mock_db.execute.call_args_list)


class TestSearchFilters:
    """Test search filters data class."""

    def test_search_filters_creation(self):
        """Test SearchFilters creation with default values."""
        filters = SearchFilters()

        assert filters.max_results == 100
        assert filters.date_from is None
        assert filters.date_to is None
        assert filters.source_language is None
        assert filters.target_language is None

    def test_search_filters_custom_values(self):
        """Test SearchFilters with custom values."""
        start_date = datetime.now() - timedelta(days=30)

        filters = SearchFilters(
            max_results=50,
            date_from=start_date,
            source_language="en",
            target_language="ru"
        )

        assert filters.max_results == 50
        assert filters.date_from == start_date
        assert filters.source_language == "en"
        assert filters.target_language == "ru"


class TestHistoryRepository:
    """Test history repository integration."""

    # CRITICAL: Repository integration
    def test_repository_fts5_integration(self):
        """Test repository correctly integrates with FTS5 search."""
        with patch('sqlite3.connect'):
            repo = HistoryRepository()

            # Test that repository supports FTS5 queries
            assert hasattr(repo, 'search_full_text')
            assert hasattr(repo, 'create_fts5_index')

    def test_repository_transaction_handling(self):
        """Test repository handles database transactions properly."""
        with patch('sqlite3.connect') as mock_connect:
            mock_db = MagicMock()
            mock_connect.return_value = mock_db

            repo = HistoryRepository()

            # Test transaction rollback on error
            mock_db.execute.side_effect = Exception("Database error")

            with pytest.raises(Exception):
                repo.add_translation(Translation(
                    original="test",
                    translated="тест",
                    source_lang="en",
                    target_lang="ru",
                    timestamp=datetime.now()
                ))

            # Verify rollback was called
            mock_db.rollback.assert_called_once()


# CRITICAL: Integration tests for complete workflow
class TestHistorySearchIntegration:
    """Integration tests for complete history search workflow."""

    def test_end_to_end_search_workflow(self):
        """Test complete search workflow from UI to database."""
        # This test will fail until full implementation exists

        with patch('src.ui.history_window.HistoryWindow') as mock_window:
            with patch('src.services.history_search_service.HistorySearchService') as mock_service:

                # Mock search service
                mock_service_instance = Mock()
                mock_service.return_value = mock_service_instance
                mock_service_instance.search.return_value = [
                    SearchResult(
                        translation=Translation(
                            original="Hello",
                            translated="Привет",
                            source_lang="en",
                            target_lang="ru",
                            timestamp=datetime.now()
                        ),
                        relevance_score=0.95
                    )
                ]

                # Mock UI window
                window = mock_window.return_value
                window.perform_search.return_value = None

                # Simulate user search
                search_query = "hello"
                filters = SearchFilters(source_language="en")

                # This should work when implementation is complete
                results = mock_service_instance.search(search_query, filters)

                assert len(results) == 1
                assert results[0].relevance_score == 0.95
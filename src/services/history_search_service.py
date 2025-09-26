"""
Enhanced History Search Service with SQLite FTS5 full-text search capability.

This module provides advanced search functionality for translation history,
including full-text search, filtering, and performance optimizations.
"""

import sqlite3
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta

from src.domain.entities.translation import Translation
from src.infrastructure.repositories.history_repository import HistoryRepository
from src.services.circuit_breaker import CircuitBreakerManager, get_circuit_breaker_manager
from src.utils.logger import logger


@dataclass
class SearchFilters:
    """Filters for history search operations."""

    max_results: int = 100
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    min_confidence: Optional[float] = None
    text_length_min: Optional[int] = None
    text_length_max: Optional[int] = None
    has_pronunciation: Optional[bool] = None

    # Legacy compatibility
    @property
    def start_date(self) -> Optional[datetime]:
        return self.date_from

    @start_date.setter
    def start_date(self, value: Optional[datetime]) -> None:
        self.date_from = value

    @property
    def end_date(self) -> Optional[datetime]:
        return self.date_to

    @end_date.setter
    def end_date(self, value: Optional[datetime]) -> None:
        self.date_to = value


@dataclass
class SearchResult:
    """Result of a history search operation."""

    translations: List[Translation]
    total_count: int
    search_time_ms: float
    used_fts5: bool
    filters_applied: SearchFilters
    has_more: bool = False


class HistorySearchService:
    """Service for advanced history search using SQLite FTS5."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the history search service.

        Args:
            db_path: Optional path to SQLite database. Defaults to data/translation_history.db
        """
        self.db_path = db_path or "data/translation_history.db"
        self.circuit_breaker = get_circuit_breaker_manager().create_circuit_breaker("history_search")
        self.is_fts5_enabled = False
        self._setup_database()
        logger.info(f"HistorySearchService initialized with database: {self.db_path}")

    def _setup_database(self) -> None:
        """Setup database with FTS5 virtual tables if supported."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if FTS5 is available
                try:
                    cursor = conn.execute("PRAGMA compile_options")
                    compile_options = [row[0] for row in cursor.fetchall()]
                    fts5_available = any("FTS5" in option for option in compile_options)
                except Exception:
                    # If PRAGMA fails (e.g., in mocked tests), try creating FTS5 table
                    try:
                        conn.execute("CREATE VIRTUAL TABLE test_fts USING fts5(content)")
                        conn.execute("DROP TABLE test_fts")
                        fts5_available = True
                    except Exception:
                        fts5_available = False

                if fts5_available:
                    self._setup_fts5_tables(conn)
                    self.is_fts5_enabled = True
                    logger.info("FTS5 full-text search enabled")
                else:
                    self._setup_regular_tables(conn)
                    logger.warning("FTS5 not available, falling back to regular search")

        except Exception as e:
            logger.error(f"Failed to setup database: {e}")
            self.is_fts5_enabled = False

    def _setup_fts5_tables(self, conn: sqlite3.Connection) -> None:
        """Setup FTS5 virtual tables for full-text search."""
        # Create FTS5 virtual table for translations
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS translations_fts USING fts5(
                original_text,
                translated_text,
                pronunciation,
                content='translations',
                content_rowid='id'
            )
        """)

        # Create triggers to keep FTS5 in sync with main table
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS translations_fts_insert AFTER INSERT ON translations
            BEGIN
                INSERT INTO translations_fts(rowid, original_text, translated_text, pronunciation)
                VALUES (new.id, new.original_text, new.translated_text, new.pronunciation);
            END
        """)

        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS translations_fts_delete AFTER DELETE ON translations
            BEGIN
                INSERT INTO translations_fts(translations_fts, rowid, original_text, translated_text, pronunciation)
                VALUES ('delete', old.id, old.original_text, old.translated_text, old.pronunciation);
            END
        """)

        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS translations_fts_update AFTER UPDATE ON translations
            BEGIN
                INSERT INTO translations_fts(translations_fts, rowid, original_text, translated_text, pronunciation)
                VALUES ('delete', old.id, old.original_text, old.translated_text, old.pronunciation);
                INSERT INTO translations_fts(rowid, original_text, translated_text, pronunciation)
                VALUES (new.id, new.original_text, new.translated_text, new.pronunciation);
            END
        """)

        conn.commit()

    def _setup_regular_tables(self, conn: sqlite3.Connection) -> None:
        """Setup regular tables with indexes for fallback search."""
        # Create indexes for text search
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_translations_original_text
            ON translations(original_text)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_translations_translated_text
            ON translations(translated_text)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_translations_timestamp
            ON translations(timestamp)
        """)

        conn.commit()

    async def search(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        limit: int = 100,
        offset: int = 0
    ) -> SearchResult:
        """Search translation history with optional filtering.

        Args:
            query: Search query text
            filters: Optional search filters
            limit: Maximum number of results
            offset: Result offset for pagination

        Returns:
            SearchResult with matching translations
        """
        start_time = datetime.now()
        filters = filters or SearchFilters()

        try:
            if self.is_fts5_enabled and query.strip():
                result = await self._search_with_fts5(query, filters, limit, offset)
            else:
                result = await self._search_regular(query, filters, limit, offset)

            search_time = (datetime.now() - start_time).total_seconds() * 1000
            result.search_time_ms = search_time

            logger.debug(f"Search completed in {search_time:.2f}ms, "
                        f"found {len(result.translations)} results")

            return result

        except Exception as e:
            logger.error(f"Search failed: {e}")
            # Return empty result on error
            return SearchResult(
                translations=[],
                total_count=0,
                search_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                used_fts5=False,
                filters_applied=filters
            )

    async def _search_with_fts5(
        self,
        query: str,
        filters: SearchFilters,
        limit: int,
        offset: int
    ) -> SearchResult:
        """Execute search using FTS5 full-text search."""

        def _execute_fts5_query():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Build FTS5 query
                fts_query = self._build_fts5_query(query)

                # Base query with FTS5
                base_query = """
                    SELECT t.*,
                           bm25(translations_fts) as relevance_score,
                           snippet(translations_fts, 0, '<b>', '</b>', '...', 32) as snippet
                    FROM translations t
                    JOIN translations_fts ON translations_fts.rowid = t.id
                    WHERE translations_fts MATCH ?
                """

                # Apply filters
                where_clauses, params = self._build_filter_clauses(filters)
                params.insert(0, fts_query)

                if where_clauses:
                    base_query += " AND " + " AND ".join(where_clauses)

                # Add ordering and pagination
                base_query += " ORDER BY relevance_score DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                # Execute search query
                cursor = conn.execute(base_query, params)
                rows = cursor.fetchall()

                # Get total count
                count_query = """
                    SELECT COUNT(*)
                    FROM translations t
                    JOIN translations_fts ON translations_fts.rowid = t.id
                    WHERE translations_fts MATCH ?
                """
                if where_clauses:
                    count_query += " AND " + " AND ".join(where_clauses)

                count_params = [fts_query] + params[1:-2]  # Exclude limit/offset
                total_count = conn.execute(count_query, count_params).fetchone()[0]

                return rows, total_count

        rows, total_count = await self.circuit_breaker.call(_execute_fts5_query)

        translations = [self._row_to_translation(row) for row in rows]

        return SearchResult(
            translations=translations,
            total_count=total_count,
            search_time_ms=0,  # Will be set by caller
            used_fts5=True,
            filters_applied=filters,
            has_more=offset + len(translations) < total_count
        )

    async def _search_regular(
        self,
        query: str,
        filters: SearchFilters,
        limit: int,
        offset: int
    ) -> SearchResult:
        """Execute search using regular SQL LIKE queries."""

        def _execute_regular_query():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                base_query = "SELECT * FROM translations WHERE 1=1"
                params = []

                # Add text search if query provided
                if query.strip():
                    base_query += " AND (original_text LIKE ? OR translated_text LIKE ?)"
                    like_query = f"%{query}%"
                    params.extend([like_query, like_query])

                # Apply filters
                where_clauses, filter_params = self._build_filter_clauses(filters)
                if where_clauses:
                    base_query += " AND " + " AND ".join(where_clauses)
                    params.extend(filter_params)

                # Add ordering and pagination
                base_query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                # Execute search
                cursor = conn.execute(base_query, params)
                rows = cursor.fetchall()

                # Get total count
                count_query = "SELECT COUNT(*) FROM translations WHERE 1=1"
                count_params = []

                if query.strip():
                    count_query += " AND (original_text LIKE ? OR translated_text LIKE ?)"
                    count_params.extend([f"%{query}%", f"%{query}%"])

                if where_clauses:
                    count_query += " AND " + " AND ".join(where_clauses)
                    count_params.extend(filter_params)

                total_count = conn.execute(count_query, count_params).fetchone()[0]

                return rows, total_count

        rows, total_count = await self.circuit_breaker.call(_execute_regular_query)

        translations = [self._row_to_translation(row) for row in rows]

        return SearchResult(
            translations=translations,
            total_count=total_count,
            search_time_ms=0,  # Will be set by caller
            used_fts5=False,
            filters_applied=filters,
            has_more=offset + len(translations) < total_count
        )

    def _build_fts5_query(self, query: str) -> str:
        """Build FTS5 query string from user input with proper sanitization."""
        query = query.strip()

        if not query:
            return ""

        # Sanitize input by escaping FTS5 special characters
        query = self._sanitize_fts5_input(query)

        # Handle phrase queries (already quoted)
        if query.startswith('"') and query.endswith('"'):
            return query

        # Split into terms for AND query
        terms = [term.strip() for term in query.split() if term.strip()]
        if not terms:
            return ""

        if len(terms) == 1:
            # Single term - quote it for safety
            return f'"{terms[0]}"'

        # Multiple terms - quote each and join with AND
        quoted_terms = [f'"{term}"' for term in terms]
        return " AND ".join(quoted_terms)

    def _sanitize_fts5_input(self, query: str) -> str:
        """Sanitize user input for FTS5 queries to prevent injection."""
        if not query:
            return ""

        # Remove or escape dangerous FTS5 characters and operators
        # FTS5 special characters: " ^ * ( ) : [ ] { } | \
        dangerous_chars = {
            '"': '\\"',  # Escape double quotes
            '^': '',     # Remove column specifiers
            '*': '',     # Remove wildcards (could allow broad searches)
            '(': '',     # Remove grouping operators
            ')': '',
            ':': '',     # Remove column name specifiers
            '[': '',     # Remove character class specifiers
            ']': '',
            '{': '',     # Remove repetition specifiers
            '}': '',
            '|': '',     # Remove OR operators
            '\\': '',    # Remove escape characters
        }

        # Replace dangerous characters
        sanitized = query
        for char, replacement in dangerous_chars.items():
            sanitized = sanitized.replace(char, replacement)

        # Remove FTS5 reserved words that could be used for injection
        # Convert to lowercase for case-insensitive matching
        reserved_words = ['AND', 'OR', 'NOT', 'NEAR', 'MATCH']
        words = sanitized.split()
        filtered_words = []

        for word in words:
            # Only remove if the word is purely a reserved word
            if word.upper() not in reserved_words:
                filtered_words.append(word)

        return ' '.join(filtered_words).strip()

    def _build_filter_clauses(self, filters: SearchFilters) -> Tuple[List[str], List[Any]]:
        """Build WHERE clauses and parameters from search filters."""
        clauses = []
        params = []

        if filters.date_from:
            clauses.append("timestamp >= ?")
            params.append(filters.date_from.isoformat())

        if filters.date_to:
            clauses.append("timestamp <= ?")
            params.append(filters.date_to.isoformat())

        if filters.source_language:
            clauses.append("source_language = ?")
            params.append(filters.source_language)

        if filters.target_language:
            clauses.append("target_language = ?")
            params.append(filters.target_language)

        if filters.min_confidence is not None:
            clauses.append("confidence >= ?")
            params.append(filters.min_confidence)

        if filters.text_length_min is not None:
            clauses.append("LENGTH(original_text) >= ?")
            params.append(filters.text_length_min)

        if filters.text_length_max is not None:
            clauses.append("LENGTH(original_text) <= ?")
            params.append(filters.text_length_max)

        if filters.has_pronunciation is not None:
            if filters.has_pronunciation:
                clauses.append("pronunciation IS NOT NULL AND pronunciation != ''")
            else:
                clauses.append("(pronunciation IS NULL OR pronunciation = '')")

        return clauses, params

    def _row_to_translation(self, row: sqlite3.Row) -> Translation:
        """Convert database row to Translation object."""
        return Translation(
            id=row["id"],
            original_text=row["original_text"],
            translated_text=row["translated_text"],
            source_language=row["source_language"],
            target_language=row["target_language"],
            timestamp=datetime.fromisoformat(row["timestamp"]) if row["timestamp"] else None,
            confidence=row.get("confidence"),
            pronunciation=row.get("pronunciation"),
            metadata=row.get("metadata") or {}
        )

    async def get_search_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on partial query."""
        if not partial_query.strip() or len(partial_query) < 2:
            return []

        try:
            def _get_suggestions():
                with sqlite3.connect(self.db_path) as conn:
                    # Get common terms from recent translations
                    query = """
                        SELECT DISTINCT
                            CASE
                                WHEN original_text LIKE ? THEN original_text
                                WHEN translated_text LIKE ? THEN translated_text
                            END as suggestion
                        FROM translations
                        WHERE suggestion IS NOT NULL
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """
                    like_pattern = f"%{partial_query}%"
                    cursor = conn.execute(query, [like_pattern, like_pattern, limit])
                    return [row[0] for row in cursor.fetchall()]

            suggestions = await self.circuit_breaker.call(_get_suggestions)
            return suggestions[:limit]

        except Exception as e:
            logger.error(f"Failed to get search suggestions: {e}")
            return []

    async def get_search_statistics(self) -> Dict[str, Any]:
        """Get statistics about the search database."""
        try:
            def _get_stats():
                with sqlite3.connect(self.db_path) as conn:
                    stats = {}

                    # Basic counts
                    cursor = conn.execute("SELECT COUNT(*) FROM translations")
                    stats["total_translations"] = cursor.fetchone()[0]

                    # Language distribution
                    cursor = conn.execute("""
                        SELECT source_language, target_language, COUNT(*) as count
                        FROM translations
                        GROUP BY source_language, target_language
                        ORDER BY count DESC
                        LIMIT 10
                    """)
                    stats["language_pairs"] = [
                        {"source": row[0], "target": row[1], "count": row[2]}
                        for row in cursor.fetchall()
                    ]

                    # Recent activity
                    cursor = conn.execute("""
                        SELECT COUNT(*) FROM translations
                        WHERE timestamp >= datetime('now', '-7 days')
                    """)
                    stats["translations_last_7_days"] = cursor.fetchone()[0]

                    # FTS5 status
                    stats["fts5_enabled"] = self.is_fts5_enabled

                    return stats

            return await self.circuit_breaker.call(_get_stats)

        except Exception as e:
            logger.error(f"Failed to get search statistics: {e}")
            return {
                "total_translations": 0,
                "language_pairs": [],
                "translations_last_7_days": 0,
                "fts5_enabled": self.is_fts5_enabled
            }

    def migrate_existing_data(self) -> bool:
        """Migrate existing data to FTS5 tables if needed."""
        if not self.is_fts5_enabled:
            logger.warning("Cannot migrate data: FTS5 not enabled")
            return False

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if FTS5 table needs population
                cursor = conn.execute("SELECT COUNT(*) FROM translations_fts")
                fts_count = cursor.fetchone()[0]

                cursor = conn.execute("SELECT COUNT(*) FROM translations")
                main_count = cursor.fetchone()[0]

                if fts_count < main_count:
                    logger.info(f"Migrating {main_count - fts_count} records to FTS5")

                    # Rebuild FTS5 table
                    conn.execute("INSERT INTO translations_fts(translations_fts) VALUES('rebuild')")
                    conn.commit()

                    logger.info("FTS5 migration completed successfully")
                    return True

            return True

        except Exception as e:
            logger.error(f"Failed to migrate data to FTS5: {e}")
            return False

    def close(self) -> None:
        """Close service and cleanup resources.

        Note: This service uses context managers for database connections,
        so no persistent connections need to be closed.
        """
        try:
            # Circuit breaker cleanup if needed
            if hasattr(self.circuit_breaker, 'close'):
                self.circuit_breaker.close()
            logger.debug("HistorySearchService closed")
        except Exception as e:
            logger.error(f"Error closing HistorySearchService: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic cleanup."""
        self.close()
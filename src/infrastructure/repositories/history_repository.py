"""
History Repository for managing translation history persistence.

This repository handles the data layer for translation history,
providing CRUD operations and database management.
"""

import sqlite3
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from src.domain.entities.translation import Translation
from src.utils.logger import logger


class HistoryRepository:
    """Repository for translation history operations."""

    def __init__(self, db_path: str = "data/translation_history.db"):
        """Initialize the history repository.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._ensure_database_exists()
        self._setup_tables()
        logger.debug(f"HistoryRepository initialized with database: {db_path}")

    def _ensure_database_exists(self) -> None:
        """Ensure the database directory and file exist."""
        db_path = Path(self.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create empty database file if it doesn't exist
        if not db_path.exists():
            db_path.touch()

    def _setup_tables(self) -> None:
        """Setup the translation history tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS translations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        original_text TEXT NOT NULL,
                        translated_text TEXT NOT NULL,
                        source_language TEXT,
                        target_language TEXT,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                        confidence REAL,
                        pronunciation TEXT,
                        metadata TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create indexes for performance
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_translations_timestamp
                    ON translations(timestamp)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_translations_languages
                    ON translations(source_language, target_language)
                """)

                conn.commit()
                logger.debug("Translation history tables created successfully")

        except Exception as e:
            logger.error(f"Failed to setup translation tables: {e}")
            raise

    async def save_translation(self, translation: Translation) -> Translation:
        """Save a translation to the history.

        Args:
            translation: Translation object to save

        Returns:
            Translation object with assigned ID
        """
        def _save():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO translations (
                        original_text, translated_text, source_language,
                        target_language, timestamp, confidence, pronunciation, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    translation.original_text,
                    translation.translated_text,
                    translation.source_language,
                    translation.target_language,
                    translation.timestamp.isoformat() if translation.timestamp else datetime.now().isoformat(),
                    translation.confidence,
                    translation.pronunciation,
                    str(translation.metadata) if translation.metadata else None
                ))

                translation.id = cursor.lastrowid
                conn.commit()
                return translation

        return await asyncio.get_event_loop().run_in_executor(None, _save)

    async def get_translation(self, translation_id: int) -> Optional[Translation]:
        """Get a translation by ID.

        Args:
            translation_id: ID of the translation to retrieve

        Returns:
            Translation object or None if not found
        """
        def _get():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM translations WHERE id = ?",
                    (translation_id,)
                )
                row = cursor.fetchone()
                return self._row_to_translation(row) if row else None

        return await asyncio.get_event_loop().run_in_executor(None, _get)

    async def get_recent_translations(self, limit: int = 100) -> List[Translation]:
        """Get recent translations from history.

        Args:
            limit: Maximum number of translations to return

        Returns:
            List of recent translations
        """
        def _get_recent():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM translations
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                return [self._row_to_translation(row) for row in rows]

        return await asyncio.get_event_loop().run_in_executor(None, _get_recent)

    async def delete_translation(self, translation_id: int) -> bool:
        """Delete a translation from history.

        Args:
            translation_id: ID of the translation to delete

        Returns:
            True if deleted, False if not found
        """
        def _delete():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM translations WHERE id = ?",
                    (translation_id,)
                )
                conn.commit()
                return cursor.rowcount > 0

        return await asyncio.get_event_loop().run_in_executor(None, _delete)

    async def update_translation(self, translation: Translation) -> bool:
        """Update an existing translation.

        Args:
            translation: Translation object to update

        Returns:
            True if updated, False if not found
        """
        def _update():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    UPDATE translations SET
                        original_text = ?, translated_text = ?, source_language = ?,
                        target_language = ?, confidence = ?, pronunciation = ?,
                        metadata = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    translation.original_text,
                    translation.translated_text,
                    translation.source_language,
                    translation.target_language,
                    translation.confidence,
                    translation.pronunciation,
                    str(translation.metadata) if translation.metadata else None,
                    translation.id
                ))
                conn.commit()
                return cursor.rowcount > 0

        return await asyncio.get_event_loop().run_in_executor(None, _update)

    async def clear_history(self, before_date: Optional[datetime] = None) -> int:
        """Clear translation history.

        Args:
            before_date: Optional date to clear history before

        Returns:
            Number of deleted records
        """
        def _clear():
            with sqlite3.connect(self.db_path) as conn:
                if before_date:
                    cursor = conn.execute(
                        "DELETE FROM translations WHERE timestamp < ?",
                        (before_date.isoformat(),)
                    )
                else:
                    cursor = conn.execute("DELETE FROM translations")
                conn.commit()
                return cursor.rowcount

        return await asyncio.get_event_loop().run_in_executor(None, _clear)

    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the translation history.

        Returns:
            Dictionary with various statistics
        """
        def _get_stats():
            with sqlite3.connect(self.db_path) as conn:
                stats = {}

                # Total count
                cursor = conn.execute("SELECT COUNT(*) FROM translations")
                stats["total_translations"] = cursor.fetchone()[0]

                # Language pairs
                cursor = conn.execute("""
                    SELECT source_language, target_language, COUNT(*) as count
                    FROM translations
                    WHERE source_language IS NOT NULL AND target_language IS NOT NULL
                    GROUP BY source_language, target_language
                    ORDER BY count DESC
                    LIMIT 10
                """)
                stats["language_pairs"] = [
                    {"source": row[0], "target": row[1], "count": row[2]}
                    for row in cursor.fetchall()
                ]

                # Date range
                cursor = conn.execute("""
                    SELECT MIN(timestamp), MAX(timestamp) FROM translations
                    WHERE timestamp IS NOT NULL
                """)
                result = cursor.fetchone()
                if result[0] and result[1]:
                    stats["date_range"] = {
                        "earliest": result[0],
                        "latest": result[1]
                    }

                return stats

        return await asyncio.get_event_loop().run_in_executor(None, _get_stats)

    def _row_to_translation(self, row: sqlite3.Row) -> Translation:
        """Convert database row to Translation object."""
        metadata = {}
        if row["metadata"]:
            try:
                import json
                # Safely parse JSON metadata instead of using eval()
                metadata = json.loads(row["metadata"])
            except (json.JSONDecodeError, TypeError):
                # Try ast.literal_eval as fallback for old format
                try:
                    import ast
                    metadata = ast.literal_eval(row["metadata"])
                except (ValueError, SyntaxError):
                    metadata = {}

        return Translation(
            id=row["id"],
            original_text=row["original_text"],
            translated_text=row["translated_text"],
            source_language=row["source_language"],
            target_language=row["target_language"],
            timestamp=datetime.fromisoformat(row["timestamp"]) if row["timestamp"] else None,
            confidence=row["confidence"],
            pronunciation=row["pronunciation"],
            metadata=metadata
        )

    def close(self) -> None:
        """Close the repository and cleanup resources."""
        # No persistent connections to close in this simple implementation
        logger.debug("HistoryRepository closed")
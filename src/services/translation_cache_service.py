"""Translation caching service for Screen Translator.

Implements a multi-layer caching system to reduce API calls and improve performance.
"""

import hashlib
import json
import sqlite3
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Any

from src.utils.logger import logger


@dataclass
class CachedTranslation:
    """Represents a cached translation result."""
    source_text: str
    translated_text: str
    source_language: str
    target_language: str
    provider: str
    confidence: float
    timestamp: float
    access_count: int = 1
    last_accessed: float = None

    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = time.time()


class TranslationCache:
    """Multi-layer translation caching system."""

    def __init__(self, cache_dir: str = "cache", max_memory_size: int = 1000):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        self.db_path = self.cache_dir / "translations.db"
        self.max_memory_size = max_memory_size

        # Memory cache (LRU-style)
        self.memory_cache: Dict[str, CachedTranslation] = {}
        self.cache_lock = threading.RLock()

        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "memory_hits": 0,
            "disk_hits": 0,
            "total_requests": 0,
            "cache_size": 0,
            "disk_cache_size": 0
        }

        self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite database for persistent caching."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS translations (
                        cache_key TEXT PRIMARY KEY,
                        source_text TEXT NOT NULL,
                        translated_text TEXT NOT NULL,
                        source_language TEXT NOT NULL,
                        target_language TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        timestamp REAL NOT NULL,
                        access_count INTEGER DEFAULT 1,
                        last_accessed REAL NOT NULL
                    )
                """)

                # Create indexes for better performance
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_source_target_lang
                    ON translations(source_language, target_language)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_last_accessed
                    ON translations(last_accessed)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_access_count
                    ON translations(access_count)
                """)

                conn.commit()

            logger.debug(f"Translation cache database initialized at {self.db_path}")
            self._update_disk_cache_size()

        except Exception as e:
            logger.error(f"Failed to initialize translation cache database: {e}")

    def _generate_cache_key(self, source_text: str, source_lang: str, target_lang: str, provider: str) -> str:
        """Generate a unique cache key for the translation request."""
        # Normalize text (strip whitespace, lowercase for consistent caching)
        normalized_text = source_text.strip().lower()

        # Create key from normalized inputs
        key_data = f"{normalized_text}|{source_lang}|{target_lang}|{provider}"

        # Use SHA-256 hash for consistent, collision-resistant keys
        return hashlib.sha256(key_data.encode('utf-8')).hexdigest()

    def get(self, source_text: str, source_lang: str, target_lang: str, provider: str) -> Optional[CachedTranslation]:
        """
        Retrieve cached translation if available.

        Returns:
            CachedTranslation object if found, None otherwise
        """
        with self.cache_lock:
            self.stats["total_requests"] += 1

            cache_key = self._generate_cache_key(source_text, source_lang, target_lang, provider)

            # Check memory cache first (fastest)
            if cache_key in self.memory_cache:
                cached = self.memory_cache[cache_key]
                cached.access_count += 1
                cached.last_accessed = time.time()

                self.stats["hits"] += 1
                self.stats["memory_hits"] += 1

                logger.debug(f"Translation cache HIT (memory): {len(source_text)} chars")
                return cached

            # Check disk cache (persistent)
            cached = self._get_from_disk(cache_key)
            if cached:
                # Update access statistics
                cached.access_count += 1
                cached.last_accessed = time.time()

                # Store in memory cache for faster future access
                self._add_to_memory_cache(cache_key, cached)

                # Update disk cache with new access stats
                self._update_disk_access_stats(cache_key, cached.access_count, cached.last_accessed)

                self.stats["hits"] += 1
                self.stats["disk_hits"] += 1

                logger.debug(f"Translation cache HIT (disk): {len(source_text)} chars")
                return cached

            # Cache miss
            self.stats["misses"] += 1
            logger.debug(f"Translation cache MISS: {len(source_text)} chars")
            return None

    def put(self, source_text: str, translated_text: str, source_lang: str, target_lang: str,
            provider: str, confidence: float = 1.0) -> None:
        """
        Store translation in cache.
        """
        with self.cache_lock:
            cache_key = self._generate_cache_key(source_text, source_lang, target_lang, provider)

            cached = CachedTranslation(
                source_text=source_text,
                translated_text=translated_text,
                source_language=source_lang,
                target_language=target_lang,
                provider=provider,
                confidence=confidence,
                timestamp=time.time()
            )

            # Store in memory cache
            self._add_to_memory_cache(cache_key, cached)

            # Store in disk cache for persistence
            self._add_to_disk_cache(cache_key, cached)

            logger.debug(f"Translation cached: {len(source_text)} chars -> {len(translated_text)} chars")

    def _add_to_memory_cache(self, cache_key: str, cached: CachedTranslation) -> None:
        """Add translation to memory cache with LRU eviction."""
        self.memory_cache[cache_key] = cached

        # Implement LRU eviction if cache is too large
        if len(self.memory_cache) > self.max_memory_size:
            # Find least recently used item
            lru_key = min(
                self.memory_cache.keys(),
                key=lambda k: self.memory_cache[k].last_accessed
            )
            del self.memory_cache[lru_key]
            logger.debug(f"Evicted LRU item from memory cache: {lru_key[:8]}...")

        self.stats["cache_size"] = len(self.memory_cache)

    def _add_to_disk_cache(self, cache_key: str, cached: CachedTranslation) -> None:
        """Add translation to persistent disk cache."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO translations
                    (cache_key, source_text, translated_text, source_language, target_language,
                     provider, confidence, timestamp, access_count, last_accessed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cache_key,
                    cached.source_text,
                    cached.translated_text,
                    cached.source_language,
                    cached.target_language,
                    cached.provider,
                    cached.confidence,
                    cached.timestamp,
                    cached.access_count,
                    cached.last_accessed
                ))
                conn.commit()

        except Exception as e:
            logger.error(f"Failed to store translation in disk cache: {e}")

    def _get_from_disk(self, cache_key: str) -> Optional[CachedTranslation]:
        """Retrieve translation from persistent disk cache."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT source_text, translated_text, source_language, target_language,
                           provider, confidence, timestamp, access_count, last_accessed
                    FROM translations
                    WHERE cache_key = ?
                """, (cache_key,))

                row = cursor.fetchone()
                if row:
                    return CachedTranslation(
                        source_text=row[0],
                        translated_text=row[1],
                        source_language=row[2],
                        target_language=row[3],
                        provider=row[4],
                        confidence=row[5],
                        timestamp=row[6],
                        access_count=row[7],
                        last_accessed=row[8]
                    )

        except Exception as e:
            logger.error(f"Failed to retrieve translation from disk cache: {e}")

        return None

    def _update_disk_access_stats(self, cache_key: str, access_count: int, last_accessed: float) -> None:
        """Update access statistics for disk cache entry."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE translations
                    SET access_count = ?, last_accessed = ?
                    WHERE cache_key = ?
                """, (access_count, last_accessed, cache_key))
                conn.commit()

        except Exception as e:
            logger.error(f"Failed to update disk cache access stats: {e}")

    def clear_memory_cache(self) -> None:
        """Clear the in-memory cache."""
        with self.cache_lock:
            self.memory_cache.clear()
            self.stats["cache_size"] = 0
            logger.info("Memory cache cleared")

    def clear_disk_cache(self) -> None:
        """Clear the persistent disk cache."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM translations")
                conn.commit()

            self.stats["disk_cache_size"] = 0
            logger.info("Disk cache cleared")

        except Exception as e:
            logger.error(f"Failed to clear disk cache: {e}")

    def clear_all(self) -> None:
        """Clear both memory and disk caches."""
        self.clear_memory_cache()
        self.clear_disk_cache()

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.cache_lock:
            # Update disk cache size
            self._update_disk_cache_size()

            # Calculate hit ratio
            total_requests = self.stats["total_requests"]
            hit_ratio = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0

            return {
                **self.stats,
                "hit_ratio_percent": round(hit_ratio, 2),
                "memory_cache_usage": f"{len(self.memory_cache)}/{self.max_memory_size}",
                "disk_cache_file": str(self.db_path),
                "disk_cache_size_mb": round(self.db_path.stat().st_size / (1024 * 1024), 2) if self.db_path.exists() else 0
            }

    def _update_disk_cache_size(self) -> None:
        """Update disk cache size statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM translations")
                self.stats["disk_cache_size"] = cursor.fetchone()[0]

        except Exception as e:
            logger.warning(f"Failed to update disk cache size: {e}")


# Global cache instance
_translation_cache: Optional[TranslationCache] = None
_cache_lock = threading.Lock()


def get_translation_cache() -> TranslationCache:
    """Get or create the global translation cache instance."""
    global _translation_cache

    if _translation_cache is None:
        with _cache_lock:
            if _translation_cache is None:
                _translation_cache = TranslationCache()

    return _translation_cache
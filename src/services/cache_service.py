import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.models.translation import Translation
from src.utils.logger import logger


class TranslationCache:
    """LRU Cache for translations with TTL support"""

    def __init__(self, max_size: int = 100, ttl_hours: int = 24):
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)
        self.cache: Dict[str, Dict] = {}
        self.access_order: List[str] = []
        self.hits = 0
        self.misses = 0

        logger.debug(f"Translation cache initialized: max_size={max_size}, ttl={ttl_hours}h")

    def _generate_key(self, text: str, target_language: str) -> str:
        """Generate cache key from text and target language"""
        # Normalize text for consistent caching
        normalized_text = text.strip().lower()
        content = f"{normalized_text}|{target_language}"
        return hashlib.md5(content.encode("utf-8"), usedforsecurity=False).hexdigest()

    def _is_expired(self, entry: Dict) -> bool:
        """Check if cache entry is expired"""
        return datetime.now() - entry["timestamp"] > self.ttl

    def _cleanup_expired(self) -> None:
        """Remove expired entries from cache"""
        current_time = datetime.now()
        expired_keys = [
            key for key, entry in self.cache.items() if current_time - entry["timestamp"] > self.ttl
        ]

        for key in expired_keys:
            self._remove_entry(key)

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    def _remove_entry(self, key: str) -> None:
        """Remove entry from cache and access order"""
        if key in self.cache:
            del self.cache[key]
        if key in self.access_order:
            self.access_order.remove(key)

    def _update_access_order(self, key: str) -> None:
        """Update LRU access order"""
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)

    def _evict_lru(self) -> None:
        """Evict least recently used entries to maintain max_size"""
        while len(self.cache) >= self.max_size and self.access_order:
            lru_key = self.access_order[0]
            self._remove_entry(lru_key)
            logger.debug(f"Evicted LRU cache entry: {lru_key}")

    def get(self, text: str, target_language: str) -> Optional[Translation]:
        """Get translation from cache"""
        if not text.strip():
            return None

        key = self._generate_key(text, target_language)

        # Cleanup expired entries periodically
        self._cleanup_expired()

        if key not in self.cache:
            self.misses += 1
            logger.debug(f"Cache miss for key: {key[:8]}...")
            return None

        entry = self.cache[key]

        if self._is_expired(entry):
            self._remove_entry(key)
            logger.debug(f"Cache entry expired: {key[:8]}...")
            return None

        # Update access order
        self._update_access_order(key)

        translation = entry["translation"]
        translation.cached = True

        self.hits += 1
        logger.debug(f"Cache hit for key: {key[:8]}...")
        return translation

    def set(self, text: str, target_language: str, translation: Translation) -> None:
        """Store translation in cache"""
        if not text.strip() or not translation.translated_text.strip():
            return

        key = self._generate_key(text, target_language)

        # Evict LRU entries if needed
        self._evict_lru()

        # Store the translation
        self.cache[key] = {"translation": translation, "timestamp": datetime.now()}

        # Update access order
        self._update_access_order(key)

        logger.debug(f"Cached translation for key: {key[:8]}...")

    def add(self, translation: Translation) -> None:
        """Add translation to cache (convenience method)"""
        self.set(translation.original_text, translation.target_language, translation)

    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()
        self.access_order.clear()
        logger.info("Translation cache cleared")

    def get_stats(self) -> Dict[str, any]:
        """Get cache statistics"""
        current_time = datetime.now()
        expired_count = sum(
            1 for entry in self.cache.values() if current_time - entry["timestamp"] > self.ttl
        )

        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

        return {
            "size": len(self.cache),
            "total_entries": len(self.cache),
            "expired_entries": expired_count,
            "active_entries": len(self.cache) - expired_count,
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "total_requests": total_requests,
        }

    def cleanup(self) -> int:
        """Manual cleanup of expired entries"""
        initial_count = len(self.cache)
        self._cleanup_expired()
        cleaned_count = initial_count - len(self.cache)

        if cleaned_count > 0:
            logger.info(f"Manual cleanup removed {cleaned_count} expired entries")

        return cleaned_count

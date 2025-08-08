"""
Cache integration for translation services.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from ...domain.entities.translation import Translation
from ...domain.value_objects.language import LanguagePair
from ...utils.logger import logger


class TranslationCacheIntegration:
    """Integration with translation cache system."""

    def __init__(self, cache_path: Optional[Path] = None, ttl_seconds: int = 3600):
        self.cache_path = cache_path or Path("cache/translations.json")
        self.cache_path.parent.mkdir(exist_ok=True)
        self.ttl_seconds = ttl_seconds

    def get_cache_key(self, text: str, language_pair: LanguagePair) -> str:
        """Generate cache key for translation."""
        cache_string = f"{text}:{language_pair.source.code}:{language_pair.target.code}"
        return hashlib.md5(cache_string.encode("utf-8")).hexdigest()

    def get_cached_translation(self, text: str, language_pair: LanguagePair) -> Optional[str]:
        """Get cached translation if available and not expired."""
        try:
            if not self.cache_path.exists():
                return None

            with open(self.cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            cache_key = self.get_cache_key(text, language_pair)

            if cache_key in cache_data:
                entry = cache_data[cache_key]

                # Check if entry is expired
                if time.time() - entry["timestamp"] < self.ttl_seconds:
                    logger.debug(f"Cache hit for translation: {cache_key}")
                    return entry["translation"]
                else:
                    logger.debug(f"Cache entry expired: {cache_key}")

            return None

        except Exception as e:
            logger.error(f"Cache retrieval failed: {e}")
            return None

    def cache_translation(self, text: str, language_pair: LanguagePair, translation: str) -> None:
        """Cache translation result."""
        try:
            cache_data = {}
            if self.cache_path.exists():
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)

            cache_key = self.get_cache_key(text, language_pair)

            cache_data[cache_key] = {
                "original": text,
                "translation": translation,
                "source_lang": language_pair.source.code,
                "target_lang": language_pair.target.code,
                "timestamp": time.time(),
            }

            # Clean up expired entries
            self._cleanup_expired_entries(cache_data)

            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            logger.debug(f"Translation cached: {cache_key}")

        except Exception as e:
            logger.error(f"Cache storage failed: {e}")

    def clear_cache(self) -> int:
        """Clear all cached translations."""
        try:
            if not self.cache_path.exists():
                return 0

            with open(self.cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            count = len(cache_data)

            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

            logger.info(f"Cache cleared: {count} entries removed")
            return count

        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return 0

    def _cleanup_expired_entries(self, cache_data: Dict[str, Any]) -> None:
        """Remove expired entries from cache data."""
        current_time = time.time()
        expired_keys = []

        for key, entry in cache_data.items():
            if current_time - entry["timestamp"] >= self.ttl_seconds:
                expired_keys.append(key)

        for key in expired_keys:
            del cache_data[key]

        if expired_keys:
            logger.debug(f"Removed {len(expired_keys)} expired cache entries")

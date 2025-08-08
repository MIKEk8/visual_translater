"""
Translation Cache Service - Screen Translator v2.0
Кэширование переводов для улучшения производительности
"""

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from src.utils.logger import logger


@dataclass
class CacheEntry:
    """Запись в кэше перевода"""

    text: str
    translation: str
    source_lang: str
    target_lang: str
    timestamp: datetime
    hit_count: int = 0

    def is_expired(self, ttl_seconds: int) -> bool:
        """Проверить, истек ли срок записи"""
        return datetime.now() - self.timestamp > timedelta(seconds=ttl_seconds)


class TranslationCache:
    """Кэш для переводов с LRU вытеснением и TTL"""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Инициализация кэша

        Args:
            max_size: Максимальный размер кэша
            ttl_seconds: Время жизни записи в секундах (по умолчанию 1 час)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0, "expirations": 0}

        logger.info(f"Translation cache initialized (max_size={max_size}, ttl={ttl_seconds}s)")

    def _generate_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """Генерировать ключ для кэша"""
        # Используем хэш для длинных текстов
        if len(text) > 100:
            text_hash = hashlib.md5(text.encode()).hexdigest()
            return f"{source_lang}:{target_lang}:{text_hash}"
        else:
            # Для коротких текстов используем сам текст
            return f"{source_lang}:{target_lang}:{text}"

    def get(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """
        Получить перевод из кэша

        Args:
            text: Исходный текст
            source_lang: Язык источника
            target_lang: Целевой язык

        Returns:
            Перевод или None, если не найден/истек
        """
        key = self._generate_key(text, source_lang, target_lang)

        if key in self._cache:
            entry = self._cache[key]

            # Проверка срока действия
            if entry.is_expired(self.ttl_seconds):
                self._cache.pop(key)
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                logger.debug(f"Cache entry expired for key: {key}")
                return None

            # Обновление позиции (LRU)
            self._cache.move_to_end(key)
            entry.hit_count += 1
            self._stats["hits"] += 1

            logger.debug(f"Cache hit for key: {key} (hits: {entry.hit_count})")
            return entry.translation

        self._stats["misses"] += 1
        return None

    def add(self, text: str, translation: str, source_lang: str, target_lang: str) -> None:
        """
        Добавить перевод в кэш

        Args:
            text: Исходный текст
            translation: Перевод
            source_lang: Язык источника
            target_lang: Целевой язык
        """
        key = self._generate_key(text, source_lang, target_lang)

        # Создание новой записи
        entry = CacheEntry(
            text=text,
            translation=translation,
            source_lang=source_lang,
            target_lang=target_lang,
            timestamp=datetime.now(),
        )

        # Добавление в кэш
        if key in self._cache:
            # Обновление существующей записи
            self._cache[key] = entry
            self._cache.move_to_end(key)
        else:
            # Проверка размера кэша
            if len(self._cache) >= self.max_size:
                # Удаление самой старой записи (LRU)
                oldest_key = next(iter(self._cache))
                self._cache.pop(oldest_key)
                self._stats["evictions"] += 1
                logger.debug(f"Evicted oldest cache entry: {oldest_key}")

            self._cache[key] = entry

        logger.debug(f"Added to cache: {key}")

    def clear(self) -> None:
        """Очистить весь кэш"""
        size = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared ({size} entries removed)")

    def get_stats(self) -> Dict[str, any]:
        """Получить статистику кэша"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": hit_rate,
            "evictions": self._stats["evictions"],
            "expirations": self._stats["expirations"],
            "ttl_seconds": self.ttl_seconds,
        }

    def cleanup_expired(self) -> int:
        """Удалить истекшие записи"""
        expired_keys = []

        for key, entry in self._cache.items():
            if entry.is_expired(self.ttl_seconds):
                expired_keys.append(key)

        for key in expired_keys:
            self._cache.pop(key)
            self._stats["expirations"] += 1

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)

    def get_most_used(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Получить наиболее используемые переводы"""
        sorted_entries = sorted(self._cache.items(), key=lambda x: x[1].hit_count, reverse=True)

        return [
            (f"{entry.text} -> {entry.translation}", entry.hit_count)
            for _, entry in sorted_entries[:limit]
        ]

    def save_to_file(self, filepath: str) -> None:
        """Сохранить кэш в файл"""
        cache_data = {
            "metadata": {
                "size": len(self._cache),
                "ttl_seconds": self.ttl_seconds,
                "saved_at": datetime.now().isoformat(),
            },
            "entries": [
                {
                    "text": entry.text,
                    "translation": entry.translation,
                    "source_lang": entry.source_lang,
                    "target_lang": entry.target_lang,
                    "timestamp": entry.timestamp.isoformat(),
                    "hit_count": entry.hit_count,
                }
                for entry in self._cache.values()
            ],
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Cache saved to {filepath} ({len(self._cache)} entries)")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def load_from_file(self, filepath: str) -> int:
        """Загрузить кэш из файла"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            self._cache.clear()
            loaded = 0

            for entry_data in cache_data.get("entries", []):
                try:
                    entry = CacheEntry(
                        text=entry_data["text"],
                        translation=entry_data["translation"],
                        source_lang=entry_data["source_lang"],
                        target_lang=entry_data["target_lang"],
                        timestamp=datetime.fromisoformat(entry_data["timestamp"]),
                        hit_count=entry_data.get("hit_count", 0),
                    )

                    # Проверка срока действия
                    if not entry.is_expired(self.ttl_seconds):
                        key = self._generate_key(entry.text, entry.source_lang, entry.target_lang)
                        self._cache[key] = entry
                        loaded += 1

                except Exception as e:
                    logger.warning(f"Failed to load cache entry: {e}")

            logger.info(f"Cache loaded from {filepath} ({loaded} entries)")
            return loaded

        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            return 0


# Глобальный экземпляр кэша
_translation_cache: Optional[TranslationCache] = None


def get_translation_cache() -> TranslationCache:
    """Получить глобальный экземпляр кэша переводов"""
    global _translation_cache
    if _translation_cache is None:
        _translation_cache = TranslationCache()
    return _translation_cache

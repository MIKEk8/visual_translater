"""
Translation repository implementations.

This module provides repository implementations for translation data persistence.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.models.translation import Translation
from src.repositories.base_repository import BaseRepository
from src.utils.logger import logger


class TranslationRepository(BaseRepository[Translation]):
    """Abstract repository for translation data."""

    async def find_by_text(self, text: str, target_lang: str) -> Optional[Translation]:
        """Find translation by original text and target language."""
        criteria = {"original_text": text, "target_language": target_lang}
        results = await self.search(criteria)
        return results[0] if results else None

    async def find_recent(self, limit: int = 100) -> List[Translation]:
        """Find recent translations ordered by timestamp."""
        all_translations = await self.find_all()
        # Sort by timestamp descending
        sorted_translations = sorted(all_translations, key=lambda t: t.timestamp, reverse=True)
        return sorted_translations[:limit]

    async def find_by_language_pair(self, source_lang: str, target_lang: str) -> List[Translation]:
        """Find translations for specific language pair."""
        criteria = {"source_language": source_lang, "target_language": target_lang}
        return await self.search(criteria)


class FileTranslationRepository(TranslationRepository):
    """File-based implementation of translation repository."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.translations_file = self.data_dir / "translations.json"
        self._cache: Dict[str, Translation] = {}
        self._load_data()

    def _load_data(self) -> None:
        """Load translations from file into cache."""
        try:
            if self.translations_file.exists():
                with open(self.translations_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for item in data.get("translations", []):
                    try:
                        translation = self._dict_to_translation(item)
                        self._cache[translation.id] = translation
                    except Exception as e:
                        logger.warning(f"Failed to load translation: {e}")

                logger.info(f"Loaded {len(self._cache)} translations from file")
            else:
                logger.info("No existing translations file found, starting fresh")

        except Exception as e:
            logger.error(f"Failed to load translations: {e}")
            self._cache = {}

    def _save_data(self) -> None:
        """Save translations from cache to file."""
        try:
            data = {
                "version": "2.0",
                "exported_at": datetime.now().isoformat(),
                "translations": [
                    self._translation_to_dict(translation) for translation in self._cache.values()
                ],
            }

            # Write to temp file first, then rename (atomic operation)
            temp_file = self.translations_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            temp_file.replace(self.translations_file)
            logger.debug(f"Saved {len(self._cache)} translations to file")

        except Exception as e:
            logger.error(f"Failed to save translations: {e}")

    def _translation_to_dict(self, translation: Translation) -> Dict[str, Any]:
        """Convert Translation object to dictionary."""
        return {
            "id": translation.id,
            "original_text": translation.original_text,
            "translated_text": translation.translated_text,
            "source_language": translation.source_language,
            "target_language": translation.target_language,
            "timestamp": translation.timestamp.isoformat(),
            "confidence": translation.confidence,
            "cached": translation.cached,
            "metadata": translation.metadata or {},
        }

    def _dict_to_translation(self, data: Dict[str, Any]) -> Translation:
        """Convert dictionary to Translation object."""
        return Translation(
            id=data.get("id", str(uuid4())),
            original_text=data["original_text"],
            translated_text=data["translated_text"],
            source_language=data.get("source_language", "auto"),
            target_language=data["target_language"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            confidence=data.get("confidence"),
            cached=data.get("cached", False),
            metadata=data.get("metadata", {}),
        )

    async def save(self, translation: Translation) -> str:
        """Save a translation."""
        if not translation.id:
            translation.id = str(uuid4())

        self._cache[translation.id] = translation
        self._save_data()

        logger.debug(f"Saved translation: {translation.id}")
        return translation.id

    async def find_by_id(self, translation_id: str) -> Optional[Translation]:
        """Find translation by ID."""
        return self._cache.get(translation_id)

    async def find_all(self, limit: Optional[int] = None, offset: int = 0) -> List[Translation]:
        """Find all translations with pagination."""
        translations = list(self._cache.values())

        # Sort by timestamp descending
        translations.sort(key=lambda t: t.timestamp, reverse=True)

        # Apply pagination
        start = offset
        end = start + limit if limit else None
        return translations[start:end]

    async def delete(self, translation_id: str) -> bool:
        """Delete a translation."""
        if translation_id in self._cache:
            del self._cache[translation_id]
            self._save_data()
            logger.debug(f"Deleted translation: {translation_id}")
            return True
        return False

    async def exists(self, translation_id: str) -> bool:
        """Check if translation exists."""
        return translation_id in self._cache

    async def count(self) -> int:
        """Count total translations."""
        return len(self._cache)

    async def search(self, criteria: Dict[str, Any]) -> List[Translation]:
        """Search translations by criteria."""
        results = []

        for translation in self._cache.values():
            if self._matches_criteria(translation, criteria):
                results.append(translation)

        # Sort by timestamp descending
        results.sort(key=lambda t: t.timestamp, reverse=True)
        return results

    def _matches_criteria(self, translation: Translation, criteria: Dict[str, Any]) -> bool:
        """Check if translation matches search criteria."""
        for key, value in criteria.items():
            if not self._check_field_match(translation, key, value):
                return False
        return True

    def _check_field_match(self, translation: Translation, field: str, value: Any) -> bool:
        """Check if a specific field matches the criteria value."""
        field_checkers = {
            "original_text": lambda t, v: v.lower() in t.original_text.lower(),
            "translated_text": lambda t, v: v.lower() in t.translated_text.lower(),
            "source_language": lambda t, v: t.source_language == v,
            "target_language": lambda t, v: t.target_language == v,
            "cached": lambda t, v: t.cached == v,
        }

        checker = field_checkers.get(field)
        if checker:
            return checker(translation, value)

        # For unknown fields, try direct attribute comparison
        return getattr(translation, field, None) == value

    async def clear_all(self) -> int:
        """Clear all translations."""
        count = len(self._cache)
        self._cache.clear()
        self._save_data()
        logger.info(f"Cleared {count} translations")
        return count

    async def get_statistics(self) -> Dict[str, Any]:
        """Get repository statistics."""
        if not self._cache:
            return {"total": 0}

        translations = list(self._cache.values())

        # Language statistics
        source_langs = {}
        target_langs = {}
        for t in translations:
            source_langs[t.source_language] = source_langs.get(t.source_language, 0) + 1
            target_langs[t.target_language] = target_langs.get(t.target_language, 0) + 1

        # Time-based statistics
        now = datetime.now()
        recent_count = len([t for t in translations if (now - t.timestamp).days <= 7])
        cached_count = len([t for t in translations if t.cached])

        return {
            "total": len(translations),
            "recent_week": recent_count,
            "cached": cached_count,
            "source_languages": source_langs,
            "target_languages": target_langs,
            "oldest": min(t.timestamp for t in translations),
            "newest": max(t.timestamp for t in translations),
        }

"""
Translation repository implementation.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ...domain.entities.translation import Translation
from ...domain.protocols.repositories import TranslationRepository
from ...domain.value_objects.language import Language, LanguagePair
from ...domain.value_objects.text import Text, TranslatedText
from .base_repository import BaseRepository


class JsonTranslationRepository(BaseRepository, TranslationRepository):
    """JSON-based translation repository."""

    def __init__(self, storage_path: Optional[Path] = None):
        super().__init__(storage_path)
        self._translations_file = "translations.json"

    async def save(self, translation: Translation) -> None:
        """Save translation to storage."""
        translations = self._load_translations()

        # Convert to dict for storage
        translation_dict = {
            "id": translation.id,
            "original": translation.original.content,
            "translated": translation.translated.content,
            "source_language": translation.language_pair.source.code,
            "target_language": translation.language_pair.target.code,
            "timestamp": translation.timestamp.isoformat(),
            "duration_ms": translation.duration_ms,
            "cached": translation.cached,
            "confidence": translation.confidence,
        }

        # Update existing or add new
        existing_index = None
        for i, existing in enumerate(translations):
            if existing.get("id") == translation.id:
                existing_index = i
                break

        if existing_index is not None:
            translations[existing_index] = translation_dict
        else:
            translations.append(translation_dict)

        # Keep only last 1000 translations
        if len(translations) > 1000:
            translations = translations[-1000:]

        self._save_to_json(self._translations_file, translations)

    async def get_by_id(self, translation_id: str) -> Optional[Translation]:
        """Get translation by ID."""
        translations = self._load_translations()

        for translation_dict in translations:
            if translation_dict.get("id") == translation_id:
                return self._dict_to_translation(translation_dict)

        return None

    async def get_recent(self, limit: int = 100) -> List[Translation]:
        """Get recent translations."""
        translations = self._load_translations()

        # Sort by timestamp (most recent first)
        sorted_translations = sorted(
            translations, key=lambda x: x.get("timestamp", ""), reverse=True
        )

        # Convert to entities
        result = []
        for translation_dict in sorted_translations[:limit]:
            try:
                translation = self._dict_to_translation(translation_dict)
                if translation:
                    result.append(translation)
            except Exception:
                continue  # Skip corrupted entries

        return result

    async def search(self, text: str, limit: int = 50) -> List[Translation]:
        """Search translations by text."""
        translations = self._load_translations()
        search_text = text.lower()

        matches = []
        for translation_dict in translations:
            original = translation_dict.get("original", "").lower()
            translated = translation_dict.get("translated", "").lower()

            if search_text in original or search_text in translated:
                try:
                    translation = self._dict_to_translation(translation_dict)
                    if translation:
                        matches.append(translation)
                except Exception:
                    continue

        # Sort by timestamp (most recent first)
        matches.sort(key=lambda x: x.timestamp, reverse=True)

        return matches[:limit]

    async def clear_all(self) -> int:
        """Clear all translations."""
        translations = self._load_translations()
        count = len(translations)

        self._save_to_json(self._translations_file, [])

        return count

    def _load_translations(self) -> List[dict]:
        """Load translations from storage."""
        return self._load_from_json(self._translations_file)

    def _dict_to_translation(self, translation_dict: dict) -> Optional[Translation]:
        """Convert dictionary to Translation entity."""
        try:
            # Parse timestamp
            timestamp_str = translation_dict.get("timestamp")
            timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.now()

            # Create language pair
            source_lang = Language(translation_dict["source_language"])
            target_lang = Language(translation_dict["target_language"])
            language_pair = LanguagePair(source_lang, target_lang)

            # Create texts
            original = Text(translation_dict["original"])
            confidence = translation_dict.get("confidence")
            translated = TranslatedText(translation_dict["translated"], confidence)

            # Create translation
            translation = Translation(
                id=translation_dict["id"],
                original=original,
                translated=translated,
                language_pair=language_pair,
                timestamp=timestamp,
                duration_ms=translation_dict.get("duration_ms"),
                cached=translation_dict.get("cached", False),
            )

            return translation

        except Exception as e:
            print(f"Error converting dict to Translation: {e}")
            return None

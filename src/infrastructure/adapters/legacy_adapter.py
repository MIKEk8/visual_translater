"""
Adapter for legacy system integration.
"""

from typing import Any, Dict, Optional

from ...core.application import ScreenTranslatorApp as LegacyApp
from ...domain.entities.screenshot import Screenshot
from ...domain.entities.translation import Translation
from ...domain.value_objects.coordinates import ScreenCoordinates
from ...domain.value_objects.language import Language, LanguagePair
from ...domain.value_objects.text import Text, TranslatedText
from ...utils.logger import logger


class LegacySystemAdapter:
    """Adapter to integrate with existing legacy system."""

    def __init__(self, legacy_app: Optional[LegacyApp] = None):
        self._legacy_app = legacy_app

    def convert_legacy_translation_to_entity(
        self, legacy_data: Dict[str, Any]
    ) -> Optional[Translation]:
        """Convert legacy translation data to domain entity."""
        try:
            # Extract data from legacy format
            original_text = legacy_data.get("original", "")
            translated_text = legacy_data.get("translated", "")
            source_lang = legacy_data.get("source_lang", "auto")
            target_lang = legacy_data.get("target_lang", "ru")

            if not original_text or not translated_text:
                return None

            # Create domain objects
            language_pair = LanguagePair(Language(source_lang), Language(target_lang))

            original = Text(original_text)
            translated = TranslatedText(translated_text)

            translation = Translation(
                original=original,
                translated=translated,
                language_pair=language_pair,
                cached=legacy_data.get("cached", False),
            )

            return translation

        except Exception as e:
            logger.error(f"Failed to convert legacy translation: {e}")
            return None

    def convert_entity_to_legacy_format(self, translation: Translation) -> Dict[str, Any]:
        """Convert domain entity to legacy format."""
        return {
            "original": translation.original.content,
            "translated": translation.translated.content,
            "source_lang": translation.language_pair.source.code,
            "target_lang": translation.language_pair.target.code,
            "cached": translation.cached,
            "confidence": translation.confidence,
            "timestamp": translation.timestamp.isoformat(),
        }

    def migrate_legacy_data(self) -> int:
        """Migrate data from legacy system."""
        if not self._legacy_app:
            return 0

        try:
            # This would extract data from legacy system
            # and convert it to new domain entities
            migrated_count = 0

            # Example: migrate translation cache
            if hasattr(self._legacy_app, "translation_cache"):
                cache = self._legacy_app.translation_cache
                for key, value in cache.items():
                    if isinstance(value, dict):
                        entity = self.convert_legacy_translation_to_entity(value)
                        if entity:
                            migrated_count += 1

            logger.info(f"Migrated {migrated_count} items from legacy system")
            return migrated_count

        except Exception as e:
            logger.error(f"Legacy migration failed: {e}")
            return 0

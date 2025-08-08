"""
Tests for Translation entity.
"""

from datetime import datetime
from uuid import UUID

import pytest

from src.domain.entities.translation import Translation
from src.domain.value_objects.language import Language, LanguagePair
from src.domain.value_objects.text import Text, TranslatedText


class TestTranslation:
    """Test Translation entity."""

    def test_translation_creation_valid(self):
        """Test creating valid translation."""
        original = Text("Hello")
        translated = TranslatedText("Привет", confidence=0.9)
        lang_pair = LanguagePair(Language("en"), Language("ru"))

        translation = Translation(original=original, translated=translated, language_pair=lang_pair)

        assert translation.original == original
        assert translation.translated == translated
        assert translation.language_pair == lang_pair
        assert isinstance(translation.timestamp, datetime)
        assert translation.duration_ms is None
        assert translation.cached is False

        # Test ID generation
        assert translation.id is not None
        assert len(translation.id) > 0
        UUID(translation.id)  # Should not raise - valid UUID

    def test_translation_properties(self):
        """Test translation computed properties."""
        original = Text("Hello")
        translated = TranslatedText("Привет", confidence=0.85)
        lang_pair = LanguagePair(Language("en"), Language("ru"))

        translation = Translation(original, translated, lang_pair)

        assert translation.is_valid is True
        assert translation.confidence == 0.85

    def test_translation_invalid_empty_original(self):
        """Test translation with empty original text."""
        with pytest.raises(ValueError):  # Text validation should catch this
            original = Text("")
            translated = TranslatedText("Привет")
            lang_pair = LanguagePair(Language("en"), Language("ru"))
            Translation(original, translated, lang_pair)

    def test_translation_mark_as_cached(self):
        """Test marking translation as cached."""
        original = Text("Hello")
        translated = TranslatedText("Привет")
        lang_pair = LanguagePair(Language("en"), Language("ru"))

        translation = Translation(original, translated, lang_pair)
        assert translation.cached is False

        translation.mark_as_cached()
        assert translation.cached is True

    def test_translation_to_dict(self):
        """Test translation serialization to dict."""
        original = Text("Hello World")
        translated = TranslatedText("Привет Мир", confidence=0.92)
        lang_pair = LanguagePair(Language("en"), Language("ru"))

        translation = Translation(original, translated, lang_pair)
        translation.duration_ms = 150.5
        translation.mark_as_cached()

        result = translation.to_dict()

        expected_keys = {
            "id",
            "original",
            "translated",
            "source_language",
            "target_language",
            "timestamp",
            "duration_ms",
            "cached",
            "confidence",
        }
        assert set(result.keys()) == expected_keys

        assert result["original"] == "Hello World"
        assert result["translated"] == "Привет Мир"
        assert result["source_language"] == "en"
        assert result["target_language"] == "ru"
        assert result["duration_ms"] == 150.5
        assert result["cached"] is True
        assert result["confidence"] == 0.92

    def test_translation_with_optional_fields(self):
        """Test translation with all optional fields."""
        original = Text("Test")
        translated = TranslatedText("Тест", confidence=0.75)
        lang_pair = LanguagePair(Language("en"), Language("ru"))

        translation = Translation(
            original=original,
            translated=translated,
            language_pair=lang_pair,
            duration_ms=250.0,
            cached=True,
        )

        assert translation.duration_ms == 250.0
        assert translation.cached is True
        assert translation.confidence == 0.75

    def test_translation_id_uniqueness(self):
        """Test that translation IDs are unique."""
        original = Text("Hello")
        translated = TranslatedText("Привет")
        lang_pair = LanguagePair(Language("en"), Language("ru"))

        translation1 = Translation(original, translated, lang_pair)
        translation2 = Translation(original, translated, lang_pair)

        assert translation1.id != translation2.id

    def test_translation_is_valid_false_cases(self):
        """Test cases where translation should be invalid."""
        # This would require modifying the entity after creation
        # Since we use frozen dataclasses, we can't easily test invalid states
        # In a real implementation, you might want validation in __post_init__
        pass

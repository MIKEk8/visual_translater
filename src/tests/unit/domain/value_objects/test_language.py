"""
Tests for Language value object.
"""

import pytest

from src.domain.value_objects.language import Language, LanguagePair


class TestLanguage:
    """Test Language value object."""

    def test_language_creation_valid(self):
        """Test creating valid language."""
        lang = Language("en")
        assert lang.code == "en"
        assert str(lang) == "en"

    def test_language_creation_invalid_empty(self):
        """Test creating language with empty code."""
        with pytest.raises(ValueError, match="Language code cannot be empty"):
            Language("")

    def test_language_creation_invalid_unsupported(self):
        """Test creating language with unsupported code."""
        with pytest.raises(ValueError, match="Unsupported language: xyz"):
            Language("xyz")

    def test_language_auto_detection(self):
        """Test auto language detection."""
        auto_lang = Language.auto()
        assert auto_lang.code == "auto"
        assert Language.is_auto("auto") is True
        assert Language.is_auto("en") is False

    def test_language_immutability(self):
        """Test that language is immutable."""
        lang = Language("en")
        with pytest.raises(AttributeError):
            lang.code = "ru"  # Should fail - frozen dataclass

    def test_supported_languages(self):
        """Test supported languages set."""
        assert "en" in Language.SUPPORTED
        assert "ru" in Language.SUPPORTED
        assert "ja" in Language.SUPPORTED
        assert "xyz" not in Language.SUPPORTED


class TestLanguagePair:
    """Test LanguagePair value object."""

    def test_language_pair_creation_valid(self):
        """Test creating valid language pair."""
        source = Language("en")
        target = Language("ru")
        pair = LanguagePair(source, target)

        assert pair.source == source
        assert pair.target == target
        assert str(pair) == "en → ru"

    def test_language_pair_same_languages_non_auto(self):
        """Test creating pair with same non-auto languages."""
        source = Language("en")
        target = Language("en")

        with pytest.raises(ValueError, match="Source and target languages must be different"):
            LanguagePair(source, target)

    def test_language_pair_auto_source_allowed(self):
        """Test that auto source with same target is allowed."""
        source = Language("auto")
        target = Language("auto")

        # This should work - auto detection allows same codes
        pair = LanguagePair(source, target)
        assert pair.source.code == "auto"
        assert pair.target.code == "auto"

    def test_language_pair_immutability(self):
        """Test that language pair is immutable."""
        pair = LanguagePair(Language("en"), Language("ru"))
        with pytest.raises(AttributeError):
            pair.source = Language("ja")  # Should fail - frozen dataclass

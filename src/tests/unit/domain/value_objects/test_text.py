"""
Tests for Text value objects.
"""

import pytest

from src.domain.value_objects.text import Text, TranslatedText


class TestText:
    """Test Text value object."""

    def test_text_creation_valid(self):
        """Test creating valid text."""
        text = Text("Hello World")
        assert text.content == "Hello World"
        assert text.length == 11
        assert str(text) == "Hello World"

    def test_text_creation_empty(self):
        """Test creating text with empty content."""
        with pytest.raises(ValueError, match="Text content cannot be empty"):
            Text("")

    def test_text_creation_too_long(self):
        """Test creating text that exceeds max length."""
        long_text = "x" * 5001
        with pytest.raises(ValueError, match="Text exceeds maximum length of 5000"):
            Text(long_text)

    def test_text_preview_short(self):
        """Test preview for short text."""
        text = Text("Short text")
        assert text.preview == "Short text"

    def test_text_preview_long(self):
        """Test preview for long text."""
        long_text = "This is a very long text that should be truncated in the preview"
        text = Text(long_text)
        assert text.preview == long_text[:47] + "..."
        assert len(text.preview) == 50

    def test_text_custom_max_length(self):
        """Test text with custom max length."""
        text = Text("Short", max_length=100)
        assert text.max_length == 100

    def test_text_immutability(self):
        """Test that text is immutable."""
        text = Text("Hello")
        with pytest.raises(AttributeError):
            text.content = "Modified"  # Should fail - frozen dataclass


class TestTranslatedText:
    """Test TranslatedText value object."""

    def test_translated_text_creation_valid(self):
        """Test creating valid translated text."""
        text = TranslatedText("Привет", confidence=0.95)
        assert text.content == "Привет"
        assert text.confidence == 0.95

    def test_translated_text_no_confidence(self):
        """Test creating translated text without confidence."""
        text = TranslatedText("Привет")
        assert text.content == "Привет"
        assert text.confidence is None

    def test_translated_text_invalid_confidence_low(self):
        """Test creating translated text with confidence too low."""
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            TranslatedText("Привет", confidence=-0.1)

    def test_translated_text_invalid_confidence_high(self):
        """Test creating translated text with confidence too high."""
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            TranslatedText("Привет", confidence=1.1)

    def test_translated_text_inherits_from_text(self):
        """Test that TranslatedText inherits Text properties."""
        text = TranslatedText("Привет Мир", confidence=0.9)
        assert text.length == 10  # Cyrillic text has 10 characters
        assert text.preview == "Привет Мир"

    def test_translated_text_empty_content(self):
        """Test that TranslatedText validates content like Text."""
        with pytest.raises(ValueError, match="Text content cannot be empty"):
            TranslatedText("", confidence=0.9)

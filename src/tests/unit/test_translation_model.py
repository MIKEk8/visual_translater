"""Unit tests for Translation model"""

import json
import unittest
from datetime import datetime

from src.models.translation import Translation


class TestTranslation(unittest.TestCase):
    """Test Translation data model"""

    def test_creation_minimal(self):
        """Test creating Translation with minimal required fields"""
        translation = Translation(
            original_text="Hello",
            translated_text="Привет",
            source_language="en",
            target_language="ru",
        )

        self.assertEqual(translation.original_text, "Hello")
        self.assertEqual(translation.translated_text, "Привет")
        self.assertEqual(translation.source_language, "en")
        self.assertEqual(translation.target_language, "ru")

        # Check defaults
        self.assertIsInstance(translation.timestamp, datetime)
        self.assertIsInstance(translation.id, str)
        self.assertIsNone(translation.confidence)
        self.assertFalse(translation.cached)
        self.assertEqual(translation.metadata, {})

    def test_creation_full(self):
        """Test creating Translation with all fields"""
        timestamp = datetime.now()
        metadata = {"model": "gpt-3", "version": "1.0"}

        translation = Translation(
            original_text="Hello world",
            translated_text="Привет мир",
            source_language="en",
            target_language="ru",
            id="custom-id-123",
            timestamp=timestamp,
            confidence=0.95,
            cached=True,
            metadata=metadata,
        )

        self.assertEqual(translation.original_text, "Hello world")
        self.assertEqual(translation.translated_text, "Привет мир")
        self.assertEqual(translation.source_language, "en")
        self.assertEqual(translation.target_language, "ru")
        self.assertEqual(translation.id, "custom-id-123")
        self.assertEqual(translation.timestamp, timestamp)
        self.assertEqual(translation.confidence, 0.95)
        self.assertTrue(translation.cached)
        self.assertEqual(translation.metadata, metadata)

    def test_to_dict(self):
        """Test conversion to dictionary"""
        translation = Translation(
            original_text="Test",
            translated_text="Тест",
            source_language="en",
            target_language="ru",
            confidence=0.88,
            cached=True,
        )

        result = translation.to_dict()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["original_text"], "Test")
        self.assertEqual(result["translated_text"], "Тест")
        self.assertEqual(result["source_language"], "en")
        self.assertEqual(result["target_language"], "ru")
        self.assertEqual(result["confidence"], 0.88)
        self.assertTrue(result["cached"])
        self.assertIn("timestamp", result)
        self.assertIn("id", result)
        self.assertIn("metadata", result)

    def test_from_dict(self):
        """Test creation from dictionary"""
        data = {
            "original_text": "Hello",
            "translated_text": "Hola",
            "source_language": "en",
            "target_language": "es",
            "timestamp": "2023-01-01T12:00:00",
            "confidence": 0.92,
            "cached": True,
            "metadata": {"key": "value"},
        }

        translation = Translation.from_dict(data)

        self.assertEqual(translation.original_text, "Hello")
        self.assertEqual(translation.translated_text, "Hola")
        self.assertEqual(translation.source_language, "en")
        self.assertEqual(translation.target_language, "es")
        self.assertIsInstance(translation.timestamp, datetime)
        self.assertEqual(translation.confidence, 0.92)
        self.assertTrue(translation.cached)
        self.assertEqual(translation.metadata, {"key": "value"})

    def test_from_dict_missing_optional(self):
        """Test creation from dictionary with missing optional fields"""
        data = {
            "original_text": "Test",
            "translated_text": "Prueba",
            "source_language": "en",
            "target_language": "es",
        }

        translation = Translation.from_dict(data)

        self.assertEqual(translation.original_text, "Test")
        self.assertEqual(translation.translated_text, "Prueba")
        self.assertIsNone(translation.confidence)
        self.assertFalse(translation.cached)
        self.assertEqual(translation.metadata, {})

    def test_from_dict_missing_required(self):
        """Test creation from dictionary with missing required fields"""
        data = {
            "original_text": "Test",
            "source_language": "en",
            # Missing translated_text and target_language
        }

        with self.assertRaises(KeyError):
            Translation.from_dict(data)

    def test_json_serialization(self):
        """Test JSON serialization/deserialization"""
        original = Translation(
            original_text="JSON test",
            translated_text="JSON тест",
            source_language="en",
            target_language="ru",
            confidence=0.9,
            metadata={"nested": {"data": "value"}},
        )

        # Serialize to JSON
        json_str = json.dumps(original.to_dict())

        # Deserialize from JSON
        data = json.loads(json_str)
        restored = Translation.from_dict(data)

        self.assertEqual(restored.original_text, original.original_text)
        self.assertEqual(restored.translated_text, original.translated_text)
        self.assertEqual(restored.source_language, original.source_language)
        self.assertEqual(restored.target_language, original.target_language)
        self.assertEqual(restored.confidence, original.confidence)
        self.assertEqual(restored.metadata, original.metadata)

    def test_str_representation(self):
        """Test string representation"""
        translation = Translation(
            original_text="Hello",
            translated_text="Привет",
            source_language="en",
            target_language="ru",
        )

        str_repr = str(translation)

        self.assertIn("Hello", str_repr)
        self.assertIn("Привет", str_repr)

    def test_repr_representation(self):
        """Test repr representation"""
        translation = Translation(
            original_text="Test",
            translated_text="Тест",
            source_language="en",
            target_language="ru",
            confidence=0.85,
        )

        repr_str = repr(translation)

        self.assertIn("Translation", repr_str)
        self.assertIn("original_text='Test'", repr_str)

    def test_equality(self):
        """Test equality comparison"""
        timestamp = datetime.now()

        trans1 = Translation(
            original_text="Same",
            translated_text="Одинаковый",
            source_language="en",
            target_language="ru",
            id="same-id",
            timestamp=timestamp,
        )

        trans2 = Translation(
            original_text="Same",
            translated_text="Одинаковый",
            source_language="en",
            target_language="ru",
            id="same-id",
            timestamp=timestamp,
        )

        trans3 = Translation(
            original_text="Different",
            translated_text="Другой",
            source_language="en",
            target_language="ru",
            id="different-id",
            timestamp=timestamp,
        )

        self.assertEqual(trans1, trans2)
        self.assertNotEqual(trans1, trans3)
        self.assertNotEqual(trans1, "not a translation")

    def test_empty_text_handling(self):
        """Test handling of empty texts"""
        translation = Translation(
            original_text="", translated_text="", source_language="en", target_language="ru"
        )

        self.assertEqual(translation.original_text, "")
        self.assertEqual(translation.translated_text, "")

    def test_whitespace_handling(self):
        """Test handling of whitespace"""
        translation = Translation(
            original_text="  Hello  ",
            translated_text="  Привет  ",
            source_language="en",
            target_language="ru",
        )

        # Whitespace should be preserved
        self.assertEqual(translation.original_text, "  Hello  ")
        self.assertEqual(translation.translated_text, "  Привет  ")

    def test_unicode_handling(self):
        """Test handling of unicode characters"""
        translation = Translation(
            original_text="Hello 👋 世界",
            translated_text="Привет 👋 мир",
            source_language="multi",
            target_language="ru",
        )

        self.assertEqual(translation.original_text, "Hello 👋 世界")
        self.assertEqual(translation.translated_text, "Привет 👋 мир")

    def test_large_metadata(self):
        """Test handling of large metadata"""
        large_metadata = {"key" + str(i): "value" + str(i) for i in range(100)}

        translation = Translation(
            original_text="Test",
            translated_text="Тест",
            source_language="en",
            target_language="ru",
            metadata=large_metadata,
        )

        self.assertEqual(len(translation.metadata), 100)
        self.assertEqual(translation.metadata["key50"], "value50")

    def test_confidence_validation(self):
        """Test confidence value validation"""
        # Valid confidence
        trans1 = Translation(
            original_text="Test",
            translated_text="Тест",
            source_language="en",
            target_language="ru",
            confidence=0.5,
        )
        self.assertEqual(trans1.confidence, 0.5)

        # Edge cases
        trans2 = Translation(
            original_text="Test",
            translated_text="Тест",
            source_language="en",
            target_language="ru",
            confidence=0.0,
        )
        self.assertEqual(trans2.confidence, 0.0)

        trans3 = Translation(
            original_text="Test",
            translated_text="Тест",
            source_language="en",
            target_language="ru",
            confidence=1.0,
        )
        self.assertEqual(trans3.confidence, 1.0)

    def test_cached_property(self):
        """Test cached property"""
        # Not cached
        trans1 = Translation(
            original_text="Fresh",
            translated_text="Свежий",
            source_language="en",
            target_language="ru",
        )
        self.assertFalse(trans1.cached)

        # Cached
        trans2 = Translation(
            original_text="Cached",
            translated_text="Кэшированный",
            source_language="en",
            target_language="ru",
            cached=True,
        )
        self.assertTrue(trans2.cached)

    def test_timestamp_iso_format(self):
        """Test timestamp ISO format in to_dict"""
        translation = Translation(
            original_text="Time",
            translated_text="Время",
            source_language="en",
            target_language="ru",
        )

        data = translation.to_dict()

        # Should contain ISO formatted timestamp
        self.assertIsInstance(data["timestamp"], str)
        self.assertGreater(len(data["timestamp"]), 0)

        # Should be parseable back to datetime
        parsed_time = datetime.fromisoformat(data["timestamp"])
        self.assertIsInstance(parsed_time, datetime)

    def test_metadata_defaults(self):
        """Test metadata defaults and initialization"""
        translation = Translation(
            original_text="Test", translated_text="Тест", source_language="en", target_language="ru"
        )

        # Should have empty dict as default
        self.assertEqual(translation.metadata, {})
        self.assertIsInstance(translation.metadata, dict)

    def test_copy_with_modifications(self):
        """Test creating modified copy of translation"""
        original = Translation(
            original_text="Original",
            translated_text="Оригинал",
            source_language="en",
            target_language="ru",
            confidence=0.9,
        )

        # Create a modified copy
        data = original.to_dict()
        data["confidence"] = 0.95
        data["cached"] = True

        modified = Translation.from_dict(data)

        self.assertEqual(modified.original_text, original.original_text)
        self.assertEqual(modified.confidence, 0.95)
        self.assertTrue(modified.cached)


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import Mock, patch

from src.models.translation import Translation
from src.services.cache_service import TranslationCache


class TestTranslationCache(unittest.TestCase):
    """Test TranslationCache functionality"""

    def setUp(self):
        """Setup test environment"""
        self.cache = TranslationCache(max_size=3, ttl_hours=1)

    def test_cache_hit(self):
        """Test cache hit scenario"""
        # Create translation
        translation = Translation(
            original_text="Hello",
            translated_text="Привет",
            source_language="en",
            target_language="ru",
            confidence=0.95,
        )

        # Add to cache
        self.cache.add(translation)

        # Retrieve from cache
        cached = self.cache.get("Hello", "ru")
        self.assertIsNotNone(cached)
        self.assertEqual(cached.translated_text, "Привет")

    def test_cache_miss(self):
        """Test cache miss scenario"""
        # Try to get non-existent translation
        result = self.cache.get("Goodbye", "ru")
        self.assertIsNone(result)

    def test_lru_eviction(self):
        """Test LRU eviction policy"""
        # Add translations to fill cache
        for i in range(4):
            translation = Translation(
                original_text=f"Text{i}",
                translated_text=f"Перевод{i}",
                source_language="en",
                target_language="ru",
                confidence=0.95,
            )
            self.cache.add(translation)

        # First translation should be evicted
        self.assertIsNone(self.cache.get("Text0", "ru"))
        # Others should still be in cache
        self.assertIsNotNone(self.cache.get("Text1", "ru"))
        self.assertIsNotNone(self.cache.get("Text2", "ru"))
        self.assertIsNotNone(self.cache.get("Text3", "ru"))

    def test_cache_key_normalization(self):
        """Test that cache keys are normalized"""
        translation = Translation(
            original_text="Hello World",
            translated_text="Привет Мир",
            source_language="en",
            target_language="ru",
            confidence=0.95,
        )

        self.cache.add(translation)

        # Should find with different case
        cached = self.cache.get("HELLO WORLD", "ru")
        self.assertIsNotNone(cached)
        self.assertEqual(cached.translated_text, "Привет Мир")

    def test_ttl_expiration(self):
        """Test TTL expiration (mocked)"""
        # Create cache with very short TTL
        cache = TranslationCache(max_size=10, ttl_hours=0)

        translation = Translation(
            original_text="Hello",
            translated_text="Привет",
            source_language="en",
            target_language="ru",
            confidence=0.95,
        )

        # Manually add expired entry
        key = cache._generate_key("Hello", "ru")
        cache.cache[key] = {
            "translation": translation,
            "timestamp": datetime.now() - timedelta(hours=1),
        }
        cache.access_order.append(key)

        # Should return None for expired entry
        result = cache.get("Hello", "ru")
        self.assertIsNone(result)

    def test_clear_cache(self):
        """Test cache clearing"""
        # Add some translations
        for i in range(3):
            translation = Translation(
                original_text=f"Text{i}",
                translated_text=f"Перевод{i}",
                source_language="en",
                target_language="ru",
                confidence=0.95,
            )
            self.cache.add(translation)

        # Clear cache
        self.cache.clear()

        # All entries should be gone
        for i in range(3):
            self.assertIsNone(self.cache.get(f"Text{i}", "ru"))

    def test_get_stats(self):
        """Test cache statistics"""
        # Add some translations
        translation = Translation(
            original_text="Hello",
            translated_text="Привет",
            source_language="en",
            target_language="ru",
            confidence=0.95,
        )
        self.cache.add(translation)

        # Get stats
        stats = self.cache.get_stats()
        self.assertEqual(stats["size"], 1)
        self.assertEqual(stats["max_size"], 3)
        self.assertEqual(stats["hit_rate"], 0.0)  # No hits yet

        # Access to create a hit
        self.cache.get("Hello", "ru")
        stats = self.cache.get_stats()
        self.assertGreater(stats["hit_rate"], 0.0)

    def test_empty_text_handling(self):
        """Test handling of empty or whitespace-only text"""
        # Empty text should return None
        result = self.cache.get("", "ru")
        self.assertIsNone(result)

        # Whitespace-only text should return None
        result = self.cache.get("   ", "ru")
        self.assertIsNone(result)

        # Try to add empty translation
        translation = Translation(
            original_text="",
            translated_text="Привет",
            source_language="en",
            target_language="ru",
            confidence=0.95,
        )
        self.cache.add(translation)

        # Should not be cached
        self.assertEqual(len(self.cache.cache), 0)

    def test_empty_translated_text_handling(self):
        """Test handling of empty translated text"""
        translation = Translation(
            original_text="Hello",
            translated_text="   ",  # Whitespace only
            source_language="en",
            target_language="ru",
            confidence=0.95,
        )

        # Should not cache empty translated text
        self.cache.add(translation)
        self.assertEqual(len(self.cache.cache), 0)

    def test_set_method_directly(self):
        """Test using set method directly"""
        translation = Translation(
            original_text="Hello",
            translated_text="Привет",
            source_language="en",
            target_language="ru",
            confidence=0.95,
        )

        # Use set method
        self.cache.set("Hello", "ru", translation)

        # Should be retrievable
        cached = self.cache.get("Hello", "ru")
        self.assertIsNotNone(cached)
        self.assertEqual(cached.translated_text, "Привет")
        self.assertTrue(cached.cached)  # Should be marked as cached

    def test_expired_entries_in_stats(self):
        """Test that expired entries are correctly counted in stats"""
        # Create cache with very short TTL
        cache = TranslationCache(max_size=10, ttl_hours=0)

        # Add translation
        translation = Translation(
            original_text="Hello",
            translated_text="Привет",
            source_language="en",
            target_language="ru",
            confidence=0.95,
        )
        cache.add(translation)

        # Manually set old timestamp
        key = cache._generate_key("Hello", "ru")
        cache.cache[key]["timestamp"] = datetime.now() - timedelta(hours=1)

        # Check stats
        stats = cache.get_stats()
        self.assertEqual(stats["expired_entries"], 1)
        self.assertEqual(stats["active_entries"], 0)
        self.assertEqual(stats["total_entries"], 1)

    @patch("src.services.cache_service.logger")
    def test_logging_operations(self, mock_logger):
        """Test that cache operations are properly logged"""
        translation = Translation(
            original_text="Hello",
            translated_text="Привет",
            source_language="en",
            target_language="ru",
            confidence=0.95,
        )

        # Add translation
        self.cache.add(translation)
        mock_logger.debug.assert_called()

        # Get translation (hit)
        self.cache.get("Hello", "ru")
        # Should have more debug calls
        self.assertGreater(mock_logger.debug.call_count, 1)

        # Clear cache
        self.cache.clear()
        mock_logger.info.assert_called()


if __name__ == "__main__":
    unittest.main()

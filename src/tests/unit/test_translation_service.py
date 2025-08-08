"""Unit tests for translation service"""

import time
import unittest
from unittest.mock import MagicMock, Mock, patch

from src.models.config import AppConfig, LanguageConfig
from src.models.translation import Translation
from src.services.translation_service import TranslationService
from src.utils.exceptions import InvalidLanguageError, TranslationFailedError


class TestTranslationService(unittest.TestCase):
    """Test TranslationService class"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_plugin_service = Mock()
        self.mock_config_manager = Mock()
        self.mock_cache_service = Mock()
        self.mock_performance_monitor = Mock()

        # Configure mock config
        self.mock_config = AppConfig(
            languages=LanguageConfig(
                ocr_languages=["eng", "rus"],
                target_languages=["ru", "en", "de"],
                default_target=0,
                auto_detect=True,
            )
        )
        self.mock_config_manager.config = self.mock_config

        # Mock translation plugin
        self.mock_translation_plugin = Mock()
        self.mock_translation_plugin.translate.return_value = "Привет мир"
        self.mock_translation_plugin.detect_language.return_value = "en"
        self.mock_translation_plugin.get_supported_languages.return_value = [
            "en",
            "ru",
            "de",
            "fr",
            "es",
        ]
        self.mock_plugin_service.get_active_plugin.return_value = self.mock_translation_plugin

        # Create service
        self.service = TranslationService(
            plugin_service=self.mock_plugin_service,
            config_manager=self.mock_config_manager,
            cache_service=self.mock_cache_service,
            performance_monitor=self.mock_performance_monitor,
        )

    def test_initialization(self):
        """Test service initialization"""
        self.assertIsNotNone(self.service)
        self.assertEqual(self.service.plugin_service, self.mock_plugin_service)
        self.assertEqual(self.service.config_manager, self.mock_config_manager)
        self.assertEqual(self.service.cache_service, self.mock_cache_service)

    def test_translate_success(self):
        """Test successful translation"""
        text = "Hello world"
        target_lang = "ru"

        result = self.service.translate(text, target_language=target_lang)

        self.assertIsInstance(result, Translation)
        self.assertEqual(result.original_text, text)
        self.assertEqual(result.translated_text, "Привет мир")
        self.assertEqual(result.target_language, target_lang)

        # Verify plugin was called
        self.mock_translation_plugin.translate.assert_called_once_with(
            text, source_language="auto", target_language=target_lang
        )

        # Verify performance monitoring
        self.mock_performance_monitor.record_metric.assert_called()

    def test_translate_no_plugin(self):
        """Test translation when no plugin is available"""
        self.mock_plugin_service.get_active_plugin.return_value = None

        with self.assertRaises(TranslationFailedError) as context:
            self.service.translate("Hello world")

        self.assertIn("No translation plugin available", str(context.exception))

    def test_translate_plugin_error(self):
        """Test handling of plugin translation error"""
        self.mock_translation_plugin.translate.side_effect = Exception("API error")

        with self.assertRaises(TranslationFailedError) as context:
            self.service.translate("Hello world")

        self.assertIn("Translation failed", str(context.exception))

    def test_translate_with_cache_hit(self):
        """Test translation with cache hit"""
        cached_translation = Translation(
            original_text="Hello world",
            translated_text="Привет мир (cached)",
            source_language="en",
            target_language="ru",
            timestamp=time.time(),
        )

        self.mock_cache_service.get.return_value = cached_translation

        result = self.service.translate("Hello world", target_language="ru")

        # Should return cached result
        self.assertEqual(result.translated_text, "Привет мир (cached)")

        # Plugin should not be called
        self.mock_translation_plugin.translate.assert_not_called()

    def test_translate_with_cache_miss(self):
        """Test translation with cache miss"""
        self.mock_cache_service.get.return_value = None

        result = self.service.translate("Hello world", target_language="ru")

        # Should call plugin
        self.mock_translation_plugin.translate.assert_called_once()

        # Should store in cache
        self.mock_cache_service.set.assert_called_once()

    def test_translate_auto_detect_language(self):
        """Test translation with automatic language detection"""
        text = "Hello world"

        # Enable auto-detect
        self.mock_config.languages.auto_detect = True

        result = self.service.translate(text, source_language="auto")

        # Should detect language
        self.mock_translation_plugin.detect_language.assert_called_once_with(text)

        # Should use detected language
        self.assertEqual(result.source_language, "en")

    def test_translate_explicit_source_language(self):
        """Test translation with explicit source language"""
        text = "Hello world"

        result = self.service.translate(text, source_language="en", target_language="ru")

        # Should not detect language
        self.mock_translation_plugin.detect_language.assert_not_called()

        # Should use provided language
        self.assertEqual(result.source_language, "en")

    def test_translate_default_target_language(self):
        """Test translation with default target language"""
        text = "Hello world"

        # Don't specify target language
        result = self.service.translate(text)

        # Should use default from config (index 0 = "ru")
        self.assertEqual(result.target_language, "ru")

    def test_translate_invalid_target_language(self):
        """Test translation with invalid target language"""
        with self.assertRaises(InvalidLanguageError) as context:
            self.service.translate("Hello", target_language="invalid")

        self.assertIn("Unsupported target language", str(context.exception))

    def test_translate_same_source_and_target(self):
        """Test translation when source and target are the same"""
        # Detect English
        self.mock_translation_plugin.detect_language.return_value = "en"

        result = self.service.translate("Hello world", target_language="en")

        # Should return original text
        self.assertEqual(result.translated_text, "Hello world")

        # Should not call translation plugin
        self.mock_translation_plugin.translate.assert_not_called()

    def test_batch_translate(self):
        """Test batch translation"""
        texts = ["Hello", "World", "Test"]

        self.mock_translation_plugin.translate.side_effect = ["Привет", "Мир", "Тест"]

        results = self.service.batch_translate(texts, target_language="ru")

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].translated_text, "Привет")
        self.assertEqual(results[1].translated_text, "Мир")
        self.assertEqual(results[2].translated_text, "Тест")

    def test_batch_translate_with_errors(self):
        """Test batch translation with some failures"""
        texts = ["Hello", "World", "Test"]

        # Second translation fails
        self.mock_translation_plugin.translate.side_effect = ["Привет", Exception("Failed"), "Тест"]

        results = self.service.batch_translate(texts, target_language="ru")

        # Should still return results for successful translations
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].translated_text, "Привет")
        self.assertIsNone(results[1])  # Failed translation
        self.assertEqual(results[2].translated_text, "Тест")

    def test_get_supported_languages(self):
        """Test getting supported languages"""
        languages = self.service.get_supported_languages()

        self.assertEqual(languages, ["en", "ru", "de", "fr", "es"])
        self.mock_translation_plugin.get_supported_languages.assert_called_once()

    def test_get_supported_languages_no_plugin(self):
        """Test getting languages when no plugin available"""
        self.mock_plugin_service.get_active_plugin.return_value = None

        languages = self.service.get_supported_languages()

        self.assertEqual(languages, [])

    def test_validate_language_pair(self):
        """Test language pair validation"""
        # Valid pair
        self.assertTrue(self.service._validate_language_pair("en", "ru"))

        # Invalid source
        self.assertFalse(self.service._validate_language_pair("invalid", "ru"))

        # Invalid target
        self.assertFalse(self.service._validate_language_pair("en", "invalid"))

    def test_translate_empty_text(self):
        """Test translation of empty text"""
        result = self.service.translate("", target_language="ru")

        # Should return empty translation
        self.assertEqual(result.original_text, "")
        self.assertEqual(result.translated_text, "")

        # Should not call plugin
        self.mock_translation_plugin.translate.assert_not_called()

    def test_translate_whitespace_text(self):
        """Test translation of whitespace-only text"""
        result = self.service.translate("   \n\t   ", target_language="ru")

        # Should handle gracefully
        self.assertEqual(result.original_text.strip(), "")
        self.assertEqual(result.translated_text.strip(), "")

    def test_translate_with_confidence_score(self):
        """Test translation with confidence score from plugin"""
        # Plugin returns tuple with confidence
        self.mock_translation_plugin.translate.return_value = ("Привет мир", 0.95)

        result = self.service.translate("Hello world", target_language="ru")

        self.assertEqual(result.translated_text, "Привет мир")
        self.assertEqual(result.confidence, 0.95)

    def test_performance_metrics(self):
        """Test performance metric recording"""
        self.service.translate("Hello world", target_language="ru")

        # Should record translation time
        self.mock_performance_monitor.record_metric.assert_called()
        call_args = self.mock_performance_monitor.record_metric.call_args
        self.assertEqual(call_args[0][0], "translation_time")
        self.assertIsInstance(call_args[0][1], float)

    def test_translation_history(self):
        """Test translation history tracking"""
        # Translate multiple texts
        texts = ["Hello", "World", "Test"]
        for text in texts:
            self.service.translate(text, target_language="ru")

        history = self.service.get_translation_history()

        self.assertEqual(len(history), 3)
        self.assertEqual(history[0].original_text, "Hello")
        self.assertEqual(history[1].original_text, "World")
        self.assertEqual(history[2].original_text, "Test")

    def test_clear_translation_history(self):
        """Test clearing translation history"""
        # Add some translations
        self.service.translate("Hello", target_language="ru")
        self.service.translate("World", target_language="ru")

        self.service.clear_history()

        history = self.service.get_translation_history()
        self.assertEqual(len(history), 0)

    def test_translation_rate_limiting(self):
        """Test rate limiting for translations"""
        # Enable rate limiting in service
        self.service._rate_limit = 10  # 10 requests per minute
        self.service._rate_counter = []

        # Translate rapidly
        for i in range(15):
            try:
                self.service.translate(f"Text {i}", target_language="ru")
            except TranslationFailedError as e:
                if "Rate limit" in str(e):
                    # Expected after 10 requests
                    self.assertGreater(i, 9)
                    break
        else:
            self.fail("Rate limiting not enforced")

    def test_fallback_translation(self):
        """Test fallback when primary translation fails"""
        # First call fails, fallback succeeds
        self.mock_translation_plugin.translate.side_effect = [
            Exception("Primary failed"),
            "Fallback translation",
        ]

        # Configure fallback plugin
        fallback_plugin = Mock()
        fallback_plugin.translate.return_value = "Fallback result"

        with patch.object(self.service, "_get_fallback_plugin", return_value=fallback_plugin):
            result = self.service.translate("Hello", target_language="ru")

            # Should use fallback
            self.assertEqual(result.translated_text, "Fallback result")


if __name__ == "__main__":
    unittest.main()

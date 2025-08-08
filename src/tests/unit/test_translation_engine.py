"""
Tests for translation engine module.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.core.translation_engine import (
    GoogleTranslationEngine,
    TranslationEngine,
    TranslationProcessor,
)
from src.models.translation import Translation
from src.services.circuit_breaker import CircuitBreakerError, CircuitState
from src.utils.exceptions import (
    TranslationEngineNotAvailableError,
    TranslationFailedError,
    UnsupportedLanguageError,
)


class MockTranslationEngine(TranslationEngine):
    """Mock translation engine for testing"""

    def __init__(self, available=True, supported_langs=None):
        self.available = available
        self.supported_langs = supported_langs or ["en", "ru", "ja"]

    def translate(self, text, target_language, source_language="auto"):
        if not self.available:
            raise TranslationEngineNotAvailableError("MockEngine", "Not available")
        if target_language not in self.supported_langs:
            raise UnsupportedLanguageError(target_language, "MockEngine")
        return f"Translated: {text}"

    def get_supported_languages(self):
        return self.supported_langs

    def is_available(self):
        return self.available


class TestTranslationEngine:
    """Test abstract TranslationEngine base class"""

    def test_translation_engine_is_abstract(self):
        """Test that TranslationEngine cannot be instantiated directly"""
        with pytest.raises(TypeError):
            TranslationEngine()

    def test_mock_engine_implementation(self):
        """Test mock engine implementation works"""
        engine = MockTranslationEngine()

        assert engine.is_available() is True
        assert "en" in engine.get_supported_languages()
        result = engine.translate("Hello", "ru")
        assert result == "Translated: Hello"


class TestGoogleTranslationEngine:
    """Test GoogleTranslationEngine implementation"""

    @patch("src.core.translation_engine.get_circuit_breaker_manager")
    @patch("src.core.translation_engine.GoogleTranslationEngine._initialize")
    def test_initialization_success(self, mock_init, mock_cb_manager):
        """Test successful initialization"""
        mock_init.return_value = None
        mock_circuit_breaker = Mock()
        mock_manager = Mock()
        mock_manager.create_circuit_breaker.return_value = mock_circuit_breaker
        mock_cb_manager.return_value = mock_manager

        engine = GoogleTranslationEngine()
        engine.translator = Mock()  # Simulate successful init

        assert engine.circuit_breaker == mock_circuit_breaker
        mock_manager.create_circuit_breaker.assert_called_once()

    @patch("src.core.translation_engine.get_circuit_breaker_manager")
    def test_initialization_no_googletrans(self, mock_cb_manager):
        """Test initialization when googletrans is not available"""
        mock_circuit_breaker = Mock()
        mock_manager = Mock()
        mock_manager.create_circuit_breaker.return_value = mock_circuit_breaker
        mock_cb_manager.return_value = mock_manager

        with patch("src.core.translation_engine.GoogleTranslationEngine._initialize") as mock_init:
            mock_init.return_value = None
            engine = GoogleTranslationEngine()
            engine.translator = None  # Simulate failed init

            assert engine.is_available() is False

    def test_get_supported_languages(self):
        """Test getting supported languages"""
        with patch("src.core.translation_engine.get_circuit_breaker_manager"):
            with patch("src.core.translation_engine.GoogleTranslationEngine._initialize"):
                engine = GoogleTranslationEngine()

                languages = engine.get_supported_languages()

                assert isinstance(languages, list)
                assert "en" in languages
                assert "ru" in languages
                assert "ja" in languages
                assert len(languages) >= 10

    def test_is_available_true(self):
        """Test is_available when translator is initialized"""
        with patch("src.core.translation_engine.get_circuit_breaker_manager"):
            with patch("src.core.translation_engine.GoogleTranslationEngine._initialize"):
                engine = GoogleTranslationEngine()
                engine.translator = Mock()

                assert engine.is_available() is True

    def test_is_available_false(self):
        """Test is_available when translator is None"""
        with patch("src.core.translation_engine.get_circuit_breaker_manager"):
            with patch("src.core.translation_engine.GoogleTranslationEngine._initialize"):
                engine = GoogleTranslationEngine()
                engine.translator = None

                assert engine.is_available() is False

    def test_translate_engine_not_available(self):
        """Test translate when engine is not available"""
        with patch("src.core.translation_engine.get_circuit_breaker_manager"):
            with patch("src.core.translation_engine.GoogleTranslationEngine._initialize"):
                engine = GoogleTranslationEngine()
                engine.translator = None

                with pytest.raises(TranslationEngineNotAvailableError):
                    engine.translate("Hello", "ru")

    def test_translate_empty_text(self):
        """Test translate with empty text"""
        with patch("src.core.translation_engine.get_circuit_breaker_manager"):
            with patch("src.core.translation_engine.GoogleTranslationEngine._initialize"):
                engine = GoogleTranslationEngine()
                engine.translator = Mock()

                with pytest.raises(TranslationFailedError):
                    engine.translate("", "ru")

                with pytest.raises(TranslationFailedError):
                    engine.translate("   ", "ru")

    def test_translate_unsupported_language(self):
        """Test translate with unsupported language"""
        with patch("src.core.translation_engine.get_circuit_breaker_manager"):
            with patch("src.core.translation_engine.GoogleTranslationEngine._initialize"):
                engine = GoogleTranslationEngine()
                engine.translator = Mock()

                with pytest.raises(UnsupportedLanguageError):
                    engine.translate("Hello", "xyz")

    @patch("asyncio.new_event_loop")
    @patch("asyncio.set_event_loop")
    def test_translate_success(self, mock_set_loop, mock_new_loop):
        """Test successful translation"""
        with patch("src.core.translation_engine.get_circuit_breaker_manager"):
            with patch("src.core.translation_engine.GoogleTranslationEngine._initialize"):
                engine = GoogleTranslationEngine()
                engine.translator = Mock()

                # Mock circuit breaker
                mock_circuit_breaker = AsyncMock()
                mock_circuit_breaker.call = AsyncMock(return_value="Привет")
                engine.circuit_breaker = mock_circuit_breaker

                # Mock event loop
                mock_loop = Mock()
                mock_loop.run_until_complete.return_value = "Привет"
                mock_new_loop.return_value = mock_loop

                result = engine.translate("Hello", "ru")

                assert result == "Привет"
                mock_loop.close.assert_called_once()

    def test_translate_circuit_breaker_error(self):
        """Test translate when circuit breaker triggers"""
        with patch("src.core.translation_engine.get_circuit_breaker_manager"):
            with patch("src.core.translation_engine.GoogleTranslationEngine._initialize"):
                engine = GoogleTranslationEngine()
                engine.translator = Mock()

                # Mock circuit breaker to raise error
                mock_circuit_breaker = Mock()
                engine.circuit_breaker = mock_circuit_breaker

                with patch("asyncio.new_event_loop") as mock_new_loop:
                    with patch("asyncio.set_event_loop"):
                        mock_loop = Mock()
                        mock_loop.run_until_complete.side_effect = CircuitBreakerError(
                            "Circuit open", CircuitState.OPEN
                        )
                        mock_new_loop.return_value = mock_loop

                        with pytest.raises(TranslationFailedError):
                            engine.translate("Hello", "ru")

                        mock_loop.close.assert_called_once()

    def test_translate_general_exception(self):
        """Test translate with general exception"""
        with patch("src.core.translation_engine.get_circuit_breaker_manager"):
            with patch("src.core.translation_engine.GoogleTranslationEngine._initialize"):
                engine = GoogleTranslationEngine()
                engine.translator = Mock()
                engine.circuit_breaker = Mock()

                with patch("asyncio.new_event_loop") as mock_new_loop:
                    with patch("asyncio.set_event_loop"):
                        mock_loop = Mock()
                        mock_loop.run_until_complete.side_effect = Exception("API Error")
                        mock_new_loop.return_value = mock_loop

                        with pytest.raises(TranslationFailedError):
                            engine.translate("Hello", "ru")

                        mock_loop.close.assert_called_once()


class TestTranslationProcessor:
    """Test TranslationProcessor class"""

    @patch("src.core.translation_engine.GoogleTranslationEngine")
    @patch("src.core.translation_engine.TranslationCache")
    def test_initialization_with_cache(self, mock_cache_class, mock_engine_class):
        """Test processor initialization with cache enabled"""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine_class.return_value = mock_engine

        mock_cache = Mock()
        mock_cache_class.return_value = mock_cache

        processor = TranslationProcessor(cache_enabled=True)

        assert processor.active_engine == mock_engine
        assert processor.cache == mock_cache
        assert processor.cache_enabled is True

    @patch("src.core.translation_engine.GoogleTranslationEngine")
    def test_initialization_without_cache(self, mock_engine_class):
        """Test processor initialization with cache disabled"""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine_class.return_value = mock_engine

        processor = TranslationProcessor(cache_enabled=False)

        assert processor.active_engine == mock_engine
        assert processor.cache is None
        assert processor.cache_enabled is False

    @patch("src.core.translation_engine.GoogleTranslationEngine")
    def test_initialization_no_available_engines(self, mock_engine_class):
        """Test processor initialization when no engines are available"""
        mock_engine = Mock()
        mock_engine.is_available.return_value = False
        mock_engine_class.return_value = mock_engine

        processor = TranslationProcessor()

        assert processor.active_engine is None

    def test_get_available_engine(self):
        """Test getting available engine"""
        available_engine = MockTranslationEngine(available=True)
        unavailable_engine = MockTranslationEngine(available=False)

        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.engines = [unavailable_engine, available_engine]

        result = processor._get_available_engine()

        assert result == available_engine

    def test_get_available_engine_none_available(self):
        """Test getting available engine when none are available"""
        engine1 = MockTranslationEngine(available=False)
        engine2 = MockTranslationEngine(available=False)

        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.engines = [engine1, engine2]

        result = processor._get_available_engine()

        assert result is None

    @patch("src.core.translation_engine.time.time")
    def test_translate_text_no_engine(self, mock_time):
        """Test translate_text when no engine is available"""
        mock_time.return_value = 1000.0

        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.active_engine = None
        processor.cache = None

        result = processor.translate_text("Hello", "ru")

        assert result is None

    @patch("src.core.translation_engine.time.time")
    def test_translate_text_empty_text(self, mock_time):
        """Test translate_text with empty text"""
        mock_time.return_value = 1000.0

        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.active_engine = MockTranslationEngine()
        processor.cache = None

        result = processor.translate_text("", "ru")

        assert result is None

    @patch("src.core.translation_engine.time.time")
    @patch("src.core.translation_engine.datetime")
    def test_translate_text_cache_hit(self, mock_datetime, mock_time):
        """Test translate_text with cache hit"""
        mock_time.return_value = 1000.0
        mock_datetime.now.return_value = datetime(2023, 1, 1)

        # Create cached translation
        cached_translation = Translation(
            original_text="Hello",
            translated_text="Привет",
            source_language="en",
            target_language="ru",
            cached=True,
        )

        # Mock cache
        mock_cache = Mock()
        mock_cache.get.return_value = cached_translation

        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.active_engine = MockTranslationEngine()
        processor.cache = mock_cache

        result = processor.translate_text("Hello", "ru")

        assert result == cached_translation
        mock_cache.get.assert_called_once_with("Hello", "ru")

    @patch("src.core.translation_engine.time.time")
    @patch("src.core.translation_engine.datetime")
    def test_translate_text_success_with_caching(self, mock_datetime, mock_time):
        """Test successful translate_text with caching"""
        mock_time.return_value = 1000.0
        mock_datetime.now.return_value = datetime(2023, 1, 1)

        # Mock engine
        mock_engine = Mock()
        mock_engine.translate.return_value = "Привет"

        # Mock cache
        mock_cache = Mock()
        mock_cache.get.return_value = None  # No cache hit

        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.active_engine = mock_engine
        processor.cache = mock_cache

        result = processor.translate_text("Hello", "ru")

        assert result is not None
        assert result.original_text == "Hello"
        assert result.translated_text == "Привет"
        assert result.target_language == "ru"
        assert result.cached is False

        mock_cache.set.assert_called_once()

    @patch("src.core.translation_engine.time.time")
    def test_translate_text_success_without_caching(self, mock_time):
        """Test successful translate_text without caching"""
        mock_time.return_value = 1000.0

        # Mock engine
        mock_engine = Mock()
        mock_engine.translate.return_value = "Привет"

        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.active_engine = mock_engine
        processor.cache = None

        with patch("src.core.translation_engine.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1)

            result = processor.translate_text("Hello", "ru")

            assert result is not None
            assert result.original_text == "Hello"
            assert result.translated_text == "Привет"

    @patch("src.core.translation_engine.time.time")
    def test_translate_text_engine_returns_none(self, mock_time):
        """Test translate_text when engine returns None"""
        mock_time.return_value = 1000.0

        # Mock engine that returns None
        mock_engine = Mock()
        mock_engine.translate.return_value = None

        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.active_engine = mock_engine
        processor.cache = None

        result = processor.translate_text("Hello", "ru")

        assert result is None

    @patch("src.core.translation_engine.time.time")
    def test_translate_text_engine_exception(self, mock_time):
        """Test translate_text when engine raises exception"""
        mock_time.return_value = 1000.0

        # Mock engine that raises exception
        mock_engine = Mock()
        mock_engine.translate.side_effect = Exception("Translation failed")

        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.active_engine = mock_engine
        processor.cache = None

        result = processor.translate_text("Hello", "ru")

        assert result is None

    def test_get_supported_languages_with_engine(self):
        """Test get_supported_languages with active engine"""
        mock_engine = Mock()
        mock_engine.get_supported_languages.return_value = ["en", "ru", "ja"]

        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.active_engine = mock_engine

        result = processor.get_supported_languages()

        assert result == ["en", "ru", "ja"]

    def test_get_supported_languages_no_engine(self):
        """Test get_supported_languages without active engine"""
        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.active_engine = None

        result = processor.get_supported_languages()

        assert result == []

    def test_is_available_with_engine(self):
        """Test is_available with active engine"""
        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.active_engine = Mock()

        assert processor.is_available() is True

    def test_is_available_no_engine(self):
        """Test is_available without active engine"""
        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.active_engine = None

        assert processor.is_available() is False

    def test_clear_cache_with_cache(self):
        """Test clear_cache when cache exists"""
        mock_cache = Mock()

        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.cache = mock_cache

        result = processor.clear_cache()

        assert result is True
        mock_cache.clear.assert_called_once()

    def test_clear_cache_no_cache(self):
        """Test clear_cache when cache doesn't exist"""
        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.cache = None

        result = processor.clear_cache()

        assert result is False

    def test_get_cache_stats_with_cache(self):
        """Test get_cache_stats when cache exists"""
        mock_cache = Mock()
        mock_cache.get_stats.return_value = {"hits": 10, "misses": 5}

        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.cache = mock_cache

        result = processor.get_cache_stats()

        assert result == {"hits": 10, "misses": 5}

    def test_get_cache_stats_no_cache(self):
        """Test get_cache_stats when cache doesn't exist"""
        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.cache = None

        result = processor.get_cache_stats()

        assert result == {"cache_enabled": False}

    @patch("src.core.translation_engine.TranslationCache")
    def test_enable_cache_enable(self, mock_cache_class):
        """Test enable_cache to enable caching"""
        mock_cache = Mock()
        mock_cache_class.return_value = mock_cache

        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.cache = None
        processor.cache_enabled = False

        processor.enable_cache(True)

        assert processor.cache == mock_cache
        assert processor.cache_enabled is True

    def test_enable_cache_disable(self):
        """Test enable_cache to disable caching"""
        mock_cache = Mock()

        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.cache = mock_cache
        processor.cache_enabled = True

        processor.enable_cache(False)

        assert processor.cache is None
        assert processor.cache_enabled is False

    def test_enable_cache_already_enabled(self):
        """Test enable_cache when already enabled"""
        mock_cache = Mock()

        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.cache = mock_cache
        processor.cache_enabled = True

        processor.enable_cache(True)

        # Should not change
        assert processor.cache == mock_cache
        assert processor.cache_enabled is True

    def test_get_engine_info_with_engine(self):
        """Test get_engine_info with active engine"""
        mock_engine = Mock()
        mock_engine.get_supported_languages.return_value = ["en", "ru", "ja"]

        # Set mock engine class name
        mock_engine.__class__.__name__ = "MockEngine"

        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.active_engine = mock_engine
        processor.cache_enabled = True

        result = processor.get_engine_info()

        assert result["engine"] == "MockEngine"
        assert result["available"] is True
        assert result["supported_languages"] == 3
        assert result["cache_enabled"] is True

    def test_get_engine_info_no_engine(self):
        """Test get_engine_info without active engine"""
        processor = TranslationProcessor.__new__(TranslationProcessor)
        processor.active_engine = None

        result = processor.get_engine_info()

        assert result == {"engine": "None", "available": False}

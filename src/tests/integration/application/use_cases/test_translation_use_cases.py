"""
Integration tests for Translation Use Cases
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.application.dto.translation_dto import TranslationRequest, TranslationResponse
from src.application.use_cases.translation_use_cases import (
    TranslateScreenshotUseCase,
    TranslateTextUseCase,
)
from src.domain.entities.screenshot import Screenshot
from src.domain.value_objects.coordinates import ScreenCoordinates
from src.domain.value_objects.language import Language, LanguagePair
from src.domain.value_objects.text import Text


class TestTranslationUseCaseIntegration:
    """Integration tests for translation use cases."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock services
        self.mock_translation_service = Mock()
        self.mock_ocr_service = Mock()
        self.mock_cache_service = Mock()
        self.mock_workflow_service = Mock()

        # Create use cases
        self.translate_text_use_case = TranslateTextUseCase(
            translation_service=self.mock_translation_service, cache_service=self.mock_cache_service
        )

        self.translate_screenshot_use_case = TranslateScreenshotUseCase(
            workflow_service=self.mock_workflow_service
        )

    @pytest.mark.asyncio
    async def test_translate_text_cache_miss_flow(self):
        """Test complete text translation flow with cache miss."""
        # Setup request
        request = TranslationRequest(text="Hello World", source_language="en", target_language="ru")

        # Mock cache miss
        self.mock_cache_service.get_cached_translation.return_value = None

        # Mock successful translation
        self.mock_translation_service.translate = AsyncMock(return_value="Привет Мир")

        # Mock cache storage
        self.mock_cache_service.cache_translation = Mock()

        # Execute
        result = await self.translate_text_use_case.execute(request)

        # Verify
        assert result is not None
        assert result.translated_text == "Привет Мир"
        assert result.source_language == "en"
        assert result.target_language == "ru"
        assert result.is_cached is False

        # Verify service calls
        lang_pair = LanguagePair(Language("en"), Language("ru"))
        self.mock_cache_service.get_cached_translation.assert_called_once_with(
            "Hello World", lang_pair
        )
        self.mock_translation_service.translate.assert_called_once()
        self.mock_cache_service.cache_translation.assert_called_once()

    @pytest.mark.asyncio
    async def test_translate_text_cache_hit_flow(self):
        """Test text translation with cache hit."""
        # Setup request
        request = TranslationRequest(text="Hello World", source_language="en", target_language="ru")

        # Mock cache hit
        cached_translation = Mock()
        cached_translation.translated.content = "Привет Мир (cached)"
        cached_translation.translated.confidence = 0.95
        self.mock_cache_service.get_cached_translation.return_value = cached_translation

        # Execute
        result = await self.translate_text_use_case.execute(request)

        # Verify
        assert result is not None
        assert result.translated_text == "Привет Мир (cached)"
        assert result.is_cached is True
        assert result.confidence == 0.95

        # Translation service should not be called
        self.mock_translation_service.translate.assert_not_called()

    @pytest.mark.asyncio
    async def test_translate_text_translation_failure(self):
        """Test handling of translation service failure."""
        request = TranslationRequest(text="Hello World", source_language="en", target_language="ru")

        # Mock cache miss
        self.mock_cache_service.get_cached_translation.return_value = None

        # Mock translation failure
        self.mock_translation_service.translate = AsyncMock(return_value=None)

        # Execute
        result = await self.translate_text_use_case.execute(request)

        # Should return None on failure
        assert result is None

    @pytest.mark.asyncio
    async def test_translate_screenshot_complete_flow(self):
        """Test complete screenshot translation flow."""
        # Setup screenshot
        coords = ScreenCoordinates(10, 20, 100, 150)
        screenshot = Screenshot(coordinates=coords)

        # Setup language pair
        lang_pair = LanguagePair(Language("en"), Language("ru"))

        # Mock workflow service
        mock_translation = Mock()
        mock_translation.original.content = "Extracted text"
        mock_translation.translated.content = "Извлечённый текст"
        mock_translation.language_pair = lang_pair
        mock_translation.to_dict.return_value = {
            "id": "test-123",
            "original": "Extracted text",
            "translated": "Извлечённый текст",
            "source_language": "en",
            "target_language": "ru",
            "confidence": 0.88,
        }

        self.mock_workflow_service.process_screenshot = AsyncMock(return_value=mock_translation)

        # Execute
        result = await self.translate_screenshot_use_case.execute(screenshot, lang_pair)

        # Verify
        assert result is not None
        assert "original" in result
        assert "translated" in result
        assert result["original"] == "Extracted text"
        assert result["translated"] == "Извлечённый текст"

        # Verify workflow service called
        self.mock_workflow_service.process_screenshot.assert_called_once_with(
            screenshot, lang_pair, auto_tts=False
        )

    @pytest.mark.asyncio
    async def test_translate_screenshot_with_tts(self):
        """Test screenshot translation with TTS enabled."""
        screenshot = Screenshot(coordinates=ScreenCoordinates(0, 0, 100, 50))
        lang_pair = LanguagePair(Language("en"), Language("ru"))

        # Mock successful workflow
        mock_translation = Mock()
        mock_translation.to_dict.return_value = {"id": "test-tts"}
        self.mock_workflow_service.process_screenshot = AsyncMock(return_value=mock_translation)

        # Execute with TTS
        result = await self.translate_screenshot_use_case.execute(
            screenshot, lang_pair, auto_tts=True
        )

        # Verify
        assert result is not None

        # Verify TTS was enabled in workflow call
        self.mock_workflow_service.process_screenshot.assert_called_once_with(
            screenshot, lang_pair, auto_tts=True
        )

    @pytest.mark.asyncio
    async def test_translate_screenshot_invalid_input(self):
        """Test screenshot translation with invalid screenshot."""
        # Invalid screenshot (no coordinates, no image)
        invalid_screenshot = Screenshot()
        lang_pair = LanguagePair(Language("en"), Language("ru"))

        # Mock workflow service to raise error
        self.mock_workflow_service.process_screenshot = AsyncMock(
            side_effect=ValueError("Invalid screenshot")
        )

        # Execute - should handle error gracefully
        result = await self.translate_screenshot_use_case.execute(invalid_screenshot, lang_pair)

        # Should return None on error
        assert result is None

    @pytest.mark.asyncio
    async def test_concurrent_translation_requests(self):
        """Test handling multiple concurrent translation requests."""
        requests = [
            TranslationRequest(text=f"Text {i}", source_language="en", target_language="ru")
            for i in range(5)
        ]

        # Mock cache misses
        self.mock_cache_service.get_cached_translation.return_value = None

        # Mock translations
        self.mock_translation_service.translate = AsyncMock(
            side_effect=lambda text, lang_pair: f"Translated: {text}"
        )

        # Execute concurrent requests
        tasks = [self.translate_text_use_case.execute(req) for req in requests]
        results = await asyncio.gather(*tasks)

        # Verify all completed
        assert len(results) == 5
        assert all(result is not None for result in results)

        # Verify each result is correct
        for i, result in enumerate(results):
            assert f"Text {i}" in result.original_text
            assert f"Translated: Text {i}" == result.translated_text

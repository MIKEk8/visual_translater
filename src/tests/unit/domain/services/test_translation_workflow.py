"""
Tests for TranslationWorkflowService.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from src.domain.entities.screenshot import Screenshot
from src.domain.services.translation_workflow import TranslationWorkflowService
from src.domain.value_objects.coordinates import ScreenCoordinates
from src.domain.value_objects.language import Language, LanguagePair
from src.domain.value_objects.text import Text


class TestTranslationWorkflowService:
    """Test TranslationWorkflowService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ocr_service = Mock()
        self.mock_translation_service = Mock()
        self.mock_tts_service = Mock()

        self.workflow = TranslationWorkflowService(
            self.mock_ocr_service, self.mock_translation_service, self.mock_tts_service
        )

    @pytest.mark.asyncio
    async def test_process_screenshot_complete_flow(self):
        """Test complete screenshot processing flow."""
        # Setup
        screenshot = Screenshot(coordinates=ScreenCoordinates(0, 0, 100, 50))
        lang_pair = LanguagePair(Language("en"), Language("ru"))

        # Mock OCR service
        self.mock_ocr_service.extract_text = AsyncMock(return_value=("Hello World", 0.9))

        # Mock translation service
        self.mock_translation_service.translate = AsyncMock(return_value="Привет Мир")

        # Mock TTS service
        self.mock_tts_service.is_available.return_value = True
        self.mock_tts_service.speak = AsyncMock()

        # Execute
        result = await self.workflow.process_screenshot(screenshot, lang_pair, auto_tts=True)

        # Verify
        assert result is not None
        assert result.original.content == "Hello World"
        assert result.translated.content == "Привет Мир"
        assert result.language_pair == lang_pair

        # Verify service calls
        self.mock_ocr_service.extract_text.assert_called_once()
        self.mock_translation_service.translate.assert_called_once_with("Hello World", lang_pair)
        self.mock_tts_service.speak.assert_called_once_with("Привет Мир", lang_pair.target)

    @pytest.mark.asyncio
    async def test_process_screenshot_invalid_screenshot(self):
        """Test processing invalid screenshot."""
        # Invalid screenshot (no coordinates, no image)
        screenshot = Screenshot()
        lang_pair = LanguagePair(Language("en"), Language("ru"))

        with pytest.raises(ValueError, match="Invalid screenshot"):
            await self.workflow.process_screenshot(screenshot, lang_pair)

    @pytest.mark.asyncio
    async def test_process_screenshot_with_existing_text(self):
        """Test processing screenshot that already has extracted text."""
        # Setup screenshot with existing text
        screenshot = Screenshot(coordinates=ScreenCoordinates(0, 0, 100, 50))
        screenshot.extract_text("Existing text", 0.8)

        lang_pair = LanguagePair(Language("en"), Language("ru"))

        # Mock translation service
        self.mock_translation_service.translate = AsyncMock(return_value="Существующий текст")

        # Mock TTS service
        self.mock_tts_service.is_available.return_value = False

        # Execute
        result = await self.workflow.process_screenshot(screenshot, lang_pair, auto_tts=True)

        # Verify
        assert result is not None
        assert result.original.content == "Existing text"
        assert result.translated.content == "Существующий текст"

        # OCR should not be called since text already exists
        self.mock_ocr_service.extract_text.assert_not_called()

        # TTS should not be called since service is not available
        self.mock_tts_service.speak.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_screenshot_ocr_failure(self):
        """Test processing when OCR returns no text."""
        screenshot = Screenshot(coordinates=ScreenCoordinates(0, 0, 100, 50))
        lang_pair = LanguagePair(Language("en"), Language("ru"))

        # Mock OCR to return empty text
        self.mock_ocr_service.extract_text = AsyncMock(return_value=("", 0.0))

        # Execute
        result = await self.workflow.process_screenshot(screenshot, lang_pair)

        # Should return None when no text is extracted
        assert result is None

    @pytest.mark.asyncio
    async def test_process_screenshot_translation_failure(self):
        """Test processing when translation fails."""
        screenshot = Screenshot(coordinates=ScreenCoordinates(0, 0, 100, 50))
        lang_pair = LanguagePair(Language("en"), Language("ru"))

        # Mock OCR service
        self.mock_ocr_service.extract_text = AsyncMock(return_value=("Hello", 0.9))

        # Mock translation service to return None (failure)
        self.mock_translation_service.translate = AsyncMock(return_value=None)

        # Execute
        result = await self.workflow.process_screenshot(screenshot, lang_pair)

        # Should return None when translation fails
        assert result is None

    def test_validate_services_all_available(self):
        """Test service validation when all services are available."""
        self.mock_ocr_service.is_available.return_value = True
        self.mock_translation_service.is_available.return_value = True
        self.mock_tts_service.is_available.return_value = True

        result = self.workflow.validate_services()

        assert result["ocr"] is True
        assert result["translation"] is True
        assert result["tts"] is True

    def test_validate_services_some_unavailable(self):
        """Test service validation when some services are unavailable."""
        self.mock_ocr_service.is_available.return_value = True
        self.mock_translation_service.is_available.return_value = False
        self.mock_tts_service.is_available.return_value = True

        result = self.workflow.validate_services()

        assert result["ocr"] is True
        assert result["translation"] is False
        assert result["tts"] is True

    def test_validate_services_no_tts(self):
        """Test service validation without TTS service."""
        workflow = TranslationWorkflowService(
            self.mock_ocr_service, self.mock_translation_service, None  # No TTS service
        )

        self.mock_ocr_service.is_available.return_value = True
        self.mock_translation_service.is_available.return_value = True

        result = workflow.validate_services()

        assert result["ocr"] is True
        assert result["translation"] is True
        assert result["tts"] is False

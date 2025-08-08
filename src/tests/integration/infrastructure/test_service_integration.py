"""
Integration tests for service interactions
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.domain.entities.screenshot import Screenshot
from src.domain.services.translation_workflow import TranslationWorkflowService
from src.domain.value_objects.coordinates import ScreenCoordinates
from src.domain.value_objects.language import Language, LanguagePair
from src.infrastructure.services.ocr_service import TesseractOCRService
from src.infrastructure.services.translation_service import GoogleTranslationService
from src.infrastructure.services.tts_service import PyttsxTTSService
from src.tests.test_utils import requires_tesseract, skip_on_ci

pytestmark = pytest.mark.integration


class TestServiceIntegration:
    """Integration tests for service interactions."""

    def setup_method(self):
        """Set up test services."""
        self.ocr_service = TesseractOCRService()
        self.translation_service = GoogleTranslationService()
        self.tts_service = PyttsxTTSService()

        self.workflow_service = TranslationWorkflowService(
            self.ocr_service, self.translation_service, self.tts_service
        )

    @skip_on_ci
    @requires_tesseract
    def test_service_availability_validation(self):
        """Test service availability validation."""
        result = self.workflow_service.validate_services()

        # Should return availability status for each service
        assert "ocr" in result
        assert "translation" in result
        assert "tts" in result

        # Values should be booleans
        assert isinstance(result["ocr"], bool)
        assert isinstance(result["translation"], bool)
        assert isinstance(result["tts"], bool)

    @skip_on_ci
    @requires_tesseract
    @pytest.mark.asyncio
    async def test_workflow_service_error_handling(self):
        """Test workflow service handles service errors gracefully."""
        # Create screenshot
        screenshot = Screenshot(coordinates=ScreenCoordinates(0, 0, 100, 50))
        lang_pair = LanguagePair(Language("en"), Language("ru"))

        # Mock OCR service to fail
        with patch.object(
            self.ocr_service, "extract_text", AsyncMock(side_effect=Exception("OCR failed"))
        ):
            result = await self.workflow_service.process_screenshot(screenshot, lang_pair)

            # Should handle error gracefully
            assert result is None

    @skip_on_ci
    @requires_tesseract
    @pytest.mark.asyncio
    async def test_service_chain_integration(self):
        """Test full service chain integration with mocked external dependencies."""
        # Create test screenshot
        screenshot = Screenshot(coordinates=ScreenCoordinates(10, 20, 110, 120))
        lang_pair = LanguagePair(Language("en"), Language("ru"))

        # Mock OCR service
        with patch.object(
            self.ocr_service, "extract_text", AsyncMock(return_value=("Hello World", 0.9))
        ):
            # Mock translation service
            with patch.object(
                self.translation_service, "translate", AsyncMock(return_value="Привет Мир")
            ):
                # Mock TTS service
                with patch.object(self.tts_service, "is_available", return_value=True):
                    with patch.object(self.tts_service, "speak", AsyncMock()):

                        # Execute workflow
                        result = await self.workflow_service.process_screenshot(
                            screenshot, lang_pair, auto_tts=True
                        )

                        # Verify result
                        assert result is not None
                        assert result.original.content == "Hello World"
                        assert result.translated.content == "Привет Мир"
                        assert result.language_pair == lang_pair

                        # Verify TTS was called
                        self.tts_service.speak.assert_called_once()

    @skip_on_ci
    @requires_tesseract
    @pytest.mark.asyncio
    async def test_service_resilience_partial_failures(self):
        """Test service resilience when some services fail."""
        screenshot = Screenshot(coordinates=ScreenCoordinates(0, 0, 50, 50))
        lang_pair = LanguagePair(Language("en"), Language("ru"))

        # Mock successful OCR and Translation, but failed TTS
        with patch.object(
            self.ocr_service, "extract_text", AsyncMock(return_value=("Test text", 0.8))
        ):
            with patch.object(
                self.translation_service, "translate", AsyncMock(return_value="Тестовый текст")
            ):
                with patch.object(self.tts_service, "is_available", return_value=False):

                    # Execute workflow
                    result = await self.workflow_service.process_screenshot(
                        screenshot, lang_pair, auto_tts=True
                    )

                    # Should still succeed even with TTS failure
                    assert result is not None
                    assert result.original.content == "Test text"
                    assert result.translated.content == "Тестовый текст"

    @skip_on_ci
    @requires_tesseract
    def test_service_configuration_loading(self):
        """Test that services load configuration correctly."""
        # Test OCR service
        assert hasattr(self.ocr_service, "_tesseract_cmd")

        # Test Translation service
        assert hasattr(self.translation_service, "_translator")

        # Test TTS service
        assert hasattr(self.tts_service, "_engine")
        assert hasattr(self.tts_service, "_lock")

    @skip_on_ci
    @requires_tesseract
    @pytest.mark.asyncio
    async def test_service_thread_safety(self):
        """Test that services handle concurrent access safely."""
        import asyncio

        screenshot = Screenshot(coordinates=ScreenCoordinates(0, 0, 100, 100))
        lang_pair = LanguagePair(Language("en"), Language("ru"))

        # Mock services for concurrent testing
        with patch.object(
            self.ocr_service, "extract_text", AsyncMock(return_value=("Concurrent test", 0.9))
        ):
            with patch.object(
                self.translation_service, "translate", AsyncMock(return_value="Тест параллелизма")
            ):
                with patch.object(self.tts_service, "is_available", return_value=False):

                    # Create multiple concurrent workflows
                    tasks = [
                        self.workflow_service.process_screenshot(screenshot, lang_pair)
                        for _ in range(5)
                    ]

                    # Execute concurrently
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # All should succeed
                    assert len(results) == 5
                    for result in results:
                        assert not isinstance(result, Exception)
                        assert result is not None

"""
Translation application service - coordinates translation operations.
"""

from typing import Optional

from ...domain.entities.screenshot import Screenshot
from ...domain.entities.translation import Translation
from ...domain.protocols.repositories import TranslationRepository
from ...domain.protocols.services import TranslationService, TTSService
from ...domain.services.translation_workflow import TranslationWorkflowService
from ..dto.translation_dto import TranslationRequest, TranslationResponse
from ..use_cases.translation_use_cases import (
    GetTranslationHistoryUseCase,
    TranslateScreenshotUseCase,
    TranslateTextUseCase,
)
from .application_service_base import ApplicationServiceBase


class TranslationApplicationService(ApplicationServiceBase):
    """Application service for translation operations."""

    def __init__(
        self,
        translation_service: TranslationService,
        translation_repository: TranslationRepository,
        workflow_service: TranslationWorkflowService,
        tts_service: Optional[TTSService] = None,
    ):
        super().__init__()
        self._translate_text_use_case = TranslateTextUseCase(
            translation_service, translation_repository, tts_service
        )
        self._translate_screenshot_use_case = TranslateScreenshotUseCase(
            workflow_service, translation_repository
        )
        self._get_history_use_case = GetTranslationHistoryUseCase(translation_repository)

    async def translate_text(self, request: TranslationRequest) -> TranslationResponse:
        """Translate text."""
        return await self._translate_text_use_case.execute(request)

    async def translate_screenshot(
        self, screenshot: Screenshot, request: TranslationRequest
    ) -> TranslationResponse:
        """Translate screenshot text."""
        return await self._translate_screenshot_use_case.execute(screenshot, request)

    async def get_translation_history(self, limit: int = 100) -> list[Translation]:
        """Get translation history."""
        return await self._get_history_use_case.execute(limit)

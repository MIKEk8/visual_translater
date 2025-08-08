"""
Translation use cases - orchestrate translation operations.
"""

from typing import Optional

from ...domain.entities.screenshot import Screenshot
from ...domain.entities.translation import Translation
from ...domain.protocols.repositories import TranslationRepository
from ...domain.protocols.services import TranslationService
from ...domain.services.translation_workflow import TranslationWorkflowService
from ...domain.value_objects.language import Language, LanguagePair
from ..dto.translation_dto import TranslationRequest, TranslationResponse
from ..services.application_service_base import ApplicationServiceBase


class TranslateTextUseCase(ApplicationServiceBase):
    """Use case for translating text with optional caching."""

    def __init__(
        self,
        translation_service: TranslationService,
        cache_service: Optional[object] = None,
    ):
        self.translation_service = translation_service
        self.cache_service = cache_service

    async def execute(self, request: TranslationRequest) -> Optional[TranslationResponse]:
        """Execute text translation."""

        source_lang = Language(request.source_language)
        target_lang = Language(request.target_language)
        language_pair = LanguagePair(source_lang, target_lang)

        # Try cache first
        if self.cache_service:
            cached = self.cache_service.get_cached_translation(request.text, language_pair)
            if cached:
                return TranslationResponse(
                    original_text=request.text,
                    translated_text=cached.translated.content,
                    source_language=request.source_language,
                    target_language=request.target_language,
                    is_cached=True,
                    confidence=getattr(cached.translated, "confidence", None),
                )

        try:
            translated_text = await self.translation_service.translate(request.text, language_pair)
        except Exception:
            return None

        if not translated_text:
            return None

        if self.cache_service:
            try:
                self.cache_service.cache_translation(request.text, translated_text, language_pair)
            except Exception:
                pass

        return TranslationResponse(
            original_text=request.text,
            translated_text=translated_text,
            source_language=request.source_language,
            target_language=request.target_language,
            is_cached=False,
        )


class TranslateScreenshotUseCase(ApplicationServiceBase):
    """Use case for translating screenshot text."""

    def __init__(self, workflow_service: TranslationWorkflowService):
        self.workflow_service = workflow_service

    async def execute(
        self, screenshot: Screenshot, language_pair: LanguagePair, auto_tts: bool = False
    ) -> Optional[dict]:
        """Execute screenshot translation."""

        try:
            translation = await self.workflow_service.process_screenshot(
                screenshot, language_pair, auto_tts=auto_tts
            )
        except Exception:
            return None

        if not translation:
            return None

        if hasattr(translation, "to_dict"):
            return translation.to_dict()

        return None


class GetTranslationHistoryUseCase(ApplicationServiceBase):
    """Use case for retrieving translation history."""

    def __init__(self, translation_repository: TranslationRepository):
        self.translation_repository = translation_repository

    async def execute(self, limit: int = 100) -> list[Translation]:
        """Execute history retrieval."""
        return await self.translation_repository.get_recent(limit)

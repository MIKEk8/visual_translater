"""
Translation use cases - orchestrate translation operations.
"""

from typing import Optional

from ...domain.entities.screenshot import Screenshot
from ...domain.entities.translation import Translation
from ...domain.protocols.repositories import TranslationRepository
from ...domain.protocols.services import TranslationService, TTSService
from ...domain.services.translation_workflow import TranslationWorkflowService
from ...domain.value_objects.language import Language, LanguagePair
from ...domain.value_objects.text import Text, TranslatedText
from ..dto.translation_dto import TranslationRequest, TranslationResponse
from ..services.application_service_base import ApplicationServiceBase
from ..validators.translation_validator import TranslationValidator


class TranslateTextUseCase(ApplicationServiceBase):
    """Use case for translating text."""

    def __init__(
        self,
        translation_service: TranslationService,
        translation_repository: TranslationRepository,
        tts_service: Optional[TTSService] = None,
        validator: Optional[TranslationValidator] = None,
    ):
        self.translation_service = translation_service
        self.translation_repository = translation_repository
        self.tts_service = tts_service
        self.validator = validator or TranslationValidator()

    async def execute(self, request: TranslationRequest) -> TranslationResponse:
        """Execute text translation."""

        # Validate request
        validation_result = self.validator.validate_translation_request(request)
        if not validation_result.is_valid:
            return TranslationResponse.error(validation_result.errors)

        try:
            # Create language pair
            source_lang = Language(request.source_language)
            target_lang = Language(request.target_language)
            language_pair = LanguagePair(source_lang, target_lang)

            # Translate text
            translated_text = await self.translation_service.translate(request.text, language_pair)

            if not translated_text:
                return TranslationResponse.error(["Translation failed"])

            # Create translation entity
            translation = Translation(
                original=Text(request.text),
                translated=TranslatedText(translated_text),
                language_pair=language_pair,
            )

            # Save to repository
            await self.translation_repository.save(translation)

            # Text-to-speech if enabled
            if request.auto_tts and self.tts_service:
                await self.tts_service.speak(translated_text, target_lang)

            return TranslationResponse.success(translation)

        except Exception as e:
            return TranslationResponse.error([f"Translation failed: {str(e)}"])


class TranslateScreenshotUseCase(ApplicationServiceBase):
    """Use case for translating screenshot text."""

    def __init__(
        self,
        workflow_service: TranslationWorkflowService,
        translation_repository: TranslationRepository,
        validator: Optional[TranslationValidator] = None,
    ):
        self.workflow_service = workflow_service
        self.translation_repository = translation_repository
        self.validator = validator or TranslationValidator()

    async def execute(
        self, screenshot: Screenshot, request: TranslationRequest
    ) -> TranslationResponse:
        """Execute screenshot translation."""

        # Validate request
        validation_result = self.validator.validate_screenshot_translation(screenshot, request)
        if not validation_result.is_valid:
            return TranslationResponse.error(validation_result.errors)

        try:
            # Create language pair
            source_lang = Language(request.source_language)
            target_lang = Language(request.target_language)
            language_pair = LanguagePair(source_lang, target_lang)

            # Process through workflow
            translation = await self.workflow_service.process_screenshot(
                screenshot, language_pair, request.auto_tts
            )

            if not translation:
                return TranslationResponse.error(["Screenshot translation failed"])

            # Save to repository
            await self.translation_repository.save(translation)

            return TranslationResponse.success(translation)

        except Exception as e:
            return TranslationResponse.error([f"Screenshot translation failed: {str(e)}"])


class GetTranslationHistoryUseCase(ApplicationServiceBase):
    """Use case for retrieving translation history."""

    def __init__(self, translation_repository: TranslationRepository):
        self.translation_repository = translation_repository

    async def execute(self, limit: int = 100) -> list[Translation]:
        """Execute history retrieval."""
        return await self.translation_repository.get_recent(limit)

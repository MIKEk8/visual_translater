"""
Preferences use cases - manage user preferences.
"""

from ...domain.entities.preferences import UserPreferences
from ...domain.value_objects.language import Language
from ..dto.preferences_dto import PreferencesRequest, PreferencesResponse
from ..services.application_service_base import ApplicationServiceBase
from ..validators.preferences_validator import PreferencesValidator


class UpdatePreferencesUseCase(ApplicationServiceBase):
    """Use case for updating user preferences."""

    def __init__(self, validator: PreferencesValidator = None):
        self.validator = validator or PreferencesValidator()

    def execute(
        self, current_preferences: UserPreferences, request: PreferencesRequest
    ) -> PreferencesResponse:
        """Execute preferences update."""

        # Validate request
        validation_result = self.validator.validate_preferences_request(request)
        if not validation_result.is_valid:
            return PreferencesResponse.error(validation_result.errors)

        try:
            # Update preferences
            if request.target_language:
                current_preferences.target_language = Language(request.target_language)

            if request.ocr_language:
                current_preferences.ocr_language = Language(request.ocr_language)

            if request.auto_tts is not None:
                current_preferences.auto_tts = request.auto_tts

            if request.tts_voice:
                current_preferences.tts_voice = request.tts_voice

            if request.tts_rate is not None:
                current_preferences.tts_rate = request.tts_rate

            if request.tts_volume is not None:
                current_preferences.tts_volume = request.tts_volume

            if request.cache_enabled is not None:
                current_preferences.cache_enabled = request.cache_enabled

            if request.theme:
                current_preferences.theme = request.theme

            if request.hotkeys:
                current_preferences.hotkeys.update(request.hotkeys)

            return PreferencesResponse.success(current_preferences)

        except Exception as e:
            return PreferencesResponse.error([f"Preferences update failed: {str(e)}"])

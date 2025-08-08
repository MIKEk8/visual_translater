"""
Preferences validation.
"""

from typing import List

from ..dto.preferences_dto import PreferencesRequest
from .validator_base import ValidationResult


class PreferencesValidator:
    """Validator for preferences operations."""

    def validate_preferences_request(self, request: PreferencesRequest) -> ValidationResult:
        """Validate preferences request."""
        errors = []

        # Check languages
        if request.target_language and not self._is_valid_language_code(request.target_language):
            errors.append("Invalid target language code")

        if request.ocr_language and not self._is_valid_language_code(request.ocr_language):
            errors.append("Invalid OCR language code")

        # Check TTS settings
        if request.tts_rate is not None:
            if not 50 <= request.tts_rate <= 300:
                errors.append("TTS rate must be between 50 and 300")

        if request.tts_volume is not None:
            if not 0.0 <= request.tts_volume <= 1.0:
                errors.append("TTS volume must be between 0 and 1")

        # Check theme
        if request.theme and request.theme not in ["light", "dark", "auto"]:
            errors.append("Theme must be light, dark, or auto")

        # Check hotkeys
        if request.hotkeys:
            for action, key_combo in request.hotkeys.items():
                if not key_combo or not key_combo.strip():
                    errors.append(f"Empty hotkey combination for action: {action}")

        return ValidationResult.success() if not errors else ValidationResult.error(errors)

    def _is_valid_language_code(self, code: str) -> bool:
        """Check if language code is valid."""
        valid_codes = {
            "auto",
            "ru",
            "en",
            "ja",
            "de",
            "fr",
            "es",
            "it",
            "pt",
            "zh",
            "ko",
            "ar",
            "hi",
            "th",
            "vi",
            "pl",
            "nl",
        }
        return code in valid_codes

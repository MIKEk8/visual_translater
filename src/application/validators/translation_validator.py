"""
Translation validation.
"""

from typing import List

from ...domain.entities.screenshot import Screenshot
from ..dto.translation_dto import TranslationRequest
from .validator_base import ValidationResult


class TranslationValidator:
    """Validator for translation operations."""

    def validate_translation_request(self, request: TranslationRequest) -> ValidationResult:
        """Validate translation request."""
        errors = []

        # Check text
        if not request.text or not request.text.strip():
            errors.append("Text cannot be empty")

        if len(request.text) > 5000:
            errors.append("Text too long (maximum 5000 characters)")

        # Check languages
        if not self._is_valid_language_code(request.source_language):
            errors.append("Invalid source language code")

        if not self._is_valid_language_code(request.target_language):
            errors.append("Invalid target language code")

        if request.source_language == request.target_language and request.source_language != "auto":
            errors.append("Source and target languages must be different")

        return ValidationResult.success() if not errors else ValidationResult.error(errors)

    def validate_screenshot_translation(
        self, screenshot: Screenshot, request: TranslationRequest
    ) -> ValidationResult:
        """Validate screenshot translation request."""
        errors = []

        # Check screenshot
        if not screenshot.is_valid:
            errors.append("Invalid screenshot")

        if not screenshot.has_text:
            errors.append("Screenshot has no extracted text")

        # Check translation request
        translation_result = self.validate_translation_request(request)
        if not translation_result.is_valid:
            errors.extend(translation_result.errors)

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

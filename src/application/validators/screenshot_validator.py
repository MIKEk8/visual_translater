"""
Screenshot validation.
"""

from typing import List

from ..dto.screenshot_dto import ScreenshotRequest
from .validator_base import ValidationResult


class ScreenshotValidator:
    """Validator for screenshot operations."""

    def validate_capture_request(self, request: ScreenshotRequest) -> ValidationResult:
        """Validate screenshot capture request."""
        errors = []

        # Check coordinates
        if request.x1 < 0 or request.y1 < 0:
            errors.append("Coordinates cannot be negative")

        if request.x2 <= request.x1 or request.y2 <= request.y1:
            errors.append("Invalid rectangle: x2/y2 must be greater than x1/y1")

        # Check area size (reasonable limits)
        width = request.x2 - request.x1
        height = request.y2 - request.y1

        if width < 10 or height < 10:
            errors.append("Screenshot area too small (minimum 10x10)")

        if width > 5000 or height > 5000:
            errors.append("Screenshot area too large (maximum 5000x5000)")

        # Check OCR settings
        if request.extract_text and request.ocr_language:
            if not self._is_valid_language_code(request.ocr_language):
                errors.append("Invalid OCR language code")

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

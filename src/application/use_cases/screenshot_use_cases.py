"""
Screenshot use cases - orchestrate screenshot operations.
"""

from typing import Optional

from ...domain.entities.screenshot import Screenshot
from ...domain.protocols.services import OCRService, ScreenCaptureService
from ...domain.value_objects.coordinates import ScreenCoordinates
from ...domain.value_objects.language import Language
from ..dto.screenshot_dto import ScreenshotRequest, ScreenshotResponse
from ..services.application_service_base import ApplicationServiceBase
from ..validators.screenshot_validator import ScreenshotValidator


class CaptureScreenshotUseCase(ApplicationServiceBase):
    """Use case for capturing screenshots."""

    def __init__(
        self,
        screen_capture_service: ScreenCaptureService,
        ocr_service: Optional[OCRService] = None,
        validator: Optional[ScreenshotValidator] = None,
    ):
        self.screen_capture_service = screen_capture_service
        self.ocr_service = ocr_service
        self.validator = validator or ScreenshotValidator()

    async def execute(self, request: ScreenshotRequest) -> ScreenshotResponse:
        """Execute screenshot capture."""

        # Validate request
        validation_result = self.validator.validate_capture_request(request)
        if not validation_result.is_valid:
            return ScreenshotResponse.error(validation_result.errors)

        try:
            # Convert coordinates
            coordinates = ScreenCoordinates(request.x1, request.y1, request.x2, request.y2)

            # Capture screenshot
            image = await self.screen_capture_service.capture_area(coordinates)

            # Create screenshot entity
            screenshot = Screenshot(coordinates=coordinates, image=image)

            # Extract text if OCR enabled
            if request.extract_text and self.ocr_service:
                language = Language(request.ocr_language or "auto")
                text, confidence = await self.ocr_service.extract_text(image, language)
                screenshot.extract_text(text, confidence)

            return ScreenshotResponse.success(screenshot)

        except Exception as e:
            return ScreenshotResponse.error([f"Screenshot capture failed: {str(e)}"])


class SelectAreaUseCase(ApplicationServiceBase):
    """Use case for interactive area selection."""

    def __init__(self, screen_capture_service: ScreenCaptureService):
        self.screen_capture_service = screen_capture_service

    async def execute(self) -> Optional[ScreenCoordinates]:
        """Execute area selection."""
        return await self.screen_capture_service.select_area()

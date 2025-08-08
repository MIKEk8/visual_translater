"""
Screenshot application service - coordinates screenshot operations.
"""

from typing import Optional

from ...domain.protocols.services import OCRService, ScreenCaptureService
from ...domain.value_objects.coordinates import ScreenCoordinates
from ..dto.screenshot_dto import ScreenshotRequest, ScreenshotResponse
from ..use_cases.screenshot_use_cases import CaptureScreenshotUseCase, SelectAreaUseCase
from .application_service_base import ApplicationServiceBase


class ScreenshotApplicationService(ApplicationServiceBase):
    """Application service for screenshot operations."""

    def __init__(
        self, screen_capture_service: ScreenCaptureService, ocr_service: Optional[OCRService] = None
    ):
        super().__init__()
        self._capture_use_case = CaptureScreenshotUseCase(screen_capture_service, ocr_service)
        self._select_area_use_case = SelectAreaUseCase(screen_capture_service)

    async def capture_screenshot(self, request: ScreenshotRequest) -> ScreenshotResponse:
        """Capture screenshot."""
        return await self._capture_use_case.execute(request)

    async def select_area(self) -> Optional[ScreenCoordinates]:
        """Select screen area interactively."""
        return await self._select_area_use_case.execute()

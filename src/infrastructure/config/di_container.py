"""
Dependency injection container for infrastructure layer.
"""

from typing import Any, Dict, Optional

from ...application.services.screenshot_app_service import ScreenshotApplicationService
from ...application.services.translation_app_service import TranslationApplicationService
from ...domain.services.translation_workflow import TranslationWorkflowService
from ..adapters.config_adapter import ConfigurationAdapter
from ..external.cache_integration import TranslationCacheIntegration
from ..repositories.screenshot_repository import FileScreenshotRepository
from ..repositories.translation_repository import JsonTranslationRepository
from ..services.ocr_service import TesseractOCRService
from ..services.screen_capture_service import PILScreenCaptureService
from ..services.translation_service import GoogleTranslationService
from ..services.tts_service import PyttsxTTSService


class InfrastructureDIContainer:
    """Dependency injection container for infrastructure components."""

    def __init__(self):
        self._instances: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}

    def register_singleton(self, name: str, instance: Any) -> None:
        """Register singleton instance."""
        self._singletons[name] = instance

    def register_factory(self, name: str, factory: callable) -> None:
        """Register factory function."""
        self._instances[name] = factory

    def get(self, name: str) -> Any:
        """Get instance by name."""
        # Check singletons first
        if name in self._singletons:
            return self._singletons[name]

        # Create from factory
        if name in self._instances:
            factory = self._instances[name]
            instance = factory()
            return instance

        raise ValueError(f"No registration found for: {name}")

    def configure_default_bindings(self) -> None:
        """Configure default infrastructure bindings."""

        # Repositories
        self.register_singleton("translation_repository", JsonTranslationRepository())
        self.register_singleton("screenshot_repository", FileScreenshotRepository())

        # External services
        self.register_singleton("ocr_service", TesseractOCRService())
        self.register_singleton("translation_service", GoogleTranslationService())
        self.register_singleton("tts_service", PyttsxTTSService())
        self.register_singleton("screen_capture_service", PILScreenCaptureService())

        # Adapters and integrations
        self.register_singleton("config_adapter", ConfigurationAdapter())
        self.register_singleton("cache_integration", TranslationCacheIntegration())

        # Domain services
        self.register_factory(
            "translation_workflow",
            lambda: TranslationWorkflowService(
                self.get("ocr_service"), self.get("translation_service"), self.get("tts_service")
            ),
        )

        # Application services
        self.register_factory(
            "translation_app_service",
            lambda: TranslationApplicationService(
                self.get("translation_service"),
                self.get("translation_repository"),
                self.get("translation_workflow"),
                self.get("tts_service"),
            ),
        )

        self.register_factory(
            "screenshot_app_service",
            lambda: ScreenshotApplicationService(
                self.get("screen_capture_service"), self.get("ocr_service")
            ),
        )


# Global container instance
container = InfrastructureDIContainer()
container.configure_default_bindings()


def get_container() -> InfrastructureDIContainer:
    """Get global DI container."""
    return container

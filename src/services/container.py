from typing import Any, Callable, Dict, Optional, Type, TypeVar

from src.utils.logger import logger

T = TypeVar("T")


class DIContainer:
    """Simple Dependency Injection Container"""

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}

        logger.debug("DI Container initialized")

    def register_singleton(self, interface: Type[T], implementation: Type[T]) -> None:
        """Register a singleton service"""
        key = self._get_key(interface)
        self._services[key] = (implementation, True)
        logger.debug(f"Registered singleton: {key}")

    def register_transient(self, interface: Type[T], implementation: Type[T]) -> None:
        """Register a transient service (new instance each time)"""
        key = self._get_key(interface)
        self._services[key] = (implementation, False)
        logger.debug(f"Registered transient: {key}")

    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Register a factory function"""
        key = self._get_key(interface)
        self._factories[key] = factory
        logger.debug(f"Registered factory: {key}")

    def register_instance(self, interface: Type[T], instance: T) -> None:
        """Register a specific instance"""
        key = self._get_key(interface)
        self._singletons[key] = instance
        logger.debug(f"Registered instance: {key}")

    def get(self, interface: Type[T]) -> T:
        """Get service instance"""
        key = self._get_key(interface)

        # Check if we have a cached singleton
        if key in self._singletons:
            return self._singletons[key]

        # Check if we have a factory
        if key in self._factories:
            instance = self._factories[key]()
            logger.debug(f"Created instance from factory: {key}")
            return instance

        # Check if we have a registered service
        if key in self._services:
            implementation, is_singleton = self._services[key]

            # Create instance
            instance = self._create_instance(implementation)

            # Cache if singleton
            if is_singleton:
                self._singletons[key] = instance

            logger.debug(f"Created instance: {key} (singleton: {is_singleton})")
            return instance

        raise ValueError(f"Service not registered: {key}")

    def _get_key(self, interface: Type) -> str:
        """Get string key for interface"""
        return f"{interface.__module__}.{interface.__name__}"

    def _create_instance(self, implementation: Type[T]) -> T:
        """Create instance with dependency injection"""
        try:
            # Simple creation - can be enhanced with constructor injection
            return implementation()
        except Exception as e:
            logger.error(f"Failed to create instance of {implementation}", error=e)
            raise

    def clear(self) -> None:
        """Clear all registered services"""
        self._services.clear()
        self._singletons.clear()
        self._factories.clear()
        logger.debug("DI Container cleared")

    def get_registered_services(self) -> Dict[str, dict]:
        """Get information about registered services"""
        services = {}

        for key, (impl, is_singleton) in self._services.items():
            services[key] = {
                "implementation": impl.__name__,
                "singleton": is_singleton,
                "instantiated": key in self._singletons,
            }

        for key in self._factories:
            services[key] = {"implementation": "Factory", "singleton": False, "instantiated": False}

        for key in self._singletons:
            if key not in services:
                services[key] = {
                    "implementation": "Instance",
                    "singleton": True,
                    "instantiated": True,
                }

        return services


# Global container instance
container = DIContainer()


def setup_default_services(target_container: Optional[DIContainer] = None):
    """Setup default service registrations"""
    if target_container is None:
        target_container = container

    from src.core.ocr_engine import OCRProcessor
    from src.core.screenshot_engine import ScreenshotEngine
    from src.core.translation_engine import TranslationProcessor
    from src.core.tts_engine import TTSProcessor
    from src.repositories import (
        FileScreenshotRepository,
        FileTranslationRepository,
        RepositoryManager,
        ScreenshotRepository,
        TranslationRepository,
        get_repository_manager,
    )
    from src.services.circuit_breaker import get_circuit_breaker_manager
    from src.services.config_manager import ConfigManager
    from src.services.plugin_service import PluginService
    from src.utils.alert_system import get_alert_manager
    from src.utils.circuit_breaker_monitor import get_circuit_breaker_monitor
    from src.utils.enhanced_metrics import get_enhanced_metrics_collector
    from src.utils.monitoring_dashboard import get_monitoring_dashboard

    # Register core services as singletons
    target_container.register_singleton(ConfigManager, ConfigManager)
    target_container.register_singleton(ScreenshotEngine, ScreenshotEngine)

    # Register plugin service
    def create_plugin_service():
        config_manager = target_container.get(ConfigManager)
        return PluginService(config_manager)

    target_container.register_factory(PluginService, create_plugin_service)

    # Register processors with factories to handle configuration dependencies
    def create_ocr_processor():
        config_manager = target_container.get(ConfigManager)
        return OCRProcessor(config_manager.get_config().image_processing)

    def create_translation_processor():
        config_manager = target_container.get(ConfigManager)
        return TranslationProcessor(config_manager.get_config().features.cache_translations)

    def create_tts_processor():
        config_manager = target_container.get(ConfigManager)
        return TTSProcessor(config_manager.get_config().tts)

    target_container.register_factory(OCRProcessor, create_ocr_processor)
    target_container.register_factory(TranslationProcessor, create_translation_processor)
    target_container.register_factory(TTSProcessor, create_tts_processor)

    # Register repository services
    def create_repository_manager():
        config_manager = target_container.get(ConfigManager)
        data_dir = getattr(config_manager.get_config(), "data_directory", "data")
        return get_repository_manager(data_dir)

    def create_translation_repository():
        config_manager = target_container.get(ConfigManager)
        data_dir = getattr(config_manager.get_config(), "data_directory", "data")
        return FileTranslationRepository(data_dir)

    def create_screenshot_repository():
        config_manager = target_container.get(ConfigManager)
        data_dir = getattr(config_manager.get_config(), "data_directory", "data")
        return FileScreenshotRepository(data_dir)

    target_container.register_factory(RepositoryManager, create_repository_manager)
    target_container.register_factory(TranslationRepository, create_translation_repository)
    target_container.register_factory(ScreenshotRepository, create_screenshot_repository)

    # Register circuit breaker services
    target_container.register_instance(
        type(get_circuit_breaker_manager()), get_circuit_breaker_manager()
    )
    target_container.register_instance(
        type(get_circuit_breaker_monitor()), get_circuit_breaker_monitor()
    )

    # Register enhanced monitoring services
    def create_enhanced_metrics():
        config_manager = target_container.get(ConfigManager)
        data_dir = getattr(config_manager.get_config(), "data_directory", "data")
        return get_enhanced_metrics_collector(data_dir)

    def create_alert_manager():
        config_manager = target_container.get(ConfigManager)
        data_dir = getattr(config_manager.get_config(), "data_directory", "data")
        return get_alert_manager(data_dir)

    def create_monitoring_dashboard():
        config_manager = target_container.get(ConfigManager)
        data_dir = getattr(config_manager.get_config(), "data_directory", "data")
        return get_monitoring_dashboard(data_dir)

    target_container.register_factory(
        type(get_enhanced_metrics_collector()), create_enhanced_metrics
    )
    target_container.register_factory(type(get_alert_manager()), create_alert_manager)
    target_container.register_factory(type(get_monitoring_dashboard()), create_monitoring_dashboard)

    logger.info(f"Default services registered in DI container ({id(target_container)})")

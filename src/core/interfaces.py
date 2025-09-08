"""
Core Interfaces for Screen Translator v2.0

This module defines abstract interfaces to break circular dependencies
and enable loose coupling between major system components.

Interface Hierarchy:
- ITrayManager: System tray management abstraction  
- IApplicationController: Main application coordination
- ISystemIntegration: OS-level integration services
- IScreenshotEngine: Screen capture abstraction
- IOCREngine: OCR processing abstraction
- ITranslationEngine: Translation service abstraction
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.models.screenshot_data import ScreenshotData
from src.models.translation import Translation


class ITrayManager(ABC):
    """Abstract interface for system tray management"""
    
    @abstractmethod
    def show_notification(self, title: str, message: str, duration: int = 3) -> None:
        """Show system notification"""
        pass
    
    @abstractmethod
    def update_menu(self) -> None:
        """Update tray menu items"""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Cleanup tray resources"""
        pass


class ISystemIntegration(ABC):
    """Abstract interface for OS-level integration"""
    
    @abstractmethod
    def register_hotkeys(self) -> bool:
        """Register global hotkeys"""
        pass
    
    @abstractmethod
    def unregister_hotkeys(self) -> None:
        """Unregister global hotkeys"""
        pass
    
    @abstractmethod
    def get_active_window_info(self) -> Dict[str, Any]:
        """Get active window information"""
        pass


class IApplicationController(ABC):
    """Abstract interface for main application coordination"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize application components"""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Graceful application shutdown"""
        pass
    
    @abstractmethod
    def process_screenshot_request(self, coordinates: Tuple[int, int, int, int]) -> None:
        """Process screenshot capture request"""
        pass


class IScreenshotEngine(ABC):
    """Abstract interface for screen capture functionality"""
    
    @abstractmethod
    def capture_area(
        self,
        x1: int,
        y1: int, 
        x2: int,
        y2: int,
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None,
    ) -> Optional[ScreenshotData]:
        """Capture screenshot of specified area"""
        pass
    
    @abstractmethod
    def get_screen_dimensions(self) -> Tuple[int, int]:
        """Get screen width and height"""
        pass


class IOCREngine(ABC):
    """Abstract interface for OCR text recognition"""
    
    @abstractmethod
    def extract_text(self, image_data: ScreenshotData) -> Tuple[str, float]:
        """Extract text from image with confidence score"""
        pass
    
    @abstractmethod
    def set_language(self, language_code: str) -> bool:
        """Set OCR language"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if OCR engine is available"""
        pass


class ITranslationEngine(ABC):
    """Abstract interface for translation services"""
    
    @abstractmethod
    def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = 'auto'
    ) -> Translation:
        """Translate text to target language"""
        pass
    
    @abstractmethod
    def detect_language(self, text: str) -> str:
        """Detect text language"""
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes"""
        pass


class ITTSEngine(ABC):
    """Abstract interface for text-to-speech"""
    
    @abstractmethod
    def speak(self, text: str, language: str = 'en') -> bool:
        """Speak text in specified language"""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop current speech"""
        pass
    
    @abstractmethod
    def set_voice_settings(self, rate: int, volume: float) -> None:
        """Configure voice settings"""
        pass


class IConfigManager(ABC):
    """Abstract interface for configuration management"""
    
    @abstractmethod
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        pass
    
    @abstractmethod
    def set_value(self, key: str, value: Any) -> None:
        """Set configuration value"""
        pass
    
    @abstractmethod
    def add_observer(self, observer: 'IConfigObserver') -> None:
        """Add configuration change observer"""
        pass
    
    @abstractmethod
    def save_config(self) -> bool:
        """Save configuration to file"""
        pass


class IConfigObserver(ABC):
    """Abstract interface for configuration change observers"""
    
    @abstractmethod
    def on_config_changed(self, key: str, old_value: Any, new_value: Any) -> None:
        """Called when configuration changes"""
        pass


class IDIContainer(ABC):
    """Abstract interface for dependency injection container"""
    
    @abstractmethod
    def get(self, interface_type: type) -> Any:
        """Get service instance by interface type"""
        pass
    
    @abstractmethod
    def register_singleton(self, interface_type: type, implementation_type: type) -> None:
        """Register singleton service"""
        pass
    
    @abstractmethod
    def register_instance(self, interface_type: type, instance: Any) -> None:
        """Register specific instance"""
        pass


# Additional interfaces for comprehensive loose coupling

class IHotkeyService(ABC):
    """Abstract interface for global hotkey management"""
    
    @abstractmethod
    def register_hotkey(self, hotkey: str, callback: Callable) -> bool:
        """Register global hotkey"""
        pass
    
    @abstractmethod
    def unregister_hotkey(self, hotkey: str) -> bool:
        """Unregister global hotkey"""
        pass
    
    @abstractmethod
    def unregister_all(self) -> None:
        """Unregister all hotkeys"""
        pass


class ICacheService(ABC):
    """Abstract interface for caching services"""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with optional TTL"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete cached value"""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all cached values"""
        pass


class INotificationService(ABC):
    """Abstract interface for system notifications"""
    
    @abstractmethod
    def show_success(self, message: str, title: str = "Success") -> None:
        """Show success notification"""
        pass
    
    @abstractmethod
    def show_error(self, message: str, title: str = "Error") -> None:
        """Show error notification"""
        pass
    
    @abstractmethod
    def show_info(self, message: str, title: str = "Info") -> None:
        """Show info notification"""
        pass


class IPluginManager(ABC):
    """Abstract interface for plugin management"""
    
    @abstractmethod
    def load_plugin(self, plugin_name: str) -> bool:
        """Load plugin by name"""
        pass
    
    @abstractmethod
    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload plugin by name"""
        pass
    
    @abstractmethod
    def get_loaded_plugins(self) -> List[str]:
        """Get list of loaded plugin names"""
        pass
    
    @abstractmethod
    def is_plugin_loaded(self, plugin_name: str) -> bool:
        """Check if plugin is loaded"""
        pass


class IBatchProcessor(ABC):
    """Abstract interface for batch processing operations"""
    
    @abstractmethod
    def process_batch(self, items: List[Any], callback: Optional[Callable] = None) -> List[Any]:
        """Process batch of items"""
        pass
    
    @abstractmethod
    def get_progress(self) -> float:
        """Get current processing progress (0.0 to 1.0)"""
        pass
    
    @abstractmethod
    def cancel_batch(self) -> bool:
        """Cancel current batch processing"""
        pass
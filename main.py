#!/usr/bin/env python3
"""
Screen Translator v2.0 - Main Application Entry Point
Modern modular translation application with AI-powered OCR and advanced features.
"""

import sys
import os
import argparse
import signal
from pathlib import Path

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description="Screen Translator v2.0 - Universal screen text translator"
    )
    
    parser.add_argument(
        '--windowed', 
        action='store_true',
        help='Run in windowed mode (no console)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run system tests'
    )
    
    args = parser.parse_args()
    
    # Redirect stdout/stderr for windowed mode
    if args.windowed:
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
    
    # Run tests if requested
    if args.test:
        return run_tests()
    
    # Initialize logger first for error handling
    logger = None
    try:
        from src.utils.logger import logger
    except Exception:
        pass  # Logger will remain None if import fails
    
    # Initialize and run application
    try:
        from src.core.application import ScreenTranslatorApp
        from src.services.container import container, setup_default_services
        from src.services.config_manager import ConfigManager
        from src.services.notification_service import initialize_notifications, NotificationConfig
        from src.services.hotkey_service import initialize_hotkeys, HotkeyConfig
        
        print("Starting Screen Translator v2.0...")
        
        # Setup default services in global container
        setup_default_services()
        
        # Initialize configuration manager with custom config file if provided
        if args.config:
            config_manager = ConfigManager(config_file=args.config)
            container.register_instance(ConfigManager, config_manager)
        
        # Initialize notification system
        notification_config = NotificationConfig(enabled=True)
        notification_service = initialize_notifications(notification_config)
        
        # Initialize hotkey system  
        hotkey_config = HotkeyConfig(enabled=True, show_notifications=True)
        hotkey_service = initialize_hotkeys(hotkey_config)
        
        # Set debug mode if requested
        if args.debug:
            if logger:
                logger.setLevel("DEBUG")
                logger.info("Debug mode enabled")
        
        # Show startup notification
        notification_service.show_success(
            "Screen Translator v2.0", 
            "Application started successfully"
        )
        
        # Initialize main application
        app = ScreenTranslatorApp()
        
        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            print("\nReceived interrupt signal, shutting down...")
            if logger:
                logger.info("Received interrupt signal, shutting down gracefully")
            try:
                app.shutdown()
            except:
                pass
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Register default hotkeys
        def create_hotkey_callbacks(app):
            return {
                "translate_selection": lambda: app.capture_area(),
                "quick_translate_center": lambda: app.quick_translate_center(),
                "quick_translate_bottom": lambda: app.quick_translate_bottom(),
                "repeat_last": lambda: app.repeat_last_translation(),
                "switch_language": lambda: app.switch_language(),
                "show_history": lambda: app.show_translation_history(),
                "show_settings": lambda: app.open_settings(),
                "emergency_stop": lambda: app.shutdown()
            }
        
        hotkey_service.register_default_hotkeys(create_hotkey_callbacks(app))
        
        if logger:
            logger.info("Screen Translator v2.0 started successfully")
        
        # Run application
        try:
            return app.run()
        except KeyboardInterrupt:
            if logger:
                logger.info("Application interrupted by user")
            notification_service.show_info("Shutdown", "Application closed by user")
        finally:
            # Cleanup
            if logger:
                logger.info("Shutting down...")
            hotkey_service.unregister_all()
            notification_service.dismiss_all()
        
        return 0
        
    except ImportError as e:
        error_msg = f"Failed to import required modules: {e}"
        print(error_msg)
        print("Please install dependencies: pip install -r requirements.txt")
        
        # Try to show notification if possible
        try:
            from src.services.notification_service import notify_error
            notify_error("Import Error", error_msg)
        except:
            pass
        
        return 1
    except Exception as e:
        error_msg = f"Application startup failed: {e}"
        print(error_msg)
        if logger:
            logger.error(error_msg)
        
        # Try to show notification if possible
        try:
            from src.services.notification_service import notify_error
            notify_error("Startup Error", error_msg)
        except:
            pass
        
        return 1


def run_tests() -> int:
    """Run system tests."""
    try:
        print("Running Screen Translator v2.0 System Tests...")
        
        # Import and run system integration tests
        from src.tests.integration.test_system_integration import main as test_main
        return test_main()
        
    except ImportError as e:
        print(f"Failed to import test modules: {e}")
        return 1
    except Exception as e:
        print(f"Test execution failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
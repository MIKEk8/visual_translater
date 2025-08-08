"""
Modern hotkey service for Screen Translator v2.0.
Provides cross-platform global hotkey management with advanced features.
"""

import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

try:
    # Primary hotkey library
    import keyboard

    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False

try:
    # Alternative hotkey library
    import pynput.keyboard as pynput_keyboard

    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

try:
    # System-specific implementations
    if sys.platform == "win32":
        import ctypes
        import ctypes.wintypes

        WIN32_AVAILABLE = True
    else:
        WIN32_AVAILABLE = False
except ImportError:
    WIN32_AVAILABLE = False

from src.services.config_manager import ConfigObserver
from src.services.notification_service import get_notification_service
from src.utils.logger import logger


class HotkeyModifier(Enum):
    """Hotkey modifier keys."""

    CTRL = "ctrl"
    ALT = "alt"
    SHIFT = "shift"
    WIN = "win"
    CMD = "cmd"  # macOS


class HotkeyState(Enum):
    """Hotkey registration states."""

    REGISTERED = "registered"
    FAILED = "failed"
    CONFLICTED = "conflicted"
    DISABLED = "disabled"


@dataclass
class HotkeyConfig:
    """Configuration for hotkey system."""

    enabled: bool = True
    suppress_original: bool = True  # Suppress original key function
    show_notifications: bool = True
    detect_conflicts: bool = True
    auto_retry: bool = True
    retry_delay: float = 1.0
    max_retries: int = 3

    # Default hotkeys
    translate_selection: str = "alt+a"
    translate_clipboard: str = "alt+c"
    ocr_screen_area: str = "alt+q"
    repeat_last: str = "alt+s"
    toggle_overlay: str = "alt+o"
    show_history: str = "alt+h"
    show_settings: str = "alt+comma"
    emergency_stop: str = "ctrl+alt+x"


@dataclass
class HotkeyBinding:
    """Individual hotkey binding data."""

    id: str
    key_combination: str
    description: str
    callback: Optional[Callable] = None
    enabled: bool = True
    state: HotkeyState = HotkeyState.REGISTERED
    modifiers: Optional[List[HotkeyModifier]] = None
    key: Optional[str] = None
    registration_time: Optional[datetime] = None
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

    def __post_init__(self):
        if self.registration_time is None:
            self.registration_time = datetime.now()
        if self.modifiers is None:
            self.modifiers = []
        if not self.key and self.key_combination:
            self._parse_key_combination()

    def _parse_key_combination(self) -> None:
        """Parse key combination string into modifiers and key."""
        parts = self.key_combination.lower().split("+")
        self.modifiers = []

        for part in parts[:-1]:  # All but last are modifiers
            if part in ["ctrl", "control"]:
                self.modifiers.append(HotkeyModifier.CTRL)
            elif part in ["alt"]:
                self.modifiers.append(HotkeyModifier.ALT)
            elif part in ["shift"]:
                self.modifiers.append(HotkeyModifier.SHIFT)
            elif part in ["win", "windows", "super"]:
                self.modifiers.append(HotkeyModifier.WIN)
            elif part in ["cmd", "command"]:
                self.modifiers.append(HotkeyModifier.CMD)

        self.key = parts[-1] if parts else ""


class HotkeyBackend:
    """Base class for hotkey backends."""

    def __init__(self, config: HotkeyConfig):
        self._lock = threading.Lock()
        self.config = config
        self.available = False
        self.registered_hotkeys: Dict[str, HotkeyBinding] = {}

    def is_available(self) -> bool:
        """Check if backend is available on current system."""
        return self.available

    def register_hotkey(self, binding: HotkeyBinding) -> bool:
        """Register a hotkey binding."""
        raise NotImplementedError

    def unregister_hotkey(self, hotkey_id: str) -> bool:
        """Unregister a hotkey binding."""
        raise NotImplementedError

    def unregister_all(self) -> bool:
        """Unregister all hotkey bindings."""
        for hotkey_id in list(self.registered_hotkeys.keys()):
            self.unregister_hotkey(hotkey_id)
        return True

    def is_registered(self, hotkey_id: str) -> bool:
        """Check if hotkey is registered."""
        return hotkey_id in self.registered_hotkeys

    def get_registered_hotkeys(self) -> List[HotkeyBinding]:
        """Get list of registered hotkeys."""
        return list(self.registered_hotkeys.values())


class KeyboardBackend(HotkeyBackend):
    """Keyboard library backend for hotkeys."""

    def __init__(self, config: HotkeyConfig):
        super().__init__(config)
        self._lock = threading.Lock()
        self.available = KEYBOARD_AVAILABLE
        self._hooks: Dict[str, Any] = {}

    def register_hotkey(self, binding: HotkeyBinding) -> bool:
        """Register hotkey using keyboard library."""
        if not self.available or not binding.callback:
            return False

        try:
            # Create wrapper callback
            def hotkey_callback():
                self._handle_hotkey_trigger(binding)

            # Register with keyboard library
            hook = keyboard.add_hotkey(
                binding.key_combination, hotkey_callback, suppress=self.config.suppress_original
            )

            # Store hook and binding
            self._hooks[binding.id] = hook
            self.registered_hotkeys[binding.id] = binding
            binding.state = HotkeyState.REGISTERED

            logger.debug(f"Keyboard hotkey registered: {binding.key_combination}")
            return True

        except Exception as e:
            logger.error(f"Failed to register keyboard hotkey {binding.key_combination}: {e}")
            binding.state = HotkeyState.FAILED
            return False

    def unregister_hotkey(self, hotkey_id: str) -> bool:
        """Unregister keyboard hotkey."""
        if hotkey_id not in self._hooks:
            return False

        try:
            keyboard.remove_hotkey(self._hooks[hotkey_id])
            del self._hooks[hotkey_id]

            if hotkey_id in self.registered_hotkeys:
                del self.registered_hotkeys[hotkey_id]

            logger.debug(f"Keyboard hotkey unregistered: {hotkey_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to unregister keyboard hotkey {hotkey_id}: {e}")
            return False

    def _handle_hotkey_trigger(self, binding: HotkeyBinding) -> None:
        """Handle hotkey trigger event."""
        binding.last_triggered = datetime.now()
        binding.trigger_count += 1

        try:
            if binding.callback:
                binding.callback()
        except Exception as e:
            logger.error(f"Hotkey callback error for {binding.id}: {e}")


class PynputBackend(HotkeyBackend):
    """Pynput library backend for hotkeys."""

    def __init__(self, config: HotkeyConfig):
        super().__init__(config)
        self._lock = threading.Lock()
        self.available = PYNPUT_AVAILABLE
        self._listener: Optional[pynput_keyboard.Listener] = None
        self._pressed_keys: Set[pynput_keyboard.Key] = set()
        self._current_hotkeys: Dict[str, HotkeyBinding] = {}
        self._running = False

    def register_hotkey(self, binding: HotkeyBinding) -> bool:
        """Register hotkey using pynput library."""
        if not self.available or not binding.callback:
            return False

        try:
            # Convert key combination to pynput format
            pynput_combo = self._convert_to_pynput_combo(binding)
            if not pynput_combo:
                return False

            # Store binding
            self.registered_hotkeys[binding.id] = binding
            self._current_hotkeys[binding.key_combination] = binding
            binding.state = HotkeyState.REGISTERED

            # Start listener if not running
            if not self._running:
                self._start_listener()

            logger.debug(f"Pynput hotkey registered: {binding.key_combination}")
            return True

        except Exception as e:
            logger.error(f"Failed to register pynput hotkey {binding.key_combination}: {e}")
            binding.state = HotkeyState.FAILED
            return False

    def unregister_hotkey(self, hotkey_id: str) -> bool:
        """Unregister pynput hotkey."""
        if hotkey_id not in self.registered_hotkeys:
            return False

        binding = self.registered_hotkeys[hotkey_id]

        # Remove from tracking
        if binding.key_combination in self._current_hotkeys:
            del self._current_hotkeys[binding.key_combination]

        del self.registered_hotkeys[hotkey_id]

        # Stop listener if no more hotkeys
        if not self._current_hotkeys and self._running:
            self._stop_listener()

        logger.debug(f"Pynput hotkey unregistered: {hotkey_id}")
        return True

    def _start_listener(self) -> None:
        """Start pynput keyboard listener."""
        if self._running:
            return

        self._listener = pynput_keyboard.Listener(
            on_press=self._on_key_press, on_release=self._on_key_release
        )
        self._listener.start()
        self._running = True

        logger.debug("Pynput keyboard listener started")

    def _stop_listener(self) -> None:
        """Stop pynput keyboard listener."""
        if not self._running:
            return

        with self._lock:
            if self._listener:
                self._listener.stop()
                self._listener = None

            self._running = False
            self._pressed_keys.clear()

        logger.debug("Pynput keyboard listener stopped")

    def _on_key_press(self, key) -> None:
        """Handle key press event."""
        self._pressed_keys.add(key)
        self._check_hotkey_combinations()

    def _on_key_release(self, key) -> None:
        """Handle key release event."""
        self._pressed_keys.discard(key)

    def _check_hotkey_combinations(self) -> None:
        """Check if current pressed keys match any hotkey combinations."""
        for combo, binding in self._current_hotkeys.items():
            if self._is_combo_pressed(binding):
                self._handle_hotkey_trigger(binding)

    def _is_combo_pressed(self, binding: HotkeyBinding) -> bool:
        """Check if hotkey combination is currently pressed."""
        # This is a simplified check - full implementation would need
        # proper key combination matching logic
        return False  # Placeholder implementation

    def _convert_to_pynput_combo(self, binding: HotkeyBinding) -> Optional[str]:
        """Convert key combination to pynput format."""
        # Simplified conversion - full implementation needed
        return binding.key_combination

    def _handle_hotkey_trigger(self, binding: HotkeyBinding) -> None:
        """Handle hotkey trigger event."""
        binding.last_triggered = datetime.now()
        binding.trigger_count += 1

        try:
            if binding.callback:
                binding.callback()
        except Exception as e:
            logger.error(f"Hotkey callback error for {binding.id}: {e}")


class Win32Backend(HotkeyBackend):
    """Windows-specific hotkey backend using Win32 API."""

    def __init__(self, config: HotkeyConfig):
        super().__init__(config)
        self._lock = threading.Lock()
        self.available = WIN32_AVAILABLE
        self._hotkey_id_counter = 1000
        self._registered_ids: Dict[str, int] = {}
        self._message_thread: Optional[threading.Thread] = None
        self._running = False

    def register_hotkey(self, binding: HotkeyBinding) -> bool:
        """Register hotkey using Win32 API."""
        if not self.available or not binding.callback:
            return False

        try:
            # Convert to Win32 modifiers and virtual key code
            modifiers, vk_code = self._convert_to_win32(binding)

            # Get unique hotkey ID
            hotkey_id = self._hotkey_id_counter
            self._hotkey_id_counter += 1

            # Register hotkey
            result = ctypes.windll.user32.RegisterHotKey(
                None, hotkey_id, modifiers, vk_code  # Window handle (None for global)
            )

            if result:
                self._registered_ids[binding.id] = hotkey_id
                self.registered_hotkeys[binding.id] = binding
                binding.state = HotkeyState.REGISTERED

                # Start message loop if not running
                if not self._running:
                    self._start_message_loop()

                logger.debug(f"Win32 hotkey registered: {binding.key_combination}")
                return True
            else:
                binding.state = HotkeyState.FAILED
                return False

        except Exception as e:
            logger.error(f"Failed to register Win32 hotkey {binding.key_combination}: {e}")
            binding.state = HotkeyState.FAILED
            return False

    def unregister_hotkey(self, hotkey_id: str) -> bool:
        """Unregister Win32 hotkey."""
        if hotkey_id not in self._registered_ids:
            return False

        try:
            win32_id = self._registered_ids[hotkey_id]
            result = ctypes.windll.user32.UnregisterHotKey(None, win32_id)

            if result:
                del self._registered_ids[hotkey_id]
                if hotkey_id in self.registered_hotkeys:
                    del self.registered_hotkeys[hotkey_id]

                # Stop message loop if no more hotkeys
                if not self._registered_ids and self._running:
                    self._stop_message_loop()

                logger.debug(f"Win32 hotkey unregistered: {hotkey_id}")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Failed to unregister Win32 hotkey {hotkey_id}: {e}")
            return False

    def _convert_to_win32(self, binding: HotkeyBinding) -> tuple:
        """Convert hotkey binding to Win32 modifiers and virtual key code."""
        # Win32 modifier constants
        MOD_ALT = 0x0001
        MOD_CONTROL = 0x0002
        MOD_SHIFT = 0x0004
        MOD_WIN = 0x0008

        modifiers = 0
        for mod in binding.modifiers:
            if mod == HotkeyModifier.ALT:
                modifiers |= MOD_ALT
            elif mod == HotkeyModifier.CTRL:
                modifiers |= MOD_CONTROL
            elif mod == HotkeyModifier.SHIFT:
                modifiers |= MOD_SHIFT
            elif mod == HotkeyModifier.WIN:
                modifiers |= MOD_WIN

        # Convert key to virtual key code
        vk_code = self._get_virtual_key_code(binding.key)

        return modifiers, vk_code

    def _get_virtual_key_code(self, key: str) -> int:
        """Get Windows virtual key code for key."""
        # Common virtual key codes
        vk_codes = {
            "a": 0x41,
            "b": 0x42,
            "c": 0x43,
            "d": 0x44,
            "e": 0x45,
            "f": 0x46,
            "g": 0x47,
            "h": 0x48,
            "i": 0x49,
            "j": 0x4A,
            "k": 0x4B,
            "l": 0x4C,
            "m": 0x4D,
            "n": 0x4E,
            "o": 0x4F,
            "p": 0x50,
            "q": 0x51,
            "r": 0x52,
            "s": 0x53,
            "t": 0x54,
            "u": 0x55,
            "v": 0x56,
            "w": 0x57,
            "x": 0x58,
            "y": 0x59,
            "z": 0x5A,
            "0": 0x30,
            "1": 0x31,
            "2": 0x32,
            "3": 0x33,
            "4": 0x34,
            "5": 0x35,
            "6": 0x36,
            "7": 0x37,
            "8": 0x38,
            "9": 0x39,
            "f1": 0x70,
            "f2": 0x71,
            "f3": 0x72,
            "f4": 0x73,
            "f5": 0x74,
            "f6": 0x75,
            "f7": 0x76,
            "f8": 0x77,
            "f9": 0x78,
            "f10": 0x79,
            "f11": 0x7A,
            "f12": 0x7B,
            "space": 0x20,
            "enter": 0x0D,
            "tab": 0x09,
            "esc": 0x1B,
            "comma": 0xBC,
            "period": 0xBE,
            "semicolon": 0xBA,
        }

        return vk_codes.get(key.lower(), 0)

    def _start_message_loop(self) -> None:
        """Start Win32 message loop in separate thread."""
        with self._lock:
            if self._running:
                return

            self._running = True
            self._message_thread = threading.Thread(target=self._message_loop, daemon=True)
            self._message_thread.start()
            logger.debug("Win32 message loop started")

    def _stop_message_loop(self) -> None:
        """Stop Win32 message loop."""
        with self._lock:
            self._running = False
            if self._message_thread:
                self._message_thread.join(timeout=1.0)
                self._message_thread = None

        logger.debug("Win32 message loop stopped")

    def _message_loop(self) -> None:
        """Win32 message loop to handle hotkey events."""
        try:
            msg = ctypes.wintypes.MSG()
            bRet = ctypes.wintypes.BOOL()

            while self._running:
                try:
                    bRet = ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)

                    if bRet == 0:  # WM_QUIT
                        break
                    elif bRet == -1:  # Error
                        break
                    else:
                        if msg.message == 0x0312:  # WM_HOTKEY
                            self._handle_hotkey_message(msg.wParam)

                        ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                        ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

                except Exception as e:
                    logger.error(f"Win32 message loop error: {e}")
                    # TODO: Performance - Consider using asyncio.sleep() for non-blocking delays
                    time.sleep(0.1)

        except Exception as e:
            logger.error(f"Win32 message loop fatal error: {e}")

    def _handle_hotkey_message(self, hotkey_id: int) -> None:
        """Handle Win32 hotkey message."""
        # Find binding by Win32 hotkey ID
        for binding_id, win32_id in self._registered_ids.items():
            if win32_id == hotkey_id:
                binding = self.registered_hotkeys.get(binding_id)
                if binding:
                    self._handle_hotkey_trigger(binding)
                break

    def _handle_hotkey_trigger(self, binding: HotkeyBinding) -> None:
        """Handle hotkey trigger event."""
        binding.last_triggered = datetime.now()
        binding.trigger_count += 1

        try:
            if binding.callback:
                # Execute callback in main thread if needed
                threading.Thread(target=binding.callback, daemon=True).start()
        except Exception as e:
            logger.error(f"Hotkey callback error for {binding.id}: {e}")


class HotkeyService(ConfigObserver):
    """Main hotkey service with multiple backends and advanced features."""

    def __init__(self, config: Optional[HotkeyConfig] = None):
        """
        Initialize hotkey service.

        Args:
            config: Hotkey configuration
        """
        self._lock = threading.Lock()
        self.config = config or HotkeyConfig()
        self.backends: List[HotkeyBackend] = []
        self.hotkeys: Dict[str, HotkeyBinding] = {}
        self.notification_service = get_notification_service()

        with self._lock:
            # Initialize backends
            self._initialize_backends()

            # Find best available backend
            self.primary_backend = self._get_primary_backend()

            # Default action callbacks
            self.action_callbacks: Dict[str, Callable] = {}

            logger.info(f"Hotkey service initialized with {len(self.backends)} backends")
            logger.debug(f"Primary backend: {type(self.primary_backend).__name__}")

    def _initialize_backends(self) -> None:
        """Initialize all available hotkey backends."""
        # Windows Win32 API (best for Windows)
        if sys.platform == "win32":
            win32_backend = Win32Backend(self.config)
            if win32_backend.is_available():
                self.backends.append(win32_backend)

        # Keyboard library (cross-platform, good compatibility)
        keyboard_backend = KeyboardBackend(self.config)
        if keyboard_backend.is_available():
            self.backends.append(keyboard_backend)

        # Pynput library (cross-platform alternative)
        pynput_backend = PynputBackend(self.config)
        if pynput_backend.is_available():
            self.backends.append(pynput_backend)

    def _get_primary_backend(self) -> Optional[HotkeyBackend]:
        """Get the primary hotkey backend to use."""
        if not self.backends:
            logger.warning("No hotkey backends available")
            return None

        # Prefer Win32 on Windows, then keyboard, then pynput
        for backend in self.backends:
            if isinstance(backend, Win32Backend):
                return backend

        for backend in self.backends:
            if isinstance(backend, KeyboardBackend):
                return backend

        # Return first available backend
        return self.backends[0]

    def register_hotkey(
        self,
        hotkey_id: str,
        key_combination: str,
        callback: Callable,
        description: str = "",
        enabled: bool = True,
    ) -> bool:
        """
        Register a new hotkey.

        Args:
            hotkey_id: Unique hotkey identifier
            key_combination: Key combination string (e.g., "ctrl+alt+a")
            callback: Function to call when hotkey is triggered
            description: Human-readable description
            enabled: Whether hotkey is enabled

        Returns:
            True if registered successfully
        """
        if not self.config.enabled:
            logger.debug("Hotkey service disabled, skipping registration")
            return False

        if not self.primary_backend:
            logger.error("No hotkey backend available")
            return False

        # Check for existing hotkey
        if hotkey_id in self.hotkeys:
            logger.warning(f"Hotkey {hotkey_id} already registered, unregistering first")
            self.unregister_hotkey(hotkey_id)

        # Create hotkey binding
        binding = HotkeyBinding(
            id=hotkey_id,
            key_combination=key_combination,
            description=description,
            callback=callback,
            enabled=enabled,
        )

        # Register with primary backend
        success = self.primary_backend.register_hotkey(binding)

        if success:
            with self._lock:
                self.hotkeys[hotkey_id] = binding

            # Show notification if enabled
            if self.config.show_notifications:
                self.notification_service.show_hotkey_registered(
                    key_combination, description or hotkey_id
                )

            logger.info(f"Hotkey registered: {key_combination} -> {hotkey_id}")
        else:
            # Try fallback backends
            success = self._try_fallback_backends(binding)

            if success:
                with self._lock:
                    self.hotkeys[hotkey_id] = binding
            else:
                logger.error(f"Failed to register hotkey: {key_combination}")

                if self.config.show_notifications:
                    self.notification_service.show_error(
                        "Hotkey Registration Failed", f"Could not register {key_combination}"
                    )

        return success

    def _try_fallback_backends(self, binding: HotkeyBinding) -> bool:
        """Try registering hotkey with fallback backends."""
        for backend in self.backends:
            if backend != self.primary_backend:
                if backend.register_hotkey(binding):
                    logger.warning(
                        f"Primary backend failed, used fallback: {type(backend).__name__}"
                    )
                    return True

        return False

    def unregister_hotkey(self, hotkey_id: str) -> bool:
        """
        Unregister a hotkey.

        Args:
            hotkey_id: Hotkey identifier to unregister

        Returns:
            True if unregistered successfully
        """
        if hotkey_id not in self.hotkeys:
            logger.warning(f"Hotkey {hotkey_id} not found for unregistration")
            return False

        # Try unregistering from all backends
        success = False
        for backend in self.backends:
            if backend.unregister_hotkey(hotkey_id):
                success = True

        # Remove from tracking
        if hotkey_id in self.hotkeys:
            del self.hotkeys[hotkey_id]

        if success:
            logger.info(f"Hotkey unregistered: {hotkey_id}")

        return success

    def unregister_all(self) -> bool:
        """Unregister all hotkeys."""
        hotkey_ids = list(self.hotkeys.keys())
        success = True

        for hotkey_id in hotkey_ids:
            if not self.unregister_hotkey(hotkey_id):
                success = False

        # Also unregister from all backends
        for backend in self.backends:
            backend.unregister_all()

        logger.info("All hotkeys unregistered")
        return success

    def enable_hotkey(self, hotkey_id: str) -> bool:
        """Enable a specific hotkey."""
        if hotkey_id not in self.hotkeys:
            return False

        binding = self.hotkeys[hotkey_id]
        if binding.enabled:
            return True

        binding.enabled = True

        # Re-register if it was disabled
        if binding.state == HotkeyState.DISABLED:
            return self._reregister_hotkey(binding)

        return True

    def disable_hotkey(self, hotkey_id: str) -> bool:
        """Disable a specific hotkey."""
        if hotkey_id not in self.hotkeys:
            return False

        binding = self.hotkeys[hotkey_id]
        binding.enabled = False
        binding.state = HotkeyState.DISABLED

        # Unregister from backends but keep in tracking
        for backend in self.backends:
            backend.unregister_hotkey(hotkey_id)

        return True

    def _reregister_hotkey(self, binding: HotkeyBinding) -> bool:
        """Re-register a hotkey binding."""
        if self.primary_backend:
            return self.primary_backend.register_hotkey(binding)
        return False

    def get_registered_hotkeys(self) -> List[HotkeyBinding]:
        """Get list of all registered hotkeys."""
        return list(self.hotkeys.values())

    def get_hotkey_info(self, hotkey_id: str) -> Optional[HotkeyBinding]:
        """Get information about a specific hotkey."""
        return self.hotkeys.get(hotkey_id)

    def is_hotkey_registered(self, hotkey_id: str) -> bool:
        """Check if hotkey is registered."""
        return hotkey_id in self.hotkeys

    def update_config(self, config: HotkeyConfig) -> None:
        """Update hotkey configuration."""
        old_enabled = self.config.enabled
        self.config = config

        # Update backend configs
        for backend in self.backends:
            backend.config = config

        # Handle enable/disable state change
        if old_enabled != config.enabled:
            if config.enabled:
                self._reregister_all_hotkeys()
            else:
                self.unregister_all()

        logger.debug("Hotkey config updated")

    def _reregister_all_hotkeys(self) -> None:
        """Re-register all hotkeys (useful after config changes)."""
        with self._lock:
            bindings = list(self.hotkeys.values())
        self.unregister_all()

        for binding in bindings:
            if binding.enabled:
                self.primary_backend.register_hotkey(binding)
                self.hotkeys[binding.id] = binding

    def on_config_changed(self, key: str, old_value: Any, new_value: Any) -> None:
        """Handle configuration changes."""
        if key.startswith("hotkeys."):
            # Hotkey configuration changed
            logger.debug(f"Hotkey config changed: {key}")

            # Update specific hotkey if it's a default hotkey change
            if hasattr(self.config, key.split(".")[-1]):
                self._update_default_hotkey(key.split(".")[-1], new_value)

    def _update_default_hotkey(self, action: str, new_combination: str) -> None:
        """Update a default hotkey combination."""
        hotkey_id = f"default_{action}"

        if hotkey_id in self.hotkeys:
            # Unregister old hotkey
            self.unregister_hotkey(hotkey_id)

        # Register new hotkey if callback exists
        if action in self.action_callbacks:
            self.register_hotkey(
                hotkey_id,
                new_combination,
                self.action_callbacks[action],
                f"Default action: {action}",
            )

    def register_default_hotkeys(self, action_callbacks: Dict[str, Callable]) -> None:
        """
        Register default hotkeys from config.

        Args:
            action_callbacks: Dictionary mapping action names to callback functions
        """
        self.action_callbacks.update(action_callbacks)

        # Register all default hotkeys
        default_hotkeys = {
            "translate_selection": self.config.translate_selection,
            "translate_clipboard": self.config.translate_clipboard,
            "ocr_screen_area": self.config.ocr_screen_area,
            "repeat_last": self.config.repeat_last,
            "toggle_overlay": self.config.toggle_overlay,
            "show_history": self.config.show_history,
            "show_settings": self.config.show_settings,
            "emergency_stop": self.config.emergency_stop,
        }

        for action, key_combination in default_hotkeys.items():
            if action in action_callbacks and key_combination:
                self.register_hotkey(
                    f"default_{action}",
                    key_combination,
                    action_callbacks[action],
                    f"Default action: {action.replace('_', ' ').title()}",
                )

    def export_hotkeys(self) -> Dict[str, Any]:
        """Export hotkey configuration to dictionary."""
        return {
            "config": asdict(self.config),
            "hotkeys": {
                hotkey_id: {
                    "key_combination": binding.key_combination,
                    "description": binding.description,
                    "enabled": binding.enabled,
                    "trigger_count": binding.trigger_count,
                }
                for hotkey_id, binding in self.hotkeys.items()
            },
        }

    def get_conflicts(self) -> List[Dict[str, Any]]:
        """Check for hotkey conflicts."""
        conflicts = []
        combinations = {}

        for hotkey_id, binding in self.hotkeys.items():
            combo = binding.key_combination
            if combo in combinations:
                conflicts.append(
                    {"combination": combo, "conflicting_hotkeys": [combinations[combo], hotkey_id]}
                )
            else:
                combinations[combo] = hotkey_id

        return conflicts


# Global hotkey service instance
_hotkey_service: Optional[HotkeyService] = None


def get_hotkey_service() -> HotkeyService:
    """Get global hotkey service instance."""
    global _hotkey_service
    if _hotkey_service is None:
        _hotkey_service = HotkeyService()
    return _hotkey_service


def initialize_hotkeys(config: Optional[HotkeyConfig] = None) -> HotkeyService:
    """Initialize global hotkey service."""
    global _hotkey_service
    _hotkey_service = HotkeyService(config)
    return _hotkey_service

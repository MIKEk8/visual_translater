"""
Hotkey Profile Service for managing gaming/reading/streaming hotkey configurations.

This service provides predefined and customizable hotkey profiles for different
use cases like gaming, reading, and streaming.
"""

import json
import asyncio
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from datetime import datetime

from src.services.hotkey_service import HotkeyService
from src.services.circuit_breaker import CircuitBreakerManager, get_circuit_breaker_manager
from src.utils.logger import logger


class ProfileContext(Enum):
    """Context types for hotkey profiles."""
    GAMING = "gaming"
    READING = "reading"
    STREAMING = "streaming"
    CUSTOM = "custom"


class ProfileConflictError(Exception):
    """Raised when hotkey profiles have conflicts."""
    pass


@dataclass
class HotkeyProfile:
    """Represents a hotkey configuration profile."""

    name: str
    description: str
    hotkeys: Dict[str, str]
    context: ProfileContext
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    is_system: bool = False  # System profiles can't be deleted
    priority: int = 0  # Higher priority profiles override lower ones

    def __post_init__(self):
        """Validate hotkey profile after initialization."""
        self._validate_hotkeys()

    def _validate_hotkeys(self) -> None:
        """Validate hotkey format and combinations."""
        for action, hotkey in self.hotkeys.items():
            if not self._is_valid_hotkey(hotkey):
                raise ValueError(f"Invalid hotkey format: {hotkey} for action {action}")

    def _is_valid_hotkey(self, hotkey: str) -> bool:
        """Check if a hotkey string is valid."""
        if not hotkey or not isinstance(hotkey, str):
            return False

        # Basic validation for hotkey format
        valid_modifiers = {"Ctrl", "Alt", "Shift", "Win", "Cmd"}
        valid_keys = {
            "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
            "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
            "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
            "Space", "Tab", "Enter", "Esc", "Backspace", "Delete",
            "Up", "Down", "Left", "Right", "Home", "End", "PageUp", "PageDown"
        }

        parts = hotkey.split("+")
        if len(parts) < 1:
            return False

        # Last part should be the key
        key = parts[-1].strip()
        if key not in valid_keys:
            return False

        # All other parts should be modifiers
        for modifier in parts[:-1]:
            if modifier.strip() not in valid_modifiers:
                return False

        return True

    def get_conflicts(self, other: "HotkeyProfile") -> Set[str]:
        """Get conflicting hotkeys between this and another profile."""
        conflicts = set()
        for action, hotkey in self.hotkeys.items():
            for other_action, other_hotkey in other.hotkeys.items():
                if hotkey == other_hotkey and action != other_action:
                    conflicts.add(hotkey)
        return conflicts

    def to_dict(self) -> Dict:
        """Convert profile to dictionary for serialization."""
        data = asdict(self)
        data["context"] = self.context.value
        data["created_at"] = self.created_at.isoformat()
        data["last_used"] = self.last_used.isoformat() if self.last_used else None
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "HotkeyProfile":
        """Create profile from dictionary."""
        # Convert string values back to appropriate types
        data["context"] = ProfileContext(data["context"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("last_used"):
            data["last_used"] = datetime.fromisoformat(data["last_used"])
        return cls(**data)


class HotkeyProfileService:
    """Service for managing hotkey profiles."""

    def __init__(self, hotkey_service: Optional[HotkeyService] = None, config_dir: str = "data/hotkeys"):
        """Initialize the hotkey profile service.

        Args:
            hotkey_service: Optional HotkeyService instance
            config_dir: Directory to store profile configurations
        """
        self.hotkey_service = hotkey_service
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.profiles: Dict[str, HotkeyProfile] = {}
        self.active_profile: Optional[HotkeyProfile] = None
        self.circuit_breaker = get_circuit_breaker_manager().create_circuit_breaker("hotkey_profile")

        self._load_profiles()
        self._create_default_profiles()

        logger.info("HotkeyProfileService initialized")

    def _create_default_profiles(self) -> None:
        """Create default system profiles if they don't exist."""
        default_profiles = [
            HotkeyProfile(
                name="Gaming",
                description="Optimized for gaming sessions with quick access keys",
                hotkeys={
                    "quick_capture": "Ctrl+Q",
                    "repeat_last": "F1",
                    "toggle_overlay": "F2",
                    "speak_last": "F3",
                    "save_last": "F4",
                    "settings": "F10"
                },
                context=ProfileContext.GAMING,
                is_system=True,
                priority=100
            ),
            HotkeyProfile(
                name="Reading",
                description="Optimized for document reading with screen capture",
                hotkeys={
                    "quick_capture": "Ctrl+Shift+C",
                    "area_capture": "Ctrl+Shift+A",
                    "translate_clipboard": "Ctrl+T",
                    "repeat_last": "Ctrl+R",
                    "toggle_overlay": "Ctrl+O",
                    "speak_last": "Ctrl+S"
                },
                context=ProfileContext.READING,
                is_system=True,
                priority=90
            ),
            HotkeyProfile(
                name="Streaming",
                description="Stream-friendly keys that don't interfere with streaming software",
                hotkeys={
                    "quick_capture": "F5",
                    "repeat_last": "F6",
                    "toggle_overlay": "F7",
                    "speak_last": "F8",
                    "mute_audio": "F9"
                },
                context=ProfileContext.STREAMING,
                is_system=True,
                priority=80
            )
        ]

        for profile in default_profiles:
            if profile.name not in self.profiles:
                self.profiles[profile.name] = profile
                logger.debug(f"Created default profile: {profile.name}")

    def _load_profiles(self) -> None:
        """Load profiles from configuration files."""
        profiles_file = self.config_dir / "profiles.json"

        if profiles_file.exists():
            try:
                with open(profiles_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for profile_data in data.get("profiles", []):
                    profile = HotkeyProfile.from_dict(profile_data)
                    self.profiles[profile.name] = profile

                # Load active profile
                active_profile_name = data.get("active_profile")
                if active_profile_name and active_profile_name in self.profiles:
                    self.active_profile = self.profiles[active_profile_name]

                logger.info(f"Loaded {len(self.profiles)} profiles from configuration")

            except Exception as e:
                logger.error(f"Failed to load profiles: {e}")

    def _save_profiles(self) -> None:
        """Save profiles to configuration file."""
        try:
            profiles_data = {
                "profiles": [profile.to_dict() for profile in self.profiles.values()],
                "active_profile": self.active_profile.name if self.active_profile else None,
                "last_updated": datetime.now().isoformat()
            }

            profiles_file = self.config_dir / "profiles.json"
            with open(profiles_file, 'w', encoding='utf-8') as f:
                json.dump(profiles_data, f, indent=2, ensure_ascii=False)

            logger.debug("Profiles saved to configuration file")

        except Exception as e:
            logger.error(f"Failed to save profiles: {e}")

    async def create_profile(
        self,
        name: str,
        description: str,
        hotkeys: Dict[str, str],
        context: ProfileContext = ProfileContext.CUSTOM
    ) -> HotkeyProfile:
        """Create a new hotkey profile.

        Args:
            name: Profile name
            description: Profile description
            hotkeys: Hotkey mappings
            context: Profile context

        Returns:
            Created HotkeyProfile

        Raises:
            ValueError: If profile name exists or hotkeys are invalid
            ProfileConflictError: If hotkeys conflict with active profile
        """
        if name in self.profiles:
            raise ValueError(f"Profile '{name}' already exists")

        # Create and validate profile
        profile = HotkeyProfile(
            name=name,
            description=description,
            hotkeys=hotkeys,
            context=context
        )

        # Check for conflicts with active profile
        if self.active_profile:
            conflicts = profile.get_conflicts(self.active_profile)
            if conflicts:
                raise ProfileConflictError(
                    f"Profile conflicts with active profile on hotkeys: {', '.join(conflicts)}"
                )

        self.profiles[name] = profile
        self._save_profiles()

        logger.info(f"Created new profile: {name}")
        return profile

    async def delete_profile(self, name: str) -> bool:
        """Delete a hotkey profile.

        Args:
            name: Name of profile to delete

        Returns:
            True if deleted, False if not found or system profile

        Raises:
            ValueError: If trying to delete a system profile or active profile
        """
        if name not in self.profiles:
            return False

        profile = self.profiles[name]

        if profile.is_system:
            raise ValueError("Cannot delete system profile")

        if self.active_profile and self.active_profile.name == name:
            raise ValueError("Cannot delete active profile")

        del self.profiles[name]
        self._save_profiles()

        logger.info(f"Deleted profile: {name}")
        return True

    async def switch_profile(self, name: str, force: bool = False) -> bool:
        """Switch to a different profile.

        Args:
            name: Name of profile to switch to
            force: Force switch even if there are conflicts

        Returns:
            True if switched successfully

        Raises:
            ValueError: If profile not found
            ProfileConflictError: If conflicts exist and force=False
        """
        if name not in self.profiles:
            raise ValueError(f"Profile '{name}' not found")

        new_profile = self.profiles[name]

        # Check for system conflicts if not forcing
        if not force and self.hotkey_service:
            conflicts = await self._check_system_conflicts(new_profile)
            if conflicts:
                raise ProfileConflictError(
                    f"Profile conflicts with system hotkeys: {', '.join(conflicts)}"
                )

        # Unregister current profile hotkeys
        if self.active_profile and self.hotkey_service:
            await self._unregister_profile_hotkeys(self.active_profile)

        # Register new profile hotkeys
        if self.hotkey_service:
            await self._register_profile_hotkeys(new_profile)

        # Update active profile
        old_profile = self.active_profile
        self.active_profile = new_profile
        new_profile.last_used = datetime.now()

        self._save_profiles()

        logger.info(f"Switched from profile '{old_profile.name if old_profile else 'None'}' "
                   f"to '{new_profile.name}'")
        return True

    async def _register_profile_hotkeys(self, profile: HotkeyProfile) -> None:
        """Register hotkeys for a profile with the hotkey service."""
        if not self.hotkey_service:
            return

        for action, hotkey in profile.hotkeys.items():
            try:
                # Create callback for this action
                callback = self._create_action_callback(action, profile)
                await self.hotkey_service.register_hotkey(hotkey, callback)
                logger.debug(f"Registered hotkey {hotkey} for action {action}")
            except Exception as e:
                logger.error(f"Failed to register hotkey {hotkey} for action {action}: {e}")

    async def _unregister_profile_hotkeys(self, profile: HotkeyProfile) -> None:
        """Unregister hotkeys for a profile from the hotkey service."""
        if not self.hotkey_service:
            return

        for action, hotkey in profile.hotkeys.items():
            try:
                await self.hotkey_service.unregister_hotkey(hotkey)
                logger.debug(f"Unregistered hotkey {hotkey} for action {action}")
            except Exception as e:
                logger.debug(f"Failed to unregister hotkey {hotkey} for action {action}: {e}")

    def _create_action_callback(self, action: str, profile: HotkeyProfile) -> Callable:
        """Create a callback function for a profile action."""
        def callback():
            logger.debug(f"Hotkey action triggered: {action} from profile {profile.name}")
            # Here you would integrate with the main application to perform the action
            # This is a placeholder that logs the action

        return callback

    async def _check_system_conflicts(self, profile: HotkeyProfile) -> Set[str]:
        """Check if profile hotkeys conflict with system hotkeys.

        Args:
            profile: Profile to check

        Returns:
            Set of conflicting hotkeys
        """
        # This is a placeholder implementation
        # In a real implementation, you'd check against registered system hotkeys
        conflicts = set()

        # Example system hotkeys that might conflict
        system_hotkeys = {
            "Ctrl+C", "Ctrl+V", "Ctrl+X", "Ctrl+Z", "Ctrl+Y",
            "Alt+Tab", "Alt+F4", "Win+L", "Win+R"
        }

        for hotkey in profile.hotkeys.values():
            if hotkey in system_hotkeys:
                conflicts.add(hotkey)

        return conflicts

    async def get_profile(self, name: str) -> Optional[HotkeyProfile]:
        """Get a profile by name."""
        return self.profiles.get(name)

    async def list_profiles(
        self,
        context: Optional[ProfileContext] = None,
        include_system: bool = True
    ) -> List[HotkeyProfile]:
        """List available profiles.

        Args:
            context: Optional context filter
            include_system: Whether to include system profiles

        Returns:
            List of matching profiles
        """
        profiles = list(self.profiles.values())

        if context:
            profiles = [p for p in profiles if p.context == context]

        if not include_system:
            profiles = [p for p in profiles if not p.is_system]

        # Sort by priority (descending) then by name
        profiles.sort(key=lambda p: (-p.priority, p.name))

        return profiles

    async def update_profile(
        self,
        name: str,
        description: Optional[str] = None,
        hotkeys: Optional[Dict[str, str]] = None
    ) -> bool:
        """Update an existing profile.

        Args:
            name: Name of profile to update
            description: New description (optional)
            hotkeys: New hotkey mappings (optional)

        Returns:
            True if updated successfully

        Raises:
            ValueError: If profile not found or is system profile
        """
        if name not in self.profiles:
            raise ValueError(f"Profile '{name}' not found")

        profile = self.profiles[name]

        if profile.is_system:
            raise ValueError("Cannot modify system profile")

        # Update fields
        if description is not None:
            profile.description = description

        if hotkeys is not None:
            # Validate new hotkeys
            temp_profile = HotkeyProfile(
                name="temp",
                description="temp",
                hotkeys=hotkeys,
                context=profile.context
            )

            # Update hotkeys if validation passes
            profile.hotkeys = hotkeys

            # If this is the active profile, re-register hotkeys
            if self.active_profile and self.active_profile.name == name:
                if self.hotkey_service:
                    await self._unregister_profile_hotkeys(profile)
                    await self._register_profile_hotkeys(profile)

        self._save_profiles()

        logger.info(f"Updated profile: {name}")
        return True

    async def detect_conflicts(self) -> Dict[str, List[str]]:
        """Detect conflicts between all profiles.

        Returns:
            Dictionary mapping hotkeys to conflicting profile names
        """
        conflicts = {}

        profiles = list(self.profiles.values())
        for i, profile1 in enumerate(profiles):
            for profile2 in profiles[i + 1:]:
                profile_conflicts = profile1.get_conflicts(profile2)
                for hotkey in profile_conflicts:
                    if hotkey not in conflicts:
                        conflicts[hotkey] = []
                    conflicts[hotkey].extend([profile1.name, profile2.name])

        return conflicts

    def get_active_profile(self) -> Optional[HotkeyProfile]:
        """Get the currently active profile."""
        return self.active_profile

    def get_available_profiles(self) -> List[str]:
        """Get list of available profile names."""
        return list(self.profiles.keys())

    async def reset_to_defaults(self) -> None:
        """Reset all profiles to default system profiles."""
        # Clear all non-system profiles
        self.profiles = {
            name: profile for name, profile in self.profiles.items()
            if profile.is_system
        }

        # Recreate default profiles
        self._create_default_profiles()

        # Set gaming as default active profile
        if "Gaming" in self.profiles:
            await self.switch_profile("Gaming", force=True)

        self._save_profiles()

        logger.info("Reset all profiles to defaults")
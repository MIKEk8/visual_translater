"""
Tests for Hotkey Profiles functionality (Gaming/Reading/Streaming modes).

FEATURE: Hotkey Profiles (Gaming/Reading/Streaming)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import Dict, List, Optional

# CRITICAL: Import paths will fail until implementation exists
from src.services.hotkey_profile_service import (
    HotkeyProfileService,
    HotkeyProfile,
    ProfileContext,
    ProfileConflictError
)
from src.services.hotkey_service import HotkeyService


class TestHotkeyProfile:
    """Test HotkeyProfile data class."""

    def test_hotkey_profile_creation(self):
        """Test HotkeyProfile creation with valid data."""
        profile = HotkeyProfile(
            name="Gaming",
            description="Optimized for gaming sessions",
            hotkeys={
                "quick_capture": "Ctrl+Q",
                "repeat_last": "F1",
                "toggle_overlay": "F2"
            },
            context=ProfileContext.GAMING
        )

        assert profile.name == "Gaming"
        assert profile.context == ProfileContext.GAMING
        assert "quick_capture" in profile.hotkeys
        assert profile.hotkeys["quick_capture"] == "Ctrl+Q"

    def test_hotkey_profile_validation(self):
        """Test HotkeyProfile validation rules."""
        # Test invalid hotkey format
        with pytest.raises(ValueError, match="Invalid hotkey format"):
            HotkeyProfile(
                name="Invalid",
                description="Invalid hotkeys",
                hotkeys={"action": "InvalidKey"},
                context=ProfileContext.GAMING
            )

    def test_profile_context_enum(self):
        """Test ProfileContext enum values."""
        assert ProfileContext.GAMING.value == "gaming"
        assert ProfileContext.READING.value == "reading"
        assert ProfileContext.STREAMING.value == "streaming"


class TestHotkeyProfileService:
    """Test suite for HotkeyProfileService."""

    @pytest.fixture
    def mock_hotkey_service(self):
        """Mock HotkeyService dependency."""
        return Mock(spec=HotkeyService)

    @pytest.fixture
    def profile_service(self, mock_hotkey_service):
        """Create HotkeyProfileService with mocked dependencies."""
        return HotkeyProfileService(mock_hotkey_service)

    # CRITICAL: Service initialization with default profiles
    def test_service_initialization_with_default_profiles(self, profile_service):
        """Test service initializes with default gaming/reading/streaming profiles."""
        profiles = profile_service.get_available_profiles()

        # CRITICAL: Must include all 3 default profiles
        assert len(profiles) >= 3

        profile_names = [p.name for p in profiles]
        assert "Gaming" in profile_names
        assert "Reading" in profile_names
        assert "Streaming" in profile_names

    def test_gaming_profile_defaults(self, profile_service):
        """Test gaming profile has appropriate hotkeys."""
        gaming_profile = profile_service.get_profile_by_name("Gaming")

        assert gaming_profile is not None
        assert gaming_profile.context == ProfileContext.GAMING

        # CRITICAL: Gaming profile should have quick access keys
        expected_hotkeys = ["Ctrl+Q", "F1", "F2", "F3"]
        hotkey_values = list(gaming_profile.hotkeys.values())

        for expected in expected_hotkeys:
            assert any(expected in hk for hk in hotkey_values)

    def test_reading_profile_defaults(self, profile_service):
        """Test reading profile has document-friendly hotkeys."""
        reading_profile = profile_service.get_profile_by_name("Reading")

        assert reading_profile is not None
        assert reading_profile.context == ProfileContext.READING

        # CRITICAL: Reading profile should avoid gaming keys
        hotkey_values = list(reading_profile.hotkeys.values())

        # Should use Ctrl+Shift combinations for reading
        assert any("Ctrl+Shift" in hk for hk in hotkey_values)
        # Should not use function keys F1-F9
        assert not any(f"F{i}" in hk for hk in hotkey_values for i in range(1, 10))

    def test_streaming_profile_defaults(self, profile_service):
        """Test streaming profile uses stream-friendly keys."""
        streaming_profile = profile_service.get_profile_by_name("Streaming")

        assert streaming_profile is not None
        assert streaming_profile.context == ProfileContext.STREAMING

        # CRITICAL: Streaming should use F5-F9 keys (not conflicting with OBS)
        hotkey_values = list(streaming_profile.hotkeys.values())
        allowed_f_keys = ["F5", "F6", "F7", "F8", "F9"]

        f_keys_used = [hk for hk in hotkey_values if any(fk in hk for fk in allowed_f_keys)]
        assert len(f_keys_used) > 0

    # CRITICAL: Profile switching functionality
    def test_switch_profile_success(self, profile_service, mock_hotkey_service):
        """Test successful profile switching."""
        gaming_profile = profile_service.get_profile_by_name("Gaming")

        result = profile_service.switch_to_profile("Gaming")

        assert result is True
        assert profile_service.current_profile == gaming_profile

        # CRITICAL: Should unregister old hotkeys and register new ones
        mock_hotkey_service.unregister_all.assert_called_once()
        mock_hotkey_service.register_hotkeys.assert_called_once_with(gaming_profile.hotkeys)

    def test_switch_profile_nonexistent(self, profile_service):
        """Test switching to non-existent profile fails gracefully."""
        result = profile_service.switch_to_profile("NonExistent")

        assert result is False
        assert profile_service.current_profile is None

    # CRITICAL: Hotkey conflict detection
    def test_hotkey_conflict_detection(self, profile_service, mock_hotkey_service):
        """Test detection of hotkey conflicts with system/other apps."""
        # Mock hotkey service to report conflicts
        mock_hotkey_service.register_hotkeys.side_effect = Exception("Hotkey already registered")

        with pytest.raises(ProfileConflictError, match="Hotkey conflict"):
            profile_service.switch_to_profile("Gaming")

    def test_validate_profile_hotkeys(self, profile_service):
        """Test profile hotkey validation before activation."""
        invalid_profile = HotkeyProfile(
            name="Invalid",
            description="Has invalid hotkeys",
            hotkeys={
                "action1": "Ctrl+Alt+Shift+F1+F2",  # Too complex
                "action2": "Invalid"  # Invalid format
            },
            context=ProfileContext.GAMING
        )

        with pytest.raises(ValueError, match="Invalid hotkey"):
            profile_service._validate_profile_hotkeys(invalid_profile)

    # CRITICAL: Custom profile creation
    def test_create_custom_profile(self, profile_service):
        """Test creation of custom user profiles."""
        custom_hotkeys = {
            "capture": "Ctrl+Alt+C",
            "translate": "Ctrl+Alt+T",
            "repeat": "Ctrl+Alt+R"
        }

        custom_profile = profile_service.create_profile(
            name="Custom Work",
            description="For work environment",
            hotkeys=custom_hotkeys,
            context=ProfileContext.READING
        )

        assert custom_profile is not None
        assert custom_profile.name == "Custom Work"
        assert custom_profile.hotkeys == custom_hotkeys

        # CRITICAL: Custom profile should be saved and retrievable
        profiles = profile_service.get_available_profiles()
        assert custom_profile in profiles

    def test_delete_custom_profile(self, profile_service):
        """Test deletion of custom profiles (not defaults)."""
        # Create custom profile first
        custom_profile = profile_service.create_profile(
            name="Temp Profile",
            description="Temporary",
            hotkeys={"action": "Ctrl+T"},
            context=ProfileContext.GAMING
        )

        # Should be able to delete custom profile
        result = profile_service.delete_profile("Temp Profile")
        assert result is True

        # Should not be able to delete default profiles
        with pytest.raises(ValueError, match="Cannot delete default profile"):
            profile_service.delete_profile("Gaming")

    # CRITICAL: Profile persistence
    def test_profile_persistence(self, profile_service):
        """Test that profiles are persisted and loaded correctly."""
        # Create custom profile
        custom_profile = profile_service.create_profile(
            name="Persistent Test",
            description="Test persistence",
            hotkeys={"test": "Ctrl+P"},
            context=ProfileContext.READING
        )

        # Mock service restart
        with patch.object(profile_service, '_load_profiles_from_storage') as mock_load:
            mock_load.return_value = [custom_profile]

            profile_service._reload_profiles()

            # Custom profile should still exist
            loaded_profile = profile_service.get_profile_by_name("Persistent Test")
            assert loaded_profile is not None
            assert loaded_profile.hotkeys == {"test": "Ctrl+P"}

    def test_auto_profile_switching_integration(self, profile_service):
        """Test integration with game detection for auto-switching."""
        with patch('src.services.game_detector_service.GameDetectorService') as mock_detector:
            mock_detector_instance = Mock()
            mock_detector.return_value = mock_detector_instance

            # Mock game detection event
            mock_detector_instance.on_game_detected.return_value = None

            # Register for auto-switching
            profile_service.enable_auto_switching(True)

            # Simulate game detection
            game_info = {"name": "Counter-Strike", "context": "gaming"}
            profile_service._on_game_detected(game_info)

            # Should auto-switch to gaming profile
            assert profile_service.current_profile.context == ProfileContext.GAMING

    # CRITICAL: Error handling and recovery
    def test_profile_switching_rollback_on_error(self, profile_service, mock_hotkey_service):
        """Test rollback to previous profile if switching fails."""
        # Start with gaming profile
        profile_service.switch_to_profile("Gaming")
        original_profile = profile_service.current_profile

        # Mock failure during switch to reading profile
        mock_hotkey_service.register_hotkeys.side_effect = Exception("Registration failed")

        with pytest.raises(ProfileConflictError):
            profile_service.switch_to_profile("Reading")

        # Should rollback to original profile
        assert profile_service.current_profile == original_profile

    def test_hotkey_service_unavailable_handling(self, mock_hotkey_service):
        """Test graceful handling when hotkey service is unavailable."""
        mock_hotkey_service.register_hotkeys.side_effect = Exception("Service unavailable")

        # Service should still initialize but with limited functionality
        profile_service = HotkeyProfileService(mock_hotkey_service)

        # Should not crash but should log warning
        with patch('src.utils.logger.Logger') as mock_logger:
            result = profile_service.switch_to_profile("Gaming")

            assert result is False
            mock_logger.warning.assert_called()


# CRITICAL: Integration tests
class TestHotkeyProfileIntegration:
    """Integration tests for complete hotkey profile workflow."""

    def test_profile_ui_integration(self):
        """Test profile selection UI integration."""
        # This test will fail until UI component exists

        with patch('src.ui.hotkey_profile_selector.HotkeyProfileSelector') as mock_selector:
            with patch('src.services.hotkey_profile_service.HotkeyProfileService') as mock_service:

                selector = mock_selector.return_value
                service = mock_service.return_value

                # Mock available profiles
                service.get_available_profiles.return_value = [
                    HotkeyProfile("Gaming", "Gaming mode", {}, ProfileContext.GAMING),
                    HotkeyProfile("Reading", "Reading mode", {}, ProfileContext.READING)
                ]

                # Simulate user selection
                selector.on_profile_selected("Gaming")

                # Should trigger service profile switch
                service.switch_to_profile.assert_called_with("Gaming")

    def test_settings_persistence_integration(self):
        """Test integration with settings/config system."""
        with patch('src.services.config_manager.ConfigManager') as mock_config:
            config_manager = mock_config.return_value
            config_manager.get.return_value = "Gaming"  # Default profile

            service = HotkeyProfileService(Mock())

            # Should load default profile from config
            assert service.get_default_profile_name() == "Gaming"

            # Should save profile changes to config
            service.set_default_profile("Reading")
            config_manager.set.assert_called_with("hotkey_profiles.default", "Reading")
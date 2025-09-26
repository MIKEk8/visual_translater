"""
Tests for Auto Game Detection with process monitoring.

FEATURE: Auto Game Detection (Process Monitoring)
"""

import pytest
import asyncio
import psutil
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# CRITICAL: Import paths will fail until implementation exists
from src.services.game_detector_service import (
    GameDetectorService,
    GameProfile,
    GameDetectionEvent,
    ProcessInfo
)
from src.domain.entities.game_profile import GameProfile as GameProfileEntity
from src.infrastructure.repositories.game_repository import GameRepository


class TestGameProfile:
    """Test GameProfile entity."""

    def test_game_profile_creation(self):
        """Test GameProfile creation with valid data."""
        profile = GameProfile(
            name="Genshin Impact",
            executable="GenshinImpact.exe",
            window_title_patterns=["Genshin Impact", "原神"],
            hotkey_profile="Gaming",
            translation_settings={
                "target_language": "en",
                "ocr_preprocessing": True,
                "glossary": "genshin_impact"
            }
        )

        assert profile.name == "Genshin Impact"
        assert profile.executable == "GenshinImpact.exe"
        assert len(profile.window_title_patterns) == 2
        assert profile.hotkey_profile == "Gaming"

    def test_game_profile_matching(self):
        """Test game profile process matching logic."""
        profile = GameProfile(
            name="Counter-Strike",
            executable="csgo.exe",
            window_title_patterns=["Counter-Strike", "CS:GO"],
            hotkey_profile="Gaming"
        )

        # Test executable matching
        assert profile.matches_process("csgo.exe", "Counter-Strike: Global Offensive")
        assert profile.matches_process("CSGO.EXE", "CS:GO")  # Case insensitive
        assert not profile.matches_process("notepad.exe", "Notepad")

    def test_game_profile_validation(self):
        """Test GameProfile validation rules."""
        # Test missing executable
        with pytest.raises(ValueError, match="Executable name required"):
            GameProfile(
                name="Test Game",
                executable="",
                window_title_patterns=["Test"],
                hotkey_profile="Gaming"
            )

        # Test invalid hotkey profile
        with pytest.raises(ValueError, match="Invalid hotkey profile"):
            GameProfile(
                name="Test Game",
                executable="test.exe",
                window_title_patterns=["Test"],
                hotkey_profile="NonExistentProfile"
            )


class TestGameDetectorService:
    """Test suite for GameDetectorService."""

    @pytest.fixture
    def mock_game_repository(self):
        """Mock GameRepository dependency."""
        return Mock(spec=GameRepository)

    @pytest.fixture
    def detector_service(self, mock_game_repository):
        """Create GameDetectorService with mocked dependencies."""
        return GameDetectorService(game_repository=mock_game_repository)

    # CRITICAL: Service initialization and database loading
    def test_service_initialization(self, detector_service, mock_game_repository):
        """Test service initializes with game database loaded."""
        mock_game_repository.load_game_profiles.return_value = [
            GameProfile("Test Game", "test.exe", ["Test"], "Gaming")
        ]

        detector_service._load_game_database()

        # Should have the 1 mocked game plus built-in games
        assert len(detector_service.game_database) >= 1
        assert mock_game_repository.load_game_profiles.call_count >= 1

    # CRITICAL: Process detection functionality
    @patch('psutil.process_iter')
    def test_detect_running_games_windows(self, mock_process_iter, detector_service):
        """Test game detection on Windows platform."""
        # Mock running processes
        mock_processes = []
        for pid, name, cmdline in [
            (1234, 'GenshinImpact.exe', ['C:\\Games\\Genshin\\GenshinImpact.exe']),
            (5678, 'notepad.exe', ['C:\\Windows\\notepad.exe']),
            (9101, 'csgo.exe', ['C:\\Steam\\csgo.exe'])
        ]:
            mock_proc = Mock()
            mock_proc.info = {'pid': pid, 'name': name, 'cmdline': cmdline, 'exe': cmdline[0]}
            mock_proc.cpu_percent.return_value = 2.0
            mock_proc.memory_info.return_value.rss = 200 * 1024 * 1024
            mock_proc.is_running.return_value = True
            mock_processes.append(mock_proc)
        mock_process_iter.return_value = mock_processes

        # Mock game database
        detector_service.game_database = {
            "genshinimpact": GameProfile("Genshin Impact", "GenshinImpact.exe", ["Genshin Impact"], "Gaming"),
            "csgo": GameProfile("Counter-Strike", "csgo.exe", ["Counter-Strike"], "Gaming")
        }

        detected_games = detector_service._detect_running_games()

        # CRITICAL: Should detect both games, not notepad
        assert len(detected_games) == 2
        game_names = [game.name for game in detected_games]
        assert "Genshin Impact" in game_names
        assert "Counter-Strike" in game_names

    @patch('platform.system')
    @patch('psutil.process_iter')
    def test_detect_running_games_cross_platform(self, mock_process_iter, mock_platform, detector_service):
        """Test cross-platform process detection."""
        # Test Linux
        mock_platform.return_value = "Linux"
        mock_processes = [
            Mock(info={'pid': 1234, 'name': 'steam', 'cmdline': ['steam', '-game', 'csgo']})
        ]
        mock_process_iter.return_value = mock_processes

        detector_service.game_database = [
            GameProfile("Counter-Strike", "csgo", ["CS:GO"], "Gaming")
        ]

        detected_games = detector_service._detect_running_processes()

        # Should adapt detection logic for Linux
        assert isinstance(detected_games, list)

    # CRITICAL: Window title detection
    @patch('win32gui.EnumWindows')
    @patch('win32gui.GetWindowText')
    @patch('win32gui.GetWindowThreadProcessId')
    def test_window_title_detection_windows(self, mock_get_pid, mock_get_text, mock_enum, detector_service):
        """Test window title-based detection on Windows."""
        # Mock Windows API calls
        def enum_callback(callback, _):
            # Simulate window enumeration
            callback(123456, None)  # hwnd, lparam
            callback(789012, None)
            return True

        mock_enum.side_effect = enum_callback
        mock_get_text.side_effect = ["Genshin Impact", "Notepad"]
        mock_get_pid.side_effect = [(1234, 0), (5678, 0)]

        # Mock process info
        with patch('psutil.Process') as mock_process:
            process1 = Mock()
            process1.name.return_value = "GenshinImpact.exe"
            process2 = Mock()
            process2.name.return_value = "notepad.exe"

            mock_process.side_effect = [process1, process2]

            detector_service.game_database = [
                GameProfile("Genshin Impact", "GenshinImpact.exe", ["Genshin Impact"], "Gaming")
            ]

            detected_games = detector_service._detect_by_window_titles()

            assert len(detected_games) == 1
            assert detected_games[0].name == "Genshin Impact"

    # CRITICAL: Continuous monitoring with async
    @pytest.mark.asyncio
    async def test_continuous_monitoring_loop(self, detector_service):
        """Test continuous background monitoring loop."""
        detector_service.check_interval = 0.1  # Fast for testing
        monitor_count = 0

        async def mock_detect():
            nonlocal monitor_count
            monitor_count += 1
            if monitor_count >= 3:
                detector_service.is_monitoring = False
            return []

        detector_service._detect_running_processes = mock_detect

        # Start monitoring
        detector_service.is_monitoring = True
        await detector_service.monitor_processes()

        # Should have called detection multiple times
        assert monitor_count >= 3

    @pytest.mark.asyncio
    async def test_game_change_detection_and_events(self, detector_service):
        """Test detection of game changes and event emission."""
        events_fired = []

        def on_game_detected(event: GameDetectionEvent):
            events_fired.append(event)

        def on_game_stopped(event: GameDetectionEvent):
            events_fired.append(event)

        detector_service.on_game_detected.connect(on_game_detected)
        detector_service.on_game_stopped.connect(on_game_stopped)

        genshin_profile = GameProfile("Genshin Impact", "GenshinImpact.exe", ["Genshin"], "Gaming")
        csgo_profile = GameProfile("Counter-Strike", "csgo.exe", ["CS:GO"], "Gaming")

        # Simulate game detection sequence
        detector_service.current_game = None

        # First detection: Genshin starts
        with patch.object(detector_service, '_detect_running_processes') as mock_detect:
            mock_detect.return_value = [genshin_profile]
            await detector_service._check_for_game_changes()

        # Should fire game detected event
        assert len(events_fired) == 1
        assert events_fired[0].event_type == "game_detected"
        assert events_fired[0].game_profile.name == "Genshin Impact"

        # Second detection: Switch to CS:GO
        with patch.object(detector_service, '_detect_running_processes') as mock_detect:
            mock_detect.return_value = [csgo_profile]
            await detector_service._check_for_game_changes()

        # Should fire game stopped + game detected
        assert len(events_fired) == 3
        assert any(e.event_type == "game_stopped" for e in events_fired)
        assert events_fired[-1].game_profile.name == "Counter-Strike"

    # CRITICAL: Performance with many processes
    def test_detection_performance_many_processes(self, detector_service):
        """Test detection performance with many running processes."""
        # Mock large number of processes
        mock_processes = []
        for i in range(1000):  # Simulate 1000 running processes
            mock_processes.append(
                Mock(info={'pid': i, 'name': f'process{i}.exe', 'cmdline': [f'process{i}.exe']})
            )

        detector_service.game_database = [
            GameProfile("Test Game", "process500.exe", ["Process 500"], "Gaming")
        ]

        with patch('psutil.process_iter', return_value=mock_processes):
            import time
            start_time = time.time()

            detected_games = detector_service._detect_running_processes()

            detection_time = time.time() - start_time

            # CRITICAL: Detection should complete under 2 seconds even with 1000 processes
            assert detection_time < 2.0
            assert len(detected_games) == 1

    # CRITICAL: Game database management
    def test_load_community_game_database(self, detector_service):
        """Test loading community-maintained game database."""
        community_db_data = {
            "version": "1.0",
            "games": [
                {
                    "name": "Genshin Impact",
                    "executable": "GenshinImpact.exe",
                    "window_titles": ["Genshin Impact", "原神"],
                    "hotkey_profile": "Gaming",
                    "settings": {"target_language": "en"}
                }
            ]
        }

        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = community_db_data
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            success = detector_service.update_community_database()

            assert success is True
            assert len(detector_service.game_database) >= 1

    def test_add_custom_game_profile(self, detector_service, mock_game_repository):
        """Test adding custom user game profiles."""
        custom_profile = GameProfile(
            name="My Custom Game",
            executable="custom_game.exe",
            window_title_patterns=["Custom Game Window"],
            hotkey_profile="Reading",
            translation_settings={"target_language": "ja"}
        )

        detector_service.add_custom_game_profile(custom_profile)

        # Should be added to database and persisted
        assert custom_profile in detector_service.game_database
        mock_game_repository.save_game_profile.assert_called_once_with(custom_profile)

    # CRITICAL: Error handling and recovery
    def test_process_access_denied_handling(self, detector_service):
        """Test graceful handling of process access denied errors."""
        with patch('psutil.process_iter') as mock_process_iter:
            # Mock process that raises access denied
            mock_process = Mock()
            mock_process.info.side_effect = psutil.AccessDenied(pid=1234)
            mock_process_iter.return_value = [mock_process]

            # Should not crash and should log warning
            with patch('src.utils.logger.Logger') as mock_logger:
                detected_games = detector_service._detect_running_processes()

                assert detected_games == []
                # Should log access denied warning but continue
                assert mock_logger.warning.called

    @pytest.mark.asyncio
    async def test_monitoring_error_recovery(self, detector_service):
        """Test monitoring continues after errors."""
        error_count = 0

        def failing_detect():
            nonlocal error_count
            error_count += 1
            if error_count < 3:
                raise Exception("Detection failed")
            return []

        detector_service._detect_running_processes = failing_detect
        detector_service.check_interval = 0.1
        detector_service.is_monitoring = True

        # Mock circuit breaker to allow retries
        with patch.object(detector_service, 'circuit_breaker') as mock_breaker:
            mock_breaker.call.side_effect = [
                Exception("Detection failed"),
                Exception("Detection failed"),
                []  # Success on third try
            ]

            # Should recover and continue monitoring
            await asyncio.wait_for(detector_service.monitor_processes(), timeout=1.0)

            assert error_count == 3  # Should have retried

    def test_platform_specific_detection(self, detector_service):
        """Test platform-specific detection methods."""
        # Windows-specific detection
        with patch('platform.system', return_value='Windows'):
            assert detector_service._is_windows_platform() is True

        # Linux-specific detection
        with patch('platform.system', return_value='Linux'):
            assert detector_service._is_windows_platform() is False

        # macOS handling
        with patch('platform.system', return_value='Darwin'):
            # Should have macOS-specific detection logic
            with patch.object(detector_service, '_detect_macos_applications') as mock_macos:
                mock_macos.return_value = []

                detected = detector_service._detect_running_processes()
                mock_macos.assert_called_once()


# CRITICAL: Integration tests
class TestGameDetectionIntegration:
    """Integration tests for complete game detection workflow."""

    @pytest.mark.asyncio
    async def test_full_detection_workflow_integration(self):
        """Test complete detection workflow with settings switching."""
        with patch('src.services.hotkey_profile_service.HotkeyProfileService') as mock_hotkey:
            with patch('src.services.config_manager.ConfigManager') as mock_config:

                hotkey_service = mock_hotkey.return_value
                config_manager = mock_config.return_value

                detector = GameDetectorService(game_repository=Mock())

                # Mock game detection
                genshin_profile = GameProfile(
                    "Genshin Impact",
                    "GenshinImpact.exe",
                    ["Genshin"],
                    "Gaming",
                    translation_settings={"target_language": "en", "glossary": "genshin_impact"}
                )

                with patch.object(detector, '_detect_running_processes') as mock_detect:
                    mock_detect.return_value = [genshin_profile]

                    # Simulate game detection
                    await detector._check_for_game_changes()

                    # Should switch hotkey profile
                    hotkey_service.switch_to_profile.assert_called_with("Gaming")

                    # Should apply translation settings
                    config_manager.set.assert_called()

    def test_ui_integration_with_game_detection(self):
        """Test UI integration when game is detected."""
        # This test will fail until UI integration exists

        with patch('src.ui.game_detection_indicator.GameDetectionIndicator') as mock_ui:
            indicator = mock_ui.return_value

            detector = GameDetectorService(game_repository=Mock())

            # Mock game detection event
            game_profile = GameProfile("Test Game", "test.exe", ["Test"], "Gaming")
            event = GameDetectionEvent("game_detected", game_profile, datetime.now())

            detector._notify_ui_game_detected(event)

            # Should update UI indicator
            indicator.show_game_detected.assert_called_with(game_profile)
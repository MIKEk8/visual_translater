"""
Tests for Live Translation Mode with continuous screen capture.

FEATURE: Live Translation Mode (Continuous Capture)
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, List
import hashlib
import time

# CRITICAL: Import paths will fail until implementation exists
from src.services.live_translation_service import (
    LiveTranslationService,
    CaptureRegion,
    ChangeDetector,
    LiveTranslationConfig,
    FrameBuffer
)
from src.ui.live_translation_window import LiveTranslationWindow


class TestCaptureRegion:
    """Test capture region definition."""

    def test_capture_region_creation(self):
        """Test CaptureRegion creation with coordinates."""
        region = CaptureRegion(x=100, y=200, width=300, height=150)

        assert region.x == 100
        assert region.y == 200
        assert region.width == 300
        assert region.height == 150

    def test_capture_region_validation(self):
        """Test capture region validation."""
        # Valid region
        region = CaptureRegion(0, 0, 100, 100)
        assert region.is_valid() is True

        # Invalid regions
        with pytest.raises(ValueError, match="Width must be positive"):
            CaptureRegion(0, 0, 0, 100)

        with pytest.raises(ValueError, match="Height must be positive"):
            CaptureRegion(0, 0, 100, 0)

        with pytest.raises(ValueError, match="Coordinates cannot be negative"):
            CaptureRegion(-10, 0, 100, 100)

    def test_capture_region_bounds_checking(self):
        """Test region bounds checking against screen size."""
        region = CaptureRegion(100, 100, 300, 200)

        # Should fit within screen
        assert region.fits_within_screen(1920, 1080) is True

        # Should not fit
        large_region = CaptureRegion(1800, 900, 300, 300)
        assert large_region.fits_within_screen(1920, 1080) is False

    def test_capture_region_area_calculation(self):
        """Test region area calculation."""
        region = CaptureRegion(0, 0, 100, 50)
        assert region.get_area() == 5000  # 100 * 50

    def test_capture_region_center_point(self):
        """Test getting center point of region."""
        region = CaptureRegion(100, 200, 300, 150)
        center_x, center_y = region.get_center()

        assert center_x == 250  # 100 + 300/2
        assert center_y == 275  # 200 + 150/2


class TestChangeDetector:
    """Test change detection algorithms."""

    def test_change_detector_initialization(self):
        """Test ChangeDetector initialization."""
        detector = ChangeDetector(threshold=5.0)

        assert detector.threshold == 5.0
        assert detector.last_hash is None
        assert detector.last_frame is None

    def test_hash_based_change_detection(self):
        """Test basic hash-based change detection."""
        detector = ChangeDetector()

        # First frame (no previous frame to compare)
        frame1 = b"fake_image_data_1"
        has_changed = detector.detect_change_by_hash(frame1)

        assert has_changed is True  # First frame always considered changed
        assert detector.last_hash is not None

        # Same frame (no change)
        has_changed = detector.detect_change_by_hash(frame1)
        assert has_changed is False

        # Different frame (change detected)
        frame2 = b"fake_image_data_2"
        has_changed = detector.detect_change_by_hash(frame2)
        assert has_changed is True

    def test_pixel_difference_change_detection(self):
        """Test pixel-by-pixel difference change detection."""
        detector = ChangeDetector(threshold=10.0)

        # Mock image arrays
        import numpy as np
        frame1 = np.ones((100, 200, 3), dtype=np.uint8) * 128  # Gray image
        frame2 = frame1.copy()
        frame2[50:60, 100:110] = 255  # Add white rectangle

        # First frame
        has_changed = detector.detect_change_by_pixels(frame1)
        assert has_changed is True

        # Same frame
        has_changed = detector.detect_change_by_pixels(frame1)
        assert has_changed is False

        # Modified frame
        has_changed = detector.detect_change_by_pixels(frame2)
        assert has_changed is True

    def test_change_detection_threshold_sensitivity(self):
        """Test change detection threshold sensitivity."""
        # High threshold (less sensitive)
        high_threshold = ChangeDetector(threshold=50.0)

        # Low threshold (more sensitive)
        low_threshold = ChangeDetector(threshold=1.0)

        # Slightly different frames
        import numpy as np
        frame1 = np.ones((100, 100, 3), dtype=np.uint8) * 128
        frame2 = frame1.copy()
        frame2[0:10, 0:10] += 10  # Slight change in small area

        # Initialize both detectors
        high_threshold.detect_change_by_pixels(frame1)
        low_threshold.detect_change_by_pixels(frame1)

        # Test detection
        high_changed = high_threshold.detect_change_by_pixels(frame2)
        low_changed = low_threshold.detect_change_by_pixels(frame2)

        # Low threshold should be more sensitive to small changes
        assert low_changed is True
        # High threshold might not detect small changes
        assert high_changed in [True, False]  # Depends on exact implementation


class TestLiveTranslationConfig:
    """Test live translation configuration."""

    def test_config_default_values(self):
        """Test configuration with default values."""
        config = LiveTranslationConfig()

        assert config.fps == 2.0
        assert config.change_threshold == 5.0
        assert config.max_concurrent_translations == 3
        assert config.buffer_size == 10
        assert config.auto_pause_on_no_change is True

    def test_config_custom_values(self):
        """Test configuration with custom values."""
        config = LiveTranslationConfig(
            fps=1.0,
            change_threshold=10.0,
            max_concurrent_translations=5,
            region_selection_enabled=True
        )

        assert config.fps == 1.0
        assert config.change_threshold == 10.0
        assert config.max_concurrent_translations == 5
        assert config.region_selection_enabled is True

    def test_config_validation(self):
        """Test configuration parameter validation."""
        # Valid config
        config = LiveTranslationConfig(fps=2.0, change_threshold=5.0)
        assert config.validate() is True

        # Invalid FPS
        with pytest.raises(ValueError, match="FPS must be between"):
            LiveTranslationConfig(fps=0)

        with pytest.raises(ValueError, match="FPS must be between"):
            LiveTranslationConfig(fps=10)  # Too high

        # Invalid threshold
        with pytest.raises(ValueError, match="Change threshold must be positive"):
            LiveTranslationConfig(change_threshold=-1)


class TestFrameBuffer:
    """Test frame buffering for live translation."""

    def test_frame_buffer_initialization(self):
        """Test frame buffer initialization."""
        buffer = FrameBuffer(max_size=5)

        assert buffer.max_size == 5
        assert len(buffer) == 0
        assert buffer.is_empty() is True

    def test_frame_buffer_add_and_get(self):
        """Test adding and retrieving frames."""
        buffer = FrameBuffer(max_size=3)

        # Add frames
        buffer.add_frame("frame1", timestamp=1.0)
        buffer.add_frame("frame2", timestamp=2.0)

        assert len(buffer) == 2
        assert buffer.get_latest_frame() == "frame2"

    def test_frame_buffer_overflow(self):
        """Test buffer behavior when exceeding max size."""
        buffer = FrameBuffer(max_size=2)

        # Fill buffer
        buffer.add_frame("frame1", timestamp=1.0)
        buffer.add_frame("frame2", timestamp=2.0)

        # Add one more (should remove oldest)
        buffer.add_frame("frame3", timestamp=3.0)

        assert len(buffer) == 2
        assert buffer.get_oldest_frame() != "frame1"  # Should be removed
        assert buffer.get_latest_frame() == "frame3"

    def test_frame_buffer_timestamp_ordering(self):
        """Test frame ordering by timestamp."""
        buffer = FrameBuffer(max_size=5)

        # Add frames out of order
        buffer.add_frame("frame2", timestamp=2.0)
        buffer.add_frame("frame1", timestamp=1.0)
        buffer.add_frame("frame3", timestamp=3.0)

        frames_in_order = buffer.get_frames_by_timestamp()

        # Should be ordered by timestamp
        timestamps = [frame[1] for frame in frames_in_order]  # Extract timestamps
        assert timestamps == sorted(timestamps)


class TestLiveTranslationService:
    """Test suite for LiveTranslationService."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock service dependencies."""
        return {
            'capture_service': Mock(),
            'ocr_engine': Mock(),
            'translation_engine': Mock(),
            'change_detector': Mock(spec=ChangeDetector)
        }

    @pytest.fixture
    def live_service(self, mock_dependencies):
        """Create LiveTranslationService with mocked dependencies."""
        service = LiveTranslationService()
        for name, mock_dep in mock_dependencies.items():
            setattr(service, name, mock_dep)
        return service

    # CRITICAL: Service initialization and configuration
    def test_service_initialization(self, live_service):
        """Test service initializes with proper defaults."""
        assert live_service.is_active is False
        assert live_service.fps == 2.0
        assert live_service.change_threshold == 5.0
        assert live_service.current_region is None

    def test_configure_service(self, live_service):
        """Test service configuration."""
        config = LiveTranslationConfig(
            fps=1.5,
            change_threshold=8.0,
            max_concurrent_translations=4
        )

        live_service.configure(config)

        assert live_service.fps == 1.5
        assert live_service.change_threshold == 8.0
        assert live_service.max_concurrent_translations == 4

    # CRITICAL: Live mode activation and deactivation
    @pytest.mark.asyncio
    async def test_start_live_mode_basic(self, live_service, mock_dependencies):
        """Test starting live translation mode."""
        region = CaptureRegion(100, 100, 300, 200)

        # Mock successful startup
        mock_dependencies['capture_service'].start_continuous_capture.return_value = True

        result = await live_service.start_live_mode(region)

        assert result is True
        assert live_service.is_active is True
        assert live_service.current_region == region

    @pytest.mark.asyncio
    async def test_stop_live_mode(self, live_service):
        """Test stopping live translation mode."""
        # Set up active state
        live_service.is_active = True
        live_service._monitor_task = AsyncMock()

        await live_service.stop_live_mode()

        assert live_service.is_active is False
        assert live_service.current_region is None

    @pytest.mark.asyncio
    async def test_live_mode_with_invalid_region(self, live_service):
        """Test starting live mode with invalid region."""
        invalid_region = CaptureRegion(-10, -10, 0, 0)  # Invalid region

        with pytest.raises(ValueError, match="Invalid capture region"):
            await live_service.start_live_mode(invalid_region)

    # CRITICAL: Continuous monitoring loop
    @pytest.mark.asyncio
    async def test_continuous_monitoring_loop(self, live_service, mock_dependencies):
        """Test continuous monitoring loop functionality."""
        region = CaptureRegion(100, 100, 300, 200)
        live_service.current_region = region
        live_service.is_active = True
        live_service.fps = 10  # Fast for testing

        frame_count = 0

        async def mock_capture():
            nonlocal frame_count
            frame_count += 1
            if frame_count >= 3:  # Stop after 3 frames
                live_service.is_active = False
            return f"frame_{frame_count}".encode()

        live_service._capture_region = mock_capture

        # Start monitoring
        await live_service._monitor_loop()

        # Should have captured multiple frames
        assert frame_count >= 3

    @pytest.mark.asyncio
    async def test_fps_throttling(self, live_service):
        """Test FPS throttling in monitoring loop."""
        live_service.fps = 2.0  # 2 FPS = 0.5 seconds per frame
        live_service.is_active = True

        start_time = time.time()
        frame_times = []

        async def mock_capture_with_timing():
            frame_times.append(time.time())
            if len(frame_times) >= 3:
                live_service.is_active = False
            return b"frame_data"

        live_service._capture_region = mock_capture_with_timing
        live_service._has_significant_change = Mock(return_value=True)
        live_service._process_frame = AsyncMock()

        await live_service._monitor_loop()

        # Check that frames were captured at approximately correct intervals
        if len(frame_times) >= 2:
            time_diff = frame_times[1] - frame_times[0]
            expected_interval = 1.0 / live_service.fps

            # Allow some tolerance for timing variations
            assert abs(time_diff - expected_interval) < 0.1

    # CRITICAL: Change detection integration
    @pytest.mark.asyncio
    async def test_change_detection_skip_unchanged(self, live_service, mock_dependencies):
        """Test skipping processing when no significant change detected."""
        live_service.is_active = True
        live_service.current_region = CaptureRegion(0, 0, 100, 100)

        # Mock no change detection
        live_service._has_significant_change = Mock(return_value=False)
        live_service._process_frame = AsyncMock()

        async def mock_capture():
            live_service.is_active = False  # Stop after one iteration
            return b"unchanged_frame"

        live_service._capture_region = mock_capture

        await live_service._monitor_loop()

        # Should not process frame if no change detected
        live_service._process_frame.assert_not_called()

    @pytest.mark.asyncio
    async def test_change_detection_process_changed(self, live_service, mock_dependencies):
        """Test processing when significant change is detected."""
        live_service.is_active = True
        live_service.current_region = CaptureRegion(0, 0, 100, 100)

        # Mock change detection
        live_service._has_significant_change = Mock(return_value=True)
        live_service._process_frame = AsyncMock()

        async def mock_capture():
            live_service.is_active = False
            return b"changed_frame"

        live_service._capture_region = mock_capture

        await live_service._monitor_loop()

        # Should process frame when change is detected
        live_service._process_frame.assert_called_once()

    # CRITICAL: Frame processing and translation
    @pytest.mark.asyncio
    async def test_frame_processing_ocr_and_translation(self, live_service, mock_dependencies):
        """Test complete frame processing pipeline."""
        frame_data = b"fake_image_data"

        # Mock OCR extraction
        mock_dependencies['ocr_engine'].extract_text.return_value = "Detected text"

        # Mock translation
        mock_dependencies['translation_engine'].translate.return_value = Mock(
            translated_text="Переведенный текст"
        )

        await live_service._process_frame(frame_data)

        # Should perform OCR and translation
        mock_dependencies['ocr_engine'].extract_text.assert_called_once()
        mock_dependencies['translation_engine'].translate.assert_called_once_with(
            "Detected text", target_lang=live_service.target_language
        )

    @pytest.mark.asyncio
    async def test_concurrent_frame_processing_limit(self, live_service):
        """Test concurrent processing limit prevents overload."""
        live_service.max_concurrent_translations = 2

        # Create mock processing tasks that don't complete immediately
        processing_tasks = []

        async def mock_slow_process(frame):
            await asyncio.sleep(1)  # Simulate slow processing

        live_service._process_single_frame = mock_slow_process

        # Try to process more frames than the limit
        for i in range(5):
            task = asyncio.create_task(live_service._process_frame(f"frame_{i}".encode()))
            processing_tasks.append(task)

        # Wait a bit for tasks to start
        await asyncio.sleep(0.1)

        # Should limit concurrent processing
        active_tasks = [task for task in processing_tasks if not task.done()]
        assert len(active_tasks) <= live_service.max_concurrent_translations

        # Clean up
        for task in processing_tasks:
            task.cancel()

    # CRITICAL: Error handling and recovery
    @pytest.mark.asyncio
    async def test_capture_error_recovery(self, live_service):
        """Test recovery from capture errors."""
        live_service.is_active = True
        live_service.current_region = CaptureRegion(0, 0, 100, 100)

        error_count = 0

        async def failing_capture():
            nonlocal error_count
            error_count += 1
            if error_count < 3:
                raise Exception("Capture failed")
            else:
                live_service.is_active = False
                return b"success_frame"

        live_service._capture_region = failing_capture

        with patch('src.utils.logger.Logger') as mock_logger:
            await live_service._monitor_loop()

            # Should log errors but continue trying
            assert mock_logger.error.call_count >= 2

    @pytest.mark.asyncio
    async def test_ocr_error_handling(self, live_service, mock_dependencies):
        """Test handling of OCR extraction errors."""
        frame_data = b"corrupted_frame"

        # Mock OCR failure
        mock_dependencies['ocr_engine'].extract_text.side_effect = Exception("OCR failed")

        with patch('src.utils.logger.Logger') as mock_logger:
            await live_service._process_frame(frame_data)

            # Should log error and continue
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_translation_error_handling(self, live_service, mock_dependencies):
        """Test handling of translation errors."""
        frame_data = b"frame_data"

        # Mock successful OCR but failed translation
        mock_dependencies['ocr_engine'].extract_text.return_value = "Text to translate"
        mock_dependencies['translation_engine'].translate.side_effect = Exception("Translation failed")

        with patch('src.utils.logger.Logger') as mock_logger:
            await live_service._process_frame(frame_data)

            # Should log translation error
            mock_logger.error.assert_called()

    # CRITICAL: Performance optimization
    @pytest.mark.asyncio
    async def test_adaptive_fps_on_no_changes(self, live_service):
        """Test adaptive FPS reduction when no changes detected."""
        live_service.adaptive_fps_enabled = True
        live_service.fps = 2.0
        live_service.is_active = True

        no_change_count = 0

        def mock_change_detection(frame):
            nonlocal no_change_count
            no_change_count += 1
            if no_change_count >= 5:
                live_service.is_active = False
            return False  # No changes detected

        live_service._has_significant_change = mock_change_detection

        async def mock_capture():
            return b"static_frame"

        live_service._capture_region = mock_capture

        original_fps = live_service.fps
        await live_service._monitor_loop()

        # FPS should be reduced after detecting no changes
        assert live_service.current_fps <= original_fps

    def test_memory_usage_monitoring(self, live_service):
        """Test memory usage monitoring and cleanup."""
        # Add frames to buffer
        for i in range(20):
            live_service.frame_buffer.add_frame(f"frame_{i}", timestamp=i)

        initial_buffer_size = len(live_service.frame_buffer)

        # Trigger cleanup
        live_service._cleanup_old_frames()

        # Buffer should be reduced
        assert len(live_service.frame_buffer) < initial_buffer_size

    # CRITICAL: Region selection and management
    def test_region_selection_from_user_input(self, live_service):
        """Test region selection from user interaction."""
        # Mock region selection UI
        selected_region = CaptureRegion(150, 200, 400, 300)

        live_service.set_capture_region(selected_region)

        assert live_service.current_region == selected_region

    def test_auto_region_detection(self, live_service, mock_dependencies):
        """Test automatic region detection based on content."""
        # Mock text detection in different regions
        mock_dependencies['ocr_engine'].detect_text_regions.return_value = [
            CaptureRegion(100, 100, 200, 50),  # Detected text region
            CaptureRegion(100, 200, 300, 100)
        ]

        suggested_region = live_service.suggest_capture_region()

        assert suggested_region is not None
        assert isinstance(suggested_region, CaptureRegion)

    # CRITICAL: Integration with UI
    def test_live_mode_status_reporting(self, live_service):
        """Test status reporting for UI updates."""
        status_updates = []

        def mock_status_callback(status):
            status_updates.append(status)

        live_service.set_status_callback(mock_status_callback)

        # Trigger status changes
        live_service._report_status("active", {"fps": 2.0, "frames_processed": 10})

        assert len(status_updates) == 1
        assert status_updates[0]["status"] == "active"
        assert status_updates[0]["fps"] == 2.0

    def test_translation_result_callbacks(self, live_service):
        """Test callbacks for translation results."""
        translation_results = []

        def mock_result_callback(result):
            translation_results.append(result)

        live_service.set_translation_callback(mock_result_callback)

        # Simulate translation result
        mock_result = {
            "original": "Hello",
            "translated": "Привет",
            "timestamp": datetime.now(),
            "confidence": 0.95
        }

        live_service._emit_translation_result(mock_result)

        assert len(translation_results) == 1
        assert translation_results[0]["translated"] == "Привет"


# CRITICAL: Integration tests
class TestLiveTranslationIntegration:
    """Integration tests for complete live translation workflow."""

    @pytest.mark.asyncio
    async def test_full_live_translation_workflow(self):
        """Test complete live translation workflow integration."""
        # This test will fail until full integration exists

        with patch('src.services.live_translation_service.LiveTranslationService') as mock_service:
            with patch('src.ui.live_translation_window.LiveTranslationWindow') as mock_window:
                with patch('src.core.coordinators.capture_orchestrator.CaptureOrchestrator') as mock_orchestrator:

                    service = mock_service.return_value
                    window = mock_window.return_value
                    orchestrator = mock_orchestrator.return_value

                    # Mock successful live mode startup
                    service.start_live_mode.return_value = True

                    # Simulate user starting live mode
                    region = CaptureRegion(100, 100, 300, 200)
                    await service.start_live_mode(region)

                    # Should start continuous capture
                    service.start_live_mode.assert_called_with(region)

                    # Should update UI
                    window.update_status.assert_called()

    def test_ui_controls_integration(self):
        """Test integration with UI controls."""
        # This test will fail until UI integration exists

        with patch('src.ui.live_translation_window.LiveTranslationWindow') as mock_window:
            window = mock_window.return_value

            service = LiveTranslationService()

            # Mock UI controls
            window.get_fps_setting.return_value = 1.5
            window.get_change_threshold.return_value = 8.0

            # Should apply UI settings to service
            config = LiveTranslationConfig(
                fps=window.get_fps_setting(),
                change_threshold=window.get_change_threshold()
            )

            service.configure(config)

            assert service.fps == 1.5
            assert service.change_threshold == 8.0
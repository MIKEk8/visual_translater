"""Unit tests for CaptureOrchestrator - Screenshot capture coordinator"""

import sys
import unittest
from unittest.mock import MagicMock, Mock, patch, call, ANY
import threading
from typing import Optional

# Mock GUI modules before imports but preserve Canvas for specific patching
tkinter_mock = MagicMock()
canvas_instance_mock = MagicMock()  # This is what Canvas() returns
canvas_mock = MagicMock(return_value=canvas_instance_mock)  # This is the Canvas constructor
tkinter_mock.Canvas = canvas_mock
tkinter_mock.BOTH = MagicMock()
sys.modules['tkinter'] = tkinter_mock
sys.modules['pystray'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()

from src.core.coordinators.capture_orchestrator import CaptureOrchestrator
from src.core.events import EventType
from src.services.task_queue import TaskPriority
from src.utils.exceptions import ScreenshotCaptureError


class TestCaptureOrchestrator(unittest.TestCase):
    """Test suite for CaptureOrchestrator"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset global mocks first
        canvas_instance_mock.reset_mock()
        canvas_mock.reset_mock()
        tkinter_mock.reset_mock()
        
        # Create mocks
        self.mock_root = MagicMock()
        self.mock_screenshot_engine = MagicMock()
        self.mock_progress_manager = MagicMock()
        self.mock_on_area_captured = MagicMock()
        self.mock_on_capture_error = MagicMock()
        
        # Configure root mock
        self.mock_root.winfo_screenwidth.return_value = 1920
        self.mock_root.winfo_screenheight.return_value = 1080
        
        # Use the canvas instance mock (what Canvas() returns)
        self.mock_canvas = canvas_instance_mock
        
        # Patch dependencies 
        self.patches = [
            patch('src.core.coordinators.capture_orchestrator.get_task_queue'),
            patch('src.core.coordinators.capture_orchestrator.publish_event'),
            patch('src.core.coordinators.capture_orchestrator.logger'),
        ]
        
        self.mocks = {}
        for p in self.patches:
            mock = p.start()
            self.mocks[p.attribute] = mock
            
        # Canvas is available via sys.modules['tkinter'].Canvas
        self.mocks['Canvas'] = sys.modules['tkinter'].Canvas
            
        # Configure task queue mock
        self.mock_task_queue = MagicMock()
        self.mocks['get_task_queue'].return_value = self.mock_task_queue
        self.mock_task_queue.submit.return_value = "task-123"

    def tearDown(self):
        """Clean up patches"""
        for p in self.patches:
            p.stop()

    def test_initialization(self):
        """Test CaptureOrchestrator initialization"""
        # Act
        orchestrator = CaptureOrchestrator(
            self.mock_root,
            self.mock_screenshot_engine,
            self.mock_progress_manager,
            self.mock_on_area_captured,
            self.mock_on_capture_error
        )
        
        # Assert
        self.assertEqual(orchestrator.root, self.mock_root)
        self.assertEqual(orchestrator.screenshot_engine, self.mock_screenshot_engine)
        self.assertEqual(orchestrator.progress_manager, self.mock_progress_manager)
        self.assertEqual(orchestrator.on_area_captured, self.mock_on_area_captured)
        self.assertEqual(orchestrator.on_capture_error, self.mock_on_capture_error)
        self.assertIsNotNone(orchestrator._lock)
        self.assertIsInstance(orchestrator._lock, type(threading.Lock()))
        
        # Verify overlay setup
        self.mock_root.attributes.assert_any_call("-alpha", 0.3)
        self.mock_root.configure.assert_called_with(background="black")
        self.mock_root.attributes.assert_any_call("-fullscreen", True)
        self.mock_root.overrideredirect.assert_called_with(True)
        
        # Verify canvas setup - check that Canvas was called with correct params
        canvas_mock.assert_called_with(self.mock_root, cursor="cross", bg="grey11") 
        self.mock_canvas.pack.assert_called_with(fill=tkinter_mock.BOTH, expand=True)
        
        # Verify event bindings
        self.mock_canvas.bind.assert_any_call("<ButtonPress-1>", orchestrator._on_press)
        self.mock_canvas.bind.assert_any_call("<B1-Motion>", orchestrator._on_drag)
        self.mock_canvas.bind.assert_any_call("<ButtonRelease-1>", orchestrator._on_release)

    def test_capture_area(self):
        """Test showing area selection overlay"""
        # Setup
        orchestrator = CaptureOrchestrator(
            self.mock_root,
            self.mock_screenshot_engine,
            self.mock_progress_manager
        )
        
        # Act
        orchestrator.capture_area()
        
        # Assert
        self.mock_root.deiconify.assert_called_once()
        self.mock_root.attributes.assert_any_call("-topmost", True)
        self.mock_root.focus_force.assert_called_once()
        self.mocks['logger'].info.assert_called_with("CaptureOrchestrator: Starting area selection")

    def test_quick_translate_center(self):
        """Test quick translate center area"""
        # Setup
        orchestrator = CaptureOrchestrator(
            self.mock_root,
            self.mock_screenshot_engine,
            self.mock_progress_manager
        )
        
        # Act
        orchestrator.quick_translate_center()
        
        # Assert
        self.mock_progress_manager.show_progress.assert_called_once_with(
            title="Quick Translation",
            message="Translating center area...",
            is_indeterminate=True
        )
        
        # Verify task submission
        self.mock_task_queue.submit.assert_called_once()
        call_args = self.mock_task_queue.submit.call_args
        self.assertEqual(call_args.kwargs['name'], "quick_translate_center")
        self.assertEqual(call_args.kwargs['priority'], TaskPriority.HIGH)
        self.assertEqual(call_args.kwargs['args'], (1920, 1080))

    def test_quick_translate_bottom(self):
        """Test quick translate bottom area"""
        # Setup
        orchestrator = CaptureOrchestrator(
            self.mock_root,
            self.mock_screenshot_engine,
            self.mock_progress_manager
        )
        
        # Act
        orchestrator.quick_translate_bottom()
        
        # Assert
        self.mock_progress_manager.show_progress.assert_called_once_with(
            title="Quick Translation",
            message="Translating bottom area...",
            is_indeterminate=True
        )
        
        # Verify task submission
        self.mock_task_queue.submit.assert_called_once()
        call_args = self.mock_task_queue.submit.call_args
        self.assertEqual(call_args.kwargs['name'], "quick_translate_bottom")
        self.assertEqual(call_args.kwargs['priority'], TaskPriority.HIGH)
        self.assertEqual(call_args.kwargs['args'], (1920, 1080))

    def test_mouse_event_flow(self):
        """Test complete mouse event flow for area selection"""
        # Setup
        orchestrator = CaptureOrchestrator(
            self.mock_root,
            self.mock_screenshot_engine,
            self.mock_progress_manager
        )
        
        # Create mock events
        press_event = MagicMock()
        press_event.x_root = 100
        press_event.y_root = 100
        press_event.x = 100
        press_event.y = 100
        
        drag_event = MagicMock()
        drag_event.x = 200
        drag_event.y = 200
        
        release_event = MagicMock()
        release_event.x_root = 300
        release_event.y_root = 300
        
        # Mock canvas methods
        self.mock_canvas.canvasx.side_effect = lambda x: x
        self.mock_canvas.canvasy.side_effect = lambda y: y
        rect_id = 1
        self.mock_canvas.create_rectangle.return_value = rect_id
        
        # Act - simulate mouse events
        orchestrator._on_press(press_event)
        orchestrator._on_drag(drag_event)
        orchestrator._on_release(release_event)
        
        # Assert
        # Check rectangle creation
        self.mock_canvas.create_rectangle.assert_called_once_with(
            100, 100, 100, 100, outline="red", width=2
        )
        
        # Check rectangle update during drag
        self.mock_canvas.coords.assert_called_with(rect_id, 100, 100, 200, 200)
        
        # Check rectangle deletion on release
        self.mock_canvas.delete.assert_called_once_with(rect_id)
        
        # Check overlay hiding
        self.mock_root.withdraw.assert_called()
        
        # Check progress indicator
        self.mock_progress_manager.show_progress.assert_called_once()
        
        # Check task submission
        self.mock_task_queue.submit.assert_called_once()
        call_args = self.mock_task_queue.submit.call_args
        self.assertEqual(call_args.kwargs['args'], (100, 100, 300, 300))  # min/max coordinates

    def test_process_area_capture_success(self):
        """Test successful area capture processing"""
        # Setup
        orchestrator = CaptureOrchestrator(
            self.mock_root,
            self.mock_screenshot_engine,
            self.mock_progress_manager
        )
        
        mock_screenshot_data = {"image": "test_image", "coordinates": (0, 0, 100, 100)}
        self.mock_screenshot_engine.capture_area.return_value = mock_screenshot_data
        
        # Act
        result = orchestrator._process_area_capture(0, 0, 100, 100)
        
        # Assert
        self.assertEqual(result, mock_screenshot_data)
        self.mock_screenshot_engine.capture_area.assert_called_once_with(0, 0, 100, 100)
        
        # Verify events published
        self.mocks['publish_event'].assert_any_call(
            EventType.SCREENSHOT_REQUESTED,
            data={"coordinates": (0, 0, 100, 100)},
            source="capture_orchestrator"
        )
        self.mocks['publish_event'].assert_any_call(
            EventType.SCREENSHOT_CAPTURED,
            data=mock_screenshot_data,
            source="capture_orchestrator"
        )

    def test_process_area_capture_failure(self):
        """Test area capture failure handling"""
        # Setup
        orchestrator = CaptureOrchestrator(
            self.mock_root,
            self.mock_screenshot_engine,
            self.mock_progress_manager
        )
        
        self.mock_screenshot_engine.capture_area.return_value = None
        
        # Act & Assert
        with self.assertRaises(ScreenshotCaptureError) as cm:
            orchestrator._process_area_capture(0, 0, 100, 100)
        
        # Verify error details
        self.assertIn("Failed to capture screenshot area", str(cm.exception))
        
        # Verify failure event published
        self.mocks['publish_event'].assert_any_call(
            EventType.SCREENSHOT_FAILED,
            data={"error": "Failed to capture screenshot", "coordinates": (0, 0, 100, 100)},
            source="capture_orchestrator"
        )

    def test_process_center_capture_success(self):
        """Test successful center area capture"""
        # Setup
        orchestrator = CaptureOrchestrator(
            self.mock_root,
            self.mock_screenshot_engine,
            self.mock_progress_manager
        )
        
        mock_screenshot_data = {"image": "center_image"}
        self.mock_screenshot_engine.capture_center_area.return_value = mock_screenshot_data
        
        # Act
        result = orchestrator._process_center_capture(1920, 1080)
        
        # Assert
        self.assertEqual(result, mock_screenshot_data)
        self.mock_screenshot_engine.capture_center_area.assert_called_once_with(1920, 1080)

    def test_process_center_capture_failure(self):
        """Test center area capture failure"""
        # Setup
        orchestrator = CaptureOrchestrator(
            self.mock_root,
            self.mock_screenshot_engine,
            self.mock_progress_manager
        )
        
        self.mock_screenshot_engine.capture_center_area.return_value = None
        
        # Act & Assert
        with self.assertRaises(ScreenshotCaptureError) as cm:
            orchestrator._process_center_capture(1920, 1080)
        
        self.assertIn("Failed to capture center area", str(cm.exception))

    def test_process_bottom_capture_success(self):
        """Test successful bottom area capture"""
        # Setup
        orchestrator = CaptureOrchestrator(
            self.mock_root,
            self.mock_screenshot_engine,
            self.mock_progress_manager
        )
        
        mock_screenshot_data = {"image": "bottom_image"}
        self.mock_screenshot_engine.capture_bottom_area.return_value = mock_screenshot_data
        
        # Act
        result = orchestrator._process_bottom_capture(1920, 1080)
        
        # Assert
        self.assertEqual(result, mock_screenshot_data)
        self.mock_screenshot_engine.capture_bottom_area.assert_called_once_with(1920, 1080)

    def test_process_bottom_capture_failure(self):
        """Test bottom area capture failure"""
        # Setup
        orchestrator = CaptureOrchestrator(
            self.mock_root,
            self.mock_screenshot_engine,
            self.mock_progress_manager
        )
        
        self.mock_screenshot_engine.capture_bottom_area.return_value = None
        
        # Act & Assert
        with self.assertRaises(ScreenshotCaptureError) as cm:
            orchestrator._process_bottom_capture(1920, 1080)
        
        self.assertIn("Failed to capture bottom area", str(cm.exception))

    def test_capture_success_callback(self):
        """Test successful capture callback invocation"""
        # Setup
        orchestrator = CaptureOrchestrator(
            self.mock_root,
            self.mock_screenshot_engine,
            self.mock_progress_manager,
            self.mock_on_area_captured
        )
        
        mock_data = {"image": "test"}
        
        # Act
        orchestrator._on_capture_success(mock_data)
        
        # Assert
        self.mock_on_area_captured.assert_called_once_with(mock_data)

    def test_capture_success_no_callback(self):
        """Test capture success without callback"""
        # Setup
        orchestrator = CaptureOrchestrator(
            self.mock_root,
            self.mock_screenshot_engine,
            self.mock_progress_manager
        )
        
        # Act - should not raise exception
        orchestrator._on_capture_success({"image": "test"})

    def test_capture_error_callback(self):
        """Test error callback invocation"""
        # Setup
        orchestrator = CaptureOrchestrator(
            self.mock_root,
            self.mock_screenshot_engine,
            self.mock_progress_manager,
            on_capture_error=self.mock_on_capture_error
        )
        
        error = Exception("Test error")
        
        # Act
        orchestrator._on_capture_error_callback(error)
        
        # Assert
        self.mock_on_capture_error.assert_called_once_with(error)

    def test_capture_error_no_callback(self):
        """Test capture error without callback"""
        # Setup
        orchestrator = CaptureOrchestrator(
            self.mock_root,
            self.mock_screenshot_engine,
            self.mock_progress_manager
        )
        
        # Act - should not raise exception
        orchestrator._on_capture_error_callback(Exception("Test"))

    def test_thread_safety(self):
        """Test thread safety with locks"""
        # Setup
        orchestrator = CaptureOrchestrator(
            self.mock_root,
            self.mock_screenshot_engine,
            self.mock_progress_manager
        )
        
        # Verify lock is created
        self.assertIsInstance(orchestrator._lock, type(threading.Lock()))
        
        # Test that operations use locks
        orchestrator.quick_translate_center()
        
        # Progress manager and task queue should be called (proving lock was acquired)
        self.mock_progress_manager.show_progress.assert_called_once()
        self.mock_task_queue.submit.assert_called_once()

    def test_hide_overlay(self):
        """Test overlay hiding"""
        # Setup
        orchestrator = CaptureOrchestrator(
            self.mock_root,
            self.mock_screenshot_engine,
            self.mock_progress_manager
        )
        
        # Reset mock to clear initialization calls
        self.mock_root.withdraw.reset_mock()
        
        # Act
        orchestrator._hide_overlay()
        
        # Assert
        self.mock_root.withdraw.assert_called_once()

    def test_exception_handling_in_process_methods(self):
        """Test exception handling in process methods"""
        # Setup
        orchestrator = CaptureOrchestrator(
            self.mock_root,
            self.mock_screenshot_engine,
            self.mock_progress_manager
        )
        
        # Mock screenshot engine to raise exception
        self.mock_screenshot_engine.capture_area.side_effect = RuntimeError("Engine error")
        
        # Act & Assert
        with self.assertRaises(RuntimeError):
            orchestrator._process_area_capture(0, 0, 100, 100)
        
        # Verify error logging
        self.mocks['logger'].error.assert_called_once()

    def test_coordinate_normalization_in_release(self):
        """Test that coordinates are normalized (min/max) on release"""
        # Setup
        orchestrator = CaptureOrchestrator(
            self.mock_root,
            self.mock_screenshot_engine,
            self.mock_progress_manager
        )
        
        # Create events with reversed coordinates
        press_event = MagicMock()
        press_event.x_root = 300
        press_event.y_root = 300
        
        release_event = MagicMock()
        release_event.x_root = 100
        release_event.y_root = 100
        
        # Setup canvas mocks
        self.mock_canvas.canvasx.side_effect = lambda x: x
        self.mock_canvas.canvasy.side_effect = lambda y: y
        
        # Act
        orchestrator._on_press(press_event)
        orchestrator._on_release(release_event)
        
        # Assert - coordinates should be normalized (min first)
        call_args = self.mock_task_queue.submit.call_args
        self.assertEqual(call_args.kwargs['args'], (100, 100, 300, 300))


if __name__ == '__main__':
    unittest.main()
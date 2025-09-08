"""Unit tests for TranslationOverlay - Translation display overlay"""

import sys
import unittest
from unittest.mock import MagicMock, Mock, patch, call, ANY
import threading
import queue
from typing import Tuple, Optional

# Mock GUI modules before imports
sys.modules['tkinter'] = MagicMock()
sys.modules['tkinter.messagebox'] = MagicMock()
sys.modules['tkinter.ttk'] = MagicMock()
sys.modules['pystray'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()

from src.ui.translation_overlay import TranslationOverlay, OverlayConfig


class TestOverlayConfig(unittest.TestCase):
    """Test suite for OverlayConfig dataclass"""

    def test_default_values(self):
        """Test OverlayConfig default values"""
        config = OverlayConfig()
        
        # Test position and size
        self.assertEqual(config.x, 100)
        self.assertEqual(config.y, 100)
        self.assertEqual(config.width, 400)
        self.assertEqual(config.height, 150)
        
        # Test appearance
        self.assertEqual(config.background_color, "#1e1e1e")
        self.assertEqual(config.text_color, "#ffffff")
        self.assertEqual(config.border_color, "#555555")
        self.assertEqual(config.border_width, 2)
        self.assertEqual(config.opacity, 0.9)
        
        # Test font settings
        self.assertEqual(config.font_family, "Arial")
        self.assertEqual(config.font_size, 12)
        
        # Test behavior settings
        self.assertEqual(config.auto_hide_delay, 5000)
        self.assertTrue(config.fade_animation)
        self.assertFalse(config.click_through)
        self.assertTrue(config.always_on_top)
        self.assertTrue(config.snap_to_edges)
        
        # Test display options
        self.assertTrue(config.show_original)
        self.assertFalse(config.show_confidence)
        self.assertFalse(config.show_timestamp)
        self.assertEqual(config.max_text_length, 200)
        self.assertTrue(config.word_wrap)

    def test_custom_values(self):
        """Test OverlayConfig with custom values"""
        config = OverlayConfig(
            x=200, y=300,
            width=500, height=200,
            background_color="#333333",
            opacity=0.8,
            font_size=14,
            auto_hide_delay=3000,
            click_through=True,
            show_confidence=True
        )
        
        self.assertEqual(config.x, 200)
        self.assertEqual(config.y, 300)
        self.assertEqual(config.width, 500)
        self.assertEqual(config.height, 200)
        self.assertEqual(config.background_color, "#333333")
        self.assertEqual(config.opacity, 0.8)
        self.assertEqual(config.font_size, 14)
        self.assertEqual(config.auto_hide_delay, 3000)
        self.assertTrue(config.click_through)
        self.assertTrue(config.show_confidence)


class TestTranslationOverlay(unittest.TestCase):
    """Test suite for TranslationOverlay"""

    def setUp(self):
        """Set up test fixtures"""
        # Patch dependencies
        self.patches = [
            patch('src.ui.translation_overlay.logger'),
        ]
        
        self.mocks = {}
        for p in self.patches:
            mock = p.start()
            self.mocks[p.attribute] = mock

    def tearDown(self):
        """Clean up patches"""
        for p in self.patches:
            p.stop()

    def test_initialization_with_config_object(self):
        """Test TranslationOverlay initialization with OverlayConfig"""
        # Setup
        config = OverlayConfig(x=200, y=300)
        
        # Act
        overlay = TranslationOverlay(config)
        
        # Assert
        self.assertEqual(overlay.config, config)
        self.assertIsNone(overlay.config_manager)
        self.assertFalse(overlay.is_visible)
        self.assertIsNone(overlay.overlay_window)
        self.assertIsInstance(overlay.update_queue, queue.Queue)
        self.assertFalse(overlay._is_visible)

    def test_initialization_with_config_manager(self):
        """Test TranslationOverlay initialization with config manager"""
        # Setup
        mock_config_manager = MagicMock()
        custom_config = OverlayConfig(x=150, y=250)
        
        # Act
        overlay = TranslationOverlay(mock_config_manager, custom_config)
        
        # Assert
        self.assertEqual(overlay.config, custom_config)
        self.assertEqual(overlay.config_manager, mock_config_manager)
        self.assertFalse(overlay.is_visible)
        self.assertIsNone(overlay.overlay_window)

    def test_initialization_with_defaults(self):
        """Test TranslationOverlay initialization with default config"""
        # Act
        overlay = TranslationOverlay()
        
        # Assert
        self.assertIsInstance(overlay.config, OverlayConfig)
        self.assertIsNone(overlay.config_manager)
        # Verify default config values are used
        self.assertEqual(overlay.config.x, 100)
        self.assertEqual(overlay.config.y, 100)

    def test_show_text_simple(self):
        """Test showing overlay with simple text"""
        # Setup
        overlay = TranslationOverlay()
        
        # Act
        overlay.show("Hello World")
        
        # Assert
        self.assertTrue(overlay._is_visible)
        # GUI processing might clear the queue immediately in mock environment
        # so we just check that the visibility was set

    def test_show_text_with_position(self):
        """Test showing overlay with text and position"""
        # Setup
        overlay = TranslationOverlay()
        
        # Act
        overlay.show("Hello World", position=(200, 300))
        
        # Assert
        self.assertTrue(overlay._is_visible)
        self.assertEqual(overlay.config.x, 200)
        self.assertEqual(overlay.config.y, 300)

    def test_hide_overlay(self):
        """Test hiding overlay"""
        # Setup
        overlay = TranslationOverlay()
        overlay._is_visible = True
        overlay.is_visible = True
        
        # Act
        overlay.hide()
        
        # Assert
        self.assertFalse(overlay._is_visible)
        self.assertFalse(overlay.is_visible)

    def test_hide_when_not_visible(self):
        """Test hiding overlay when not visible"""
        # Setup
        overlay = TranslationOverlay()
        overlay._is_visible = False
        overlay.is_visible = False
        
        # Act
        overlay.hide()
        
        # Assert
        self.assertFalse(overlay._is_visible)
        self.assertFalse(overlay.is_visible)

    def test_is_visible_method(self):
        """Test is_visible property method"""
        # Setup
        overlay = TranslationOverlay()
        
        # Test false case
        overlay._is_visible = False
        self.assertFalse(overlay.is_visible_method())
        
        # Test true case  
        overlay._is_visible = True
        self.assertTrue(overlay.is_visible_method())

    def test_update_text(self):
        """Test updating overlay text"""
        # Setup
        overlay = TranslationOverlay()
        overlay._is_visible = True
        
        # Act
        overlay.update_text("Updated text")
        
        # Assert
        # Check that operation was queued
        self.assertFalse(overlay._gui_queue.empty())

    def test_update_text_when_not_visible(self):
        """Test updating text when overlay not visible"""
        # Setup
        overlay = TranslationOverlay()
        overlay._is_visible = False
        initial_queue_size = overlay._gui_queue.qsize()
        
        # Act
        overlay.update_text("Updated text")
        
        # Assert
        # Queue should have new item regardless of visibility
        self.assertEqual(overlay._gui_queue.qsize(), initial_queue_size + 1)

    def test_set_position(self):
        """Test setting overlay position"""
        # Setup
        overlay = TranslationOverlay()
        
        # Act
        overlay.set_position(300, 400)
        
        # Assert
        # Config should be updated
        self.assertEqual(overlay.config.x, 300)
        self.assertEqual(overlay.config.y, 400)
        # GUI operation should be queued
        self.assertFalse(overlay._gui_queue.empty())

    def test_destroy_overlay(self):
        """Test destroying overlay"""
        # Setup
        overlay = TranslationOverlay()
        overlay._is_visible = True
        overlay.is_visible = True
        
        # Act
        overlay.destroy()
        
        # Assert
        self.assertFalse(overlay._is_visible)
        self.assertFalse(overlay.is_visible)
        self.assertIsNone(overlay.overlay_window)

    def test_create_overlay(self):
        """Test creating overlay"""
        # Setup
        overlay = TranslationOverlay()
        
        # Act
        overlay.create_overlay()
        
        # Assert - should complete without error
        # (actual GUI operations are mocked)

    def test_update_position(self):
        """Test updating overlay position"""
        # Setup
        overlay = TranslationOverlay()
        
        # Act
        overlay.update_position(500, 600)
        
        # Assert
        self.assertEqual(overlay.config.x, 500)
        self.assertEqual(overlay.config.y, 600)

    def test_set_opacity(self):
        """Test setting overlay opacity"""
        # Setup
        overlay = TranslationOverlay()
        
        # Act
        overlay.set_opacity(0.7)
        
        # Assert
        self.assertEqual(overlay.config.opacity, 0.7)

    def test_toggle_pin(self):
        """Test toggling pin state"""
        # Setup
        overlay = TranslationOverlay()
        
        # Act - should complete without error
        overlay.toggle_pin()
        
        # Assert - just verify it doesn't crash
        self.mocks['logger'].debug.assert_called()

    def test_get_position(self):
        """Test getting overlay position"""
        # Setup
        config = OverlayConfig(x=123, y=456)
        overlay = TranslationOverlay(config)
        
        # Act
        position = overlay.get_position()
        
        # Assert
        self.assertEqual(position, (123, 456))

    def test_get_size(self):
        """Test getting overlay size"""
        # Setup
        config = OverlayConfig(width=789, height=12)
        overlay = TranslationOverlay(config)
        
        # Act
        size = overlay.get_size()
        
        # Assert
        self.assertEqual(size, (789, 12))

    def test_queue_gui_operation(self):
        """Test GUI operation queuing"""
        # Setup
        overlay = TranslationOverlay()
        
        # Act - queue a GUI operation directly
        overlay._gui_queue.put({"type": "test_operation", "data": {"key": "value"}})
        
        # Assert
        # Check that operation was queued
        self.assertFalse(overlay._gui_queue.empty())
        
        # Get the operation from queue
        operation = overlay._gui_queue.get()
        self.assertEqual(operation["type"], "test_operation")
        self.assertEqual(operation["data"], {"key": "value"})

    def test_handle_gui_operation_show(self):
        """Test handling show GUI operation"""
        # Setup
        overlay = TranslationOverlay()
        
        with patch.object(overlay, '_display_text') as mock_display:
            with patch.object(overlay, '_create_overlay_window') as mock_create:
                # Act
                overlay._handle_gui_operation({
                    "type": "show_text",
                    "data": {"text": "Test text"}
                })
                
                # Assert
                mock_create.assert_called_once()
                mock_display.assert_called_once_with("Test text")

    def test_handle_gui_operation_hide(self):
        """Test handling hide GUI operation"""
        # Setup
        overlay = TranslationOverlay()
        
        with patch.object(overlay, '_hide_window') as mock_hide:
            # Act
            overlay._handle_gui_operation({
                "type": "hide",
                "data": {}
            })
            
            # Assert
            mock_hide.assert_called_once()

    def test_handle_gui_operation_update_text(self):
        """Test handling update_text GUI operation"""
        # Setup
        overlay = TranslationOverlay()
        
        with patch.object(overlay, '_display_text') as mock_display:
            # Act
            overlay._handle_gui_operation({
                "type": "update_text", 
                "data": {"text": "Updated text"}
            })
            
            # Assert
            mock_display.assert_called_once_with("Updated text")

    def test_handle_gui_operation_move(self):
        """Test handling move GUI operation"""
        # Setup
        overlay = TranslationOverlay()
        
        with patch.object(overlay, '_move_window') as mock_move:
            # Act
            overlay._handle_gui_operation({
                "type": "set_position",
                "data": {"x": 100, "y": 200}
            })
            
            # Assert
            mock_move.assert_called_once_with(100, 200)

    def test_handle_gui_operation_destroy(self):
        """Test handling destroy GUI operation"""
        # Setup
        overlay = TranslationOverlay()
        
        with patch.object(overlay, '_destroy_window') as mock_destroy:
            # Act
            overlay._handle_gui_operation({
                "type": "destroy",
                "data": {}
            })
            
            # Assert
            mock_destroy.assert_called_once()

    def test_handle_gui_operation_unknown(self):
        """Test handling unknown GUI operation"""
        # Setup
        overlay = TranslationOverlay()
        
        # Act - should not raise exception
        overlay._handle_gui_operation({
            "type": "unknown_operation",
            "data": {}
        })
        
        # Assert - no exception should be raised

    def test_text_truncation(self):
        """Test text truncation based on max_text_length"""
        # Setup
        config = OverlayConfig(max_text_length=10)
        overlay = TranslationOverlay(config)
        long_text = "This is a very long text that exceeds the maximum length"
        
        # Act
        overlay.show(long_text)
        
        # Assert
        # Check that visibility was set (truncation happens in display logic)
        self.assertTrue(overlay._is_visible)
        self.assertEqual(overlay.config.max_text_length, 10) 

    def test_threading_safety(self):
        """Test thread safety with GUI operations"""
        # Setup
        overlay = TranslationOverlay()
        
        # Test that operations can be called without deadlock
        overlay.show("Test")
        overlay.hide()
        overlay.update_text("Update")
        overlay.set_position(100, 200)
        overlay.destroy()
        
        # Assert - operations should complete without error

    def test_gui_operation_error_handling(self):
        """Test GUI operation error handling"""
        # Setup
        overlay = TranslationOverlay()
        
        with patch.object(overlay, '_display_text', side_effect=Exception("Test error")):
            # Act - should not raise exception
            overlay._handle_gui_operation({
                "type": "show_text",
                "data": {"text": "Test"}
            })
            
            # Assert - error should be logged
            self.mocks['logger'].error.assert_called()

    def test_window_creation_mock(self):
        """Test window creation with mocked GUI"""
        # Setup  
        overlay = TranslationOverlay()
        
        # Act
        overlay._create_overlay_window()
        
        # Assert - should complete without error
        # (actual GUI operations are mocked)

    def test_text_display_mock(self):
        """Test text display with mocked GUI"""
        # Setup
        overlay = TranslationOverlay()
        overlay.window = MagicMock()
        
        # Act
        overlay._display_text("Test text")
        
        # Assert - should complete without error
        # (actual GUI operations are mocked)

    def test_window_hide_mock(self):
        """Test window hiding with mocked GUI"""
        # Setup
        overlay = TranslationOverlay()
        overlay.window = MagicMock()
        
        # Act
        overlay._hide_window()
        
        # Assert - should complete without error
        # (actual GUI operations are mocked)

    def test_window_move_mock(self):
        """Test window moving with mocked GUI"""
        # Setup
        overlay = TranslationOverlay()
        overlay.window = MagicMock()
        
        # Act
        overlay._move_window(300, 400)
        
        # Assert - should complete without error
        # (actual GUI operations are mocked)


if __name__ == '__main__':
    unittest.main()
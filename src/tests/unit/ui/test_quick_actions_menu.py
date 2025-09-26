"""
Tests for Quick Actions Menu (Floating Context Menu).

FEATURE: Quick Actions Menu (Floating Context Menu)
"""

import pytest
import tkinter as tk
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Callable, Optional

# CRITICAL: Import paths will fail until implementation exists
from src.ui.quick_actions_menu import (
    QuickActionsMenu,
    ActionButton,
    MenuAction,
    MenuPosition
)


class TestActionButton:
    """Test ActionButton component."""

    def test_action_button_creation(self):
        """Test ActionButton creation with icon and callback."""
        callback = Mock()

        button = ActionButton(
            icon="📷",
            text="Capture",
            tooltip="Quick screen capture",
            callback=callback,
            hotkey="Ctrl+Q"
        )

        assert button.icon == "📷"
        assert button.text == "Capture"
        assert button.tooltip == "Quick screen capture"
        assert button.hotkey == "Ctrl+Q"
        assert button.callback == callback

    def test_action_button_click(self):
        """Test ActionButton click triggers callback."""
        callback = Mock()
        button = ActionButton("🔄", "Test", "Test action", callback)

        # Simulate button click
        button.on_click()

        callback.assert_called_once()

    def test_action_button_disabled_state(self):
        """Test ActionButton disabled state."""
        callback = Mock()
        button = ActionButton("📷", "Capture", "Capture screen", callback)

        # Test enabling/disabling
        button.set_enabled(False)
        assert button.is_enabled is False

        button.on_click()
        callback.assert_not_called()  # Should not trigger when disabled

        button.set_enabled(True)
        assert button.is_enabled is True

        button.on_click()
        callback.assert_called_once()  # Should trigger when enabled


class TestMenuAction:
    """Test MenuAction data structure."""

    def test_menu_action_creation(self):
        """Test MenuAction creation with metadata."""
        def test_callback():
            pass

        action = MenuAction(
            id="quick_capture",
            icon="📷",
            label="Capture",
            tooltip="Quick screen capture",
            callback=test_callback,
            hotkey="Ctrl+Q",
            priority=1
        )

        assert action.id == "quick_capture"
        assert action.icon == "📷"
        assert action.label == "Capture"
        assert action.priority == 1

    def test_menu_action_priority_ordering(self):
        """Test MenuAction priority for ordering."""
        action1 = MenuAction("test1", "📷", "Test1", "Test", Mock(), priority=1)
        action2 = MenuAction("test2", "🔄", "Test2", "Test", Mock(), priority=3)
        action3 = MenuAction("test3", "💾", "Test3", "Test", Mock(), priority=2)

        actions = [action2, action1, action3]
        sorted_actions = sorted(actions, key=lambda a: a.priority)

        # Should be ordered by priority (lower number = higher priority)
        assert sorted_actions[0].id == "test1"
        assert sorted_actions[1].id == "test3"
        assert sorted_actions[2].id == "test2"


class TestMenuPosition:
    """Test menu positioning logic."""

    def test_menu_position_from_cursor(self):
        """Test menu positioning relative to cursor."""
        position = MenuPosition.from_cursor(x=100, y=200)

        assert position.x == 100
        assert position.y == 200
        assert position.positioning_mode == "cursor"

    def test_menu_position_screen_bounds_adjustment(self):
        """Test menu position adjustment for screen boundaries."""
        # Mock screen dimensions
        screen_width, screen_height = 1920, 1080
        menu_width, menu_height = 200, 150

        # Position near right edge
        position = MenuPosition(x=1850, y=500)
        adjusted = position.adjust_for_screen_bounds(
            screen_width, screen_height, menu_width, menu_height
        )

        # Should adjust to keep menu on screen
        assert adjusted.x <= screen_width - menu_width

        # Position near bottom edge
        position = MenuPosition(x=500, y=950)
        adjusted = position.adjust_for_screen_bounds(
            screen_width, screen_height, menu_width, menu_height
        )

        assert adjusted.y <= screen_height - menu_height


class TestQuickActionsMenu:
    """Test suite for QuickActionsMenu."""

    @pytest.fixture
    def mock_root_window(self):
        """Mock tkinter root window."""
        with patch('tkinter.Tk') as mock_tk:
            root = Mock()
            mock_tk.return_value = root
            return root

    @pytest.fixture
    def quick_actions_menu(self, mock_root_window):
        """Create QuickActionsMenu with mocked Tkinter."""
        with patch('tkinter.Toplevel') as mock_toplevel:
            menu_window = Mock()
            mock_toplevel.return_value = menu_window

            menu = QuickActionsMenu()
            menu.menu_window = menu_window
            return menu

    # CRITICAL: Menu initialization and default actions
    def test_menu_initialization_with_default_actions(self, quick_actions_menu):
        """Test menu initializes with default quick actions."""
        # CRITICAL: Should have default actions for core functionality
        expected_actions = ["capture", "retry", "speak", "save", "copy"]

        for action_id in expected_actions:
            assert action_id in quick_actions_menu.actions
            action = quick_actions_menu.actions[action_id]
            assert action.icon is not None
            assert action.label is not None
            assert action.callback is not None

    def test_default_action_icons_and_labels(self, quick_actions_menu):
        """Test default actions have appropriate icons and labels."""
        expected_defaults = {
            "capture": ("📷", "Capture"),
            "retry": ("🔄", "Retry"),
            "speak": ("🔊", "Speak"),
            "save": ("💾", "Save"),
            "copy": ("📋", "Copy")
        }

        for action_id, (expected_icon, expected_label) in expected_defaults.items():
            action = quick_actions_menu.actions[action_id]
            assert action.icon == expected_icon
            assert action.label == expected_label

    # CRITICAL: Menu display and positioning
    def test_show_menu_at_position(self, quick_actions_menu):
        """Test showing menu at specific screen position."""
        position = MenuPosition(x=500, y=300)

        quick_actions_menu.show_at_position(position)

        # CRITICAL: Menu should be visible and positioned correctly
        assert quick_actions_menu.is_visible is True
        quick_actions_menu.menu_window.geometry.assert_called()
        quick_actions_menu.menu_window.deiconify.assert_called()

    def test_show_menu_at_cursor(self, quick_actions_menu):
        """Test showing menu at current cursor position."""
        with patch('tkinter.Tk.winfo_pointerx') as mock_x:
            with patch('tkinter.Tk.winfo_pointery') as mock_y:
                mock_x.return_value = 150
                mock_y.return_value = 250

                quick_actions_menu.show_at_cursor()

                assert quick_actions_menu.is_visible is True
                # Should use cursor coordinates
                geometry_call = quick_actions_menu.menu_window.geometry.call_args[0][0]
                assert "+150+" in geometry_call or "+250+" in geometry_call

    def test_hide_menu(self, quick_actions_menu):
        """Test hiding the menu."""
        # First show menu
        quick_actions_menu.show_at_cursor()
        assert quick_actions_menu.is_visible is True

        # Then hide it
        quick_actions_menu.hide()

        assert quick_actions_menu.is_visible is False
        quick_actions_menu.menu_window.withdraw.assert_called()

    # CRITICAL: Auto-hide functionality
    def test_menu_auto_hide_on_focus_loss(self, quick_actions_menu):
        """Test menu automatically hides when losing focus."""
        quick_actions_menu.show_at_cursor()

        # Mock focus loss event
        focus_out_event = Mock()
        quick_actions_menu._on_focus_out(focus_out_event)

        # Should auto-hide after delay
        with patch('threading.Timer') as mock_timer:
            timer_instance = Mock()
            mock_timer.return_value = timer_instance

            quick_actions_menu._schedule_auto_hide()

            mock_timer.assert_called_once()
            timer_instance.start.assert_called_once()

    def test_menu_cancel_auto_hide_on_hover(self, quick_actions_menu):
        """Test canceling auto-hide when mouse hovers over menu."""
        # Start auto-hide timer
        quick_actions_menu._schedule_auto_hide()

        # Mock mouse enter event
        enter_event = Mock()
        quick_actions_menu._on_mouse_enter(enter_event)

        # Should cancel auto-hide
        assert quick_actions_menu._auto_hide_timer is None

    # CRITICAL: Action execution
    def test_action_execution_quick_capture(self, quick_actions_menu):
        """Test quick capture action execution."""
        with patch('src.core.coordinators.capture_orchestrator.CaptureOrchestrator') as mock_orchestrator:
            orchestrator = mock_orchestrator.return_value

            # Execute capture action
            action = quick_actions_menu.actions["capture"]
            action.callback()

            # Should trigger screen capture
            orchestrator.capture_screen_region.assert_called_once()

    def test_action_execution_retry_last(self, quick_actions_menu):
        """Test retry last translation action."""
        with patch('src.core.coordinators.translation_workflow.TranslationWorkflow') as mock_workflow:
            workflow = mock_workflow.return_value
            workflow.get_last_translation.return_value = Mock(original_text="Hello")

            # Execute retry action
            action = quick_actions_menu.actions["retry"]
            action.callback()

            # Should retry last translation
            workflow.retry_last_translation.assert_called_once()

    def test_action_execution_speak_last(self, quick_actions_menu):
        """Test speak last translation action."""
        with patch('src.core.tts_engine.TTSEngine') as mock_tts:
            tts_engine = mock_tts.return_value

            # Mock last translation
            with patch.object(quick_actions_menu, '_get_last_translation_text') as mock_get_text:
                mock_get_text.return_value = "Последний перевод"

                # Execute speak action
                action = quick_actions_menu.actions["speak"]
                action.callback()

                # Should speak the translation
                tts_engine.speak.assert_called_with("Последний перевод")

    def test_action_execution_save_translation(self, quick_actions_menu):
        """Test save translation action."""
        with patch('src.utils.export_manager.ExportManager') as mock_export:
            export_manager = mock_export.return_value

            # Execute save action
            action = quick_actions_menu.actions["save"]
            action.callback()

            # Should save to history/export
            export_manager.save_current_translation.assert_called_once()

    # CRITICAL: Custom action management
    def test_add_custom_action(self, quick_actions_menu):
        """Test adding custom user-defined actions."""
        custom_callback = Mock()

        custom_action = MenuAction(
            id="custom_action",
            icon="⭐",
            label="Custom",
            tooltip="Custom user action",
            callback=custom_callback,
            priority=10
        )

        quick_actions_menu.add_action(custom_action)

        # CRITICAL: Custom action should be added and accessible
        assert "custom_action" in quick_actions_menu.actions
        assert quick_actions_menu.actions["custom_action"] == custom_action

    def test_remove_action(self, quick_actions_menu):
        """Test removing actions from menu."""
        # Should be able to remove non-critical actions
        result = quick_actions_menu.remove_action("save")
        assert result is True
        assert "save" not in quick_actions_menu.actions

        # Should not be able to remove critical actions
        result = quick_actions_menu.remove_action("capture")
        assert result is False  # Protected action
        assert "capture" in quick_actions_menu.actions

    def test_reorder_actions_by_priority(self, quick_actions_menu):
        """Test reordering actions by priority."""
        # Add custom action with higher priority
        high_priority = MenuAction("priority_test", "⭐", "Priority", "Test", Mock(), priority=0)
        quick_actions_menu.add_action(high_priority)

        ordered_actions = quick_actions_menu.get_ordered_actions()

        # High priority action should be first
        assert ordered_actions[0].id == "priority_test"

    # CRITICAL: Menu appearance and theming
    def test_menu_styling_and_theming(self, quick_actions_menu):
        """Test menu visual styling and theme support."""
        # Test setting theme
        quick_actions_menu.set_theme("dark")
        assert quick_actions_menu.current_theme == "dark"

        # Mock menu window configuration
        quick_actions_menu.menu_window.configure = Mock()

        quick_actions_menu._apply_theme_styles()

        # Should apply theme-specific styles
        quick_actions_menu.menu_window.configure.assert_called()

    def test_menu_size_adjustment_for_actions(self, quick_actions_menu):
        """Test menu size adjusts based on number of actions."""
        original_height = quick_actions_menu._calculate_menu_height()

        # Add more actions
        for i in range(5):
            quick_actions_menu.add_action(
                MenuAction(f"test{i}", "🔧", f"Test{i}", "Test", Mock())
            )

        new_height = quick_actions_menu._calculate_menu_height()

        # Menu should grow to accommodate more actions
        assert new_height > original_height

    # CRITICAL: Keyboard navigation and accessibility
    def test_keyboard_navigation_support(self, quick_actions_menu):
        """Test keyboard navigation within menu."""
        quick_actions_menu.show_at_cursor()

        # Mock keyboard events
        with patch.object(quick_actions_menu, '_handle_key_press') as mock_handler:
            # Simulate arrow key navigation
            key_event = Mock()
            key_event.keysym = "Down"
            quick_actions_menu._handle_key_press(key_event)

            mock_handler.assert_called_with(key_event)

    def test_action_hotkey_display(self, quick_actions_menu):
        """Test hotkey display in menu items."""
        action = quick_actions_menu.actions["capture"]

        # Should display hotkey hint
        assert hasattr(action, 'hotkey')
        assert action.hotkey is not None

    # CRITICAL: Performance and responsiveness
    def test_menu_show_performance(self, quick_actions_menu):
        """Test menu shows quickly without delay."""
        import time

        start_time = time.time()
        quick_actions_menu.show_at_cursor()
        show_time = time.time() - start_time

        # CRITICAL: Menu should appear instantly (under 50ms)
        assert show_time < 0.05

    def test_menu_with_many_actions_performance(self, quick_actions_menu):
        """Test menu performance with many custom actions."""
        # Add many custom actions
        for i in range(50):
            quick_actions_menu.add_action(
                MenuAction(f"perf_test_{i}", "🔧", f"Test{i}", "Test action", Mock())
            )

        import time
        start_time = time.time()
        quick_actions_menu.show_at_cursor()
        show_time = time.time() - start_time

        # Should still show quickly even with many actions
        assert show_time < 0.2

    # CRITICAL: Error handling
    def test_action_callback_error_handling(self, quick_actions_menu):
        """Test graceful handling of action callback errors."""
        # Create action with failing callback
        failing_callback = Mock(side_effect=Exception("Action failed"))
        failing_action = MenuAction("failing", "❌", "Fail", "Failing action", failing_callback)
        quick_actions_menu.add_action(failing_action)

        with patch('src.utils.logger.Logger') as mock_logger:
            # Execute failing action
            failing_action.callback()

            # Should log error but not crash
            mock_logger.error.assert_called()

    def test_menu_window_creation_error_handling(self):
        """Test handling of menu window creation errors."""
        with patch('tkinter.Toplevel') as mock_toplevel:
            mock_toplevel.side_effect = Exception("Window creation failed")

            with patch('src.utils.logger.Logger') as mock_logger:
                # Should handle window creation failure gracefully
                menu = QuickActionsMenu()

                assert menu.menu_window is None
                mock_logger.error.assert_called()

    # CRITICAL: Integration with translation workflow
    def test_menu_context_awareness(self, quick_actions_menu):
        """Test menu actions are context-aware based on current state."""
        # Mock no active translation
        with patch.object(quick_actions_menu, '_has_active_translation') as mock_has_active:
            mock_has_active.return_value = False

            # Retry action should be disabled
            retry_action = quick_actions_menu.actions["retry"]
            assert retry_action.is_enabled is False

            # Mock active translation
            mock_has_active.return_value = True

            # Retry action should be enabled
            quick_actions_menu._update_action_states()
            assert retry_action.is_enabled is True

    def test_menu_integration_with_overlay(self):
        """Test integration with translation overlay."""
        # This test will fail until overlay integration exists

        with patch('src.ui.translation_overlay.TranslationOverlay') as mock_overlay:
            overlay = mock_overlay.return_value

            menu = QuickActionsMenu()

            # Mock overlay requesting quick actions menu
            overlay.show_quick_actions_menu.return_value = None

            # Should show menu near overlay
            menu.show_near_overlay(overlay)

            # Should position menu relative to overlay
            assert menu.is_visible is True

    def test_menu_trigger_from_overlay_context(self):
        """Test triggering menu from translation overlay context."""
        with patch('src.ui.translation_overlay.TranslationOverlay') as mock_overlay:
            overlay = mock_overlay.return_value
            overlay.get_position.return_value = (100, 200)
            overlay.get_current_translation.return_value = Mock(translated_text="Test")

            menu = QuickActionsMenu()

            # Trigger from overlay context
            menu.show_for_translation_overlay(overlay)

            # Should have translation-specific actions available
            assert menu.is_visible is True
            # Actions should be contextually enabled
            assert menu.actions["speak"].is_enabled is True
            assert menu.actions["copy"].is_enabled is True


# CRITICAL: Integration tests
class TestQuickActionsIntegration:
    """Integration tests for quick actions menu workflow."""

    def test_full_quick_capture_workflow(self):
        """Test complete quick capture workflow integration."""
        # This test will fail until full integration exists

        with patch('src.core.coordinators.capture_orchestrator.CaptureOrchestrator') as mock_orchestrator:
            with patch('src.ui.quick_actions_menu.QuickActionsMenu') as mock_menu:

                orchestrator = mock_orchestrator.return_value
                menu = mock_menu.return_value

                # Mock successful capture
                orchestrator.capture_screen_region.return_value = Mock(success=True)

                # Simulate quick action trigger
                capture_action = menu.actions["capture"]
                capture_action.callback()

                # Should trigger capture and hide menu
                orchestrator.capture_screen_region.assert_called_once()
                menu.hide.assert_called()

    def test_hotkey_integration_with_menu(self):
        """Test hotkey integration for showing/hiding menu."""
        with patch('src.services.hotkey_service.HotkeyService') as mock_hotkey:
            hotkey_service = mock_hotkey.return_value

            menu = QuickActionsMenu()

            # Should register hotkey for menu toggle
            hotkey_service.register_hotkey.assert_called_with(
                "Ctrl+Space", menu.toggle_visibility
            )
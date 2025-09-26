"""
Quick Actions Menu - Floating context menu for common translation actions.

This module provides a floating quick access menu with common actions
like capture, retry, speak, and save operations.
"""

import tkinter as tk
from tkinter import ttk
import asyncio
from typing import Dict, List, Optional, Callable, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from src.services.circuit_breaker import get_circuit_breaker_manager
from src.utils.logger import logger


class ActionType(Enum):
    """Types of quick actions."""
    CAPTURE = "capture"
    RETRY = "retry"
    SPEAK = "speak"
    SAVE = "save"
    SETTINGS = "settings"
    HISTORY = "history"
    COPY = "copy"
    TRANSLATE_CLIPBOARD = "translate_clipboard"


@dataclass
class MenuAction:
    """Represents a single menu action."""

    action_type: ActionType
    label: str
    icon: str
    callback: Callable[[], None]
    tooltip: Optional[str] = None
    hotkey: Optional[str] = None
    enabled: bool = True
    visible: bool = True
    priority: int = 0  # Higher priority appears first


@dataclass
class ActionButton:
    """Represents a UI button for an action."""

    button: ttk.Button
    action: MenuAction
    position: Tuple[int, int]


class QuickActionsMenu:
    """Floating quick access menu for translation actions."""

    def __init__(self, parent=None, auto_hide_delay: int = 5000):
        """Initialize the quick actions menu.

        Args:
            parent: Optional parent window
            auto_hide_delay: Auto-hide delay in milliseconds (0 to disable)
        """
        self.parent = parent
        self.auto_hide_delay = auto_hide_delay
        self.circuit_breaker = get_circuit_breaker_manager().create_circuit_breaker("quick_actions")

        # Menu window
        self.menu_window: Optional[tk.Toplevel] = None
        self.is_visible = False
        self.is_pinned = False

        # Actions and buttons
        self.actions: Dict[str, MenuAction] = {}
        self.action_buttons: Dict[str, ActionButton] = {}

        # Position and sizing
        self.position = (100, 100)
        self.menu_size = (200, 300)
        self.button_size = (180, 35)

        # Auto-hide timer
        self._hide_timer_id: Optional[str] = None
        self._last_interaction: Optional[datetime] = None

        # Performance tracking
        self.action_usage: Dict[str, int] = {}

        self._setup_default_actions()
        self._create_menu_window()

        logger.info("QuickActionsMenu initialized")

    def _setup_default_actions(self) -> None:
        """Setup default actions for the menu."""
        default_actions = [
            MenuAction(
                ActionType.CAPTURE,
                "📷 Quick Capture",
                "📷",
                self._action_capture,
                "Capture screen region (Ctrl+Q)",
                "Ctrl+Q",
                priority=10
            ),
            MenuAction(
                ActionType.RETRY,
                "🔄 Retry Last",
                "🔄",
                self._action_retry,
                "Retry last translation (F1)",
                "F1",
                priority=9
            ),
            MenuAction(
                ActionType.SPEAK,
                "🔊 Speak",
                "🔊",
                self._action_speak,
                "Speak last translation (F3)",
                "F3",
                priority=8
            ),
            MenuAction(
                ActionType.SAVE,
                "💾 Save",
                "💾",
                self._action_save,
                "Save to history (F4)",
                "F4",
                priority=7
            ),
            MenuAction(
                ActionType.COPY,
                "📋 Copy",
                "📋",
                self._action_copy,
                "Copy to clipboard (Ctrl+C)",
                "Ctrl+C",
                priority=6
            ),
            MenuAction(
                ActionType.TRANSLATE_CLIPBOARD,
                "📄 Translate Clipboard",
                "📄",
                self._action_translate_clipboard,
                "Translate clipboard content",
                priority=5
            ),
            MenuAction(
                ActionType.HISTORY,
                "📚 History",
                "📚",
                self._action_history,
                "Open translation history",
                priority=4
            ),
            MenuAction(
                ActionType.SETTINGS,
                "⚙️ Settings",
                "⚙️",
                self._action_settings,
                "Open settings (F10)",
                "F10",
                priority=3
            )
        ]

        for action in default_actions:
            self.actions[action.action_type.value] = action

    def _create_menu_window(self) -> None:
        """Create the floating menu window."""
        self.menu_window = tk.Toplevel(self.parent)
        self.menu_window.title("Quick Actions")

        # Configure window
        self.menu_window.geometry(f"{self.menu_size[0]}x{self.menu_size[1]}+{self.position[0]}+{self.position[1]}")
        self.menu_window.resizable(False, False)
        self.menu_window.overrideredirect(True)  # Remove window decorations

        # Make window stay on top
        self.menu_window.wm_attributes("-topmost", True)

        # Configure transparency (if supported)
        try:
            self.menu_window.wm_attributes("-alpha", 0.95)
        except tk.TclError:
            pass  # Transparency not supported

        # Hide window initially
        self.menu_window.withdraw()

        # Setup window styling
        self._setup_window_styling()

        # Bind events
        self._bind_window_events()

        # Create menu content
        self._create_menu_content()

    def _setup_window_styling(self) -> None:
        """Setup window styling and theme."""
        style = ttk.Style()

        # Configure menu style
        style.configure(
            "QuickMenu.TFrame",
            background="#2d3748",
            relief="flat",
            borderwidth=1
        )

        style.configure(
            "QuickAction.TButton",
            background="#4a5568",
            foreground="#ffffff",
            font=("Segoe UI", 9),
            padding=(5, 5),
            relief="flat"
        )

        style.map(
            "QuickAction.TButton",
            background=[
                ("active", "#718096"),
                ("pressed", "#2d3748")
            ],
            foreground=[("active", "#ffffff")]
        )

    def _bind_window_events(self) -> None:
        """Bind window events for interaction handling."""
        if self.menu_window:
            # Mouse events for auto-hide
            self.menu_window.bind("<Enter>", self._on_mouse_enter)
            self.menu_window.bind("<Leave>", self._on_mouse_leave)
            self.menu_window.bind("<Motion>", self._on_mouse_motion)

            # Focus events
            self.menu_window.bind("<FocusIn>", self._on_focus_in)
            self.menu_window.bind("<FocusOut>", self._on_focus_out)

            # Keyboard events
            self.menu_window.bind("<Key>", self._on_key_press)
            self.menu_window.bind("<Escape>", lambda e: self.hide())

            # Make window focusable
            self.menu_window.focus_set()

    def _create_menu_content(self) -> None:
        """Create the menu content with action buttons."""
        if not self.menu_window:
            return

        # Main container
        main_frame = ttk.Frame(self.menu_window, style="QuickMenu.TFrame")
        main_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Title bar
        title_frame = ttk.Frame(main_frame, style="QuickMenu.TFrame")
        title_frame.pack(fill="x", pady=(0, 5))

        title_label = ttk.Label(
            title_frame,
            text="Quick Actions",
            font=("Segoe UI", 10, "bold"),
            background="#2d3748",
            foreground="#ffffff"
        )
        title_label.pack(side="left", padx=5)

        # Pin button
        pin_button = ttk.Button(
            title_frame,
            text="📌" if not self.is_pinned else "📌",
            width=3,
            command=self._toggle_pin,
            style="QuickAction.TButton"
        )
        pin_button.pack(side="right", padx=5)

        # Actions container
        actions_frame = ttk.Frame(main_frame, style="QuickMenu.TFrame")
        actions_frame.pack(fill="both", expand=True, pady=5)

        # Create action buttons
        self._create_action_buttons(actions_frame)

    def _create_action_buttons(self, parent_frame: ttk.Frame) -> None:
        """Create buttons for all visible actions."""
        # Sort actions by priority and name
        sorted_actions = sorted(
            [action for action in self.actions.values() if action.visible],
            key=lambda a: (-a.priority, a.label)
        )

        row = 0
        for action in sorted_actions:
            # Create button
            button_text = f"{action.icon} {action.label}"
            if action.hotkey:
                button_text += f" ({action.hotkey})"

            button = ttk.Button(
                parent_frame,
                text=button_text,
                width=25,
                command=lambda a=action: self._execute_action(a),
                style="QuickAction.TButton",
                state="normal" if action.enabled else "disabled"
            )

            button.grid(row=row, column=0, sticky="ew", padx=5, pady=2)

            # Setup tooltip
            if action.tooltip:
                self._create_tooltip(button, action.tooltip)

            # Store button reference
            self.action_buttons[action.action_type.value] = ActionButton(
                button=button,
                action=action,
                position=(0, row)
            )

            row += 1

        # Configure grid weights
        parent_frame.grid_columnconfigure(0, weight=1)

    def _create_tooltip(self, widget: tk.Widget, text: str) -> None:
        """Create a tooltip for a widget."""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            tooltip.configure(bg="#2d3748")

            label = tk.Label(
                tooltip,
                text=text,
                background="#2d3748",
                foreground="#ffffff",
                font=("Segoe UI", 8),
                padx=5,
                pady=3
            )
            label.pack()

            # Store tooltip reference
            widget.tooltip = tooltip

        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                delattr(widget, 'tooltip')

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    async def show(self, position: Optional[Tuple[int, int]] = None, context: Optional[str] = None) -> None:
        """Show the quick actions menu.

        Args:
            position: Optional position (x, y) to show menu at
            context: Optional context for action filtering
        """
        try:
            if self.menu_window:
                # Update position if provided
                if position:
                    self.position = position
                    self.menu_window.geometry(
                        f"{self.menu_size[0]}x{self.menu_size[1]}+{position[0]}+{position[1]}"
                    )

                # Show window
                self.menu_window.deiconify()
                self.menu_window.lift()
                self.menu_window.focus_set()

                self.is_visible = True
                self._last_interaction = datetime.now()

                # Start auto-hide timer
                if not self.is_pinned and self.auto_hide_delay > 0:
                    self._start_auto_hide_timer()

                # Apply context filtering if provided
                if context:
                    self._apply_context_filter(context)

                logger.debug(f"Quick actions menu shown at {self.position}")

        except Exception as e:
            logger.error(f"Failed to show quick actions menu: {e}")

    def hide(self) -> None:
        """Hide the quick actions menu."""
        if self.menu_window and self.is_visible:
            self.menu_window.withdraw()
            self.is_visible = False
            self._cancel_auto_hide_timer()

            logger.debug("Quick actions menu hidden")

    def toggle(self, position: Optional[Tuple[int, int]] = None) -> None:
        """Toggle menu visibility."""
        if self.is_visible:
            self.hide()
        else:
            asyncio.create_task(self.show(position))

    def _execute_action(self, action: MenuAction) -> None:
        """Execute a menu action."""
        if not action.enabled:
            return

        try:
            self._last_interaction = datetime.now()

            # Track usage
            self.action_usage[action.action_type.value] = self.action_usage.get(action.action_type.value, 0) + 1

            # Execute callback
            if action.callback:
                action.callback()

            # Hide menu unless pinned
            if not self.is_pinned:
                self.hide()

            logger.debug(f"Executed quick action: {action.action_type.value}")

        except Exception as e:
            logger.error(f"Failed to execute action {action.action_type.value}: {e}")

    def _apply_context_filter(self, context: str) -> None:
        """Apply context filtering to show relevant actions."""
        # Context-based action visibility
        context_actions = {
            "translation": ["capture", "retry", "speak", "save", "copy"],
            "history": ["history", "save", "copy"],
            "settings": ["settings"]
        }

        relevant_actions = context_actions.get(context, list(self.actions.keys()))

        # Update button visibility
        for action_id, button_info in self.action_buttons.items():
            visible = action_id in relevant_actions
            button_info.button.grid_remove() if not visible else button_info.button.grid()

    def _toggle_pin(self) -> None:
        """Toggle menu pin state."""
        self.is_pinned = not self.is_pinned

        if self.is_pinned:
            self._cancel_auto_hide_timer()
        elif self.auto_hide_delay > 0:
            self._start_auto_hide_timer()

        logger.debug(f"Menu pin state: {self.is_pinned}")

    def _start_auto_hide_timer(self) -> None:
        """Start the auto-hide timer."""
        self._cancel_auto_hide_timer()

        if self.menu_window and self.auto_hide_delay > 0:
            self._hide_timer_id = self.menu_window.after(self.auto_hide_delay, self._auto_hide)

    def _cancel_auto_hide_timer(self) -> None:
        """Cancel the auto-hide timer."""
        if self._hide_timer_id and self.menu_window:
            self.menu_window.after_cancel(self._hide_timer_id)
            self._hide_timer_id = None

    def _auto_hide(self) -> None:
        """Auto-hide callback."""
        if not self.is_pinned:
            self.hide()

    def _on_mouse_enter(self, event) -> None:
        """Handle mouse enter event."""
        self._last_interaction = datetime.now()
        self._cancel_auto_hide_timer()

    def _on_mouse_leave(self, event) -> None:
        """Handle mouse leave event."""
        if not self.is_pinned and self.auto_hide_delay > 0:
            self._start_auto_hide_timer()

    def _on_mouse_motion(self, event) -> None:
        """Handle mouse motion event."""
        self._last_interaction = datetime.now()

    def _on_focus_in(self, event) -> None:
        """Handle focus in event."""
        self._cancel_auto_hide_timer()

    def _on_focus_out(self, event) -> None:
        """Handle focus out event."""
        if not self.is_pinned and self.auto_hide_delay > 0:
            self._start_auto_hide_timer()

    def _on_key_press(self, event) -> None:
        """Handle keyboard shortcuts."""
        self._last_interaction = datetime.now()

        # Handle number keys for quick action selection
        if event.char.isdigit() and 1 <= int(event.char) <= 9:
            action_index = int(event.char) - 1
            visible_actions = [a for a in self.actions.values() if a.visible and a.enabled]

            if action_index < len(visible_actions):
                self._execute_action(visible_actions[action_index])

    # Default action implementations
    def _action_capture(self) -> None:
        """Default capture action."""
        logger.info("Quick action: Capture")
        # This would integrate with the main application's capture functionality

    def _action_retry(self) -> None:
        """Default retry action."""
        logger.info("Quick action: Retry")
        # This would integrate with the main application's retry functionality

    def _action_speak(self) -> None:
        """Default speak action."""
        logger.info("Quick action: Speak")
        # This would integrate with the TTS functionality

    def _action_save(self) -> None:
        """Default save action."""
        logger.info("Quick action: Save")
        # This would integrate with the history saving functionality

    def _action_copy(self) -> None:
        """Default copy action."""
        logger.info("Quick action: Copy")
        # This would copy to clipboard

    def _action_translate_clipboard(self) -> None:
        """Default translate clipboard action."""
        logger.info("Quick action: Translate clipboard")
        # This would translate clipboard content

    def _action_history(self) -> None:
        """Default history action."""
        logger.info("Quick action: History")
        # This would open the history window

    def _action_settings(self) -> None:
        """Default settings action."""
        logger.info("Quick action: Settings")
        # This would open the settings window

    # Public API methods
    def add_action(self, action: MenuAction) -> None:
        """Add a custom action to the menu."""
        self.actions[action.action_type.value] = action

        # Recreate menu if visible
        if self.is_visible and self.menu_window:
            self._refresh_menu_content()

        logger.debug(f"Added custom action: {action.action_type.value}")

    def remove_action(self, action_type: ActionType) -> bool:
        """Remove an action from the menu."""
        action_id = action_type.value

        if action_id in self.actions:
            del self.actions[action_id]

            if action_id in self.action_buttons:
                del self.action_buttons[action_id]

            # Recreate menu if visible
            if self.is_visible and self.menu_window:
                self._refresh_menu_content()

            logger.debug(f"Removed action: {action_id}")
            return True

        return False

    def enable_action(self, action_type: ActionType, enabled: bool = True) -> None:
        """Enable or disable an action."""
        action_id = action_type.value

        if action_id in self.actions:
            self.actions[action_id].enabled = enabled

            if action_id in self.action_buttons:
                button = self.action_buttons[action_id].button
                button.configure(state="normal" if enabled else "disabled")

    def set_action_callback(self, action_type: ActionType, callback: Callable[[], None]) -> None:
        """Set or update an action's callback function."""
        action_id = action_type.value

        if action_id in self.actions:
            self.actions[action_id].callback = callback
            logger.debug(f"Updated callback for action: {action_id}")

    def _refresh_menu_content(self) -> None:
        """Refresh the menu content after changes."""
        if self.menu_window:
            # Clear existing content
            for widget in self.menu_window.winfo_children():
                widget.destroy()

            self.action_buttons.clear()

            # Recreate content
            self._create_menu_content()

    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get usage statistics for the menu."""
        return {
            "total_actions": len(self.actions),
            "action_usage": self.action_usage.copy(),
            "is_pinned": self.is_pinned,
            "auto_hide_delay": self.auto_hide_delay,
            "last_interaction": self._last_interaction.isoformat() if self._last_interaction else None
        }

    def destroy(self) -> None:
        """Clean up and destroy the menu."""
        self._cancel_auto_hide_timer()

        if self.menu_window:
            self.menu_window.destroy()
            self.menu_window = None

        self.is_visible = False
        logger.debug("Quick actions menu destroyed")
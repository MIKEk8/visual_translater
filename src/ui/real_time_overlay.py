"""
Real-time translation overlay for displaying results on screen.
"""

import threading
import time
import tkinter as tk
from dataclasses import dataclass
from enum import Enum
from tkinter import ttk
from typing import Callable, Optional, Tuple

from src.models.translation import Translation
from src.utils.logger import logger


class OverlayPosition(Enum):
    """Overlay positioning options."""

    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    CENTER = "center"
    FOLLOW_CURSOR = "follow_cursor"
    CUSTOM = "custom"


class OverlayStyle(Enum):
    """Overlay visual styles."""

    MINIMAL = "minimal"
    STANDARD = "standard"
    DETAILED = "detailed"
    POPUP = "popup"
    TOOLTIP = "tooltip"


@dataclass
class OverlayConfig:
    """Configuration for real-time overlay."""

    # Positioning
    position: OverlayPosition = OverlayPosition.TOP_RIGHT
    custom_x: int = 0
    custom_y: int = 0
    offset_x: int = 10
    offset_y: int = 10

    # Appearance
    style: OverlayStyle = OverlayStyle.STANDARD
    background_color: str = "#2d2d2d"
    text_color: str = "#ffffff"
    border_color: str = "#555555"
    font_family: str = "Segoe UI"
    font_size: int = 12

    # Behavior
    auto_hide_delay: float = 5.0  # seconds
    fade_animation: bool = True
    always_on_top: bool = True
    click_through: bool = False

    # Content
    show_original_text: bool = True
    show_confidence: bool = False
    show_language_info: bool = True
    max_text_length: int = 200

    # Size constraints
    min_width: int = 200
    max_width: int = 500
    min_height: int = 50
    max_height: int = 300


class RealTimeOverlay:
    """Real-time overlay window for displaying translations."""

    def __init__(self, config: Optional[OverlayConfig] = None):
        self.config = config or OverlayConfig()

        # Window state
        self.window: Optional[tk.Toplevel] = None
        self.is_visible = False
        self.is_animating = False

        # Content state
        self.current_translation: Optional[Translation] = None
        self.auto_hide_timer: Optional[threading.Timer] = None

        # UI components
        self.main_frame: Optional[ttk.Frame] = None
        self.original_label: Optional[ttk.Label] = None
        self.translated_label: Optional[ttk.Label] = None
        self.info_label: Optional[ttk.Label] = None

        # Event callbacks
        self.on_click_callback: Optional[Callable] = None
        self.on_close_callback: Optional[Callable] = None

        # Initialize overlay
        self._create_overlay()

        logger.info("Real-time overlay initialized")

    def _create_overlay(self) -> None:
        """Create the overlay window."""
        # Create root window if needed
        try:
            root = tk._default_root
        except AttributeError:
            root = tk.Tk()
            root.withdraw()  # Hide main window

        # Create overlay window
        self.window = tk.Toplevel(root)
        self.window.withdraw()  # Start hidden

        # Configure window
        self._configure_window()

        # Create UI components
        self._create_ui_components()

        # Bind events
        self._bind_events()

    def _configure_window(self) -> None:
        """Configure overlay window properties."""
        if not self.window:
            return

        # Window properties
        self.window.title("Translation Overlay")
        self.window.overrideredirect(True)  # Remove window decorations

        if self.config.always_on_top:
            self.window.attributes("-topmost", True)

        # Make window click-through if configured
        if self.config.click_through:
            try:
                # Windows-specific: make window click-through
                import win32con
                import win32gui

                hwnd = self.window.winfo_id()
                extended_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                win32gui.SetWindowLong(
                    hwnd, win32con.GWL_EXSTYLE, extended_style | win32con.WS_EX_TRANSPARENT
                )
            except ImportError:
                logger.debug("Click-through not supported on this platform")

        # Transparency
        try:
            self.window.attributes("-alpha", 0.9)
        except tk.TclError:
            logger.debug("Window transparency not supported")

        # Styling
        self.window.configure(bg=self.config.background_color)

    def _create_ui_components(self) -> None:
        """Create UI components based on style."""
        if not self.window:
            return

        # Main container
        self.main_frame = ttk.Frame(self.window)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configure styles
        style = ttk.Style()
        style.configure(
            "Overlay.TLabel",
            background=self.config.background_color,
            foreground=self.config.text_color,
            font=(self.config.font_family, self.config.font_size),
        )

        if self.config.style == OverlayStyle.MINIMAL:
            self._create_minimal_ui()
        elif self.config.style == OverlayStyle.DETAILED:
            self._create_detailed_ui()
        elif self.config.style == OverlayStyle.POPUP:
            self._create_popup_ui()
        elif self.config.style == OverlayStyle.TOOLTIP:
            self._create_tooltip_ui()
        else:  # STANDARD
            self._create_standard_ui()

    def _create_standard_ui(self) -> None:
        """Create standard overlay UI."""
        # Original text (if configured)
        if self.config.show_original_text:
            self.original_label = ttk.Label(
                self.main_frame,
                text="",
                style="Overlay.TLabel",
                wraplength=self.config.max_width - 20,
                justify=tk.LEFT,
            )
            self.original_label.pack(fill=tk.X, pady=(0, 5))

        # Translated text
        self.translated_label = ttk.Label(
            self.main_frame,
            text="",
            style="Overlay.TLabel",
            wraplength=self.config.max_width - 20,
            justify=tk.LEFT,
            font=(self.config.font_family, self.config.font_size + 2, "bold"),
        )
        self.translated_label.pack(fill=tk.X, pady=5)

        # Info line (language, confidence)
        if self.config.show_language_info or self.config.show_confidence:
            self.info_label = ttk.Label(
                self.main_frame,
                text="",
                style="Overlay.TLabel",
                font=(self.config.font_family, self.config.font_size - 1),
                foreground="#cccccc",
            )
            self.info_label.pack(fill=tk.X, pady=(5, 0))

    def _create_minimal_ui(self) -> None:
        """Create minimal overlay UI (translated text only)."""
        self.translated_label = ttk.Label(
            self.main_frame,
            text="",
            style="Overlay.TLabel",
            wraplength=self.config.max_width - 10,
            justify=tk.CENTER,
            font=(self.config.font_family, self.config.font_size, "bold"),
        )
        self.translated_label.pack(fill=tk.BOTH, expand=True)

    def _create_detailed_ui(self) -> None:
        """Create detailed overlay UI with all information."""
        # Create notebook for tabbed interface
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Translation tab
        translation_frame = ttk.Frame(notebook)
        notebook.add(translation_frame, text="Translation")

        self._create_standard_ui_in_frame(translation_frame)

        # Details tab
        details_frame = ttk.Frame(notebook)
        notebook.add(details_frame, text="Details")

        self.info_label = ttk.Label(details_frame, text="", style="Overlay.TLabel", justify=tk.LEFT)
        self.info_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _create_popup_ui(self) -> None:
        """Create popup-style overlay UI."""
        # Add border
        border_frame = tk.Frame(self.main_frame, bg=self.config.border_color, padx=2, pady=2)
        border_frame.pack(fill=tk.BOTH, expand=True)

        content_frame = tk.Frame(border_frame, bg=self.config.background_color)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Title bar
        title_frame = tk.Frame(content_frame, bg=self.config.background_color)
        title_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

        title_label = tk.Label(
            title_frame,
            text="Translation",
            bg=self.config.background_color,
            fg=self.config.text_color,
            font=(self.config.font_family, self.config.font_size, "bold"),
        )
        title_label.pack(side=tk.LEFT)

        # Close button
        close_button = tk.Button(
            title_frame,
            text="×",
            bg=self.config.background_color,
            fg=self.config.text_color,
            bd=0,
            command=self.hide,
        )
        close_button.pack(side=tk.RIGHT)

        # Content
        self._create_standard_ui_in_frame(content_frame)

    def _create_tooltip_ui(self) -> None:
        """Create tooltip-style overlay UI."""
        # Simple single label with arrow
        self.translated_label = ttk.Label(
            self.main_frame,
            text="",
            style="Overlay.TLabel",
            wraplength=self.config.max_width - 20,
            justify=tk.LEFT,
            relief=tk.SOLID,
            borderwidth=1,
        )
        self.translated_label.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    def _create_standard_ui_in_frame(self, parent_frame: tk.Widget) -> None:
        """Create standard UI components in specific frame."""
        if self.config.show_original_text:
            self.original_label = ttk.Label(
                parent_frame,
                text="",
                style="Overlay.TLabel",
                wraplength=self.config.max_width - 20,
                justify=tk.LEFT,
            )
            self.original_label.pack(fill=tk.X, padx=5, pady=(5, 2))

        self.translated_label = ttk.Label(
            parent_frame,
            text="",
            style="Overlay.TLabel",
            wraplength=self.config.max_width - 20,
            justify=tk.LEFT,
            font=(self.config.font_family, self.config.font_size + 1, "bold"),
        )
        self.translated_label.pack(fill=tk.X, padx=5, pady=2)

        if self.config.show_language_info or self.config.show_confidence:
            self.info_label = ttk.Label(
                parent_frame,
                text="",
                style="Overlay.TLabel",
                font=(self.config.font_family, self.config.font_size - 1),
            )
            self.info_label.pack(fill=tk.X, padx=5, pady=(2, 5))

    def _bind_events(self) -> None:
        """Bind window events."""
        if not self.window:
            return

        # Window events
        self.window.bind("<Button-1>", self._on_click)
        self.window.bind("<Double-Button-1>", self._on_double_click)
        self.window.bind("<B1-Motion>", self._on_drag)
        self.window.bind("<Enter>", self._on_mouse_enter)
        self.window.bind("<Leave>", self._on_mouse_leave)

        # Keyboard events
        self.window.bind("<Escape>", lambda e: self.hide())
        self.window.bind("<space>", self._on_space_key)

    def show_translation(self, translation: Translation) -> None:
        """Show translation in overlay."""
        self.current_translation = translation

        # Update content
        self._update_content()

        # Position overlay
        self._position_overlay()

        # Show window
        self.show()

        # Start auto-hide timer
        self._start_auto_hide_timer()

        logger.debug("Translation displayed in overlay")

    def _update_content(self) -> None:
        """Update overlay content with current translation."""
        if not self.current_translation:
            return

        # Truncate text if needed
        original_text = self.current_translation.original_text
        translated_text = self.current_translation.translated_text

        if len(translated_text) > self.config.max_text_length:
            translated_text = translated_text[: self.config.max_text_length] + "..."

        if len(original_text) > self.config.max_text_length:
            original_text = original_text[: self.config.max_text_length] + "..."

        # Update labels
        if self.original_label and self.config.show_original_text:
            self.original_label.config(text=original_text)

        if self.translated_label:
            self.translated_label.config(text=translated_text)

        if self.info_label:
            info_text = self._build_info_text()
            self.info_label.config(text=info_text)

    def _build_info_text(self) -> str:
        """Build information text for display."""
        if not self.current_translation:
            return ""

        info_parts = []

        if self.config.show_language_info:
            source_lang = self.current_translation.source_language.upper()
            target_lang = self.current_translation.target_language.upper()
            info_parts.append(f"{source_lang} → {target_lang}")

        if self.config.show_confidence and self.current_translation.confidence:
            confidence_pct = int(self.current_translation.confidence * 100)
            info_parts.append(f"Confidence: {confidence_pct}%")

        return " | ".join(info_parts)

    def _position_overlay(self) -> None:
        """Position overlay based on configuration."""
        if not self.window:
            return

        # Update window to get accurate size
        self.window.update_idletasks()

        window_width = self.window.winfo_reqwidth()
        window_height = self.window.winfo_reqheight()

        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()

        # Calculate position based on configuration
        if self.config.position == OverlayPosition.TOP_LEFT:
            x = self.config.offset_x
            y = self.config.offset_y
        elif self.config.position == OverlayPosition.TOP_RIGHT:
            x = screen_width - window_width - self.config.offset_x
            y = self.config.offset_y
        elif self.config.position == OverlayPosition.BOTTOM_LEFT:
            x = self.config.offset_x
            y = screen_height - window_height - self.config.offset_y
        elif self.config.position == OverlayPosition.BOTTOM_RIGHT:
            x = screen_width - window_width - self.config.offset_x
            y = screen_height - window_height - self.config.offset_y
        elif self.config.position == OverlayPosition.CENTER:
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
        elif self.config.position == OverlayPosition.FOLLOW_CURSOR:
            # Get mouse position
            x = self.window.winfo_pointerx() + self.config.offset_x
            y = self.window.winfo_pointery() + self.config.offset_y

            # Keep on screen
            x = max(0, min(x, screen_width - window_width))
            y = max(0, min(y, screen_height - window_height))
        else:  # CUSTOM
            x = self.config.custom_x
            y = self.config.custom_y

        # Set position
        self.window.geometry(f"+{x}+{y}")

    def show(self) -> None:
        """Show overlay window."""
        if not self.window or self.is_visible:
            return

        if self.config.fade_animation and not self.is_animating:
            self._fade_in()
        else:
            self.window.deiconify()
            self.is_visible = True

    def hide(self) -> None:
        """Hide overlay window."""
        if not self.window or not self.is_visible:
            return

        self._cancel_auto_hide_timer()

        if self.config.fade_animation and not self.is_animating:
            self._fade_out()
        else:
            self.window.withdraw()
            self.is_visible = False

        if self.on_close_callback:
            self.on_close_callback()

    def _fade_in(self) -> None:
        """Fade in animation."""
        if self.is_animating or self.window is None:
            return

        self.is_animating = True
        self.window.deiconify()

        def animate(alpha: float) -> None:
            if self.window is None:
                return
            if alpha >= 0.9:
                self.window.attributes("-alpha", 0.9)
                self.is_animating = False
                self.is_visible = True
                return

            self.window.attributes("-alpha", alpha)
            self.window.after(50, lambda: animate(alpha + 0.1))

        self.window.attributes("-alpha", 0.0)
        animate(0.1)

    def _fade_out(self) -> None:
        """Fade out animation."""
        if self.is_animating or self.window is None:
            return

        self.is_animating = True

        def animate(alpha: float) -> None:
            if self.window is None:
                return
            if alpha <= 0.0:
                self.window.withdraw()
                self.window.attributes("-alpha", 0.9)  # Reset for next show
                self.is_animating = False
                self.is_visible = False
                return

            self.window.attributes("-alpha", alpha)
            self.window.after(50, lambda: animate(alpha - 0.1))

        animate(0.9)

    def _start_auto_hide_timer(self) -> None:
        """Start auto-hide timer."""
        self._cancel_auto_hide_timer()

        if self.config.auto_hide_delay > 0:
            self.auto_hide_timer = threading.Timer(self.config.auto_hide_delay, self.hide)
            self.auto_hide_timer.start()

    def _cancel_auto_hide_timer(self) -> None:
        """Cancel auto-hide timer."""
        if self.auto_hide_timer:
            self.auto_hide_timer.cancel()
            self.auto_hide_timer = None

    def _on_click(self, event) -> None:
        """Handle click event."""
        if self.on_click_callback:
            self.on_click_callback(event)

    def _on_double_click(self, event) -> None:
        """Handle double-click event."""
        # Copy translation to clipboard
        if self.current_translation:
            try:
                import pyperclip

                pyperclip.copy(self.current_translation.translated_text)
                logger.debug("Translation copied to clipboard")
            except ImportError:
                logger.warning("pyperclip not available")

    def _on_drag(self, event) -> None:
        """Handle drag event for repositioning."""
        if self.config.position == OverlayPosition.CUSTOM and self.window is not None:
            x = self.window.winfo_pointerx() - self.window.winfo_rootx()
            y = self.window.winfo_pointery() - self.window.winfo_rooty()
            self.window.geometry(f"+{x}+{y}")

    def _on_mouse_enter(self, event) -> None:
        """Handle mouse enter event."""
        # Cancel auto-hide when mouse hovers
        self._cancel_auto_hide_timer()

    def _on_mouse_leave(self, event) -> None:
        """Handle mouse leave event."""
        # Restart auto-hide timer
        self._start_auto_hide_timer()

    def _on_space_key(self, event) -> None:
        """Handle space key press."""
        # Toggle between original and translated text
        if self.original_label and self.translated_label:
            # Implementation for toggling display
            pass

    def update_config(self, config: OverlayConfig) -> None:
        """Update overlay configuration."""
        self.config = config

        # Recreate UI if style changed
        if self.window:
            self._configure_window()
            # Note: Full UI recreation would require destroying and recreating components
            logger.info("Overlay configuration updated")

    def is_showing(self) -> bool:
        """Check if overlay is currently visible."""
        return self.is_visible

    def get_current_translation(self) -> Optional[Translation]:
        """Get currently displayed translation."""
        return self.current_translation

    def set_click_callback(self, callback: Callable) -> None:
        """Set callback for click events."""
        self.on_click_callback = callback

    def set_close_callback(self, callback: Callable) -> None:
        """Set callback for close events."""
        self.on_close_callback = callback

    def destroy(self) -> None:
        """Destroy overlay window."""
        self._cancel_auto_hide_timer()

        if self.window:
            self.window.destroy()
            self.window = None

        self.is_visible = False
        logger.info("Real-time overlay destroyed")

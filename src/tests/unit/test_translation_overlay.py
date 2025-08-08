"""Unit tests for translation overlay UI module"""

import queue
import threading

try:
    import tkinter as tk
except ImportError:
    print("tkinter не доступен в данной среде")
    tk = None
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.models.translation import Translation
from src.ui.translation_overlay import OverlayConfig, TranslationOverlay


@pytest.fixture
def overlay_config():
    """Create overlay configuration"""
    return OverlayConfig(
        x=100,
        y=100,
        width=400,
        height=150,
        background_color="#1e1e1e",
        text_color="#ffffff",
        opacity=0.9,
        auto_hide_delay=5000,
    )


@pytest.fixture
def mock_config_manager():
    """Create mock configuration manager"""
    manager = Mock()
    manager.add_observer = Mock()
    manager.remove_observer = Mock()
    manager.get_config.return_value = Mock()
    return manager


@pytest.fixture
def sample_translation():
    """Create sample translation"""
    return Translation(
        original_text="Hello world",
        translated_text="Привет мир",
        source_language="en",
        target_language="ru",
        timestamp=datetime.now().timestamp(),
        confidence=0.95,
        id="test_trans",
    )


@pytest.fixture
def translation_overlay(mock_config_manager, overlay_config):
    """Create TranslationOverlay instance with mocked dependencies"""
    # В контейнерной среде TranslationOverlay уже использует mock GUI
    overlay = TranslationOverlay(mock_config_manager, overlay_config)
    return overlay


class TestOverlayConfig:
    """Test OverlayConfig dataclass"""

    def test_config_defaults(self):
        """Test default configuration values"""
        config = OverlayConfig()

        assert config.x == 100
        assert config.y == 100
        assert config.width == 400
        assert config.height == 150
        assert config.background_color == "#1e1e1e"
        assert config.text_color == "#ffffff"
        assert config.opacity == 0.9
        assert config.auto_hide_delay == 5000
        assert config.fade_animation is True
        assert config.always_on_top is True

    def test_config_customization(self):
        """Test custom configuration values"""
        config = OverlayConfig(
            x=200,
            y=300,
            width=500,
            height=200,
            background_color="#000000",
            opacity=0.8,
            auto_hide_delay=3000,
        )

        assert config.x == 200
        assert config.y == 300
        assert config.width == 500
        assert config.height == 200
        assert config.background_color == "#000000"
        assert config.opacity == 0.8
        assert config.auto_hide_delay == 3000


class TestTranslationOverlay:
    """Test TranslationOverlay class"""

    def test_initialization(self, translation_overlay, mock_config_manager, overlay_config):
        """Test overlay initialization"""
        assert translation_overlay.config_manager == mock_config_manager
        assert translation_overlay.overlay_config == overlay_config
        assert translation_overlay.overlay_window is None
        assert translation_overlay.is_visible is False
        assert isinstance(translation_overlay.update_queue, queue.Queue)

        # Should register as config observer
        mock_config_manager.add_observer.assert_called_once_with(translation_overlay)

    @patch("tkinter.Toplevel")
    def test_show_translation(self, mock_toplevel, translation_overlay, sample_translation):
        """Test showing translation in overlay"""
        mock_window = Mock()
        mock_toplevel.return_value = mock_window

        with patch.object(
            translation_overlay, "_create_overlay_window"
        ) as mock_create, patch.object(translation_overlay, "_update_content") as mock_update:

            translation_overlay.show_translation(sample_translation)

            mock_create.assert_called_once()
            mock_update.assert_called_once_with(sample_translation)
            assert translation_overlay.current_translation == sample_translation

    def test_show_translation_already_visible(self, translation_overlay, sample_translation):
        """Test showing translation when overlay already visible"""
        mock_window = Mock()
        translation_overlay.overlay_window = mock_window
        translation_overlay.is_visible = True

        with patch.object(translation_overlay, "_update_content") as mock_update:
            translation_overlay.show_translation(sample_translation)

            # Should just update content, not create new window
            mock_update.assert_called_once_with(sample_translation)

    @patch("tkinter.Toplevel")
    def test_create_overlay_window(self, mock_toplevel, translation_overlay, overlay_config):
        """Test creating overlay window"""
        mock_window = Mock()
        mock_toplevel.return_value = mock_window

        translation_overlay._create_overlay_window()

        # Should configure window properties
        mock_window.overrideredirect.assert_called_once_with(True)
        mock_window.attributes.assert_called()  # Should set topmost and alpha
        mock_window.geometry.assert_called_with(
            f"{overlay_config.width}x{overlay_config.height}+{overlay_config.x}+{overlay_config.y}"
        )
        mock_window.configure.assert_called_with(bg=overlay_config.background_color)

    def test_update_content(self, translation_overlay, sample_translation):
        """Test updating overlay content"""
        # Mock UI elements
        mock_original_label = Mock()
        mock_translated_label = Mock()
        mock_info_label = Mock()

        translation_overlay.original_label = mock_original_label
        translation_overlay.translated_label = mock_translated_label
        translation_overlay.info_label = mock_info_label
        translation_overlay.overlay_config.show_original = True
        translation_overlay.overlay_config.show_confidence = True
        translation_overlay.overlay_config.show_timestamp = True

        translation_overlay._update_content(sample_translation)

        # Should update all labels
        mock_original_label.config.assert_called()
        mock_translated_label.config.assert_called_with(text="Привет мир")
        mock_info_label.config.assert_called()

    def test_hide_overlay(self, translation_overlay):
        """Test hiding overlay"""
        mock_window = Mock()
        translation_overlay.overlay_window = mock_window
        translation_overlay.is_visible = True

        translation_overlay.hide()

        mock_window.withdraw.assert_called_once()
        assert translation_overlay.is_visible is False

    def test_destroy_overlay(self, translation_overlay, mock_config_manager):
        """Test destroying overlay"""
        mock_window = Mock()
        translation_overlay.overlay_window = mock_window

        translation_overlay.destroy()

        mock_window.destroy.assert_called_once()
        assert translation_overlay.overlay_window is None
        assert translation_overlay.is_visible is False
        mock_config_manager.remove_observer.assert_called_once_with(translation_overlay)

    def test_auto_hide_functionality(self, translation_overlay):
        """Test auto-hide functionality"""
        translation_overlay.overlay_config.auto_hide_delay = 1000  # 1 second

        with patch.object(translation_overlay, "hide") as mock_hide:
            translation_overlay._schedule_auto_hide()

            # Should schedule hide after delay
            assert hasattr(translation_overlay, "_hide_timer")

    def test_cancel_auto_hide(self, translation_overlay):
        """Test cancelling auto-hide"""
        mock_timer = Mock()
        translation_overlay._hide_timer = mock_timer

        translation_overlay._cancel_auto_hide()

        mock_timer.cancel.assert_called_once()
        assert translation_overlay._hide_timer is None

    def test_fade_in_animation(self, translation_overlay):
        """Test fade-in animation"""
        mock_window = Mock()
        translation_overlay.overlay_window = mock_window
        translation_overlay.overlay_config.fade_animation = True

        with patch.object(translation_overlay, "_animate_fade") as mock_animate:
            translation_overlay._fade_in()

            mock_animate.assert_called_once_with(start_alpha=0.0, end_alpha=0.9, duration=300)

    def test_fade_out_animation(self, translation_overlay):
        """Test fade-out animation"""
        mock_window = Mock()
        translation_overlay.overlay_window = mock_window
        translation_overlay.overlay_config.fade_animation = True

        with patch.object(translation_overlay, "_animate_fade") as mock_animate:
            translation_overlay._fade_out()

            mock_animate.assert_called_once_with(start_alpha=0.9, end_alpha=0.0, duration=300)

    def test_animate_fade(self, translation_overlay):
        """Test fade animation implementation"""
        mock_window = Mock()
        translation_overlay.overlay_window = mock_window

        # Mock animation steps
        with patch.object(translation_overlay, "_fade_step") as mock_step:
            translation_overlay._animate_fade(0.0, 1.0, 100)

            # Should start animation
            assert hasattr(translation_overlay, "_animation_step")

    def test_position_snapping(self, translation_overlay):
        """Test snapping overlay to screen edges"""
        translation_overlay.overlay_config.snap_to_edges = True

        # Mock screen dimensions
        with patch("tkinter.Tk.winfo_screenwidth", return_value=1920), patch(
            "tkinter.Tk.winfo_screenheight", return_value=1080
        ):

            # Test snapping to right edge
            new_x, new_y = translation_overlay._snap_to_edges(1800, 100, 400, 150)

            # Should snap to right edge
            assert new_x == 1920 - 400  # Screen width - overlay width

    def test_click_through_functionality(self, translation_overlay):
        """Test click-through functionality"""
        mock_window = Mock()
        translation_overlay.overlay_window = mock_window
        translation_overlay.overlay_config.click_through = True

        translation_overlay._setup_click_through()

        # Should configure window for click-through
        mock_window.attributes.assert_called()

    def test_drag_functionality(self, translation_overlay):
        """Test dragging overlay window"""
        mock_window = Mock()
        translation_overlay.overlay_window = mock_window

        # Setup drag
        mock_event = Mock()
        mock_event.x_root = 150
        mock_event.y_root = 150

        translation_overlay._start_drag(mock_event)

        # Should record start position
        assert hasattr(translation_overlay, "_drag_start_x")
        assert hasattr(translation_overlay, "_drag_start_y")

    def test_drag_motion(self, translation_overlay):
        """Test drag motion handling"""
        mock_window = Mock()
        translation_overlay.overlay_window = mock_window
        translation_overlay._drag_start_x = 100
        translation_overlay._drag_start_y = 100

        mock_event = Mock()
        mock_event.x_root = 150
        mock_event.y_root = 150

        with patch.object(translation_overlay, "_snap_to_edges", return_value=(150, 150)):
            translation_overlay._on_drag(mock_event)

            # Should update window position
            mock_window.geometry.assert_called()

    def test_resize_functionality(self, translation_overlay):
        """Test resizing overlay"""
        translation_overlay.overlay_config.width = 500
        translation_overlay.overlay_config.height = 200

        with patch.object(translation_overlay, "_update_window_size") as mock_update:
            translation_overlay.resize(500, 200)

            mock_update.assert_called_once()

    def test_text_wrapping(self, translation_overlay):
        """Test text wrapping for long translations"""
        long_translation = Translation(
            original_text="This is a very long text that should be wrapped across multiple lines",
            translated_text="Это очень длинный текст, который должен быть перенесен на несколько строк",
            source_language="en",
            target_language="ru",
            timestamp=datetime.now().timestamp(),
            confidence=0.95,
        )

        translation_overlay.overlay_config.word_wrap = True
        translation_overlay.overlay_config.max_text_length = 50

        wrapped_text = translation_overlay._wrap_text(long_translation.translated_text)

        # Should wrap text
        assert len(wrapped_text) <= 50 or "\n" in wrapped_text

    def test_font_scaling(self, translation_overlay):
        """Test font scaling based on text length"""
        short_text = "Hi"
        long_text = "This is a very long translation that might need smaller font"

        short_font_size = translation_overlay._calculate_font_size(short_text)
        long_font_size = translation_overlay._calculate_font_size(long_text)

        # Long text should use smaller font
        assert long_font_size <= short_font_size

    def test_theme_support(self, translation_overlay):
        """Test theme switching"""
        # Dark theme
        dark_config = OverlayConfig(
            background_color="#1e1e1e", text_color="#ffffff", border_color="#555555"
        )

        translation_overlay.update_theme(dark_config)

        assert translation_overlay.overlay_config.background_color == "#1e1e1e"
        assert translation_overlay.overlay_config.text_color == "#ffffff"

    def test_multi_monitor_support(self, translation_overlay):
        """Test positioning on multiple monitors"""
        # Mock multiple monitor setup
        with patch("tkinter.Tk.winfo_screenwidth", return_value=3840), patch(
            "tkinter.Tk.winfo_screenheight", return_value=1080
        ):

            # Position on second monitor
            x, y = translation_overlay._adjust_for_monitors(2000, 100)

            # Should be within screen bounds
            assert 0 <= x <= 3840
            assert 0 <= y <= 1080

    def test_keyboard_shortcuts(self, translation_overlay):
        """Test keyboard shortcuts"""
        mock_window = Mock()
        translation_overlay.overlay_window = mock_window

        # Mock Escape key to hide
        mock_event = Mock()
        mock_event.keysym = "Escape"

        with patch.object(translation_overlay, "hide") as mock_hide:
            translation_overlay._on_key_press(mock_event)

            mock_hide.assert_called_once()

    def test_context_menu(self, translation_overlay):
        """Test right-click context menu"""
        with patch("tkinter.Menu") as mock_menu:
            mock_menu_instance = Mock()
            mock_menu.return_value = mock_menu_instance

            menu = translation_overlay._create_context_menu()

            # Should create menu with options
            mock_menu.assert_called_once()
            mock_menu_instance.add_command.assert_called()

    def test_copy_to_clipboard(self, translation_overlay, sample_translation):
        """Test copying translation to clipboard"""
        translation_overlay.current_translation = sample_translation

        with patch("tkinter.Tk.clipboard_clear") as mock_clear, patch(
            "tkinter.Tk.clipboard_append"
        ) as mock_append:

            translation_overlay._copy_to_clipboard()

            mock_clear.assert_called_once()
            mock_append.assert_called_once_with("Привет мир")

    def test_opacity_control(self, translation_overlay):
        """Test opacity control"""
        mock_window = Mock()
        translation_overlay.overlay_window = mock_window

        translation_overlay.set_opacity(0.7)

        mock_window.attributes.assert_called_with("-alpha", 0.7)

    def test_update_queue_processing(self, translation_overlay, sample_translation):
        """Test processing update queue"""
        # Add update to queue
        translation_overlay.update_queue.put(("show", sample_translation))
        translation_overlay.update_queue.put(("stop", None))

        with patch.object(translation_overlay, "show_translation") as mock_show:
            translation_overlay._process_update_queue()

            mock_show.assert_called_once_with(sample_translation)

    def test_window_state_persistence(self, translation_overlay):
        """Test saving and restoring window state"""
        state = {"x": 200, "y": 300, "width": 500, "height": 200, "opacity": 0.8}

        translation_overlay.save_window_state(state)
        restored_state = translation_overlay.restore_window_state()

        assert restored_state["x"] == 200
        assert restored_state["y"] == 300

    def test_on_config_changed(self, translation_overlay):
        """Test handling configuration changes"""
        with patch.object(translation_overlay, "_update_appearance") as mock_update:
            translation_overlay.on_config_changed("overlay.opacity", 0.9, 0.7)

            mock_update.assert_called_once()

    def test_performance_optimization(self, translation_overlay):
        """Test performance optimizations"""
        # Test update throttling
        for i in range(10):
            translation_overlay.update_queue.put(("show", Mock()))

        # Should throttle updates to prevent UI freezing
        with patch.object(translation_overlay, "_throttle_updates") as mock_throttle:
            translation_overlay._process_update_queue()

            mock_throttle.assert_called()

    def test_accessibility_features(self, translation_overlay):
        """Test accessibility features"""
        # Test high contrast mode
        translation_overlay.enable_high_contrast()

        assert translation_overlay.overlay_config.text_color == "#ffffff"
        assert translation_overlay.overlay_config.background_color == "#000000"

    def test_error_handling(self, translation_overlay):
        """Test error handling in overlay operations"""
        # Test with invalid window
        translation_overlay.overlay_window = None

        # Should not raise exception
        translation_overlay.hide()
        translation_overlay.show_translation(Mock())
        translation_overlay.set_opacity(0.5)

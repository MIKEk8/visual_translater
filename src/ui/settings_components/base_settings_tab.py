"""Base class for settings tabs."""

import threading
try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    from src.utils.mock_gui import tk, ttk

from typing import Dict, Any
from src.services.config_manager import ConfigManager
from src.utils.logger import logger


class BaseSettingsTab:
    """Base class for all settings tabs."""

    def __init__(self, parent: ttk.Notebook, config_manager: ConfigManager, tab_name: str):
        self.parent = parent
        self.config_manager = config_manager
        self.tab_name = tab_name
        self._lock = threading.Lock()

        # Create the tab frame
        self.frame = ttk.Frame(parent)
        self.parent.add(self.frame, text=tab_name)

        # Track if tab is initialized
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the tab components. Override in subclasses."""
        if self._initialized:
            return

        try:
            self._create_components()
            self._setup_bindings()
            self._load_current_values()
            self._initialized = True
            logger.debug(f"Initialized {self.tab_name} tab")
        except Exception as e:
            logger.error(f"Failed to initialize {self.tab_name} tab", error=e)

    def _create_components(self) -> None:
        """Create UI components. Override in subclasses."""
        pass

    def _setup_bindings(self) -> None:
        """Setup event bindings. Override in subclasses."""
        pass

    def _load_current_values(self) -> None:
        """Load current config values. Override in subclasses."""
        pass

    def save_settings(self) -> bool:
        """Save settings from this tab. Override in subclasses."""
        return True

    def validate_settings(self) -> tuple[bool, str]:
        """Validate settings. Override in subclasses."""
        return True, ""

    def reset_to_defaults(self) -> None:
        """Reset tab to default values. Override in subclasses."""
        pass

    def get_config_section(self, section: str) -> Dict[str, Any]:
        """Get configuration section safely."""
        config = self.config_manager.get_config()
        return getattr(config, section, {})

    def update_config_value(self, section: str, key: str, value: Any) -> bool:
        """Update a configuration value."""
        try:
            with self._lock:
                self.config_manager.update_config(f"{section}.{key}", value)
                return True
        except Exception as e:
            logger.error(f"Failed to update config {section}.{key}", error=e)
            return False

    def create_labeled_frame(self, parent: tk.Widget, title: str, **kwargs) -> ttk.LabelFrame:
        """Create a labeled frame with consistent styling."""
        frame = ttk.LabelFrame(parent, text=title, **kwargs)
        frame.pack(fill=tk.X, padx=10, pady=5)
        return frame

    def create_option_row(self, parent: tk.Widget, label_text: str, widget_type: str = "entry", **widget_kwargs) -> tuple[tk.Label, tk.Widget]:
        """Create a label-widget row."""
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, padx=5, pady=2)

        label = ttk.Label(row_frame, text=label_text)
        label.pack(side=tk.LEFT, anchor=tk.W)

        if widget_type == "entry":
            widget = ttk.Entry(row_frame, **widget_kwargs)
        elif widget_type == "combobox":
            widget = ttk.Combobox(row_frame, **widget_kwargs)
        elif widget_type == "checkbutton":
            widget = ttk.Checkbutton(row_frame, **widget_kwargs)
        elif widget_type == "scale":
            widget = ttk.Scale(row_frame, **widget_kwargs)
        else:
            widget = ttk.Entry(row_frame, **widget_kwargs)

        widget.pack(side=tk.RIGHT, anchor=tk.E)

        return label, widget
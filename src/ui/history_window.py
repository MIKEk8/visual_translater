"""
Enhanced history window for Screen Translator v2.0.
Provides advanced translation history management with search, filtering, and export capabilities.
"""

import csv
import json

try:
    import tkinter as tk
except ImportError:
    print(f"tkinter недоступен в {__name__}")
    # Используем заглушку
    from src.utils.mock_gui import tk

from dataclasses import asdict
from datetime import datetime, timedelta

try:
    from tkinter import filedialog, messagebox, ttk
except ImportError:
    print(f"tkinter недоступен в {__name__}")
    # Используем заглушки для импортированных компонентов
    from src.utils.mock_gui import filedialog, messagebox, ttk

from typing import Any, Callable, Dict, List, Optional

from src.models.translation import Translation
from src.services.config_manager import ConfigManager, ConfigObserver
from src.utils.logger import logger


class HistoryWindow(ConfigObserver):
    """Enhanced translation history window with advanced features."""

    def __init__(self, config_manager: ConfigManager, parent: Optional[tk.Tk] = None):
        """
        Initialize history window.

        Args:
            config_manager: Configuration manager instance
            parent: Parent window (optional)
        """
        self.config_manager = config_manager
        self.parent = parent
        self.window: Optional[tk.Toplevel] = None
        self.translations: List[Translation] = []
        self.filtered_translations: List[Translation] = []
        self.favorites: List[str] = []  # List of translation IDs

        # UI components
        self.search_var = tk.StringVar()
        self.source_lang_var = tk.StringVar(value="All")
        self.target_lang_var = tk.StringVar(value="All")
        self.date_filter_var = tk.StringVar(value="All time")
        self.show_favorites_var = tk.BooleanVar(value=False)
        self.tree: Optional[ttk.Treeview] = None
        self.stats_labels: Dict[str, tk.Label] = {}

        # Register as config observer
        self.config_manager.add_observer(self)

        # Callbacks
        self.on_translation_select: Optional[Callable[[Translation], None]] = None
        self.on_translation_repeat: Optional[Callable[[Translation], None]] = None

        logger.debug("History window initialized")

    def show(self) -> None:
        """Show the history window."""
        if self.window is not None:
            self.window.lift()
            self.window.focus()
            return

        self._create_window()
        self._load_translations()
        self._update_display()

        logger.info("History window opened")

    def hide(self) -> None:
        """Hide the history window."""
        if self.window:
            self.window.withdraw()

    def close(self) -> None:
        """Close the history window."""
        if self.window:
            self.window.destroy()
            self.window = None
            logger.info("History window closed")

    def add_translation(self, translation: Translation) -> None:
        """
        Add a new translation to the history.

        Args:
            translation: Translation to add
        """
        # Insert at beginning (most recent first)
        self.translations.insert(0, translation)

        # Limit history size (configurable)
        max_history = 1000  # Could be made configurable
        if len(self.translations) > max_history:
            self.translations = self.translations[:max_history]

        if self.window:
            self._apply_filters()
            self._update_display()

        logger.debug(f"Added translation to history: {len(translation.original_text)} chars")

    def toggle_favorite(self, translation_id: str) -> None:
        """Toggle favorite status of a translation."""
        if translation_id in self.favorites:
            self.favorites.remove(translation_id)
            logger.debug(f"Removed from favorites: {translation_id}")
        else:
            self.favorites.append(translation_id)
            logger.debug(f"Added to favorites: {translation_id}")

        if self.window:
            self._update_display()

    def export_history(self, format_type: str, file_path: str) -> bool:
        """
        Export translation history to file.

        Args:
            format_type: Export format ('csv', 'json', 'txt')
            file_path: Output file path

        Returns:
            True if export successful
        """
        try:
            translations_to_export = self.filtered_translations or self.translations

            if format_type.lower() == "csv":
                self._export_csv(translations_to_export, file_path)
            elif format_type.lower() == "json":
                self._export_json(translations_to_export, file_path)
            elif format_type.lower() == "txt":
                self._export_txt(translations_to_export, file_path)
            else:
                raise ValueError(f"Unsupported format: {format_type}")

            logger.info(f"Exported {len(translations_to_export)} translations to {file_path}")
            return True

        except Exception as e:
            logger.error("Failed to export history", error=e)
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get translation history statistics."""
        if not self.translations:
            return {}

        # Calculate statistics
        total_translations = len(self.translations)
        total_characters = sum(
            len(t.original_text) + len(t.translated_text) for t in self.translations
        )

        # Language statistics
        source_langs = {}
        target_langs = {}
        for t in self.translations:
            source_langs[t.source_language] = source_langs.get(t.source_language, 0) + 1
            target_langs[t.target_language] = target_langs.get(t.target_language, 0) + 1

        # Time-based statistics
        today = datetime.now().date()
        today_count = len([t for t in self.translations if t.timestamp.date() == today])

        week_ago = today - timedelta(days=7)
        week_count = len([t for t in self.translations if t.timestamp.date() >= week_ago])

        # Cache statistics
        cached_count = len([t for t in self.translations if t.cached])
        cache_ratio = cached_count / total_translations if total_translations > 0 else 0

        # Average confidence
        confidences = [t.confidence for t in self.translations if t.confidence is not None]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return {
            "total_translations": total_translations,
            "total_characters": total_characters,
            "today_count": today_count,
            "week_count": week_count,
            "cache_ratio": cache_ratio,
            "avg_confidence": avg_confidence,
            "favorites_count": len(self.favorites),
            "top_source_lang": (
                max(source_langs.items(), key=lambda x: x[1])[0] if source_langs else "None"
            ),
            "top_target_lang": (
                max(target_langs.items(), key=lambda x: x[1])[0] if target_langs else "None"
            ),
        }

    def on_config_changed(self, key: str, old_value: Any, new_value: Any) -> None:
        """Handle configuration changes."""
        if key.startswith("ui.") and self.window:
            # UI-related config changed, might need to update display
            self._update_display()

    def _create_window(self) -> None:
        """Create the history window UI."""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Translation History")
        self.window.geometry("1000x700")
        self.window.minsize(800, 500)

        # Configure window closing
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        # Create main frame
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create filter frame
        self._create_filter_frame(main_frame)

        # Create statistics frame
        self._create_stats_frame(main_frame)

        # Create main content frame
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Create translation list
        self._create_translation_list(content_frame)

        # Create action buttons
        self._create_action_buttons(main_frame)

        # Bind events
        self._bind_events()

    def _create_filter_frame(self, parent: tk.Widget) -> None:
        """Create the filter controls frame."""
        filter_frame = ttk.LabelFrame(parent, text="Filters", padding=10)
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        # Search box
        ttk.Label(filter_frame, text="Search:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=30)
        search_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))

        # Language filters
        ttk.Label(filter_frame, text="Source:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        source_combo = ttk.Combobox(
            filter_frame, textvariable=self.source_lang_var, width=10, state="readonly"
        )
        source_combo.grid(row=0, column=3, sticky=tk.W, padx=(0, 20))

        ttk.Label(filter_frame, text="Target:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        target_combo = ttk.Combobox(
            filter_frame, textvariable=self.target_lang_var, width=10, state="readonly"
        )
        target_combo.grid(row=0, column=5, sticky=tk.W, padx=(0, 20))

        # Date filter
        ttk.Label(filter_frame, text="Date:").grid(
            row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(10, 0)
        )
        date_combo = ttk.Combobox(
            filter_frame, textvariable=self.date_filter_var, width=15, state="readonly"
        )
        date_combo["values"] = ("All time", "Today", "This week", "This month")
        date_combo.grid(row=1, column=1, sticky=tk.W, pady=(10, 0), padx=(0, 20))

        # Favorites checkbox
        favorites_cb = ttk.Checkbutton(
            filter_frame, text="Favorites only", variable=self.show_favorites_var
        )
        favorites_cb.grid(row=1, column=2, sticky=tk.W, pady=(10, 0), padx=(0, 20))

        # Clear filters button
        clear_btn = ttk.Button(filter_frame, text="Clear Filters", command=self._clear_filters)
        clear_btn.grid(row=1, column=3, sticky=tk.W, pady=(10, 0))

        # Store comboboxes for updating
        self.source_combo = source_combo
        self.target_combo = target_combo

    def _create_stats_frame(self, parent: tk.Widget) -> None:
        """Create the statistics frame."""
        stats_frame = ttk.LabelFrame(parent, text="Statistics", padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        # Create statistics labels
        self.stats_labels["total"] = ttk.Label(stats_frame, text="Total: 0")
        self.stats_labels["total"].grid(row=0, column=0, sticky=tk.W, padx=(0, 20))

        self.stats_labels["today"] = ttk.Label(stats_frame, text="Today: 0")
        self.stats_labels["today"].grid(row=0, column=1, sticky=tk.W, padx=(0, 20))

        self.stats_labels["cache"] = ttk.Label(stats_frame, text="Cached: 0%")
        self.stats_labels["cache"].grid(row=0, column=2, sticky=tk.W, padx=(0, 20))

        self.stats_labels["confidence"] = ttk.Label(stats_frame, text="Avg Confidence: 0%")
        self.stats_labels["confidence"].grid(row=0, column=3, sticky=tk.W, padx=(0, 20))

        self.stats_labels["favorites"] = ttk.Label(stats_frame, text="Favorites: 0")
        self.stats_labels["favorites"].grid(row=0, column=4, sticky=tk.W)

    def _create_translation_list(self, parent: tk.Widget) -> None:
        """Create the translation list with treeview."""
        # Create treeview with scrollbars
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Define columns
        columns = (
            "Time",
            "Source",
            "Target",
            "Original",
            "Translation",
            "Confidence",
            "Cached",
            "Favorite",
        )
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)

        # Configure column headings and widths
        self.tree.heading("Time", text="Time")
        self.tree.heading("Source", text="Source Lang")
        self.tree.heading("Target", text="Target Lang")
        self.tree.heading("Original", text="Original Text")
        self.tree.heading("Translation", text="Translation")
        self.tree.heading("Confidence", text="Confidence")
        self.tree.heading("Cached", text="Cached")
        self.tree.heading("Favorite", text="★")

        self.tree.column("Time", width=120, minwidth=100)
        self.tree.column("Source", width=80, minwidth=60)
        self.tree.column("Target", width=80, minwidth=60)
        self.tree.column("Original", width=200, minwidth=150)
        self.tree.column("Translation", width=200, minwidth=150)
        self.tree.column("Confidence", width=80, minwidth=60)
        self.tree.column("Cached", width=60, minwidth=50)
        self.tree.column("Favorite", width=30, minwidth=30)

        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Pack treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

    def _create_action_buttons(self, parent: tk.Widget) -> None:
        """Create action buttons frame."""
        buttons_frame = ttk.Frame(parent)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))

        # Left side buttons
        left_frame = ttk.Frame(buttons_frame)
        left_frame.pack(side=tk.LEFT)

        ttk.Button(left_frame, text="Repeat", command=self._repeat_translation).pack(
            side=tk.LEFT, padx=(0, 10)
        )
        ttk.Button(left_frame, text="Copy", command=self._copy_translation).pack(
            side=tk.LEFT, padx=(0, 10)
        )
        ttk.Button(left_frame, text="Toggle ★", command=self._toggle_favorite).pack(
            side=tk.LEFT, padx=(0, 10)
        )

        # Right side buttons
        right_frame = ttk.Frame(buttons_frame)
        right_frame.pack(side=tk.RIGHT)

        ttk.Button(right_frame, text="Export...", command=self._export_dialog).pack(
            side=tk.LEFT, padx=(10, 0)
        )
        ttk.Button(right_frame, text="Clear History", command=self._clear_history).pack(
            side=tk.LEFT, padx=(10, 0)
        )
        ttk.Button(right_frame, text="Close", command=self.close).pack(side=tk.LEFT, padx=(10, 0))

    def _bind_events(self) -> None:
        """Bind UI events."""
        # Filter change events
        self.search_var.trace_add("write", lambda *args: self._apply_filters())
        self.source_lang_var.trace_add("write", lambda *args: self._apply_filters())
        self.target_lang_var.trace_add("write", lambda *args: self._apply_filters())
        self.date_filter_var.trace_add("write", lambda *args: self._apply_filters())
        self.show_favorites_var.trace_add("write", lambda *args: self._apply_filters())

        # Tree selection events
        if self.tree:
            self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
            self.tree.bind("<Double-1>", self._on_tree_double_click)

    def _load_translations(self) -> None:
        """Load translations from history (placeholder - would integrate with actual history storage)."""
        # This would typically load from a file or database
        # For now, we'll use empty list
        self.translations = []

        # Update language filter options
        self._update_language_filters()

    def _update_language_filters(self) -> None:
        """Update language filter dropdown options."""
        if not hasattr(self, "source_combo"):
            return

        # Get unique languages
        source_langs = set(t.source_language for t in self.translations)
        target_langs = set(t.target_language for t in self.translations)

        # Update comboboxes
        source_values = ["All"] + sorted(source_langs)
        target_values = ["All"] + sorted(target_langs)

        self.source_combo["values"] = source_values
        self.target_combo["values"] = target_values

    def _apply_filters(self) -> None:
        """Apply current filters to translation list."""
        filtered = self.translations.copy()

        # Search filter
        search_text = self.search_var.get().lower()
        if search_text:
            filtered = [
                t
                for t in filtered
                if search_text in t.original_text.lower()
                or search_text in t.translated_text.lower()
            ]

        # Language filters
        source_lang = self.source_lang_var.get()
        if source_lang != "All":
            filtered = [t for t in filtered if t.source_language == source_lang]

        target_lang = self.target_lang_var.get()
        if target_lang != "All":
            filtered = [t for t in filtered if t.target_language == target_lang]

        # Date filter
        date_filter = self.date_filter_var.get()
        if date_filter != "All time":
            now = datetime.now()
            if date_filter == "Today":
                cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif date_filter == "This week":
                cutoff = now - timedelta(days=7)
            elif date_filter == "This month":
                cutoff = now - timedelta(days=30)
            else:
                cutoff = None

            if cutoff:
                filtered = [t for t in filtered if t.timestamp >= cutoff]

        # Favorites filter
        if self.show_favorites_var.get():
            filtered = [t for t in filtered if self._get_translation_id(t) in self.favorites]

        self.filtered_translations = filtered
        self._update_display()

    def _update_display(self) -> None:
        """Update the display with current translations."""
        if not self.tree:
            return

        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add filtered translations
        for translation in self.filtered_translations:
            self._add_translation_to_tree(translation)

        # Update statistics
        self._update_statistics()

    def _add_translation_to_tree(self, translation: Translation) -> None:
        """Add a translation to the treeview."""
        if not self.tree:
            return

        translation_id = self._get_translation_id(translation)
        is_favorite = translation_id in self.favorites

        # Format values
        time_str = translation.timestamp.strftime("%m/%d %H:%M")
        confidence_str = f"{translation.confidence:.1%}" if translation.confidence else "N/A"
        cached_str = "Yes" if translation.cached else "No"
        favorite_str = "★" if is_favorite else ""

        # Truncate long text
        original_preview = (
            translation.original_text[:50] + "..."
            if len(translation.original_text) > 50
            else translation.original_text
        )
        translated_preview = (
            translation.translated_text[:50] + "..."
            if len(translation.translated_text) > 50
            else translation.translated_text
        )

        # Insert item
        values = (
            time_str,
            translation.source_language,
            translation.target_language,
            original_preview,
            translated_preview,
            confidence_str,
            cached_str,
            favorite_str,
        )

        item = self.tree.insert("", tk.END, values=values)

        # Store translation reference
        self.tree.set(item, "#0", translation_id)

    def _update_statistics(self) -> None:
        """Update statistics display."""
        stats = self.get_statistics()

        if self.stats_labels:
            self.stats_labels["total"].config(text=f"Total: {stats.get('total_translations', 0)}")
            self.stats_labels["today"].config(text=f"Today: {stats.get('today_count', 0)}")
            self.stats_labels["cache"].config(text=f"Cached: {stats.get('cache_ratio', 0):.1%}")
            self.stats_labels["confidence"].config(
                text=f"Avg Confidence: {stats.get('avg_confidence', 0):.1%}"
            )
            self.stats_labels["favorites"].config(
                text=f"Favorites: {stats.get('favorites_count', 0)}"
            )

    def _get_translation_id(self, translation: Translation) -> str:
        """Generate unique ID for translation."""
        # Simple ID based on timestamp and text hash
        text_hash = hash(translation.original_text + translation.translated_text)
        return f"{translation.timestamp.isoformat()}_{text_hash}"

    def _get_selected_translation(self) -> Optional[Translation]:
        """Get currently selected translation."""
        if not self.tree:
            return None

        selection = self.tree.selection()
        if not selection:
            return None

        item = selection[0]
        translation_id = self.tree.set(item, "#0")

        # Find translation by ID
        for translation in self.filtered_translations:
            if self._get_translation_id(translation) == translation_id:
                return translation

        return None

    # Event handlers
    def _on_tree_select(self, event) -> None:
        """Handle tree selection change."""
        translation = self._get_selected_translation()
        if translation and self.on_translation_select:
            self.on_translation_select(translation)

    def _on_tree_double_click(self, event) -> None:
        """Handle tree double-click."""
        translation = self._get_selected_translation()
        if translation and self.on_translation_repeat:
            self.on_translation_repeat(translation)

    def _repeat_translation(self) -> None:
        """Repeat selected translation."""
        translation = self._get_selected_translation()
        if translation:
            if self.on_translation_repeat:
                self.on_translation_repeat(translation)
            else:
                messagebox.showinfo("Repeat", f"Would repeat: {translation.original_text}")

    def _copy_translation(self) -> None:
        """Copy selected translation to clipboard."""
        translation = self._get_selected_translation()
        if translation:
            self.window.clipboard_clear()
            self.window.clipboard_append(translation.translated_text)
            messagebox.showinfo("Copied", "Translation copied to clipboard!")

    def _toggle_favorite(self) -> None:
        """Toggle favorite status of selected translation."""
        translation = self._get_selected_translation()
        if translation:
            translation_id = self._get_translation_id(translation)
            self.toggle_favorite(translation_id)

    def _clear_filters(self) -> None:
        """Clear all filters."""
        self.search_var.set("")
        self.source_lang_var.set("All")
        self.target_lang_var.set("All")
        self.date_filter_var.set("All time")
        self.show_favorites_var.set(False)

    def _export_dialog(self) -> None:
        """Show export dialog."""
        if not self.filtered_translations and not self.translations:
            messagebox.showwarning("Export", "No translations to export!")
            return

        # Ask for format
        format_window = tk.Toplevel(self.window)
        format_window.title("Export Format")
        format_window.geometry("300x150")
        format_window.resizable(False, False)

        ttk.Label(format_window, text="Select export format:").pack(pady=10)

        format_var = tk.StringVar(value="csv")
        ttk.Radiobutton(
            format_window, text="CSV (Comma Separated Values)", variable=format_var, value="csv"
        ).pack(anchor=tk.W, padx=20)
        ttk.Radiobutton(
            format_window,
            text="JSON (JavaScript Object Notation)",
            variable=format_var,
            value="json",
        ).pack(anchor=tk.W, padx=20)
        ttk.Radiobutton(
            format_window, text="TXT (Plain Text)", variable=format_var, value="txt"
        ).pack(anchor=tk.W, padx=20)

        def do_export():
            format_type = format_var.get()
            file_path = filedialog.asksaveasfilename(
                title="Export History",
                defaultextension=f".{format_type}",
                filetypes=[
                    (f"{format_type.upper()} files", f"*.{format_type}"),
                    ("All files", "*.*"),
                ],
            )

            if file_path:
                success = self.export_history(format_type, file_path)
                if success:
                    messagebox.showinfo("Export", f"History exported successfully to {file_path}")
                else:
                    messagebox.showerror("Export", "Failed to export history!")

            format_window.destroy()

        ttk.Button(format_window, text="Export", command=do_export).pack(pady=10)
        ttk.Button(format_window, text="Cancel", command=format_window.destroy).pack()

    def _clear_history(self) -> None:
        """Clear translation history."""
        if messagebox.askyesno(
            "Clear History", "Are you sure you want to clear all translation history?"
        ):
            self.translations.clear()
            self.filtered_translations.clear()
            self.favorites.clear()
            self._update_display()
            logger.info("Translation history cleared")

    # Export methods
    def _export_csv(self, translations: List[Translation], file_path: str) -> None:
        """Export translations to CSV format."""
        with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)

            # Write header
            writer.writerow(
                [
                    "Timestamp",
                    "Source Language",
                    "Target Language",
                    "Original Text",
                    "Translated Text",
                    "Confidence",
                    "Cached",
                ]
            )

            # Write data
            for t in translations:
                writer.writerow(
                    [
                        t.timestamp.isoformat(),
                        t.source_language,
                        t.target_language,
                        t.original_text,
                        t.translated_text,
                        t.confidence or "",
                        t.cached,
                    ]
                )

    def _export_json(self, translations: List[Translation], file_path: str) -> None:
        """Export translations to JSON format."""
        data = {
            "export_timestamp": datetime.now().isoformat(),
            "total_translations": len(translations),
            "translations": [asdict(t) for t in translations],
        }

        with open(file_path, "w", encoding="utf-8") as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False, default=str)

    def _export_txt(self, translations: List[Translation], file_path: str) -> None:
        """Export translations to plain text format."""
        with open(file_path, "w", encoding="utf-8") as txtfile:
            txtfile.write("Screen Translator - Translation History\n")
            txtfile.write("=" * 50 + "\n\n")

            for i, t in enumerate(translations, 1):
                txtfile.write(f"Translation #{i}\n")
                txtfile.write(f"Time: {t.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
                txtfile.write(f"Languages: {t.source_language} → {t.target_language}\n")
                txtfile.write(f"Original: {t.original_text}\n")
                txtfile.write(f"Translation: {t.translated_text}\n")
                if t.confidence:
                    txtfile.write(f"Confidence: {t.confidence:.2%}\n")
                txtfile.write(f"Cached: {'Yes' if t.cached else 'No'}\n")
                txtfile.write("-" * 30 + "\n\n")

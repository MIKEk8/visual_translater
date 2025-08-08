"""Unit tests for history window UI module"""

import csv
import json

try:
    import tkinter as tk
except ImportError:
    print("tkinter не доступен в данной среде")
    tk = None
from datetime import datetime, timedelta
from unittest.mock import Mock, mock_open, patch

import pytest

from src.models.translation import Translation
from src.ui.history_window import HistoryWindow


@pytest.fixture
def mock_config_manager():
    """Create mock configuration manager"""
    manager = Mock()
    manager.add_observer = Mock()
    manager.remove_observer = Mock()
    manager.get_config.return_value = Mock()
    return manager


@pytest.fixture
def sample_translations():
    """Create sample translations for testing"""
    now = datetime.now()
    return [
        Translation(
            original_text="Hello",
            translated_text="Привет",
            source_language="en",
            target_language="ru",
            timestamp=now.timestamp(),
            confidence=0.95,
            id="trans1",
        ),
        Translation(
            original_text="World",
            translated_text="Мир",
            source_language="en",
            target_language="ru",
            timestamp=(now - timedelta(hours=1)).timestamp(),
            confidence=0.88,
            id="trans2",
        ),
        Translation(
            original_text="こんにちは",
            translated_text="Hello",
            source_language="ja",
            target_language="en",
            timestamp=(now - timedelta(days=1)).timestamp(),
            confidence=0.92,
            id="trans3",
        ),
    ]


@pytest.fixture
def mock_parent():
    """Create mock parent window"""
    parent = Mock(spec=(tk.Tk if tk else None))
    return parent


@pytest.fixture
def history_window(mock_config_manager, mock_parent):
    """Create HistoryWindow instance with mocked dependencies"""
    with patch("tkinter.StringVar"), patch("tkinter.BooleanVar"):
        window = HistoryWindow(mock_config_manager, mock_parent)
        return window


class TestHistoryWindow:
    """Test HistoryWindow class"""

    def test_initialization(self, history_window, mock_config_manager):
        """Test history window initialization"""
        assert history_window.config_manager == mock_config_manager
        assert history_window.window is None
        assert history_window.translations == []
        assert history_window.filtered_translations == []
        assert history_window.favorites == []

        # Should register as config observer
        mock_config_manager.add_observer.assert_called_once_with(history_window)

    @patch("tkinter.Toplevel")
    def test_show_window_first_time(self, mock_toplevel, history_window):
        """Test showing window for first time"""
        mock_window = Mock()
        mock_toplevel.return_value = mock_window

        with patch.object(history_window, "_create_ui") as mock_create_ui, patch.object(
            history_window, "_load_translations"
        ) as mock_load:

            history_window.show()

            # Should create window and UI
            mock_toplevel.assert_called_once()
            mock_window.title.assert_called_with("История переводов")
            mock_window.geometry.assert_called_with("900x600")
            mock_create_ui.assert_called_once()
            mock_load.assert_called_once()

    def test_show_window_already_exists(self, history_window):
        """Test showing window when it already exists"""
        mock_window = Mock()
        mock_window.winfo_exists.return_value = True
        history_window.window = mock_window

        with patch.object(history_window, "_create_ui") as mock_create_ui:
            history_window.show()

            # Should just lift existing window
            mock_window.lift.assert_called_once()
            mock_window.focus_force.assert_called_once()
            mock_create_ui.assert_not_called()

    def test_load_translations(self, history_window, sample_translations):
        """Test loading translations"""
        history_window.translations = sample_translations

        with patch.object(
            history_window, "_update_filtered_translations"
        ) as mock_update, patch.object(
            history_window, "_update_tree_view"
        ) as mock_tree, patch.object(
            history_window, "_update_statistics"
        ) as mock_stats:

            history_window._load_translations()

            mock_update.assert_called_once()
            mock_tree.assert_called_once()
            mock_stats.assert_called_once()

    def test_add_translation(self, history_window, sample_translations):
        """Test adding new translation"""
        new_translation = sample_translations[0]

        with patch.object(
            history_window, "_update_filtered_translations"
        ) as mock_update, patch.object(
            history_window, "_update_tree_view"
        ) as mock_tree, patch.object(
            history_window, "_update_statistics"
        ) as mock_stats:

            history_window.add_translation(new_translation)

            assert new_translation in history_window.translations
            mock_update.assert_called_once()
            mock_tree.assert_called_once()
            mock_stats.assert_called_once()

    def test_remove_translation(self, history_window, sample_translations):
        """Test removing translation"""
        history_window.translations = sample_translations.copy()
        translation_to_remove = sample_translations[0]

        with patch.object(
            history_window, "_update_filtered_translations"
        ) as mock_update, patch.object(history_window, "_update_tree_view") as mock_tree:

            history_window.remove_translation(translation_to_remove.id)

            assert translation_to_remove not in history_window.translations
            mock_update.assert_called_once()
            mock_tree.assert_called_once()

    def test_search_filtering(self, history_window, sample_translations):
        """Test search-based filtering"""
        history_window.translations = sample_translations
        history_window.search_var = Mock()
        history_window.search_var.get.return_value = "Hello"

        history_window._update_filtered_translations()

        # Should filter to translations containing "Hello"
        filtered = history_window.filtered_translations
        assert len(filtered) >= 1
        assert any("Hello" in t.original_text or "Hello" in t.translated_text for t in filtered)

    def test_language_filtering(self, history_window, sample_translations):
        """Test language-based filtering"""
        history_window.translations = sample_translations
        history_window.search_var = Mock()
        history_window.search_var.get.return_value = ""
        history_window.source_lang_var = Mock()
        history_window.source_lang_var.get.return_value = "en"
        history_window.target_lang_var = Mock()
        history_window.target_lang_var.get.return_value = "All"

        history_window._update_filtered_translations()

        # Should filter to English source translations
        filtered = history_window.filtered_translations
        assert all(t.source_language == "en" for t in filtered)

    def test_date_filtering(self, history_window, sample_translations):
        """Test date-based filtering"""
        history_window.translations = sample_translations
        history_window.search_var = Mock()
        history_window.search_var.get.return_value = ""
        history_window.source_lang_var = Mock()
        history_window.source_lang_var.get.return_value = "All"
        history_window.target_lang_var = Mock()
        history_window.target_lang_var.get.return_value = "All"
        history_window.date_filter_var = Mock()
        history_window.date_filter_var.get.return_value = "Last 24 hours"

        history_window._update_filtered_translations()

        # Should filter to recent translations
        cutoff_time = (datetime.now() - timedelta(hours=24)).timestamp()
        filtered = history_window.filtered_translations
        assert all(t.timestamp >= cutoff_time for t in filtered)

    def test_favorites_filtering(self, history_window, sample_translations):
        """Test favorites filtering"""
        history_window.translations = sample_translations
        history_window.favorites = ["trans1", "trans3"]
        history_window.search_var = Mock()
        history_window.search_var.get.return_value = ""
        history_window.source_lang_var = Mock()
        history_window.source_lang_var.get.return_value = "All"
        history_window.target_lang_var = Mock()
        history_window.target_lang_var.get.return_value = "All"
        history_window.date_filter_var = Mock()
        history_window.date_filter_var.get.return_value = "All time"
        history_window.show_favorites_var = Mock()
        history_window.show_favorites_var.get.return_value = True

        history_window._update_filtered_translations()

        # Should filter to favorite translations only
        filtered = history_window.filtered_translations
        assert all(t.id in history_window.favorites for t in filtered)

    def test_add_to_favorites(self, history_window):
        """Test adding translation to favorites"""
        translation_id = "trans1"

        history_window.add_to_favorites(translation_id)

        assert translation_id in history_window.favorites

    def test_remove_from_favorites(self, history_window):
        """Test removing translation from favorites"""
        translation_id = "trans1"
        history_window.favorites = [translation_id]

        history_window.remove_from_favorites(translation_id)

        assert translation_id not in history_window.favorites

    def test_statistics_calculation(self, history_window, sample_translations):
        """Test statistics calculation"""
        history_window.filtered_translations = sample_translations

        stats_mock = Mock()
        history_window.stats_labels = {
            "total": stats_mock,
            "languages": stats_mock,
            "avg_confidence": stats_mock,
            "recent": stats_mock,
        }

        history_window._update_statistics()

        # Should update all statistics labels
        assert stats_mock.config.call_count >= 4

    def test_export_to_csv(self, history_window, sample_translations):
        """Test exporting translations to CSV"""
        history_window.filtered_translations = sample_translations

        with patch("tkinter.filedialog.asksaveasfilename", return_value="export.csv"), patch(
            "builtins.open", mock_open()
        ) as mock_file, patch("csv.writer") as mock_csv_writer:

            mock_writer = Mock()
            mock_csv_writer.return_value = mock_writer

            history_window._export_to_csv()

            # Should write CSV headers and data
            mock_writer.writerow.assert_called()
            assert mock_writer.writerow.call_count >= len(sample_translations) + 1

    def test_export_to_json(self, history_window, sample_translations):
        """Test exporting translations to JSON"""
        history_window.filtered_translations = sample_translations

        with patch("tkinter.filedialog.asksaveasfilename", return_value="export.json"), patch(
            "builtins.open", mock_open()
        ) as mock_file:

            history_window._export_to_json()

            # Should write JSON data
            mock_file.assert_called_once_with("export.json", "w", encoding="utf-8")

    def test_import_from_json(self, history_window):
        """Test importing translations from JSON"""
        import_data = [
            {
                "original_text": "Test",
                "translated_text": "Тест",
                "source_language": "en",
                "target_language": "ru",
                "timestamp": datetime.now().timestamp(),
                "confidence": 0.9,
                "id": "imported1",
            }
        ]

        with patch("tkinter.filedialog.askopenfilename", return_value="import.json"), patch(
            "builtins.open", mock_open(read_data=json.dumps(import_data))
        ), patch.object(history_window, "_load_translations") as mock_load:

            history_window._import_from_json()

            # Should add imported translations
            assert len(history_window.translations) == 1
            assert history_window.translations[0].original_text == "Test"
            mock_load.assert_called_once()

    def test_clear_history(self, history_window, sample_translations):
        """Test clearing translation history"""
        history_window.translations = sample_translations

        with patch("tkinter.messagebox.askyesno", return_value=True), patch.object(
            history_window, "_load_translations"
        ) as mock_load:

            history_window._clear_history()

            assert history_window.translations == []
            mock_load.assert_called_once()

    def test_clear_history_cancelled(self, history_window, sample_translations):
        """Test cancelling history clear"""
        history_window.translations = sample_translations
        original_count = len(history_window.translations)

        with patch("tkinter.messagebox.askyesno", return_value=False):
            history_window._clear_history()

            # Should not clear translations
            assert len(history_window.translations) == original_count

    @patch("tkinter.t(tk.Treeview if tk else None)")
    def test_create_tree_view(self, mock_treeview, history_window):
        """Test creating tree view"""
        mock_tree = Mock()
        mock_treeview.return_value = mock_tree
        parent_frame = Mock()

        tree = history_window._create_tree_view(parent_frame)

        # Should create treeview with columns
        mock_treeview.assert_called_once()
        mock_tree.heading.assert_called()  # Should set column headings
        assert tree == mock_tree

    def test_on_tree_select(self, history_window, sample_translations):
        """Test tree selection handling"""
        history_window.filtered_translations = sample_translations
        history_window.tree = Mock()
        history_window.tree.selection.return_value = ["item1"]
        history_window.tree.item.return_value = {
            "values": ["Hello", "Привет", "en", "ru", "2024-01-01 12:00:00", "95%"]
        }

        # Mock callback
        callback = Mock()
        history_window.on_translation_select = callback

        history_window._on_tree_select()

        # Should call callback with selected translation
        callback.assert_called_once()

    def test_context_menu(self, history_window):
        """Test context menu creation"""
        with patch("tkinter.Menu") as mock_menu:
            mock_menu_instance = Mock()
            mock_menu.return_value = mock_menu_instance

            menu = history_window._create_context_menu()

            # Should create menu with options
            mock_menu.assert_called_once()
            mock_menu_instance.add_command.assert_called()

    def test_copy_translation(self, history_window, sample_translations):
        """Test copying translation to clipboard"""
        translation = sample_translations[0]

        with patch("tkinter.Tk.clipboard_clear") as mock_clear, patch(
            "tkinter.Tk.clipboard_append"
        ) as mock_append:

            history_window._copy_translation(translation)

            mock_clear.assert_called_once()
            mock_append.assert_called_once()

    def test_search_functionality(self, history_window, sample_translations):
        """Test search functionality"""
        history_window.translations = sample_translations
        history_window.search_var = Mock()

        # Test case-insensitive search
        history_window.search_var.get.return_value = "hello"

        with patch.object(history_window, "_update_tree_view") as mock_update:
            history_window._on_search_changed()

            mock_update.assert_called_once()
            # Should find translations with "Hello" (case-insensitive)
            filtered = history_window.filtered_translations
            assert len(filtered) >= 1

    def test_sort_translations(self, history_window, sample_translations):
        """Test sorting translations"""
        history_window.filtered_translations = sample_translations.copy()

        # Sort by timestamp descending (newest first)
        history_window._sort_translations("timestamp", reverse=True)

        sorted_translations = history_window.filtered_translations
        timestamps = [t.timestamp for t in sorted_translations]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_get_language_pairs(self, history_window, sample_translations):
        """Test getting unique language pairs"""
        history_window.translations = sample_translations

        pairs = history_window._get_language_pairs()

        # Should return unique language pairs
        expected_pairs = {("en", "ru"), ("ja", "en")}
        assert len(pairs) >= 2
        assert any(pair in expected_pairs for pair in pairs)

    def test_filter_by_confidence(self, history_window, sample_translations):
        """Test filtering by confidence threshold"""
        history_window.translations = sample_translations

        # Filter translations with confidence >= 0.9
        high_confidence = history_window._filter_by_confidence(0.9)

        assert all(t.confidence >= 0.9 for t in high_confidence)

    def test_window_close_cleanup(self, history_window, mock_config_manager):
        """Test cleanup when window is closed"""
        history_window.window = Mock()

        history_window.close()

        # Should remove observer and cleanup
        mock_config_manager.remove_observer.assert_called_once_with(history_window)
        history_window.window.destroy.assert_called_once()
        assert history_window.window is None

    def test_on_config_changed(self, history_window):
        """Test handling configuration changes"""
        with patch.object(history_window, "_update_ui_theme") as mock_update_theme:
            history_window.on_config_changed("ui.theme", "light", "dark")

            mock_update_theme.assert_called_once()

    def test_keyboard_shortcuts(self, history_window):
        """Test keyboard shortcuts"""
        history_window.window = Mock()

        with patch.object(history_window, "_export_to_csv") as mock_export:
            # Simulate Ctrl+E keypress
            mock_event = Mock()
            mock_event.keysym = "e"
            mock_event.state = 4  # Ctrl modifier

            history_window._on_key_press(mock_event)

            mock_export.assert_called_once()

    def test_bulk_operations(self, history_window, sample_translations):
        """Test bulk operations on selected translations"""
        history_window.filtered_translations = sample_translations
        history_window.tree = Mock()
        history_window.tree.selection.return_value = ["item1", "item2"]

        with patch.object(history_window, "_get_selected_translations") as mock_get_selected:
            mock_get_selected.return_value = sample_translations[:2]

            # Test bulk delete
            with patch("tkinter.messagebox.askyesno", return_value=True):
                history_window._bulk_delete()

                # Should remove selected translations
                remaining = [
                    t for t in history_window.translations if t not in sample_translations[:2]
                ]
                assert len(remaining) < len(sample_translations)

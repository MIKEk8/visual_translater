import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

try:
    import tkinter as tk

    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    tk = None

import pytest
from PIL import Image

from src.tests.test_utils import skip_without_display
from src.ui.drag_drop_handler import BatchImageProcessor, DragDropHandler, ImageDropZone


@skip_without_display
@pytest.mark.skipif(not TKINTER_AVAILABLE, reason="tkinter not available")
class TestDragDropHandler(unittest.TestCase):
    """Test DragDropHandler functionality"""

    def setUp(self):
        """Setup test environment"""
        self.root = (tk.Tk if tk else None)()
        self.root.withdraw()  # Hide window during tests

        self.callback_calls = []

        def test_callback(files):
            self.callback_calls.append(files)

        self.handler = DragDropHandler(self.root, test_callback)

    def tearDown(self):
        """Cleanup test environment"""
        if self.root:
            self.root.destroy()

    def test_supported_formats(self):
        """Test supported file formats"""
        expected_formats = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"}
        self.assertEqual(self.handler.supported_formats, expected_formats)

    @patch("src.ui.drag_drop_handler.logger")
    def test_setup_drag_drop_with_tkinterdnd2(self, mock_logger):
        """Test setup with tkinterdnd2 available"""
        with patch("builtins.__import__") as mock_import:
            mock_tkinterdnd2 = Mock()
            mock_tkinterdnd2.DND_FILES = "DND_FILES"

            def mock_import_func(name, *args, **kwargs):
                if name == "tkinterdnd2":
                    return mock_tkinterdnd2
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = mock_import_func

            # Mock the tkinter widget methods that tkinterdnd2 would add
            self.root.drop_target_register = Mock()
            self.root.dnd_bind = Mock()

            # Create new handler to trigger setup
            handler = DragDropHandler(self.root, lambda x: None)

            # Should log success message
            mock_logger.info.assert_called_with("Advanced drag & drop enabled with tkinterdnd2")

            # Should call the mocked methods
            self.root.drop_target_register.assert_called_once_with("DND_FILES")
            self.root.dnd_bind.assert_called_once_with("<<Drop>>", handler._on_drop)

    @patch("src.ui.drag_drop_handler.logger")
    def test_setup_drag_drop_fallback(self, mock_logger):
        """Test fallback setup when tkinterdnd2 not available"""
        with patch("importlib.import_module", side_effect=ImportError("No module")):
            # Create new handler to trigger fallback
            _ = DragDropHandler(self.root, lambda x: None)

            # Should log fallback message
            mock_logger.info.assert_called_with("Using fallback drag & drop with right-click menu")

    def test_filter_supported_files(self):
        """Test filtering supported files"""
        test_files = [
            "image1.png",
            "image2.jpg",
            "document.pdf",  # Not supported
            "image3.bmp",
            "video.mp4",  # Not supported
            "image4.tiff",
        ]

        # Create temporary files
        temp_dir = tempfile.mkdtemp()
        try:
            file_paths = []
            for filename in test_files:
                file_path = os.path.join(temp_dir, filename)
                Path(file_path).touch()  # Create empty file
                file_paths.append(file_path)

            valid_files = self.handler._filter_supported_files(file_paths)

            # Should only include supported image formats
            self.assertEqual(len(valid_files), 4)  # png, jpg, bmp, tiff

            valid_names = [os.path.basename(f) for f in valid_files]
            self.assertIn("image1.png", valid_names)
            self.assertIn("image2.jpg", valid_names)
            self.assertIn("image3.bmp", valid_names)
            self.assertIn("image4.tiff", valid_names)
            self.assertNotIn("document.pdf", valid_names)
            self.assertNotIn("video.mp4", valid_names)

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_filter_non_existent_files(self):
        """Test filtering with non-existent files"""
        test_files = ["/non/existent/image1.png", "/another/fake/image2.jpg"]

        valid_files = self.handler._filter_supported_files(test_files)
        self.assertEqual(len(valid_files), 0)

    def test_filter_files_with_quotes(self):
        """Test filtering files with quotes in path"""
        temp_dir = tempfile.mkdtemp()
        try:
            file_path = os.path.join(temp_dir, "image.png")
            Path(file_path).touch()

            # Test with quotes
            quoted_files = [f'"{file_path}"', f"'{file_path}'"]

            valid_files = self.handler._filter_supported_files(quoted_files)
            self.assertEqual(len(valid_files), 2)

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    @patch("tkinter.filedialog.askopenfilenames")
    def test_select_files(self, mock_dialog):
        """Test file selection dialog"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create test files
            test_files = ["image1.png", "image2.jpg"]
            file_paths = []
            for filename in test_files:
                file_path = os.path.join(temp_dir, filename)
                Path(file_path).touch()
                file_paths.append(file_path)

            mock_dialog.return_value = file_paths

            self.handler._select_files()

            # Should call callback with selected files
            self.assertEqual(len(self.callback_calls), 1)
            self.assertEqual(len(self.callback_calls[0]), 2)

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    @patch("tkinter.filedialog.askopenfilenames")
    def test_select_files_cancelled(self, mock_dialog):
        """Test file selection dialog cancelled"""
        mock_dialog.return_value = ()  # Empty tuple when cancelled

        self.handler._select_files()

        # Should not call callback
        self.assertEqual(len(self.callback_calls), 0)

    @patch("PIL.ImageGrab.grabclipboard")
    @patch("tkinter.messagebox.showinfo")
    def test_paste_from_clipboard_success(self, mock_showinfo, mock_grabclipboard):
        """Test successful clipboard paste"""
        # Mock clipboard image
        mock_image = Mock(spec=Image.Image)
        mock_grabclipboard.return_value = mock_image

        with patch("tempfile.NamedTemporaryFile") as mock_temp:
            import tempfile

            temp_dir = tempfile.gettempdir()
            mock_temp.return_value.__enter__.return_value.name = f"{temp_dir}/clipboard.png"

            self.handler._paste_from_clipboard()

            # Should save image and call callback
            mock_image.save.assert_called_once()
            self.assertEqual(len(self.callback_calls), 1)

    @patch("PIL.ImageGrab.grabclipboard")
    @patch("tkinter.messagebox.showinfo")
    def test_paste_from_clipboard_no_image(self, mock_showinfo, mock_grabclipboard):
        """Test clipboard paste with no image"""
        mock_grabclipboard.return_value = None  # No image

        self.handler._paste_from_clipboard()

        # Should show info message and not call callback
        mock_showinfo.assert_called_once_with("Clipboard", "No image found in clipboard")
        self.assertEqual(len(self.callback_calls), 0)

    @patch("tkinter.messagebox.showerror")
    def test_paste_from_clipboard_import_error(self, mock_showerror):
        """Test clipboard paste with import error"""
        with patch.dict("sys.modules", {"PIL.ImageGrab": None}):
            with patch("builtins.__import__", side_effect=ImportError("No PIL")):
                self.handler._paste_from_clipboard()

                # Should show error message
                mock_showerror.assert_called_once_with("Error", "PIL ImageGrab not available")


@skip_without_display
@pytest.mark.skipif(not TKINTER_AVAILABLE, reason="tkinter not available")
class TestImageDropZone(unittest.TestCase):
    """Test ImageDropZone functionality"""

    def setUp(self):
        """Setup test environment"""
        self.root = (tk.Tk if tk else None)()
        self.root.withdraw()  # Hide window during tests

        self.callback_calls = []

        def test_callback(files):
            self.callback_calls.append(files)

        self.drop_zone = ImageDropZone(self.root, test_callback)

    def tearDown(self):
        """Cleanup test environment"""
        if self.root:
            self.root.destroy()

    def test_creation(self):
        """Test drop zone creation"""
        self.assertIsNotNone(self.drop_zone.frame)
        self.assertIsNotNone(self.drop_zone.label)
        self.assertIn("Drop image files here", self.drop_zone.label.cget("text"))

    def test_files_dropped(self):
        """Test files being dropped"""
        test_files = ["image1.png", "image2.jpg"]

        self.drop_zone._on_files_dropped(test_files)

        # Should update label and call callback
        self.assertIn("Processing 2 files", self.drop_zone.label.cget("text"))
        self.assertEqual(len(self.callback_calls), 1)
        self.assertEqual(self.callback_calls[0], test_files)

    def test_single_file_dropped(self):
        """Test single file dropped"""
        test_files = ["single_image.png"]

        self.drop_zone._on_files_dropped(test_files)

        # Should show "Processing 1 file" (no 's')
        self.assertIn("Processing 1 file", self.drop_zone.label.cget("text"))

    def test_no_files_dropped(self):
        """Test empty file list"""
        self.drop_zone._on_files_dropped([])

        # Should not update label or call callback
        self.assertIn("Drop image files here", self.drop_zone.label.cget("text"))
        self.assertEqual(len(self.callback_calls), 0)


@pytest.mark.skipif(not TKINTER_AVAILABLE, reason="tkinter not available")
class TestBatchImageProcessor(unittest.TestCase):
    """Test BatchImageProcessor functionality"""

    def setUp(self):
        """Setup test environment"""
        self.mock_app = Mock()
        self.mock_app.progress_manager = Mock()
        self.mock_app.batch_processor = Mock()

        self.processor = BatchImageProcessor(self.mock_app)

    def test_load_image_file_success(self):
        """Test successful image file loading"""
        # Create temporary image file
        temp_dir = tempfile.mkdtemp()
        try:
            image_path = os.path.join(temp_dir, "test.png")

            # Create and save test image
            test_image = Image.new("RGB", (100, 100), color="red")
            test_image.save(image_path, "PNG")

            screenshot_data = self.processor._load_image_file(image_path)

            self.assertIsNotNone(screenshot_data)
            self.assertEqual(screenshot_data.image.size, (100, 100))
            self.assertEqual(screenshot_data.coordinates, (0, 0, 100, 100))

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_load_image_file_rgba_conversion(self):
        """Test RGBA to RGB conversion"""
        temp_dir = tempfile.mkdtemp()
        try:
            image_path = os.path.join(temp_dir, "test.png")

            # Create RGBA image
            test_image = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
            test_image.save(image_path, "PNG")

            screenshot_data = self.processor._load_image_file(image_path)

            self.assertIsNotNone(screenshot_data)
            self.assertEqual(screenshot_data.image.mode, "RGB")

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_load_image_file_not_found(self):
        """Test loading non-existent file"""
        screenshot_data = self.processor._load_image_file("/non/existent/file.png")
        self.assertIsNone(screenshot_data)

    def test_process_image_files_success(self):
        """Test processing multiple image files"""
        # Setup mocks
        self.mock_app.batch_processor.create_batch_job.return_value = "job123"
        self.mock_app.batch_processor.start_batch_job.return_value = True

        # Create temporary image files
        temp_dir = tempfile.mkdtemp()
        try:
            file_paths = []
            for i in range(3):
                image_path = os.path.join(temp_dir, f"image{i}.png")
                test_image = Image.new("RGB", (100, 100), color="white")
                test_image.save(image_path, "PNG")
                file_paths.append(image_path)

            job_id = self.processor.process_image_files(file_paths)

            self.assertEqual(job_id, "job123")

            # Should create batch job
            self.mock_app.batch_processor.create_batch_job.assert_called_once()
            create_args = self.mock_app.batch_processor.create_batch_job.call_args
            self.assertIn("Image Files", create_args[1]["name"])

            # Should start batch job
            self.mock_app.batch_processor.start_batch_job.assert_called_once_with(
                "job123",
                progress_callback=self.mock_app._on_batch_progress,
                completion_callback=self.processor._on_image_batch_completion,
            )

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_process_image_files_no_valid_images(self):
        """Test processing with no valid images"""
        # Non-existent files
        file_paths = ["/fake/image1.png", "/fake/image2.jpg"]

        job_id = self.processor.process_image_files(file_paths)

        self.assertIsNone(job_id)
        self.mock_app.progress_manager.show_error.assert_called_with(
            "No valid images could be loaded"
        )

    def test_process_image_files_batch_start_failure(self):
        """Test when batch job fails to start"""
        self.mock_app.batch_processor.create_batch_job.return_value = "job123"
        self.mock_app.batch_processor.start_batch_job.return_value = False

        # Create one temporary image
        temp_dir = tempfile.mkdtemp()
        try:
            image_path = os.path.join(temp_dir, "test.png")
            test_image = Image.new("RGB", (100, 100), color="white")
            test_image.save(image_path, "PNG")

            job_id = self.processor.process_image_files([image_path])

            self.assertIsNone(job_id)
            self.mock_app.progress_manager.show_error.assert_called_with(
                "Failed to start image processing"
            )

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_on_image_batch_completion_success(self):
        """Test successful batch completion callback"""
        # Mock batch job with results
        mock_job = Mock()
        mock_job.status.value = "completed"
        mock_job.completed_items = 2
        mock_job.failed_items = 0

        # Mock results
        mock_results = [Mock(), Mock()]  # 2 translations
        self.mock_app.batch_processor.get_job_results.return_value = mock_results

        with patch("tkinter.Toplevel") as _:
            with patch("tkinter.scrolledtext.ScrolledText") as _:
                with patch("tkinter.Button") as _:
                    self.processor._on_image_batch_completion("job123", mock_job)

        # Should hide progress and show success
        self.mock_app.progress_manager.hide_progress.assert_called_once()
        self.mock_app.progress_manager.show_success.assert_called()

    def test_on_image_batch_completion_no_results(self):
        """Test batch completion with no results"""
        mock_job = Mock()
        mock_job.status.value = "failed"

        self.mock_app.batch_processor.get_job_results.return_value = []

        self.processor._on_image_batch_completion("job123", mock_job)

        # Should show error
        self.mock_app.progress_manager.show_error.assert_called_with(
            "No successful translations from image batch"
        )


@skip_without_display
@pytest.mark.skipif(not TKINTER_AVAILABLE, reason="tkinter not available")
class TestCreateImageDropInterface(unittest.TestCase):
    """Test create_image_drop_interface function"""

    def setUp(self):
        """Setup test environment"""
        self.root = (tk.Tk if tk else None)()
        self.root.withdraw()  # Hide window during tests
        self.mock_app = Mock()

    def tearDown(self):
        """Cleanup test environment"""
        if self.root:
            self.root.destroy()

    def test_create_interface(self):
        """Test creating drop interface"""
        from src.ui.drag_drop_handler import create_image_drop_interface

        drop_zone = create_image_drop_interface(self.root, self.mock_app)

        self.assertIsInstance(drop_zone, ImageDropZone)
        self.assertIsNotNone(drop_zone.frame)


if __name__ == "__main__":
    unittest.main()

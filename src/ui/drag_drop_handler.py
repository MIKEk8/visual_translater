"""
Drag and drop handler for images and files
"""

import io

try:
    import tkinter as tk
except ImportError:
    print(f"tkinter недоступен в {__name__}")
    # Используем заглушку
    from src.utils.mock_gui import tk

from pathlib import Path

try:
    from tkinter import filedialog, messagebox
except ImportError:
    print(f"tkinter недоступен в {__name__}")
    # Используем заглушки для импортированных компонентов
    from src.utils.mock_gui import filedialog, messagebox

from typing import Callable, List, Optional

from PIL import Image

from src.utils.logger import logger


class DragDropHandler:
    """Handler for drag and drop functionality"""

    def __init__(self, widget: tk.Widget, callback: Callable[[List[str]], None]):
        self.widget = widget
        self.callback = callback
        self.supported_formats = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"}

        # Enable drag and drop
        self._setup_drag_drop()

    def _setup_drag_drop(self):
        """Setup drag and drop bindings"""
        try:
            # Try to use tkinterdnd2 if available
            import tkinterdnd2

            self.widget.drop_target_register(tkinterdnd2.DND_FILES)
            self.widget.dnd_bind("<<Drop>>", self._on_drop)
            logger.info("Advanced drag & drop enabled with tkinterdnd2")
        except ImportError:
            # Fallback to basic file dialog approach
            logger.info("Using fallback drag & drop with right-click menu")
            self._setup_fallback_menu()

    def _setup_fallback_menu(self):
        """Setup right-click menu as fallback for drag & drop"""
        menu = tk.Menu(self.widget, tearoff=0)
        menu.add_command(label="Select Image Files...", command=self._select_files)
        menu.add_separator()
        menu.add_command(label="Paste from Clipboard", command=self._paste_from_clipboard)

        def show_menu(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        self.widget.bind("<Button-3>", show_menu)  # Right click

    def _on_drop(self, event):
        """Handle drop event"""
        try:
            files = event.data.split()
            valid_files = self._filter_supported_files(files)

            if valid_files:
                self.callback(valid_files)
            else:
                logger.warning("No supported image files in drop")

        except Exception as e:
            logger.error("Error handling drop", error=e)

    def _select_files(self):
        """Open file dialog to select images"""
        try:
            filetypes = [
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp"),
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("All files", "*.*"),
            ]

            files = filedialog.askopenfilenames(title="Select Image Files", filetypes=filetypes)

            if files:
                self.callback(list(files))

        except Exception as e:
            logger.error("Error selecting files", error=e)

    def _paste_from_clipboard(self):
        """Try to paste image from clipboard"""
        try:
            # Try to get image from clipboard
            from PIL import ImageGrab

            image = ImageGrab.grabclipboard()
            if image:
                # Save to temporary file
                import tempfile

                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    image.save(tmp.name, "PNG")
                    self.callback([tmp.name])
                    logger.info("Pasted image from clipboard")
            else:
                messagebox.showinfo("Clipboard", "No image found in clipboard")

        except ImportError:
            messagebox.showerror("Error", "PIL ImageGrab not available")
        except Exception as e:
            logger.error("Error pasting from clipboard", error=e)
            messagebox.showerror("Error", f"Failed to paste from clipboard: {str(e)}")

    def _filter_supported_files(self, files: List[str]) -> List[str]:
        """Filter files to only include supported image formats"""
        valid_files = []

        for file_path in files:
            try:
                # Remove quotes and normalize path
                file_path = file_path.strip('"').strip("'")
                path = Path(file_path)

                if path.exists() and path.is_file():
                    if path.suffix.lower() in self.supported_formats:
                        valid_files.append(str(path))
                    else:
                        logger.debug(f"Unsupported file format: {path.suffix}")

            except Exception as e:
                logger.debug(f"Error processing file path {file_path}: {e}")

        return valid_files


class ImageDropZone:
    """Visual drop zone widget for images"""

    def __init__(self, parent: tk.Widget, callback: Callable[[List[str]], None]):
        self.parent = parent
        self.callback = callback

        # Create drop zone frame
        self.frame = tk.Frame(parent, relief="solid", bd=2, bg="#f0f0f0")
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Add label
        self.label = tk.Label(
            self.frame,
            text="Drop image files here\nor right-click to select",
            bg="#f0f0f0",
            fg="#666666",
            font=("TkDefaultFont", 12),
            justify=tk.CENTER,
        )
        self.label.pack(expand=True)

        # Setup drag and drop
        self.drag_handler = DragDropHandler(self.frame, self._on_files_dropped)
        self.drag_handler_label = DragDropHandler(self.label, self._on_files_dropped)

        # Visual feedback
        self._setup_hover_effects()

    def _setup_hover_effects(self):
        """Setup visual feedback for hover"""

        def on_enter(event):
            self.frame.config(bg="#e6f3ff", relief="solid", bd=3)
            self.label.config(bg="#e6f3ff", fg="#0066cc")

        def on_leave(event):
            self.frame.config(bg="#f0f0f0", relief="solid", bd=2)
            self.label.config(bg="#f0f0f0", fg="#666666")

        self.frame.bind("<Enter>", on_enter)
        self.frame.bind("<Leave>", on_leave)
        self.label.bind("<Enter>", on_enter)
        self.label.bind("<Leave>", on_leave)

    def _on_files_dropped(self, files: List[str]):
        """Handle files being dropped"""
        if files:
            # Update label to show file count
            count = len(files)
            self.label.config(text=f"Processing {count} file{'s' if count > 1 else ''}...")

            # Reset label after callback
            self.parent.after(
                2000,
                lambda: self.label.config(text="Drop image files here\nor right-click to select"),
            )

            # Call the callback
            self.callback(files)


class BatchImageProcessor:
    """Process multiple images from drag & drop or file selection"""

    def __init__(self, application_instance):
        self.app = application_instance

    def process_image_files(self, file_paths: List[str]) -> Optional[str]:
        """Process multiple image files for OCR and translation"""
        try:
            logger.info(f"Processing {len(file_paths)} image files")

            # Convert file paths to screenshot data
            screenshots = []
            for file_path in file_paths:
                screenshot_data = self._load_image_file(file_path)
                if screenshot_data:
                    screenshots.append(screenshot_data)

            if not screenshots:
                self.app.progress_manager.show_error("No valid images could be loaded")
                return None

            # Start batch processing
            job_name = f"Image Files ({len(screenshots)} items)"
            job_id = self.app.batch_processor.create_batch_job(
                name=job_name, screenshots=screenshots
            )

            # Show progress and start processing
            _ = self.app.progress_manager.show_progress(
                title="Processing Images",
                message=f"Processing {len(screenshots)} images...",
                is_indeterminate=False,
            )

            success = self.app.batch_processor.start_batch_job(
                job_id,
                progress_callback=self.app._on_batch_progress,
                completion_callback=self._on_image_batch_completion,
            )

            if success:
                logger.info(f"Started image batch processing: {job_id}")
                return job_id
            else:
                self.app.progress_manager.show_error("Failed to start image processing")
                return None

        except Exception as e:
            logger.error("Error processing image files", error=e)
            self.app.progress_manager.show_error(f"Failed to process images: {str(e)}")
            return None

    def _load_image_file(self, file_path: str) -> Optional:
        """Load image file and convert to screenshot data format"""
        try:
            from src.models.screenshot_data import ScreenshotData

            # Load image
            image = Image.open(file_path)

            # Convert to bytes
            img_byte_arr = io.BytesIO()

            # Ensure RGB format for consistency
            if image.mode != "RGB":
                image = image.convert("RGB")

            image.save(img_byte_arr, format="PNG")
            image_bytes = img_byte_arr.getvalue()

            # Create screenshot data
            screenshot_data = ScreenshotData(
                image=image,
                image_data=image_bytes,  # For backward compatibility
                coordinates=(0, 0, image.width, image.height),
                timestamp=None,
            )

            logger.debug(f"Loaded image file: {file_path} ({image.width}x{image.height})")
            return screenshot_data

        except Exception as e:
            logger.error(f"Failed to load image file {file_path}", error=e)
            return None

    def _on_image_batch_completion(self, job_id: str, job) -> None:
        """Handle completion of image batch processing"""
        # Hide progress
        self.app.progress_manager.hide_progress()

        # Get results
        results = self.app.batch_processor.get_job_results(job_id)

        if results:
            # Show results summary
            total_text = "\n\n".join(
                [
                    f"Image {i+1}:\n{result.original_text}\n→ {result.translated_text}"
                    for i, result in enumerate(results[:3])  # Show first 3
                ]
            )

            if len(results) > 3:
                total_text += f"\n\n... and {len(results) - 3} more translations"

            # Show in dialog
            from tkinter import scrolledtext

            window = tk.Toplevel(self.app.root)
            window.title(f"Batch Results - {len(results)} Translations")
            window.geometry("600x400")

            text_widget = scrolledtext.ScrolledText(window, wrap=tk.WORD)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text_widget.insert(tk.END, total_text)
            text_widget.config(state=tk.DISABLED)

            # Add close button
            close_btn = tk.Button(window, text="Close", command=window.destroy)
            close_btn.pack(pady=5)

            self.app.progress_manager.show_success(f"Processed {len(results)} images successfully")
        else:
            self.app.progress_manager.show_error("No successful translations from image batch")


def create_image_drop_interface(parent: tk.Widget, application_instance) -> ImageDropZone:
    """Create a complete drag & drop interface for images"""
    batch_processor = BatchImageProcessor(application_instance)

    def handle_dropped_files(files: List[str]):
        batch_processor.process_image_files(files)

    return ImageDropZone(parent, handle_dropped_files)

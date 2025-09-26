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
        dnd_enabled = False

        try:
            # Try to use tkinterdnd2 if available
            import tkinterdnd2

            # Check if the widget's root window is a TkinterDnD window
            root = self.widget.winfo_toplevel()

            # Try multiple ways to detect DnD support
            if hasattr(root, 'TkdndVersion'):
                # The window has TkinterDnD2 support
                self.widget.drop_target_register(tkinterdnd2.DND_FILES)
                self.widget.dnd_bind("<<Drop>>", self._on_drop)
                logger.info("Advanced drag & drop enabled with tkinterdnd2")
                dnd_enabled = True
            elif hasattr(root, 'tk') and hasattr(root.tk, 'call'):
                # Try to register anyway - sometimes the attribute is not set but it works
                try:
                    self.widget.drop_target_register(tkinterdnd2.DND_FILES)
                    self.widget.dnd_bind("<<Drop>>", self._on_drop)
                    logger.info("Drag & drop enabled via tkinterdnd2 (forced)")
                    dnd_enabled = True
                except Exception as e:
                    logger.debug(f"Could not force DnD registration: {e}")

            if not dnd_enabled:
                logger.info("Root window is not TkinterDnD-enabled, using fallback")

        except ImportError:
            logger.info("tkinterdnd2 not installed, using fallback")
        except Exception as e:
            logger.warning(f"Error setting up drag & drop: {e}")

        # Always set up the fallback menu for right-click and paste
        self._setup_fallback_menu()

    def _setup_fallback_menu(self):
        """Setup right-click menu as fallback for drag & drop"""
        menu = tk.Menu(self.widget, tearoff=0)
        menu.add_command(label="Select Image Files...", command=self._select_files)
        menu.add_separator()
        menu.add_command(label="Paste from Clipboard (Ctrl+V)", command=self._paste_from_clipboard)

        def show_menu(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        self.widget.bind("<Button-3>", show_menu)  # Right click

        # Also bind Ctrl+V for paste
        self.widget.bind("<Control-v>", lambda e: self._paste_from_clipboard())
        self.widget.bind("<Control-V>", lambda e: self._paste_from_clipboard())  # For uppercase V

        # Make widget focusable so it can receive keyboard events
        self.widget.configure(takefocus=True)
        self.widget.bind("<Button-1>", lambda e: self.widget.focus_set())  # Focus on click

    def _on_drop(self, event):
        """Handle drop event"""
        try:
            # Parse the dropped data - it might be in different formats
            if hasattr(event, 'data'):
                data = event.data
            elif hasattr(event, 'Data'):
                data = event.Data
            else:
                logger.error("Drop event has no data attribute")
                return

            # Handle Windows paths with spaces and special characters
            # TkinterDnD2 returns paths in curly braces if they contain spaces
            files = []

            # Check if data is a string
            if isinstance(data, str):
                # Remove extra whitespace
                data = data.strip()

                # Handle curly braces for paths with spaces (Windows specific)
                if data.startswith('{') and data.endswith('}'):
                    # Single file with spaces
                    files = [data[1:-1]]
                elif '{' in data:
                    # Multiple files, some with spaces
                    import re
                    # Find all paths in curly braces
                    braced = re.findall(r'\{([^}]+)\}', data)
                    # Find all paths without spaces
                    unbraced = [p for p in data.split() if not (p.startswith('{') or p.endswith('}'))]
                    files = braced + unbraced
                else:
                    # Simple space-separated paths
                    files = data.split()
            else:
                # Data might be a list already
                files = list(data) if hasattr(data, '__iter__') else [str(data)]

            # Clean up file paths
            cleaned_files = []
            for f in files:
                # Remove quotes and extra whitespace
                f = f.strip().strip('"').strip("'")
                if f:
                    cleaned_files.append(f)

            logger.debug(f"Dropped files: {cleaned_files}")
            valid_files = self._filter_supported_files(cleaned_files)

            if valid_files:
                logger.info(f"Processing {len(valid_files)} valid image file(s)")
                self.callback(valid_files)
            else:
                logger.warning("No supported image files in drop")
                messagebox.showinfo("Drag & Drop", "Перетащенные файлы не содержат поддерживаемых изображений.\n\nПоддерживаемые форматы: PNG, JPG, BMP, GIF, TIFF, WebP")

        except Exception as e:
            logger.error(f"Error handling drop: {e}", error=e)
            messagebox.showerror("Ошибка", f"Ошибка при обработке перетащенных файлов:\n{str(e)}")

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
            import tempfile
            import os

            image = ImageGrab.grabclipboard()
            if image:
                # Check if it's an image
                if isinstance(image, list):
                    # It's a list of file paths
                    valid_files = self._filter_supported_files(image)
                    if valid_files:
                        self.callback(valid_files)
                        logger.info(f"Pasted {len(valid_files)} file(s) from clipboard")
                    else:
                        messagebox.showinfo("Буфер обмена", "В буфере обмена нет поддерживаемых изображений")
                else:
                    # It's an actual image
                    # Use NamedTemporaryFile for automatic cleanup
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                        temp_file = tmp_file.name

                        # Convert to RGB if necessary
                        if image.mode in ('RGBA', 'LA', 'P'):
                            # Create a white background
                            background = Image.new('RGB', image.size, (255, 255, 255))
                            if image.mode == 'P':
                                image = image.convert('RGBA')
                            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                            image = background
                        elif image.mode != 'RGB':
                            image = image.convert('RGB')

                        image.save(temp_file, "PNG")

                    # Schedule cleanup after a delay (give time for processing)
                    def cleanup_temp_file():
                        try:
                            if os.path.exists(temp_file):
                                os.unlink(temp_file)
                                logger.debug(f"Cleaned up temporary file: {temp_file}")
                        except Exception as e:
                            logger.debug(f"Could not cleanup temp file {temp_file}: {e}")

                    # Clean up after 60 seconds
                    import threading
                    threading.Timer(60.0, cleanup_temp_file).start()

                    self.callback([temp_file])
                    logger.info("Pasted image from clipboard")

                    # Show success feedback
                    if hasattr(self, 'widget'):
                        # Flash the widget briefly to show success
                        orig_bg = self.widget.cget('bg') if hasattr(self.widget, 'cget') else None
                        if orig_bg:
                            self.widget.config(bg='#90EE90')  # Light green
                            self.widget.after(200, lambda: self.widget.config(bg=orig_bg))
            else:
                messagebox.showinfo("Буфер обмена", "В буфере обмена нет изображения.\n\nСкопируйте изображение или сделайте скриншот (Print Screen),\nзатем нажмите Ctrl+V")

        except ImportError:
            messagebox.showerror("Ошибка", "Модуль PIL ImageGrab не доступен.\nУстановите Pillow: pip install Pillow")
        except Exception as e:
            logger.error("Error pasting from clipboard", error=e)
            messagebox.showerror("Ошибка", f"Не удалось вставить из буфера обмена:\n{str(e)}")

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
            text="📥 Перетащите изображения сюда\n\n• Правый клик - выбрать файлы\n• Ctrl+V - вставить из буфера обмена",
            bg="#f0f0f0",
            fg="#666666",
            font=("TkDefaultFont", 11),
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
            self.label.config(text=f"⏳ Обрабатывается {count} {'файл' if count == 1 else 'файла' if count < 5 else 'файлов'}...")

            # Reset label after callback
            self.parent.after(
                2000,
                lambda: self.label.config(text="📥 Перетащите изображения сюда\n\n• Правый клик - выбрать файлы\n• Ctrl+V - вставить из буфера обмена"),
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

            # Load image using context manager to prevent memory leak
            with Image.open(file_path) as image:
                # Store dimensions before closing
                width, height = image.size

                # Convert to bytes
                img_byte_arr = io.BytesIO()

                # Ensure RGB format for consistency
                if image.mode != "RGB":
                    image = image.convert("RGB")

                image.save(img_byte_arr, format="PNG")
                image_bytes = img_byte_arr.getvalue()

                # Create PIL image copy for screenshot data
                img_copy = image.copy()

            # Create screenshot data
            screenshot_data = ScreenshotData(
                image=img_copy,
                image_data=image_bytes,  # For backward compatibility
                coordinates=(0, 0, width, height),
                timestamp=None,
            )

            logger.debug(f"Loaded image file: {file_path} ({width}x{height})")
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

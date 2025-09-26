"""
Tests for Enhanced Drag & Drop Support (URLs and more file types).

FEATURE: Drop Zone Support (Drag & Drop Files/URLs)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urlparse

# CRITICAL: Import paths will fail until implementation exists
from src.ui.drag_drop_handler import DragDropHandler  # Base class
from src.ui.enhanced_drag_drop_handler import (
    EnhancedDragDropHandler,
    DropZone,
    SupportedFileType,
    URLProcessor
)
from src.services.url_processor_service import URLProcessorService


class TestSupportedFileType:
    """Test file type support enumeration."""

    def test_supported_file_types(self):
        """Test supported file type definitions."""
        # CRITICAL: Should support all planned file types
        expected_extensions = {
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",  # Images
            ".pdf",  # Documents
            ".txt",  # Text files
            ".url", ".webloc"  # Web bookmarks
        }

        supported = SupportedFileType.get_all_extensions()

        for ext in expected_extensions:
            assert ext in supported

    def test_file_type_validation(self):
        """Test file type validation."""
        assert SupportedFileType.is_supported(".png") is True
        assert SupportedFileType.is_supported(".jpg") is True
        assert SupportedFileType.is_supported(".pdf") is True
        assert SupportedFileType.is_supported(".txt") is True

        # Unsupported types
        assert SupportedFileType.is_supported(".exe") is False
        assert SupportedFileType.is_supported(".docx") is False

    def test_file_type_categories(self):
        """Test file type categorization."""
        assert SupportedFileType.get_category(".png") == "image"
        assert SupportedFileType.get_category(".pdf") == "document"
        assert SupportedFileType.get_category(".txt") == "text"
        assert SupportedFileType.get_category(".url") == "web_bookmark"


class TestURLProcessor:
    """Test URL processing functionality."""

    def test_url_validation(self):
        """Test URL validation."""
        processor = URLProcessor()

        # Valid URLs
        assert processor.is_valid_url("https://example.com") is True
        assert processor.is_valid_url("http://example.com/image.png") is True
        assert processor.is_valid_url("ftp://files.example.com") is True

        # Invalid URLs
        assert processor.is_valid_url("not-a-url") is False
        assert processor.is_valid_url("") is False
        assert processor.is_valid_url("javascript:alert('xss')") is False

    def test_image_url_detection(self):
        """Test detection of image URLs."""
        processor = URLProcessor()

        # Direct image URLs
        assert processor.is_image_url("https://example.com/image.png") is True
        assert processor.is_image_url("https://example.com/photo.jpg") is True
        assert processor.is_image_url("https://example.com/pic.gif") is True

        # Non-image URLs
        assert processor.is_image_url("https://example.com/page.html") is False
        assert processor.is_image_url("https://example.com/document.pdf") is False

    def test_url_content_type_detection(self):
        """Test content type detection from URL headers."""
        processor = URLProcessor()

        with patch('requests.head') as mock_head:
            # Mock response with image content type
            mock_response = Mock()
            mock_response.headers = {'content-type': 'image/jpeg'}
            mock_response.status_code = 200
            mock_head.return_value = mock_response

            content_type = processor.get_content_type("https://example.com/unknown")

            assert content_type == "image/jpeg"
            mock_head.assert_called_once()

    def test_url_security_validation(self):
        """Test URL security validation."""
        processor = URLProcessor()

        # Safe URLs
        assert processor.is_safe_url("https://imgur.com/image.png") is True
        assert processor.is_safe_url("https://github.com/user/repo/blob/main/screenshot.png") is True

        # Potentially unsafe URLs
        assert processor.is_safe_url("javascript:alert('xss')") is False
        assert processor.is_safe_url("data:text/html,<script>alert('xss')</script>") is False
        assert processor.is_safe_url("file:///etc/passwd") is False


class TestDropZone:
    """Test drop zone UI component."""

    @pytest.fixture
    def mock_drop_zone_window(self):
        """Mock drop zone window."""
        with patch('tkinter.Toplevel') as mock_toplevel:
            window = Mock()
            mock_toplevel.return_value = window
            return window

    def test_drop_zone_creation(self, mock_drop_zone_window):
        """Test drop zone creation and initialization."""
        drop_zone = DropZone(title="Drop files here")

        assert drop_zone.title == "Drop files here"
        assert drop_zone.is_visible is False
        assert hasattr(drop_zone, 'supported_types')

    def test_drop_zone_show_hide(self, mock_drop_zone_window):
        """Test showing and hiding drop zone."""
        drop_zone = DropZone("Test Zone")

        # Show drop zone
        drop_zone.show()
        assert drop_zone.is_visible is True

        # Hide drop zone
        drop_zone.hide()
        assert drop_zone.is_visible is False

    def test_drop_zone_drag_enter_feedback(self, mock_drop_zone_window):
        """Test visual feedback when drag enters zone."""
        drop_zone = DropZone("Test Zone")
        drop_zone.window = mock_drop_zone_window

        # Mock drag enter event
        drag_event = Mock()
        drop_zone._on_drag_enter(drag_event)

        # Should provide visual feedback
        drop_zone.window.configure.assert_called()

    def test_drop_zone_size_and_position(self, mock_drop_zone_window):
        """Test drop zone positioning and sizing."""
        drop_zone = DropZone("Test Zone", width=400, height=300)

        drop_zone.show()

        # Should set window geometry
        geometry_call = drop_zone.window.geometry.call_args[0][0] if drop_zone.window.geometry.called else None
        if geometry_call:
            assert "400x300" in geometry_call


class TestEnhancedDragDropHandler:
    """Test suite for EnhancedDragDropHandler."""

    @pytest.fixture
    def mock_url_processor_service(self):
        """Mock URLProcessorService dependency."""
        return Mock(spec=URLProcessorService)

    @pytest.fixture
    def enhanced_handler(self, mock_url_processor_service):
        """Create EnhancedDragDropHandler with mocked dependencies."""
        with patch('src.services.container') as mock_container:
            mock_container.get.return_value = mock_url_processor_service
            return EnhancedDragDropHandler()

    # CRITICAL: Handler initialization and file type support
    def test_handler_initialization_extends_base(self, enhanced_handler):
        """Test handler properly extends base DragDropHandler."""
        # Should inherit from base handler
        assert isinstance(enhanced_handler, DragDropHandler)

        # Should extend supported formats
        base_formats = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
        extended_formats = {".pdf", ".txt", ".url", ".webloc"}

        for fmt in base_formats | extended_formats:
            assert fmt in enhanced_handler.supported_formats

    def test_enhanced_file_type_detection(self, enhanced_handler):
        """Test enhanced file type detection."""
        test_cases = [
            ("image.png", "image"),
            ("document.pdf", "document"),
            ("readme.txt", "text"),
            ("bookmark.url", "web_bookmark"),
            ("unsupported.exe", None)
        ]

        for filename, expected_type in test_cases:
            file_type = enhanced_handler._detect_file_type(filename)
            assert file_type == expected_type

    # CRITICAL: URL drag and drop functionality
    def test_handle_url_drop_image_url(self, enhanced_handler, mock_url_processor_service):
        """Test handling of image URL drops."""
        image_url = "https://example.com/screenshot.png"

        # Mock URL processor to return image data
        mock_image = Mock()
        mock_url_processor_service.fetch_image.return_value = mock_image

        with patch.object(enhanced_handler, 'process_image') as mock_process:
            enhanced_handler.handle_url_drop(image_url)

            # Should fetch and process image
            mock_url_processor_service.fetch_image.assert_called_once_with(image_url)
            mock_process.assert_called_once_with(mock_image)

    def test_handle_url_drop_non_image(self, enhanced_handler):
        """Test handling of non-image URL drops."""
        webpage_url = "https://example.com/page.html"

        with patch.object(enhanced_handler, '_show_url_not_supported_message') as mock_message:
            enhanced_handler.handle_url_drop(webpage_url)

            # Should show not supported message
            mock_message.assert_called_once()

    def test_url_validation_before_processing(self, enhanced_handler):
        """Test URL validation before processing."""
        invalid_urls = [
            "javascript:alert('xss')",
            "not-a-url",
            "",
            "file:///etc/passwd"
        ]

        for invalid_url in invalid_urls:
            with patch.object(enhanced_handler, '_show_invalid_url_message') as mock_message:
                enhanced_handler.handle_url_drop(invalid_url)

                mock_message.assert_called_once()

    # CRITICAL: PDF file processing
    def test_handle_pdf_drop(self, enhanced_handler):
        """Test handling of PDF file drops."""
        pdf_path = Path("test_document.pdf")

        with patch('src.core.pdf_processor.PDFProcessor') as mock_pdf_processor:
            processor = mock_pdf_processor.return_value
            processor.extract_text_pages.return_value = ["Page 1 text", "Page 2 text"]

            with patch.object(enhanced_handler, 'process_text_content') as mock_process_text:
                enhanced_handler.handle_file_drop(str(pdf_path))

                # Should extract and process PDF text
                processor.extract_text_pages.assert_called_once_with(str(pdf_path))
                mock_process_text.assert_called()

    def test_pdf_processing_error_handling(self, enhanced_handler):
        """Test error handling for PDF processing."""
        pdf_path = Path("corrupted.pdf")

        with patch('src.core.pdf_processor.PDFProcessor') as mock_pdf_processor:
            processor = mock_pdf_processor.return_value
            processor.extract_text_pages.side_effect = Exception("PDF parsing failed")

            with patch.object(enhanced_handler, '_show_pdf_error_message') as mock_error:
                enhanced_handler.handle_file_drop(str(pdf_path))

                mock_error.assert_called_once()

    # CRITICAL: Text file processing
    def test_handle_text_file_drop(self, enhanced_handler):
        """Test handling of text file drops."""
        text_content = "This is sample text content for translation."

        with patch('builtins.open', mock_open(read_data=text_content)):
            with patch.object(enhanced_handler, 'process_text_content') as mock_process:
                enhanced_handler.handle_file_drop("sample.txt")

                # Should read and process text content
                mock_process.assert_called_once_with(text_content)

    def test_text_file_encoding_handling(self, enhanced_handler):
        """Test handling of different text file encodings."""
        # Test UTF-8 encoding
        utf8_content = "Текст на русском языке"

        with patch('builtins.open', mock_open(read_data=utf8_content.encode('utf-8'))):
            with patch.object(enhanced_handler, 'process_text_content') as mock_process:
                enhanced_handler.handle_file_drop("utf8_text.txt")

                mock_process.assert_called_once()

    # CRITICAL: Web bookmark processing
    def test_handle_web_bookmark_drop(self, enhanced_handler):
        """Test handling of web bookmark files (.url, .webloc)."""
        # Windows .url file content
        url_file_content = """[InternetShortcut]
URL=https://example.com/screenshot.png
"""

        with patch('builtins.open', mock_open(read_data=url_file_content)):
            with patch.object(enhanced_handler, 'handle_url_drop') as mock_handle_url:
                enhanced_handler.handle_file_drop("bookmark.url")

                # Should extract URL and handle as URL drop
                mock_handle_url.assert_called_once_with("https://example.com/screenshot.png")

    def test_handle_macos_webloc_bookmark(self, enhanced_handler):
        """Test handling of macOS .webloc bookmark files."""
        # macOS .webloc file content (plist format)
        webloc_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>URL</key>
    <string>https://example.com/image.jpg</string>
</dict>
</plist>"""

        with patch('builtins.open', mock_open(read_data=webloc_content)):
            with patch('plistlib.load') as mock_plist:
                mock_plist.return_value = {'URL': 'https://example.com/image.jpg'}

                with patch.object(enhanced_handler, 'handle_url_drop') as mock_handle_url:
                    enhanced_handler.handle_file_drop("bookmark.webloc")

                    mock_handle_url.assert_called_once_with("https://example.com/image.jpg")

    # CRITICAL: Multiple file drops
    def test_handle_multiple_file_drops(self, enhanced_handler):
        """Test handling multiple files dropped simultaneously."""
        file_paths = [
            "image1.png",
            "image2.jpg",
            "document.pdf",
            "text.txt"
        ]

        with patch.object(enhanced_handler, 'handle_file_drop') as mock_handle_single:
            enhanced_handler.handle_multiple_drops(file_paths)

            # Should process each file
            assert mock_handle_single.call_count == len(file_paths)

    def test_mixed_files_and_urls_drop(self, enhanced_handler):
        """Test handling mixed files and URLs in single drop."""
        mixed_drops = [
            "local_image.png",
            "https://example.com/remote_image.jpg",
            "document.pdf"
        ]

        with patch.object(enhanced_handler, 'handle_file_drop') as mock_file:
            with patch.object(enhanced_handler, 'handle_url_drop') as mock_url:
                enhanced_handler.handle_mixed_drops(mixed_drops)

                # Should route each item to appropriate handler
                mock_file.assert_any_call("local_image.png")
                mock_file.assert_any_call("document.pdf")
                mock_url.assert_any_call("https://example.com/remote_image.jpg")

    # CRITICAL: Error handling and validation
    def test_large_file_size_validation(self, enhanced_handler):
        """Test validation of large file sizes."""
        large_file_path = "huge_image.png"

        with patch('os.path.getsize', return_value=100 * 1024 * 1024):  # 100MB file
            with patch.object(enhanced_handler, '_show_file_too_large_message') as mock_message:
                enhanced_handler.handle_file_drop(large_file_path)

                # Should show file too large message
                mock_message.assert_called_once()

    def test_file_access_permission_error(self, enhanced_handler):
        """Test handling of file access permission errors."""
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            with patch.object(enhanced_handler, '_show_permission_error_message') as mock_message:
                enhanced_handler.handle_file_drop("protected_file.txt")

                mock_message.assert_called_once()

    def test_corrupted_file_handling(self, enhanced_handler):
        """Test handling of corrupted or unreadable files."""
        with patch('builtins.open', side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")):
            with patch.object(enhanced_handler, '_show_corrupted_file_message') as mock_message:
                enhanced_handler.handle_file_drop("corrupted.txt")

                mock_message.assert_called_once()

    # CRITICAL: Performance with multiple/large files
    def test_performance_multiple_images(self, enhanced_handler):
        """Test performance with multiple image files."""
        image_paths = [f"image_{i}.png" for i in range(20)]

        with patch.object(enhanced_handler, 'process_image'):
            with patch('PIL.Image.open', return_value=Mock()):
                import time
                start_time = time.time()

                enhanced_handler.handle_multiple_drops(image_paths)

                processing_time = time.time() - start_time

                # CRITICAL: Should process 20 images under 5 seconds
                assert processing_time < 5.0

    def test_async_url_processing(self, enhanced_handler, mock_url_processor_service):
        """Test asynchronous URL processing for responsiveness."""
        image_urls = [f"https://example.com/image_{i}.png" for i in range(10)]

        with patch('asyncio.create_task') as mock_create_task:
            enhanced_handler.handle_multiple_url_drops(image_urls)

            # Should create async tasks for URL processing
            assert mock_create_task.call_count == len(image_urls)

    # CRITICAL: Integration with existing systems
    def test_integration_with_translation_workflow(self, enhanced_handler):
        """Test integration with translation workflow."""
        with patch('src.core.coordinators.translation_workflow.TranslationWorkflow') as mock_workflow:
            workflow = mock_workflow.return_value

            # Process text content
            enhanced_handler.process_text_content("Sample text for translation")

            # Should trigger translation workflow
            workflow.process_text_input.assert_called_once_with("Sample text for translation")

    def test_integration_with_ocr_engine(self, enhanced_handler):
        """Test integration with OCR engine for image processing."""
        with patch('src.core.ocr_engine.OCREngine') as mock_ocr:
            ocr_engine = mock_ocr.return_value
            ocr_engine.extract_text.return_value = "Extracted text from image"

            mock_image = Mock()
            enhanced_handler.process_image(mock_image)

            # Should use OCR to extract text from image
            ocr_engine.extract_text.assert_called_once_with(mock_image)

    # CRITICAL: Drop zone integration
    def test_drop_zone_activation_on_drag_over(self, enhanced_handler):
        """Test drop zone appears during drag over operations."""
        with patch.object(enhanced_handler, '_create_drop_zone') as mock_create:
            drop_zone = Mock()
            mock_create.return_value = drop_zone

            # Simulate drag over main window
            enhanced_handler.on_drag_over_main_window()

            # Should show drop zone
            drop_zone.show.assert_called_once()

    def test_drop_zone_visual_feedback(self, enhanced_handler):
        """Test visual feedback in drop zone."""
        drop_zone = DropZone("Drop files here")

        with patch.object(drop_zone, 'update_feedback_message') as mock_update:
            # Simulate drag enter with supported file
            enhanced_handler._update_drop_zone_feedback(drop_zone, ["image.png"])

            # Should show positive feedback
            mock_update.assert_called_with("✅ Ready to process image", "success")

            # Simulate drag enter with unsupported file
            enhanced_handler._update_drop_zone_feedback(drop_zone, ["unsupported.exe"])

            # Should show negative feedback
            mock_update.assert_called_with("❌ Unsupported file type", "error")


class TestURLProcessorService:
    """Test URLProcessorService integration."""

    @pytest.fixture
    def url_processor_service(self):
        """Create URLProcessorService instance."""
        return URLProcessorService()

    # CRITICAL: Image fetching from URLs
    def test_fetch_image_from_url(self, url_processor_service):
        """Test fetching image from URL."""
        image_url = "https://example.com/test.png"

        with patch('requests.get') as mock_get:
            # Mock successful image response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'image/png'}
            mock_response.content = b'fake_png_data'
            mock_get.return_value = mock_response

            with patch('PIL.Image.open') as mock_image_open:
                mock_image = Mock()
                mock_image_open.return_value = mock_image

                result = url_processor_service.fetch_image(image_url)

                assert result == mock_image
                mock_get.assert_called_once_with(image_url, timeout=10)

    def test_fetch_image_timeout_handling(self, url_processor_service):
        """Test timeout handling for slow URLs."""
        slow_url = "https://slow-server.com/image.png"

        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

            with pytest.raises(Exception, match="timeout"):
                url_processor_service.fetch_image(slow_url)

    def test_fetch_image_invalid_content_type(self, url_processor_service):
        """Test handling of non-image content types."""
        html_url = "https://example.com/page.html"

        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'text/html'}
            mock_get.return_value = mock_response

            with pytest.raises(ValueError, match="not an image"):
                url_processor_service.fetch_image(html_url)

    # CRITICAL: Security validation
    def test_url_security_filtering(self, url_processor_service):
        """Test security filtering of malicious URLs."""
        malicious_urls = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "file:///etc/passwd"
        ]

        for url in malicious_urls:
            with pytest.raises(SecurityError, match="Unsafe URL"):
                url_processor_service.fetch_image(url)

    def test_circuit_breaker_integration(self, url_processor_service):
        """Test circuit breaker integration for URL processing."""
        failing_url = "https://unreliable-server.com/image.png"

        with patch('src.services.circuit_breaker.CircuitBreaker') as mock_breaker:
            breaker = mock_breaker.return_value
            breaker.call.side_effect = Exception("Circuit breaker open")

            with pytest.raises(Exception, match="Circuit breaker open"):
                url_processor_service.fetch_image(failing_url)


# CRITICAL: Integration tests
class TestEnhancedDragDropIntegration:
    """Integration tests for complete enhanced drag & drop workflow."""

    def test_full_image_url_workflow(self):
        """Test complete workflow from URL drop to translation."""
        # This test will fail until full integration exists

        with patch('src.ui.enhanced_drag_drop_handler.EnhancedDragDropHandler') as mock_handler:
            with patch('src.services.url_processor_service.URLProcessorService') as mock_url_service:
                with patch('src.core.coordinators.translation_workflow.TranslationWorkflow') as mock_workflow:

                    handler = mock_handler.return_value
                    url_service = mock_url_service.return_value
                    workflow = mock_workflow.return_value

                    # Mock successful image fetch and OCR
                    mock_image = Mock()
                    url_service.fetch_image.return_value = mock_image
                    workflow.process_image.return_value = Mock(translated_text="Translated text")

                    # Simulate URL drop
                    image_url = "https://example.com/screenshot.png"
                    handler.handle_url_drop(image_url)

                    # Should complete full workflow
                    url_service.fetch_image.assert_called_with(image_url)
                    workflow.process_image.assert_called_with(mock_image)

    def test_pdf_text_extraction_workflow(self):
        """Test complete PDF processing workflow."""
        with patch('src.core.pdf_processor.PDFProcessor') as mock_pdf:
            with patch('src.core.coordinators.translation_workflow.TranslationWorkflow') as mock_workflow:

                pdf_processor = mock_pdf.return_value
                workflow = mock_workflow.return_value

                # Mock PDF text extraction
                pdf_processor.extract_text_pages.return_value = ["Page 1 text", "Page 2 text"]

                handler = EnhancedDragDropHandler()
                handler.handle_file_drop("document.pdf")

                # Should extract text and process for translation
                pdf_processor.extract_text_pages.assert_called_once()
                workflow.process_text_input.assert_called()
"""
Enhanced Drag & Drop Handler with URL support and multiple file types.

This module extends the existing drag-drop functionality to support URLs,
multiple file formats, and enhanced security validation.
"""

import tkinter as tk
import asyncio
import re
import requests
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Set, Optional, Callable, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from io import BytesIO

from PIL import Image
from src.services.circuit_breaker import get_circuit_breaker_manager
from src.services.url_processor_service import URLProcessorService
from src.utils.logger import logger


class DropZoneType(Enum):
    """Types of drop zones."""
    IMAGE = "image"
    TEXT = "text"
    URL = "url"
    MIXED = "mixed"


class SupportedFileType(Enum):
    """Supported file types for drag & drop."""
    # Image files
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    GIF = "gif"
    BMP = "bmp"
    WEBP = "webp"

    # Document files
    PDF = "pdf"
    TXT = "txt"

    # Web content
    HTML = "html"
    HTM = "htm"


@dataclass
class DropZone:
    """Represents a drop zone configuration."""

    zone_type: DropZoneType
    supported_types: Set[SupportedFileType]
    callback: Callable[[Any], None]
    security_level: int = 2  # 1=Low, 2=Medium, 3=High
    max_file_size: int = 10 * 1024 * 1024  # 10MB default
    allow_urls: bool = True
    visual_feedback: bool = True


class EnhancedDragDropHandler:
    """Enhanced drag & drop handler with URL and multi-format support."""

    def __init__(self, widget: tk.Widget, url_processor: Optional[URLProcessorService] = None):
        """Initialize the enhanced drag-drop handler.

        Args:
            widget: Tkinter widget to enable drag-drop on
            url_processor: Optional URL processor service
        """
        self.widget = widget
        self.url_processor = url_processor or URLProcessorService()
        self.circuit_breaker = get_circuit_breaker_manager().create_circuit_breaker("drag_drop")

        # Drop zones configuration
        self.drop_zones: Dict[str, DropZone] = {}
        self.active_drop_zone: Optional[str] = None

        # Supported formats with MIME types
        self.supported_formats: Dict[SupportedFileType, List[str]] = {
            SupportedFileType.PNG: ["image/png"],
            SupportedFileType.JPG: ["image/jpeg"],
            SupportedFileType.JPEG: ["image/jpeg"],
            SupportedFileType.GIF: ["image/gif"],
            SupportedFileType.BMP: ["image/bmp"],
            SupportedFileType.WEBP: ["image/webp"],
            SupportedFileType.PDF: ["application/pdf"],
            SupportedFileType.TXT: ["text/plain"],
            SupportedFileType.HTML: ["text/html"],
            SupportedFileType.HTM: ["text/html"],
        }

        # URL patterns for validation
        self.url_patterns = {
            "image": re.compile(r'.*\.(png|jpg|jpeg|gif|bmp|webp)(\?.*)?$', re.IGNORECASE),
            "general": re.compile(r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE)
        }

        # Security settings
        self.blocked_domains = {"localhost", "127.0.0.1", "0.0.0.0"}
        self.allowed_schemes = {"http", "https", "file"}

        # Performance tracking
        self.drop_statistics = {
            "total_drops": 0,
            "successful_drops": 0,
            "failed_drops": 0,
            "url_drops": 0,
            "file_drops": 0
        }

        self._setup_drag_drop()

        logger.info("EnhancedDragDropHandler initialized")

    def _setup_drag_drop(self) -> None:
        """Setup drag and drop functionality."""
        try:
            # Register for various data types
            self.widget.drop_target_register("DND_Files", "DND_Text")

            # Bind drag-drop events
            self.widget.dnd_bind("<<DropEnter>>", self._on_drop_enter)
            self.widget.dnd_bind("<<DropPosition>>", self._on_drop_position)
            self.widget.dnd_bind("<<DropLeave>>", self._on_drop_leave)
            self.widget.dnd_bind("<<Drop>>", self._on_drop)

            logger.debug("Drag-drop events bound successfully")

        except Exception as e:
            logger.warning(f"Native drag-drop not available, using fallback: {e}")
            self._setup_fallback_drag_drop()

    def _setup_fallback_drag_drop(self) -> None:
        """Setup fallback drag-drop using tkinter events."""
        # Bind mouse events for visual feedback
        self.widget.bind("<Button-1>", self._on_click)
        self.widget.bind("<B1-Motion>", self._on_drag)
        self.widget.bind("<ButtonRelease-1>", self._on_drop_release)

        # Bind keyboard shortcut for paste
        self.widget.bind("<Control-v>", self._on_paste)

    def add_drop_zone(
        self,
        name: str,
        zone_type: DropZoneType,
        callback: Callable[[Any], None],
        supported_types: Optional[Set[SupportedFileType]] = None,
        **kwargs
    ) -> None:
        """Add a new drop zone configuration.

        Args:
            name: Unique name for the drop zone
            zone_type: Type of drop zone
            callback: Function to call when items are dropped
            supported_types: Set of supported file types
            **kwargs: Additional drop zone options
        """
        if supported_types is None:
            # Default supported types based on zone type
            if zone_type == DropZoneType.IMAGE:
                supported_types = {
                    SupportedFileType.PNG, SupportedFileType.JPG,
                    SupportedFileType.JPEG, SupportedFileType.GIF,
                    SupportedFileType.BMP, SupportedFileType.WEBP
                }
            elif zone_type == DropZoneType.TEXT:
                supported_types = {SupportedFileType.TXT, SupportedFileType.PDF}
            elif zone_type == DropZoneType.URL:
                supported_types = set()  # URLs don't need file type restrictions
            else:  # MIXED
                supported_types = set(SupportedFileType)

        self.drop_zones[name] = DropZone(
            zone_type=zone_type,
            supported_types=supported_types,
            callback=callback,
            **kwargs
        )

        logger.debug(f"Added drop zone: {name} ({zone_type.value})")

    def set_active_drop_zone(self, name: str) -> bool:
        """Set the active drop zone.

        Args:
            name: Name of the drop zone to activate

        Returns:
            True if zone was set successfully
        """
        if name in self.drop_zones:
            self.active_drop_zone = name
            logger.debug(f"Active drop zone set to: {name}")
            return True
        else:
            logger.warning(f"Drop zone not found: {name}")
            return False

    async def handle_drop(self, data: Any) -> bool:
        """Handle dropped data.

        Args:
            data: Dropped data (files, URLs, text)

        Returns:
            True if handled successfully
        """
        if not self.active_drop_zone:
            logger.warning("No active drop zone configured")
            return False

        drop_zone = self.drop_zones[self.active_drop_zone]
        self.drop_statistics["total_drops"] += 1

        try:
            # Process the dropped data
            processed_data = await self.circuit_breaker.call(
                self._process_dropped_data,
                data,
                drop_zone
            )

            if processed_data is not None:
                # Execute callback
                drop_zone.callback(processed_data)
                self.drop_statistics["successful_drops"] += 1

                logger.info(f"Successfully processed drop: {type(data).__name__}")
                return True
            else:
                self.drop_statistics["failed_drops"] += 1
                return False

        except Exception as e:
            logger.error(f"Drop handling failed: {e}")
            self.drop_statistics["failed_drops"] += 1
            return False

    async def _process_dropped_data(self, data: Any, drop_zone: DropZone) -> Optional[Any]:
        """Process different types of dropped data.

        Args:
            data: Raw dropped data
            drop_zone: Target drop zone configuration

        Returns:
            Processed data or None if processing failed
        """
        # Handle different data types
        if isinstance(data, str):
            return await self._process_string_data(data, drop_zone)
        elif isinstance(data, list):
            return await self._process_list_data(data, drop_zone)
        elif hasattr(data, 'string'):  # tkinter event data
            return await self._process_string_data(data.string, drop_zone)
        else:
            logger.warning(f"Unsupported data type: {type(data)}")
            return None

    async def _process_string_data(self, data: str, drop_zone: DropZone) -> Optional[Any]:
        """Process string data (URLs, file paths, text).

        Args:
            data: String data
            drop_zone: Target drop zone

        Returns:
            Processed data
        """
        data = data.strip()

        # Check if it's a URL
        if self._is_url(data):
            if drop_zone.allow_urls:
                return await self._process_url(data, drop_zone)
            else:
                logger.warning("URLs not allowed in this drop zone")
                return None

        # Check if it's a file path
        elif self._is_file_path(data):
            return await self._process_file_path(data, drop_zone)

        # Handle as plain text
        elif drop_zone.zone_type in [DropZoneType.TEXT, DropZoneType.MIXED]:
            return {"type": "text", "content": data}

        else:
            logger.warning(f"Unsupported string data for zone type: {drop_zone.zone_type}")
            return None

    async def _process_list_data(self, data: List, drop_zone: DropZone) -> Optional[List]:
        """Process list of dropped items.

        Args:
            data: List of items
            drop_zone: Target drop zone

        Returns:
            List of processed items
        """
        processed_items = []

        for item in data:
            processed_item = await self._process_string_data(str(item), drop_zone)
            if processed_item:
                processed_items.append(processed_item)

        return processed_items if processed_items else None

    async def _process_url(self, url: str, drop_zone: DropZone) -> Optional[Dict]:
        """Process a dropped URL.

        Args:
            url: URL to process
            drop_zone: Target drop zone

        Returns:
            Processed URL data
        """
        # Security validation
        if not await self._validate_url_security(url, drop_zone.security_level):
            logger.warning(f"URL failed security validation: {url}")
            return None

        self.drop_statistics["url_drops"] += 1

        # Determine URL type
        if self.url_patterns["image"].match(url):
            # Process as image URL
            if drop_zone.zone_type in [DropZoneType.IMAGE, DropZoneType.MIXED]:
                image_data = await self.url_processor.fetch_image(url)
                if image_data:
                    return {
                        "type": "image",
                        "source": "url",
                        "url": url,
                        "image": image_data
                    }
            else:
                logger.warning("Image URL not supported in this drop zone")
                return None

        else:
            # Process as general URL
            if drop_zone.allow_urls:
                return {
                    "type": "url",
                    "url": url,
                    "parsed": urlparse(url)
                }

        return None

    async def _process_file_path(self, file_path: str, drop_zone: DropZone) -> Optional[Dict]:
        """Process a dropped file path.

        Args:
            file_path: Path to file
            drop_zone: Target drop zone

        Returns:
            Processed file data
        """
        path = Path(file_path)

        # Validate file exists and is accessible
        if not path.exists() or not path.is_file():
            logger.warning(f"File not found or not accessible: {file_path}")
            return None

        # Check file size
        file_size = path.stat().st_size
        if file_size > drop_zone.max_file_size:
            logger.warning(f"File too large: {file_size} bytes (max: {drop_zone.max_file_size})")
            return None

        # Get file type
        file_ext = path.suffix.lower().lstrip('.')
        try:
            file_type = SupportedFileType(file_ext)
        except ValueError:
            logger.warning(f"Unsupported file type: {file_ext}")
            return None

        # Check if file type is supported by drop zone
        if file_type not in drop_zone.supported_types:
            logger.warning(f"File type {file_ext} not supported in this drop zone")
            return None

        self.drop_statistics["file_drops"] += 1

        # Process based on file type
        if file_type in [SupportedFileType.PNG, SupportedFileType.JPG,
                        SupportedFileType.JPEG, SupportedFileType.GIF,
                        SupportedFileType.BMP, SupportedFileType.WEBP]:
            # Process as image
            try:
                image = Image.open(path)
                return {
                    "type": "image",
                    "source": "file",
                    "path": str(path),
                    "image": image
                }
            except Exception as e:
                logger.error(f"Failed to load image {path}: {e}")
                return None

        elif file_type == SupportedFileType.TXT:
            # Process as text
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {
                    "type": "text",
                    "source": "file",
                    "path": str(path),
                    "content": content
                }
            except Exception as e:
                logger.error(f"Failed to read text file {path}: {e}")
                return None

        elif file_type == SupportedFileType.PDF:
            # Process as PDF
            return {
                "type": "pdf",
                "source": "file",
                "path": str(path),
                "size": file_size
            }

        else:
            # Generic file
            return {
                "type": "file",
                "path": str(path),
                "extension": file_ext,
                "size": file_size
            }

    async def _validate_url_security(self, url: str, security_level: int) -> bool:
        """Validate URL security based on security level.

        Args:
            url: URL to validate
            security_level: Security level (1=Low, 2=Medium, 3=High)

        Returns:
            True if URL passes security checks
        """
        try:
            parsed = urlparse(url)

            # Check scheme
            if parsed.scheme not in self.allowed_schemes:
                return False

            # Check for blocked domains
            if parsed.netloc.lower() in self.blocked_domains:
                return False

            # Additional checks based on security level
            if security_level >= 2:
                # Medium security: HTTPS preferred
                if parsed.scheme != "https" and parsed.netloc not in ["localhost", "127.0.0.1"]:
                    logger.warning(f"Non-HTTPS URL at medium security level: {url}")

            if security_level >= 3:
                # High security: Only HTTPS allowed
                if parsed.scheme != "https":
                    return False

            return True

        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return False

    def _is_url(self, text: str) -> bool:
        """Check if text is a URL."""
        return bool(self.url_patterns["general"].match(text))

    def _is_file_path(self, text: str) -> bool:
        """Check if text is a file path."""
        try:
            path = Path(text)
            return path.exists() and path.is_file()
        except Exception:
            return False

    # Event handlers
    def _on_drop_enter(self, event) -> str:
        """Handle drop enter event."""
        if self.active_drop_zone:
            drop_zone = self.drop_zones[self.active_drop_zone]
            if drop_zone.visual_feedback:
                self._show_drop_feedback("enter")
        return "copy"

    def _on_drop_position(self, event) -> str:
        """Handle drop position event."""
        return "copy"

    def _on_drop_leave(self, event) -> None:
        """Handle drop leave event."""
        self._hide_drop_feedback()

    def _on_drop(self, event) -> str:
        """Handle drop event."""
        self._hide_drop_feedback()

        # Process the drop asynchronously
        asyncio.create_task(self.handle_drop(event.data))

        return "copy"

    def _on_click(self, event) -> None:
        """Handle click event (fallback)."""
        pass

    def _on_drag(self, event) -> None:
        """Handle drag event (fallback)."""
        pass

    def _on_drop_release(self, event) -> None:
        """Handle drop release event (fallback)."""
        pass

    def _on_paste(self, event) -> None:
        """Handle paste event (Ctrl+V fallback)."""
        try:
            # Get clipboard content
            clipboard_data = self.widget.selection_get(selection="CLIPBOARD")
            asyncio.create_task(self.handle_drop(clipboard_data))
        except Exception as e:
            logger.debug(f"Paste operation failed: {e}")

    def _show_drop_feedback(self, feedback_type: str) -> None:
        """Show visual feedback for drop operations."""
        # This would typically change the widget appearance
        # Implementation depends on the specific widget being used
        pass

    def _hide_drop_feedback(self) -> None:
        """Hide drop feedback."""
        # Reset widget appearance
        pass

    # Public API methods
    def enable_drag_drop(self, enable: bool = True) -> None:
        """Enable or disable drag-drop functionality."""
        if enable:
            self.widget.configure(state="normal")
        else:
            self.widget.configure(state="disabled")

        logger.debug(f"Drag-drop {'enabled' if enable else 'disabled'}")

    def clear_drop_zones(self) -> None:
        """Clear all drop zones."""
        self.drop_zones.clear()
        self.active_drop_zone = None
        logger.debug("All drop zones cleared")

    def get_drop_statistics(self) -> Dict[str, Any]:
        """Get drop operation statistics."""
        stats = self.drop_statistics.copy()

        if stats["total_drops"] > 0:
            stats["success_rate"] = stats["successful_drops"] / stats["total_drops"]
        else:
            stats["success_rate"] = 0.0

        return stats

    def set_security_settings(
        self,
        blocked_domains: Optional[Set[str]] = None,
        allowed_schemes: Optional[Set[str]] = None
    ) -> None:
        """Update security settings.

        Args:
            blocked_domains: Set of domains to block
            allowed_schemes: Set of allowed URL schemes
        """
        if blocked_domains is not None:
            self.blocked_domains = blocked_domains

        if allowed_schemes is not None:
            self.allowed_schemes = allowed_schemes

        logger.debug("Security settings updated")

    def add_supported_format(
        self,
        file_type: SupportedFileType,
        mime_types: List[str]
    ) -> None:
        """Add support for a new file format.

        Args:
            file_type: File type enum
            mime_types: List of MIME types for this format
        """
        self.supported_formats[file_type] = mime_types
        logger.debug(f"Added support for {file_type.value}: {mime_types}")

    def validate_dropped_content(
        self,
        content: Any,
        drop_zone_name: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate dropped content against drop zone requirements.

        Args:
            content: Content to validate
            drop_zone_name: Name of target drop zone

        Returns:
            Tuple of (is_valid, error_message)
        """
        if drop_zone_name not in self.drop_zones:
            return False, f"Drop zone '{drop_zone_name}' not found"

        drop_zone = self.drop_zones[drop_zone_name]

        # Perform validation based on drop zone configuration
        # This is a simplified implementation
        if isinstance(content, dict):
            content_type = content.get("type")

            if drop_zone.zone_type == DropZoneType.IMAGE and content_type != "image":
                return False, "Only images are allowed in this drop zone"

            if drop_zone.zone_type == DropZoneType.TEXT and content_type != "text":
                return False, "Only text content is allowed in this drop zone"

        return True, None
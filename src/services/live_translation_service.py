"""
Live Translation Service for continuous screen monitoring and translation.

This service provides continuous screen capture with change detection,
automatically translating text when significant changes are detected.
"""

import asyncio
import hashlib
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from PIL import Image, ImageChops
from src.services.circuit_breaker import get_circuit_breaker_manager
from src.utils.logger import logger


class CaptureMode(Enum):
    """Live capture modes."""
    REGION = "region"
    WINDOW = "window"
    FULLSCREEN = "fullscreen"


@dataclass
class CaptureRegion:
    """Defines a screen region for capture."""

    x: int
    y: int
    width: int
    height: int
    name: str = "default"
    active: bool = True

    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """Get region bounds as (left, top, right, bottom)."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    @property
    def area(self) -> int:
        """Get region area in pixels."""
        return self.width * self.height


@dataclass
class LiveTranslationConfig:
    """Configuration for live translation service."""

    fps: float = 2.0
    max_concurrent_translations: int = 3
    change_threshold: float = 5.0
    capture_mode: CaptureMode = CaptureMode.REGION
    auto_start: bool = False
    buffer_size: int = 100


@dataclass
class FrameBuffer:
    """Buffer for storing captured frames."""

    frames: List = None
    max_size: int = 100
    current_index: int = 0

    def __post_init__(self):
        if self.frames is None:
            self.frames = []

    def add_frame(self, frame) -> None:
        """Add a frame to the buffer."""
        if len(self.frames) >= self.max_size:
            self.frames.pop(0)
        self.frames.append(frame)

    def get_recent_frames(self, count: int = 10) -> List:
        """Get recent frames from buffer."""
        return self.frames[-count:]


@dataclass
class ChangeDetector:
    """Configuration for change detection algorithms."""

    method: str = "hash"  # "hash", "diff", "structural"
    threshold: float = 5.0  # Percentage change threshold
    min_change_area: int = 100  # Minimum changed area in pixels
    ignore_minor_changes: bool = True
    hash_precision: int = 8  # For hash-based detection
    diff_sensitivity: int = 30  # For pixel diff detection

    # Performance settings
    downscale_factor: float = 0.5  # Scale down for faster processing
    max_comparison_size: Tuple[int, int] = (800, 600)


@dataclass
class LiveFrame:
    """Represents a captured frame with metadata."""

    image: Image.Image
    timestamp: datetime
    region: CaptureRegion
    hash: str
    change_score: float = 0.0
    processed: bool = False
    translation_result: Optional[Any] = None


class LiveTranslationService:
    """Service for continuous live translation of screen regions."""

    def __init__(self, fps: float = 2.0, max_concurrent_translations: int = 3):
        """Initialize the live translation service.

        Args:
            fps: Frames per second for capture
            max_concurrent_translations: Maximum concurrent translation tasks
        """
        self.fps = fps
        self.max_concurrent_translations = max_concurrent_translations
        self.circuit_breaker = get_circuit_breaker_manager().create_circuit_breaker("live_translation")

        # Service state
        self.is_active = False
        self.is_paused = False

        # Capture configuration
        self.capture_regions: Dict[str, CaptureRegion] = {}
        self.active_regions: List[str] = []
        self.current_region: Optional[CaptureRegion] = None
        self.change_threshold: float = 5.0
        self.change_detector = ChangeDetector()

        # Frame management
        self.current_frames: Dict[str, LiveFrame] = {}
        self.previous_frames: Dict[str, LiveFrame] = {}
        self.frame_history: List[LiveFrame] = []
        self.max_history_size = 100

        # Processing queues
        self.translation_queue: asyncio.Queue = asyncio.Queue()
        self.processing_tasks: List[asyncio.Task] = []
        self.translation_semaphore = asyncio.Semaphore(max_concurrent_translations)

        # Performance tracking
        self.performance_stats = {
            "total_frames": 0,
            "frames_with_changes": 0,
            "translations_triggered": 0,
            "avg_processing_time": 0.0,
            "fps_actual": 0.0,
            "last_fps_calculation": datetime.now()
        }

        # Event callbacks
        self.change_callbacks: List[Callable[[LiveFrame], None]] = []
        self.translation_callbacks: List[Callable[[LiveFrame, Any], None]] = []

        logger.info(f"LiveTranslationService initialized (FPS: {fps}, Max concurrent: {max_concurrent_translations})")

    async def start_live_mode(self, regions: Optional[List[CaptureRegion]] = None) -> bool:
        """Start live translation monitoring.

        Args:
            regions: Optional list of regions to monitor

        Returns:
            True if started successfully
        """
        if self.is_active:
            logger.warning("Live translation is already active")
            return False

        try:
            # Setup regions
            if regions:
                for region in regions:
                    self.add_capture_region(region)

            if not self.capture_regions:
                logger.error("No capture regions configured")
                return False

            # Reset state
            self.is_active = True
            self.is_paused = False
            self.current_frames.clear()
            self.previous_frames.clear()

            # Start main capture loop
            capture_task = asyncio.create_task(self._capture_loop())
            self.processing_tasks.append(capture_task)

            # Start translation workers
            for i in range(self.max_concurrent_translations):
                worker_task = asyncio.create_task(self._translation_worker(f"worker_{i}"))
                self.processing_tasks.append(worker_task)

            logger.info(f"Live translation started with {len(self.capture_regions)} regions")
            return True

        except Exception as e:
            logger.error(f"Failed to start live translation: {e}")
            self.is_active = False
            return False

    async def stop_live_mode(self) -> None:
        """Stop live translation monitoring."""
        if not self.is_active:
            return

        try:
            self.is_active = False

            # Cancel all processing tasks
            for task in self.processing_tasks:
                task.cancel()

            # Wait for tasks to complete
            if self.processing_tasks:
                await asyncio.gather(*self.processing_tasks, return_exceptions=True)

            self.processing_tasks.clear()

            # Clear queues
            while not self.translation_queue.empty():
                try:
                    self.translation_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

            logger.info("Live translation stopped")

        except Exception as e:
            logger.error(f"Error stopping live translation: {e}")

    async def pause_live_mode(self, paused: bool = True) -> None:
        """Pause or resume live translation.

        Args:
            paused: True to pause, False to resume
        """
        if not self.is_active:
            logger.warning("Live translation is not active")
            return

        self.is_paused = paused
        logger.info(f"Live translation {'paused' if paused else 'resumed'}")

    async def _capture_loop(self) -> None:
        """Main capture loop for continuous monitoring."""
        frame_interval = 1.0 / self.fps
        last_frame_time = datetime.now()

        while self.is_active:
            try:
                loop_start = datetime.now()

                # Skip if paused
                if self.is_paused:
                    await asyncio.sleep(frame_interval)
                    continue

                # Capture frames for all active regions
                tasks = []
                for region_name in self.active_regions:
                    if region_name in self.capture_regions:
                        region = self.capture_regions[region_name]
                        task = asyncio.create_task(self._capture_region_frame(region))
                        tasks.append((region_name, task))

                # Wait for all captures to complete
                for region_name, task in tasks:
                    try:
                        frame = await task
                        if frame:
                            await self._process_captured_frame(region_name, frame)
                    except Exception as e:
                        logger.error(f"Error processing frame for region {region_name}: {e}")

                # Update performance statistics
                self._update_fps_stats(loop_start)

                # Sleep to maintain target FPS
                elapsed = (datetime.now() - loop_start).total_seconds()
                sleep_time = max(0, frame_interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

                self.performance_stats["total_frames"] += len(tasks)

            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                await asyncio.sleep(frame_interval)

    async def _capture_region_frame(self, region: CaptureRegion) -> Optional[LiveFrame]:
        """Capture a single frame from a region.

        Args:
            region: Region to capture

        Returns:
            Captured frame or None if failed
        """
        try:
            # This would integrate with the actual screenshot service
            # For now, this is a placeholder implementation
            screenshot = await self._take_screenshot(region)

            if screenshot:
                # Calculate frame hash for change detection
                frame_hash = self._calculate_image_hash(screenshot)

                return LiveFrame(
                    image=screenshot,
                    timestamp=datetime.now(),
                    region=region,
                    hash=frame_hash
                )

        except Exception as e:
            logger.debug(f"Failed to capture region {region.name}: {e}")

        return None

    async def _take_screenshot(self, region: CaptureRegion) -> Optional[Image.Image]:
        """Take a screenshot of the specified region.

        Args:
            region: Region to capture

        Returns:
            PIL Image or None if failed
        """
        # This is a placeholder - would integrate with the actual screenshot service
        # For testing, return a dummy image
        try:
            # Create a simple test image
            image = Image.new('RGB', (region.width, region.height), color='white')
            return image
        except Exception as e:
            logger.debug(f"Screenshot capture failed: {e}")
            return None

    async def _process_captured_frame(self, region_name: str, frame: LiveFrame) -> None:
        """Process a captured frame and check for changes.

        Args:
            region_name: Name of the capture region
            frame: Captured frame to process
        """
        try:
            # Get previous frame for comparison
            previous_frame = self.previous_frames.get(region_name)

            # Calculate change score
            if previous_frame:
                change_score = await self._detect_changes(frame, previous_frame)
                frame.change_score = change_score
            else:
                # First frame, assume it's a change
                frame.change_score = 100.0

            # Update frame storage
            self.previous_frames[region_name] = self.current_frames.get(region_name)
            self.current_frames[region_name] = frame

            # Add to history
            self.frame_history.append(frame)
            if len(self.frame_history) > self.max_history_size:
                self.frame_history.pop(0)

            # Check if change is significant enough
            if frame.change_score >= self.change_detector.threshold:
                self.performance_stats["frames_with_changes"] += 1

                # Notify change callbacks
                for callback in self.change_callbacks:
                    try:
                        callback(frame)
                    except Exception as e:
                        logger.error(f"Change callback error: {e}")

                # Queue for translation if needed
                if not self.translation_queue.full():
                    await self.translation_queue.put(frame)
                    self.performance_stats["translations_triggered"] += 1
                else:
                    logger.debug("Translation queue is full, skipping frame")

        except Exception as e:
            logger.error(f"Error processing frame: {e}")

    async def _detect_changes(self, current_frame: LiveFrame, previous_frame: LiveFrame) -> float:
        """Detect changes between two frames.

        Args:
            current_frame: Current frame
            previous_frame: Previous frame for comparison

        Returns:
            Change score as percentage (0-100)
        """
        try:
            detector = self.change_detector

            if detector.method == "hash":
                return await self._hash_based_change_detection(current_frame, previous_frame)
            elif detector.method == "diff":
                return await self._pixel_diff_change_detection(current_frame, previous_frame)
            elif detector.method == "structural":
                return await self._structural_change_detection(current_frame, previous_frame)
            else:
                logger.warning(f"Unknown change detection method: {detector.method}")
                return 0.0

        except Exception as e:
            logger.error(f"Change detection error: {e}")
            return 0.0

    async def _hash_based_change_detection(
        self,
        current_frame: LiveFrame,
        previous_frame: LiveFrame
    ) -> float:
        """Hash-based change detection (fast but less precise).

        Args:
            current_frame: Current frame
            previous_frame: Previous frame

        Returns:
            Change score percentage
        """
        if current_frame.hash == previous_frame.hash:
            return 0.0
        else:
            # Simple binary change detection
            return 100.0

    async def _pixel_diff_change_detection(
        self,
        current_frame: LiveFrame,
        previous_frame: LiveFrame
    ) -> float:
        """Pixel difference change detection.

        Args:
            current_frame: Current frame
            previous_frame: Previous frame

        Returns:
            Change score percentage
        """
        try:
            # Ensure images are same size
            if current_frame.image.size != previous_frame.image.size:
                return 100.0

            # Calculate pixel differences
            diff = ImageChops.difference(current_frame.image, previous_frame.image)

            # Convert to grayscale for analysis
            diff_gray = diff.convert('L')

            # Get pixel data
            pixel_data = list(diff_gray.getdata())
            total_pixels = len(pixel_data)

            # Count changed pixels above threshold
            threshold = self.change_detector.diff_sensitivity
            changed_pixels = sum(1 for pixel in pixel_data if pixel > threshold)

            # Calculate percentage
            change_percentage = (changed_pixels / total_pixels) * 100

            return min(change_percentage, 100.0)

        except Exception as e:
            logger.error(f"Pixel diff change detection error: {e}")
            return 0.0

    async def _structural_change_detection(
        self,
        current_frame: LiveFrame,
        previous_frame: LiveFrame
    ) -> float:
        """Structural change detection using image features.

        Args:
            current_frame: Current frame
            previous_frame: Previous frame

        Returns:
            Change score percentage
        """
        # This would implement more advanced structural comparison
        # For now, fallback to pixel diff
        return await self._pixel_diff_change_detection(current_frame, previous_frame)

    async def _translation_worker(self, worker_id: str) -> None:
        """Translation worker that processes frames from the queue.

        Args:
            worker_id: Unique worker identifier
        """
        logger.debug(f"Translation worker {worker_id} started")

        while self.is_active:
            try:
                # Get frame from queue with timeout
                try:
                    frame = await asyncio.wait_for(
                        self.translation_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Process translation with semaphore
                async with self.translation_semaphore:
                    translation_result = await self._translate_frame(frame)

                    if translation_result:
                        frame.translation_result = translation_result
                        frame.processed = True

                        # Notify translation callbacks
                        for callback in self.translation_callbacks:
                            try:
                                callback(frame, translation_result)
                            except Exception as e:
                                logger.error(f"Translation callback error: {e}")

                # Mark task as done
                self.translation_queue.task_done()

            except Exception as e:
                logger.error(f"Translation worker {worker_id} error: {e}")

        logger.debug(f"Translation worker {worker_id} stopped")

    async def _translate_frame(self, frame: LiveFrame) -> Optional[Any]:
        """Translate text found in a frame.

        Args:
            frame: Frame to translate

        Returns:
            Translation result or None if failed
        """
        try:
            # This would integrate with the actual OCR and translation services
            # For now, this is a placeholder
            await asyncio.sleep(0.1)  # Simulate processing time

            # Placeholder translation result
            return {
                "original_text": "Sample text",
                "translated_text": "Образец текста",
                "confidence": 0.95,
                "language_detected": "en",
                "processing_time": 0.1
            }

        except Exception as e:
            logger.error(f"Frame translation error: {e}")
            return None

    def _calculate_image_hash(self, image: Image.Image) -> str:
        """Calculate hash of an image for comparison.

        Args:
            image: PIL Image

        Returns:
            Image hash as hexadecimal string
        """
        try:
            # Resize to standard size for consistent hashing
            hash_size = self.change_detector.hash_precision
            resized = image.resize((hash_size, hash_size), Image.Resampling.LANCZOS)

            # Convert to grayscale
            grayscale = resized.convert('L')

            # Calculate average pixel value
            pixel_data = list(grayscale.getdata())
            avg_pixel = sum(pixel_data) / len(pixel_data)

            # Create binary hash
            hash_bits = ''.join('1' if pixel > avg_pixel else '0' for pixel in pixel_data)

            # Convert to hexadecimal
            hash_bytes = int(hash_bits, 2).to_bytes((len(hash_bits) + 7) // 8, byteorder='big')
            return hashlib.md5(hash_bytes).hexdigest()

        except Exception as e:
            logger.error(f"Image hash calculation error: {e}")
            return hashlib.md5(str(datetime.now()).encode()).hexdigest()

    def _update_fps_stats(self, loop_start: datetime) -> None:
        """Update FPS performance statistics.

        Args:
            loop_start: Time when the current loop iteration started
        """
        now = datetime.now()
        elapsed_since_last_calc = (now - self.performance_stats["last_fps_calculation"]).total_seconds()

        if elapsed_since_last_calc >= 5.0:  # Update every 5 seconds
            # Calculate actual FPS
            frames_in_period = self.performance_stats["total_frames"]
            if elapsed_since_last_calc > 0:
                actual_fps = frames_in_period / elapsed_since_last_calc
                self.performance_stats["fps_actual"] = actual_fps

            self.performance_stats["last_fps_calculation"] = now

    # Region management methods

    def add_capture_region(self, region: CaptureRegion) -> None:
        """Add a capture region.

        Args:
            region: Region to add
        """
        self.capture_regions[region.name] = region
        if region.active:
            if region.name not in self.active_regions:
                self.active_regions.append(region.name)

        logger.debug(f"Added capture region: {region.name}")

    def remove_capture_region(self, region_name: str) -> bool:
        """Remove a capture region.

        Args:
            region_name: Name of region to remove

        Returns:
            True if region was removed
        """
        if region_name in self.capture_regions:
            del self.capture_regions[region_name]

            if region_name in self.active_regions:
                self.active_regions.remove(region_name)

            # Clean up frame data
            self.current_frames.pop(region_name, None)
            self.previous_frames.pop(region_name, None)

            logger.debug(f"Removed capture region: {region_name}")
            return True

        return False

    def set_region_active(self, region_name: str, active: bool) -> bool:
        """Set a region's active state.

        Args:
            region_name: Name of region
            active: True to activate, False to deactivate

        Returns:
            True if state was changed
        """
        if region_name not in self.capture_regions:
            return False

        self.capture_regions[region_name].active = active

        if active and region_name not in self.active_regions:
            self.active_regions.append(region_name)
        elif not active and region_name in self.active_regions:
            self.active_regions.remove(region_name)

        logger.debug(f"Region {region_name} {'activated' if active else 'deactivated'}")
        return True

    # Callback management

    def add_change_callback(self, callback: Callable[[LiveFrame], None]) -> None:
        """Add callback for change detection events."""
        self.change_callbacks.append(callback)

    def add_translation_callback(self, callback: Callable[[LiveFrame, Any], None]) -> None:
        """Add callback for translation completion events."""
        self.translation_callbacks.append(callback)

    def remove_change_callback(self, callback: Callable[[LiveFrame], None]) -> None:
        """Remove change detection callback."""
        if callback in self.change_callbacks:
            self.change_callbacks.remove(callback)

    def remove_translation_callback(self, callback: Callable[[LiveFrame, Any], None]) -> None:
        """Remove translation completion callback."""
        if callback in self.translation_callbacks:
            self.translation_callbacks.remove(callback)

    # Configuration and status

    def set_fps(self, fps: float) -> None:
        """Set capture frame rate.

        Args:
            fps: Target frames per second
        """
        self.fps = max(0.1, min(fps, 30.0))  # Limit to reasonable range
        logger.debug(f"FPS set to: {self.fps}")

    def set_change_detector_config(self, config: ChangeDetector) -> None:
        """Update change detector configuration.

        Args:
            config: New change detector configuration
        """
        self.change_detector = config
        logger.debug(f"Change detector updated: {config.method}")

    def get_status(self) -> Dict[str, Any]:
        """Get current service status.

        Returns:
            Status dictionary
        """
        return {
            "is_active": self.is_active,
            "is_paused": self.is_paused,
            "fps_target": self.fps,
            "fps_actual": self.performance_stats["fps_actual"],
            "regions_count": len(self.capture_regions),
            "active_regions": self.active_regions.copy(),
            "queue_size": self.translation_queue.qsize(),
            "performance_stats": self.performance_stats.copy(),
            "change_detector_method": self.change_detector.method,
            "change_threshold": self.change_detector.threshold
        }

    def get_recent_frames(self, region_name: Optional[str] = None, limit: int = 10) -> List[LiveFrame]:
        """Get recent frames from history.

        Args:
            region_name: Optional region filter
            limit: Maximum number of frames to return

        Returns:
            List of recent frames
        """
        frames = self.frame_history

        if region_name:
            frames = [f for f in frames if f.region.name == region_name]

        return frames[-limit:] if frames else []

    async def manual_capture(self, region_name: str) -> Optional[LiveFrame]:
        """Manually capture a single frame from a region.

        Args:
            region_name: Name of region to capture

        Returns:
            Captured frame or None if failed
        """
        if region_name not in self.capture_regions:
            return None

        region = self.capture_regions[region_name]
        return await self._capture_region_frame(region)
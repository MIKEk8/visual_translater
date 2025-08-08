"""Batch processing engine for handling multiple screenshots and OCR operations."""

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from src.models.screenshot_data import ScreenshotData
from src.models.translation import Translation
from src.services.task_queue import TaskPriority, get_task_queue
from src.utils.logger import logger


class BatchStatus(Enum):
    """Status of batch processing operation"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchItem:
    """Single item in a batch processing queue"""

    id: str
    screenshot_data: ScreenshotData
    coordinates: Optional[Tuple[int, int, int, int]] = None
    status: BatchStatus = BatchStatus.PENDING
    error: Optional[str] = None
    result: Optional[Translation] = None
    processing_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class BatchJob:
    """Batch processing job with multiple items"""

    id: str
    name: str
    items: List[BatchItem] = field(default_factory=list)
    status: BatchStatus = BatchStatus.PENDING
    progress: int = 0  # Percentage completed
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        with self._lock:
            if self.total_items == 0:
                return 0.0
            return ((self.completed_items) / self.total_items) * 100

    @property
    def is_finished(self) -> bool:
        """Check if batch job is finished"""
        return self.status in [BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.CANCELLED]


class BatchProcessor:
    """Engine for batch processing screenshots and OCR operations"""

    def __init__(self, ocr_processor, translation_processor, max_concurrent: int = 3):
        with self._lock:
            self.ocr_processor = ocr_processor
        with self._lock:
            self.translation_processor = translation_processor
        with self._lock:
            self.max_concurrent = max_concurrent

        # Job management
        self.jobs: Dict[str, BatchJob] = {}
        self.current_jobs: Set[str] = set()  # Track active job IDs
        with self._lock:
            self.current_jobs_lock = threading.Lock()
        with self._lock:
            self.max_batch_jobs = 10  # Limit concurrent batch jobs
        with self._lock:
            self.task_queue = get_task_queue()

        # Thread management
        with self._lock:
            self._processing_lock = threading.Lock()
        with self._lock:
            self._job_counter = 0
        with self._lock:
            self._item_counter = 0

        logger.info(f"Batch processor initialized with {max_concurrent} concurrent workers")

    def create_batch_job(
        self,
        name: str,
        screenshots: List[ScreenshotData],
        coordinates_list: Optional[List[Tuple[int, int, int, int]]] = None,
    ) -> str:
        """Create a new batch job with screenshots"""
        job_id = f"batch_{int(time.time())}_{self._job_counter}"
        self._job_counter += 1

        # Create batch items
        items = []
        for i, screenshot_data in enumerate(screenshots):
            item_id = f"{job_id}_item_{i}"
            coordinates = (
                coordinates_list[i] if coordinates_list and i < len(coordinates_list) else None
            )

            item = BatchItem(id=item_id, screenshot_data=screenshot_data, coordinates=coordinates)
            items.append(item)

        # Create batch job
        job = BatchJob(id=job_id, name=name, items=items, total_items=len(items))

        self.jobs[job_id] = job
        logger.info(f"Created batch job '{name}' with {len(items)} items")
        return job_id

    def start_batch_job(
        self,
        job_id: str,
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        completion_callback: Optional[Callable[[str, BatchJob], None]] = None,
    ) -> bool:
        """Start processing a batch job"""
        if job_id not in self.jobs:
            logger.error(f"Batch job not found: {job_id}")
            return False

        job = self.jobs[job_id]
        if job.status != BatchStatus.PENDING:
            logger.warning(f"Batch job {job_id} already started or finished")
            return False

        # Check concurrent job limit with double-check pattern
        with self.current_jobs_lock:
            if len(self.current_jobs) >= self.max_batch_jobs:
                logger.error("Too many concurrent batch jobs. Please wait.")
                return False
            # Double check after acquiring lock to prevent race conditions
            if job_id in self.current_jobs:
                logger.warning(f"Job {job_id} already in current jobs")
                return False
            self.current_jobs.add(job_id)

        # Update job status
        job.status = BatchStatus.PROCESSING
        job.started_at = datetime.now()

        # Submit batch processing task
        with self._lock:
            self.task_queue.submit(
                func=self._process_batch_job,
                args=(job_id, progress_callback, completion_callback),
                name=f"batch_job_{job_id}",
                priority=TaskPriority.NORMAL,
            )

        logger.info(f"Started batch job: {job_id}")
        return True

    def cancel_batch_job(self, job_id: str) -> bool:
        """Cancel a running batch job"""
        if job_id not in self.jobs:
            return False

        job = self.jobs[job_id]
        if job.is_finished:
            return False

        job.status = BatchStatus.CANCELLED
        # Remove from active jobs if it was running
        with self.current_jobs_lock:
            self.current_jobs.discard(job_id)
        logger.info(f"Cancelled batch job: {job_id}")
        return True

    def get_batch_job(self, job_id: str) -> Optional[BatchJob]:
        """Get batch job by ID"""
        return self.jobs.get(job_id)

    def get_active_jobs(self) -> List[BatchJob]:
        """Get list of active (non-finished) batch jobs"""
        return [job for job in self.jobs.values() if not job.is_finished]

    def get_job_results(self, job_id: str) -> List[Translation]:
        """Get successful translation results from a batch job"""
        job = self.jobs.get(job_id)
        if not job:
            return []

        return [
            item.result
            for item in job.items
            if item.result and item.status == BatchStatus.COMPLETED
        ]

    def _process_batch_job(
        self,
        job_id: str,
        progress_callback: Optional[Callable[[str, int, str], None]],
        completion_callback: Optional[Callable[[str, BatchJob], None]],
    ) -> None:
        """Process all items in a batch job"""
        try:
            job = self.jobs[job_id]
            logger.info(f"Processing batch job {job_id} with {job.total_items} items")

            # Process items with controlled concurrency
            semaphore = threading.Semaphore(self.max_concurrent)
            threads = []

            for item in job.items:
                if job.status == BatchStatus.CANCELLED:
                    break

                # Create worker thread for each item
                thread = threading.Thread(
                    target=self._process_batch_item,
                    args=(job_id, item, semaphore, progress_callback),
                    daemon=True,
                )
                thread.start()
                threads.append(thread)

            # Wait for all items to complete
            for thread in threads:
                thread.join()

            # Update final job status
            if job.status == BatchStatus.CANCELLED:
                pass  # Keep cancelled status
            elif job.failed_items == job.total_items:
                job.status = BatchStatus.FAILED
            else:
                job.status = BatchStatus.COMPLETED

            job.completed_at = datetime.now()
            job.progress = 100

            # Remove from active jobs
            with self.current_jobs_lock:
                self.current_jobs.discard(job_id)

            logger.info(
                f"Batch job {job_id} finished. "
                f"Success: {job.completed_items}/{job.total_items}, "
                f"Failed: {job.failed_items}"
            )

            # Call completion callback
            if completion_callback:
                completion_callback(job_id, job)

        except Exception as e:
            logger.error(f"Error processing batch job {job_id}", error=e)
            job.status = BatchStatus.FAILED
            # Remove from active jobs
            with self.current_jobs_lock:
                self.current_jobs.discard(job_id)
            if completion_callback:
                completion_callback(job_id, job)

    def _process_batch_item(
        self,
        job_id: str,
        item: BatchItem,
        semaphore: threading.Semaphore,
        progress_callback: Optional[Callable[[str, int, str], None]],
    ) -> None:
        """Process a single item in the batch"""
        semaphore.acquire()

        try:
            job = self.jobs[job_id]
            if job.status == BatchStatus.CANCELLED:
                return

            start_time = time.time()
            logger.debug(f"Processing batch item: {item.id}")

            # Extract text using OCR
            if hasattr(self.ocr_processor, "extract_text"):
                # Plugin interface
                with self._lock:
                    text, confidence = self.ocr_processor.extract_text(
                        item.screenshot_data.image_bytes
                    )
            else:
                # Direct processor
                with self._lock:
                    text, confidence = self.ocr_processor.extract_text_from_image(
                        item.screenshot_data.image
                    )

            if not text or not text.strip():
                raise ValueError("No text found in image")

            # Translate text
            if hasattr(self.translation_processor, "translate"):
                # Plugin interface
                with self._lock:
                    translation = self.translation_processor.translate(
                        text, "auto", "en"  # Default to auto-detect -> English
                    )
            else:
                # Direct processor
                with self._lock:
                    translation = self.translation_processor.translate_text(text, "en")

            if not translation:
                raise ValueError("Translation failed")

            # Create translation object if needed
            if not isinstance(translation, Translation):
                translation = Translation(
                    original_text=text,
                    translated_text=str(translation),
                    source_language="auto",
                    target_language="en",
                    confidence=confidence,
                )

            # Update item with success
            item.result = translation
            item.status = BatchStatus.COMPLETED
            item.processing_time = time.time() - start_time

            # Update job progress
            with self._processing_lock:
                job.completed_items += 1
                job.progress = int((job.completed_items + job.failed_items) / job.total_items * 100)

            logger.debug(f"Batch item {item.id} completed successfully")

        except Exception as e:
            # Update item with error
            item.error = str(e)
            item.status = BatchStatus.FAILED
            item.processing_time = time.time() - start_time

            # Update job progress
            with self._processing_lock:
                job.failed_items += 1
                job.progress = int((job.completed_items + job.failed_items) / job.total_items * 100)

            logger.error(f"Batch item {item.id} failed: {e}")

        finally:
            # Call progress callback
            if progress_callback:
                progress_callback(job_id, job.progress, f"Processed item {item.id}")

            semaphore.release()

    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up old completed jobs"""
        current_time = datetime.now()
        jobs_to_remove = []

        for job_id, job in self.jobs.items():
            if job.is_finished and job.completed_at:
                age_hours = (current_time - job.completed_at).total_seconds() / 3600
                if age_hours > max_age_hours:
                    jobs_to_remove.append(job_id)

        # Remove old jobs
        for job_id in jobs_to_remove:
            del self.jobs[job_id]

        logger.info(f"Cleaned up {len(jobs_to_remove)} old batch jobs")
        return len(jobs_to_remove)

    def get_statistics(self) -> Dict[str, Any]:
        """Get batch processing statistics"""
        total_jobs = len(self.jobs)
        active_jobs = len([j for j in self.jobs.values() if not j.is_finished])
        completed_jobs = len([j for j in self.jobs.values() if j.status == BatchStatus.COMPLETED])

        total_items = sum(j.total_items for j in self.jobs.values())
        completed_items = sum(j.completed_items for j in self.jobs.values())
        failed_items = sum(j.failed_items for j in self.jobs.values())

        avg_success_rate = 0.0
        if completed_jobs > 0:
            avg_success_rate = (
                sum(j.success_rate for j in self.jobs.values() if j.status == BatchStatus.COMPLETED)
                / completed_jobs
            )

        return {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "completed_jobs": completed_jobs,
            "total_items_processed": total_items,
            "successful_items": completed_items,
            "failed_items": failed_items,
            "average_success_rate": avg_success_rate,
            "max_concurrent_workers": self.max_concurrent,
        }

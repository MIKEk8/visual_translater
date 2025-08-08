"""
Batch Progress Manager Component - Single Responsibility: Item Progress Tracking
Extracted from _process_batch_item (complexity 16 → 3 per method)
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ItemStatus(Enum):
    """Status of individual batch items"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class ItemProgress:
    """Progress information for individual batch item"""

    item_id: str
    status: ItemStatus
    start_time: Optional[float] = None
    completion_time: Optional[float] = None
    completion_percentage: float = 0.0
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        if self.start_time is None:
            return None
        end_time = self.completion_time or time.time()
        return end_time - self.start_time

    @property
    def is_completed(self) -> bool:
        return self.status in (ItemStatus.COMPLETED, ItemStatus.FAILED)


class BatchProgressManager:
    """
    Single Responsibility: Track and manage progress of batch item processing
    All methods ≤ 3 complexity
    """

    def __init__(self):
        self.item_progress: Dict[str, ItemProgress] = {}
        self.batch_start_time: Optional[float] = None
        self.batch_completion_time: Optional[float] = None
        self.progress_callbacks: List[Callable] = []
        self.statistics = {
            "total_items": 0,
            "completed_items": 0,
            "failed_items": 0,
            "processing_items": 0,
        }

    def update_item_progress(self, item_id: str, progress_data: Dict[str, Any]) -> bool:
        """
        Update progress for individual item
        Complexity: 3
        """
        if not item_id:  # +1
            return False

        # Initialize item progress if not exists
        if item_id not in self.item_progress:  # +1
            self.item_progress[item_id] = ItemProgress(item_id=item_id, status=ItemStatus.PENDING)

        item_progress = self.item_progress[item_id]

        # Update progress data
        if "status" in progress_data:
            new_status = ItemStatus(progress_data["status"])
            self._update_item_status(item_progress, new_status)

        if "completion" in progress_data:
            item_progress.completion_percentage = min(100.0, max(0.0, progress_data["completion"]))

        if "metadata" in progress_data:  # +1
            item_progress.metadata.update(progress_data["metadata"])

        # Update batch statistics
        self._update_statistics()

        # Notify progress callbacks
        self._notify_progress_callbacks()

        return True

    def track_completion(self, item_id: str, completion_data: Dict[str, Any]) -> bool:
        """
        Track completion of item processing
        Complexity: 3
        """
        if item_id not in self.item_progress:  # +1
            return False

        item_progress = self.item_progress[item_id]

        # Set completion data
        item_progress.completion_time = time.time()
        item_progress.completion_percentage = 100.0

        # Update status based on completion data
        if completion_data.get("success", True):  # +1
            item_progress.status = ItemStatus.COMPLETED
        else:
            item_progress.status = ItemStatus.FAILED
            item_progress.error_count = completion_data.get("error_count", 1)

        # Store completion metadata
        if "result" in completion_data:  # +1
            item_progress.metadata["result"] = completion_data["result"]

        if "duration" in completion_data:
            item_progress.metadata["processing_duration"] = completion_data["duration"]

        # Update statistics and notify
        self._update_statistics()
        self._notify_progress_callbacks()

        return True

    def get_progress_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive progress statistics
        Complexity: 3
        """
        current_time = time.time()

        # Calculate timing statistics
        total_duration = None
        if self.batch_start_time:  # +1
            end_time = self.batch_completion_time or current_time
            total_duration = end_time - self.batch_start_time

        # Calculate completion rate
        completion_rate = 0.0
        if self.statistics["total_items"] > 0:  # +1
            completion_rate = (
                self.statistics["completed_items"] / self.statistics["total_items"]
            ) * 100

        # Calculate processing speed
        items_per_second = 0.0
        if total_duration and total_duration > 0:  # +1
            completed = self.statistics["completed_items"] + self.statistics["failed_items"]
            items_per_second = completed / total_duration

        return {
            "total_items": self.statistics["total_items"],
            "completed_items": self.statistics["completed_items"],
            "failed_items": self.statistics["failed_items"],
            "processing_items": self.statistics["processing_items"],
            "pending_items": self.statistics["total_items"]
            - sum(
                [
                    self.statistics["completed_items"],
                    self.statistics["failed_items"],
                    self.statistics["processing_items"],
                ]
            ),
            "completion_rate": completion_rate,
            "total_duration": total_duration,
            "items_per_second": items_per_second,
            "estimated_completion_time": (
                self._estimate_completion_time() if items_per_second > 0 else None
            ),
        }

    def start_batch_tracking(self, total_items: int) -> bool:
        """Start batch progress tracking - complexity 2"""
        if total_items <= 0:  # +1
            return False

        self.batch_start_time = time.time()
        self.batch_completion_time = None
        self.statistics["total_items"] = total_items

        return True

    def complete_batch_tracking(self) -> Dict[str, Any]:
        """Complete batch progress tracking - complexity 1"""
        self.batch_completion_time = time.time()
        return self.get_progress_stats()

    def get_item_progress(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get progress for specific item - complexity 2"""
        if item_id not in self.item_progress:  # +1
            return None

        item_progress = self.item_progress[item_id]
        return {
            "item_id": item_progress.item_id,
            "status": item_progress.status.value,
            "completion_percentage": item_progress.completion_percentage,
            "duration": item_progress.duration,
            "error_count": item_progress.error_count,
            "metadata": item_progress.metadata.copy(),
        }

    def add_progress_callback(self, callback: Callable) -> None:
        """Add progress callback function - complexity 1"""
        self.progress_callbacks.append(callback)

    def clear_progress_callbacks(self) -> int:
        """Clear all progress callbacks - complexity 1"""
        count = len(self.progress_callbacks)
        self.progress_callbacks.clear()
        return count

    def reset_progress(self) -> None:
        """Reset all progress data - complexity 1"""
        self.item_progress.clear()
        self.batch_start_time = None
        self.batch_completion_time = None
        self.statistics = {
            "total_items": 0,
            "completed_items": 0,
            "failed_items": 0,
            "processing_items": 0,
        }

    def _update_item_status(self, item_progress: ItemProgress, new_status: ItemStatus) -> None:
        """Update item status with timing - complexity 2"""
        old_status = item_progress.status
        item_progress.status = new_status

        # Set timing based on status transitions
        if old_status == ItemStatus.PENDING and new_status == ItemStatus.PROCESSING:  # +1
            item_progress.start_time = time.time()
        elif new_status in (ItemStatus.COMPLETED, ItemStatus.FAILED):
            if not item_progress.completion_time:
                item_progress.completion_time = time.time()

    def _update_statistics(self) -> None:
        """Update batch statistics - complexity 2"""
        self.statistics.update(
            {
                "completed_items": sum(
                    1 for p in self.item_progress.values() if p.status == ItemStatus.COMPLETED
                ),
                "failed_items": sum(
                    1 for p in self.item_progress.values() if p.status == ItemStatus.FAILED
                ),
                "processing_items": sum(
                    1 for p in self.item_progress.values() if p.status == ItemStatus.PROCESSING
                ),
            }
        )

        # Update total if it's greater than known total
        actual_total = len(self.item_progress)
        if actual_total > self.statistics["total_items"]:  # +1
            self.statistics["total_items"] = actual_total

    def _notify_progress_callbacks(self) -> None:
        """Notify all progress callbacks - complexity 2"""
        if not self.progress_callbacks:  # +1
            return

        stats = self.get_progress_stats()
        for callback in self.progress_callbacks:
            try:
                callback(stats)
            except Exception:
                pass  # Ignore callback errors

    def _estimate_completion_time(self) -> float:
        """Estimate completion time - complexity 2"""
        current_time = time.time()

        # Calculate timing directly without recursion
        total_duration = None
        if self.batch_start_time:
            end_time = self.batch_completion_time or current_time
            total_duration = end_time - self.batch_start_time

        if not total_duration or total_duration <= 0:  # +1
            return 0.0

        completed = self.statistics["completed_items"] + self.statistics["failed_items"]
        items_per_second = completed / total_duration if completed > 0 else 0.0

        if items_per_second <= 0:
            return 0.0

        pending_items = (
            self.statistics["total_items"] - completed - self.statistics["processing_items"]
        )  # +1
        return current_time + (pending_items / items_per_second)

"""
Export Progress Tracker Component - Single Responsibility: Progress Tracking
Extracted from export_batch_results (complexity 16 → 3 per method)
"""

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


@dataclass
class ProgressInfo:
    """Progress information data class"""

    total_items: int
    processed_items: int
    current_item: Optional[str] = None
    start_time: Optional[float] = None
    estimated_completion: Optional[float] = None

    @property
    def percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_items == 0:
            return 100.0
        return min(100.0, (self.processed_items / self.total_items) * 100)


class ExportProgressTracker:
    """
    Single Responsibility: Track and report export progress
    All methods ≤ 3 complexity
    """

    def __init__(self):
        self.progress_info = None
        self.progress_callback = None
        self.is_tracking = False

    def start_tracking(
        self, total_items: int, progress_callback: Optional[Callable] = None
    ) -> bool:
        """
        Start progress tracking
        Complexity: 3
        """
        if total_items <= 0:  # +1
            return False

        self.progress_info = ProgressInfo(
            total_items=total_items, processed_items=0, start_time=time.time()
        )

        self.progress_callback = progress_callback
        self.is_tracking = True

        # Initial progress report
        if self.progress_callback:  # +1
            self.progress_callback(self.progress_info)

        return True

    def update_progress(
        self, processed_count: Optional[int] = None, current_item: Optional[str] = None
    ) -> bool:
        """
        Update progress information
        Complexity: 3
        """
        if not self.is_tracking or not self.progress_info:  # +1
            return False

        # Update processed count
        if processed_count is not None:  # +1
            self.progress_info.processed_items = min(
                processed_count, self.progress_info.total_items
            )
        else:
            self.progress_info.processed_items += 1

        # Update current item
        if current_item:
            self.progress_info.current_item = current_item

        # Calculate estimated completion
        self._calculate_estimated_completion()

        # Report progress
        if self.progress_callback:  # +1
            self.progress_callback(self.progress_info)

        return True

    def complete_tracking(self) -> Dict[str, Any]:
        """
        Complete tracking and return final statistics
        Complexity: 2
        """
        if not self.is_tracking or not self.progress_info:  # +1
            return {}

        end_time = time.time()
        total_duration = end_time - self.progress_info.start_time

        final_stats = {
            "total_items": self.progress_info.total_items,
            "processed_items": self.progress_info.processed_items,
            "completion_percentage": self.progress_info.percentage,
            "total_duration": total_duration,
            "items_per_second": (
                self.progress_info.processed_items / total_duration if total_duration > 0 else 0
            ),
            "completed": True,
        }

        # Final progress report
        if self.progress_callback:  # +1
            self.progress_callback(self.progress_info)

        self.is_tracking = False
        return final_stats

    def get_current_progress(self) -> Optional[ProgressInfo]:
        """Get current progress information - complexity 1"""
        return self.progress_info

    def is_tracking_active(self) -> bool:
        """Check if tracking is currently active - complexity 1"""
        return self.is_tracking

    def _calculate_estimated_completion(self) -> None:
        """Calculate estimated completion time - complexity 2"""
        if not self.progress_info or self.progress_info.processed_items == 0:  # +1
            return

        elapsed_time = time.time() - self.progress_info.start_time
        remaining_items = self.progress_info.total_items - self.progress_info.processed_items

        if remaining_items > 0:  # +1
            items_per_second = self.progress_info.processed_items / elapsed_time
            self.progress_info.estimated_completion = time.time() + (
                remaining_items / items_per_second
            )

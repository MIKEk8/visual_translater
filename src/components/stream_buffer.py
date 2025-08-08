"""
Stream Buffer Component - Single Responsibility: Stream Buffering & Flow Control
"""

import threading
from collections import deque
from typing import Any, Dict, Iterator, List, Optional


class StreamBuffer:
    """Manage streaming data buffer - complexity ≤ 3 per method"""

    def __init__(self, max_size: int = 1000):
        self.buffer = deque(maxlen=max_size)
        self.max_size = max_size
        self.lock = threading.Lock()
        self.stats = {"items_buffered": 0, "items_consumed": 0}

    def add_to_buffer(self, item: Dict[str, Any]) -> bool:
        """Add item to buffer - complexity 2"""
        with self.lock:
            if len(self.buffer) >= self.max_size:  # +1
                return False  # Buffer full

            self.buffer.append(item)
            self.stats["items_buffered"] += 1
            return True

    def consume_from_buffer(self, batch_size: int = 10) -> List[Dict[str, Any]]:
        """Consume items from buffer - complexity 3"""
        with self.lock:
            items = []

            for _ in range(min(batch_size, len(self.buffer))):  # +1
                if self.buffer:  # +1
                    items.append(self.buffer.popleft())
                    self.stats["items_consumed"] += 1

            return items

    def get_buffer_status(self) -> Dict[str, Any]:
        """Get buffer status - complexity 2"""
        with self.lock:
            return {
                "current_size": len(self.buffer),
                "max_size": self.max_size,
                "utilization": len(self.buffer) / self.max_size,  # +1
                "stats": self.stats.copy(),
            }

    def clear_buffer(self) -> int:
        """Clear buffer - complexity 1"""
        with self.lock:
            count = len(self.buffer)
            self.buffer.clear()
            return count

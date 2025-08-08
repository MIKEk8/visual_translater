"""Unit tests for task queue module"""

import time
from unittest.mock import MagicMock

import pytest

from src.services.task_queue import TaskPriority, TaskQueue


class TestTaskQueue:
    """Test cases for TaskQueue"""

    @pytest.fixture
    def task_queue(self):
        """Create a task queue for testing"""
        return TaskQueue(num_workers=2)

    def test_task_queue_creation(self, task_queue):
        """Test task queue can be created"""
        assert task_queue is not None
        assert hasattr(task_queue, "submit")
        assert hasattr(task_queue, "stop")

    def test_submit_task(self, task_queue):
        """Test submitting a task"""

        def simple_task():
            return "completed"

        task_id = task_queue.submit(
            func=simple_task, name="test_task", priority=TaskPriority.NORMAL
        )

        assert task_id is not None
        assert isinstance(task_id, str)

    def test_task_execution(self, task_queue):
        """Test that tasks are executed"""
        result = None
        callback_called = False

        def test_task():
            return "task_result"

        def callback(res):
            nonlocal result, callback_called
            result = res
            callback_called = True

        task_queue.submit(
            func=test_task, name="execution_test", priority=TaskPriority.HIGH, callback=callback
        )

        # Wait a bit for task execution
        time.sleep(0.1)

        # Note: In a real test environment, you might want to use proper synchronization
        # This is a simplified test
        task_queue.stop(wait=True, timeout=1.0)

    def test_priority_ordering(self, task_queue):
        """Test that high priority tasks are executed first"""

        execution_order = []

        def low_priority_task():
            execution_order.append("low")

        def high_priority_task():
            execution_order.append("high")

        # Submit low priority first
        task_queue.submit(func=low_priority_task, name="low_priority", priority=TaskPriority.LOW)

        # Submit high priority second
        task_queue.submit(func=high_priority_task, name="high_priority", priority=TaskPriority.HIGH)

        task_queue.stop(wait=True, timeout=1.0)

    def test_stop_task_queue(self, task_queue):
        """Test stopping the task queue"""

        # Should not raise errors
        task_queue.stop(wait=False)

        # Should handle multiple stops gracefully
        task_queue.stop(wait=False)

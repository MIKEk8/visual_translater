"""
Task queue service for asynchronous processing of screenshots and translations.
Provides non-blocking operations for better UI responsiveness.
"""

import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from src.utils.logger import logger


class TaskStatus(Enum):
    """Task execution status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels"""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Task:
    """Represents a task in the queue"""

    id: str
    name: str
    func: Callable
    args: tuple = ()
    kwargs: Optional[dict] = None
    priority: TaskPriority = TaskPriority.NORMAL
    callback: Optional[Callable] = None
    error_callback: Optional[Callable] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None

    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}
        if self.created_at is None:
            self.created_at = datetime.now()

    def __lt__(self, other):
        """For priority queue comparison"""
        return self.priority.value > other.priority.value


class TaskQueue:
    """Asynchronous task queue with priority support"""

    def __init__(self, num_workers: int = 2, max_queue_size: int = 100):
        self.num_workers = num_workers
        self.max_queue_size = max_queue_size

        # Priority queue for tasks
        self.task_queue = queue.PriorityQueue(maxsize=max_queue_size)

        # Task tracking
        self.tasks: Dict[str, Task] = {}
        self.completed_tasks: List[Task] = []
        self.task_lock = threading.Lock()

        # Worker threads
        self.workers: List[threading.Thread] = []
        self.running = False

        # Statistics
        self.total_tasks = 0
        self.completed_count = 0
        self.failed_count = 0

        logger.info(f"Task queue initialized with {num_workers} workers")

    def start(self):
        """Start worker threads"""
        if self.running:
            return

        self.running = True

        # Create and start worker threads
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop, daemon=True, name=f"TaskWorker-{i+1}"
            )
            worker.start()
            self.workers.append(worker)

        logger.info(f"Started {self.num_workers} task workers")

    def stop(self, wait: bool = True, timeout: float = 5.0):
        """Stop worker threads"""
        if not self.running:
            return

        self.running = False

        # Add sentinel values to wake up workers
        for _ in range(self.num_workers):
            try:
                # Используем кортеж с низким приоритетом для sentinel
                self.task_queue.put((-1, None), block=False)
            except queue.Full:
                pass

        if wait:
            # Wait for workers to finish
            for worker in self.workers:
                worker.join(timeout=timeout)

        self.workers.clear()
        logger.info("Task queue stopped")

    def submit(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        name: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None,
    ) -> str:
        """Submit a task to the queue"""

        # Generate task ID
        task_id = f"task-{self.total_tasks + 1}-{int(time.time() * 1000)}"

        # Create task
        task = Task(
            id=task_id,
            name=name or func.__name__,
            func=func,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
            callback=callback,
            error_callback=error_callback,
        )

        # Track task
        with self.task_lock:
            self.tasks[task_id] = task
            self.total_tasks += 1

        # Queue task
        try:
            self.task_queue.put((task.priority.value, task), timeout=1.0)
            logger.debug(f"Task {task_id} ({task.name}) queued with priority {priority.name}")
        except queue.Full:
            task.status = TaskStatus.FAILED
            task.error = Exception("Task queue is full")
            logger.error(f"Failed to queue task {task_id}: queue full")
            raise

        return task_id

    def cancel(self, task_id: str) -> bool:
        """Cancel a pending task"""
        with self.task_lock:
            task = self.tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                logger.info(f"Task {task_id} cancelled")
                return True
        return False

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get status of a task"""
        with self.task_lock:
            task = self.tasks.get(task_id)
            return task.status if task else None

    def get_task_result(self, task_id: str) -> Any:
        """Get result of completed task"""
        with self.task_lock:
            task = self.tasks.get(task_id)
            if task and task.status == TaskStatus.COMPLETED:
                return task.result
            return None

    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> bool:
        """Wait for task completion"""
        start_time = time.time()

        while True:
            with self.task_lock:
                task = self.tasks.get(task_id)
                if not task:
                    return False
                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    return task.status == TaskStatus.COMPLETED

            if timeout and (time.time() - start_time) >= timeout:
                return False

            time.sleep(0.1)

    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self.task_queue.qsize()

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        with self.task_lock:
            pending_count = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)
            running_count = sum(1 for t in self.tasks.values() if t.status == TaskStatus.RUNNING)

        return {
            "queue_size": self.get_queue_size(),
            "total_tasks": self.total_tasks,
            "pending": pending_count,
            "running": running_count,
            "completed": self.completed_count,
            "failed": self.failed_count,
            "workers": self.num_workers,
            "is_running": self.running,
        }

    def _handle_task_success(self, task, result):
        """Handle successful task completion."""
        with self.task_lock:
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now()
            self.completed_count += 1
            self.completed_tasks.append(task)

            # Limit completed tasks history
            if len(self.completed_tasks) > 100:
                self.completed_tasks = self.completed_tasks[-100:]

        # Call success callback
        if task.callback:
            try:
                task.callback(result)
            except Exception as e:
                logger.error(f"Task callback error: {e}")

        logger.debug(f"Task {task.id} completed successfully")

    def _handle_task_failure(self, task, error):
        """Handle task failure."""
        logger.error(f"Task {task.id} failed: {error}")

        with self.task_lock:
            task.status = TaskStatus.FAILED
            task.error = error
            task.completed_at = datetime.now()
            self.failed_count += 1

        # Call error callback
        if task.error_callback:
            try:
                task.error_callback(error)
            except Exception as cb_error:
                logger.error(f"Error callback failed: {cb_error}")

    def _execute_task(self, task, worker_name):
        """Execute a single task."""
        try:
            logger.debug(f"{worker_name} executing task {task.id} ({task.name})")
            result = task.func(*task.args, **task.kwargs)
            self._handle_task_success(task, result)
        except Exception as e:
            self._handle_task_failure(task, e)

    def _worker_loop(self):
        """Worker thread main loop"""
        worker_name = threading.current_thread().name
        logger.debug(f"{worker_name} started")

        while self.running:
            try:
                # Get task from queue
                item = self.task_queue.get(timeout=1.0)

                # Check for shutdown sentinel
                priority, task = item
                if task is None:
                    break

                # Check if task was cancelled
                with self.task_lock:
                    if task.status == TaskStatus.CANCELLED:
                        continue
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now()

                self._execute_task(task, worker_name)

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"{worker_name} error: {e}")

        logger.debug(f"{worker_name} stopped")


# Global task queue instance
_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """Get global task queue instance"""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
        _task_queue.start()
    return _task_queue


def submit_task(func: Callable, *args, **kwargs) -> str:
    """Convenience function to submit task to global queue"""
    queue = get_task_queue()
    return queue.submit(func, args=args, kwargs=kwargs)


def shutdown_task_queue():
    """Shutdown global task queue"""
    global _task_queue
    if _task_queue:
        _task_queue.stop()
        _task_queue = None

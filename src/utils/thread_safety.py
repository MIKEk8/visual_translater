"""
Thread-safe components and utilities for Screen Translator v2.0
"""

import queue
import threading
from typing import Any, Callable, Dict, Optional


class ThreadSafeState:
    """Thread-safe state container with proper locking."""

    def __init__(self):
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Thread-safe get operation."""
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Thread-safe set operation."""
        with self._lock:
            self._data[key] = value

    def update(self, updates: Dict[str, Any]) -> None:
        """Thread-safe bulk update."""
        with self._lock:
            self._data.update(updates)

    def delete(self, key: str) -> None:
        """Thread-safe delete operation."""
        with self._lock:
            self._data.pop(key, None)

    def clear(self) -> None:
        """Thread-safe clear operation."""
        with self._lock:
            self._data.clear()

    def get_all(self) -> Dict[str, Any]:
        """Get a copy of all data (thread-safe)."""
        with self._lock:
            return self._data.copy()


class SafeGUIUpdater:
    """Thread-safe GUI updater using queue pattern."""

    def __init__(self, root):
        self.root = root
        self.gui_queue: queue.Queue = queue.Queue()
        self._running = True
        self._start_gui_processor()

    def update_gui_safely(self, func: Callable, *args, **kwargs) -> None:
        """Queue a GUI update for thread-safe execution."""
        if self._running:
            self.gui_queue.put((func, args, kwargs))

    def stop(self) -> None:
        """Stop the GUI processor."""
        self._running = False

    def _start_gui_processor(self) -> None:
        """Start processing GUI updates."""
        if hasattr(self.root, "after"):
            self.root.after(50, self._process_gui_queue)

    def _process_gui_queue(self) -> None:
        """Process queued GUI updates."""
        if not self._running:
            return

        deadline = threading.current_thread().ident + 0.01  # Process for max 10ms

        try:
            while not self.gui_queue.empty():
                func, args, kwargs = self.gui_queue.get_nowait()
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    print(f"Error in GUI update: {e}")

                if threading.current_thread().ident > deadline:
                    break  # Don't block GUI thread too long

        except queue.Empty:
            pass
        finally:
            if self._running and hasattr(self.root, "after"):
                self.root.after(50, self._process_gui_queue)


class ThreadSafeEventBus:
    """Thread-safe event bus for decoupled communication."""

    def __init__(self):
        self._lock = threading.RLock()
        self._handlers: Dict[str, list] = {}
        self._queue: queue.Queue = queue.Queue()
        self._processor_thread: Optional[threading.Thread] = None
        self._running = False

    def subscribe(self, event: str, handler: Callable) -> None:
        """Subscribe to an event (thread-safe)."""
        with self._lock:
            if event not in self._handlers:
                self._handlers[event] = []
            self._handlers[event].append(handler)

    def unsubscribe(self, event: str, handler: Callable) -> None:
        """Unsubscribe from an event (thread-safe)."""
        with self._lock:
            if event in self._handlers:
                self._handlers[event].remove(handler)
                if not self._handlers[event]:
                    del self._handlers[event]

    def emit(self, event: str, *args, **kwargs) -> None:
        """Emit an event (thread-safe, non-blocking)."""
        if self._running:
            self._queue.put((event, args, kwargs))

    def start(self) -> None:
        """Start the event processor."""
        if not self._running:
            self._running = True
            self._processor_thread = threading.Thread(target=self._process_events, daemon=True)
            self._processor_thread.start()

    def stop(self) -> None:
        """Stop the event processor."""
        self._running = False
        if self._processor_thread:
            self._processor_thread.join(timeout=1.0)

    def _process_events(self) -> None:
        """Process events in background thread."""
        while self._running:
            try:
                event, args, kwargs = self._queue.get(timeout=0.1)
                with self._lock:
                    handlers = self._handlers.get(event, []).copy()

                for handler in handlers:
                    try:
                        handler(*args, **kwargs)
                    except Exception as e:
                        print(f"Error in event handler for {event}: {e}")

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing events: {e}")

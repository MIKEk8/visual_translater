# 🧵 Thread Safety Guidelines for Screen Translator v2.0

## 🎯 Critical Rules

### 1. **Always Protect Shared State**
```python
class MyClass:
    def __init__(self):
        self._lock = threading.Lock()
        self.shared_data = {}
    
    def update_data(self, key, value):
        with self._lock:  # REQUIRED for thread safety
            self.shared_data[key] = value
```

### 2. **Use Context Managers for Locks**
```python
# ✅ GOOD - Automatic lock release
with self._lock:
    self.counter += 1
    
# ❌ BAD - Manual lock management
self._lock.acquire()
try:
    self.counter += 1
finally:
    self._lock.release()
```

### 3. **Protect Collection Operations**
```python
# ✅ GOOD - Protected list operations
with self._lock:
    self.items.append(new_item)
    self.items.remove(old_item)
    
# ❌ BAD - Unprotected operations
self.items.append(new_item)  # Race condition!
```

### 4. **Use Thread-Safe Data Structures**
```python
import queue
import threading
from collections import deque

# Thread-safe alternatives:
safe_queue = queue.Queue()           # Instead of list
safe_dict = {}  # Protected with lock
safe_counter = threading.local()     # Thread-local
```

## 🔧 Patterns to Fix

### **Pattern 1: Unprotected Instance Variables**
```python
# BEFORE (Unsafe):
def update_status(self, status):
    self.current_status = status  # Race condition!

# AFTER (Safe):
def update_status(self, status):
    with self._lock:
        self.current_status = status
```

### **Pattern 2: Complex Shared Operations**
```python
# BEFORE (Unsafe):
def process_batch(self, items):
    for item in items:
        self.results.append(self.process_item(item))
        self.completed_count += 1

# AFTER (Safe):
def process_batch(self, items):
    local_results = []
    for item in items:
        local_results.append(self.process_item(item))
    
    with self._lock:
        self.results.extend(local_results)
        self.completed_count += len(local_results)
```

### **Pattern 3: Event Callbacks**
```python
# BEFORE (Unsafe):
def on_event(self, event_data):
    self.event_history.append(event_data)
    self.last_event = event_data

# AFTER (Safe):
def on_event(self, event_data):
    with self._lock:
        self.event_history.append(event_data)
        self.last_event = event_data
```

## 🚨 Common Mistakes to Avoid

1. **Assuming atomic operations**: Even simple assignments can be non-atomic
2. **Forgetting collection modifications**: append(), pop(), update() need protection
3. **Lock granularity issues**: Too coarse = performance loss, too fine = race conditions
4. **Deadlock scenarios**: Always acquire locks in same order
5. **Exception safety**: Use context managers to ensure lock release

## 🎯 Performance Considerations

### **Minimize Lock Scope**
```python
# ✅ GOOD - Minimal lock time
def get_summary(self):
    with self._lock:
        data_copy = self.data.copy()
    
    # Process outside lock
    return self._calculate_summary(data_copy)

# ❌ BAD - Long lock time
def get_summary(self):
    with self._lock:
        data_copy = self.data.copy()
        return self._calculate_summary(data_copy)  # Slow operation in lock!
```

### **Use RLock for Recursive Calls**
```python
class Counter:
    def __init__(self):
        self._lock = threading.RLock()  # Reentrant lock
        self.value = 0
    
    def increment(self):
        with self._lock:
            self.value += 1
            self._log_change()  # May also need lock
    
    def _log_change(self):
        with self._lock:  # OK with RLock
            print(f"Counter: {self.value}")
```

## 🔍 Testing Thread Safety

```python
import threading
import time

def test_thread_safety():
    """Test concurrent access to shared resource"""
    counter = ThreadSafeCounter()
    threads = []
    
    def worker():
        for _ in range(1000):
            counter.increment()
    
    # Start 10 concurrent threads
    for _ in range(10):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()
    
    # Wait for completion
    for t in threads:
        t.join()
    
    # Should be 10,000 if thread-safe
    assert counter.value == 10000
```

## 🎯 Implementation Checklist

- [ ] Add `self._lock = threading.Lock()` to `__init__`
- [ ] Wrap all shared variable access in `with self._lock:`
- [ ] Protect list/dict operations (append, pop, update, etc.)
- [ ] Use thread-safe data structures where possible
- [ ] Test with concurrent access
- [ ] Document thread safety guarantees
- [ ] Consider using `threading.RLock()` for recursive scenarios

Remember: **Thread safety is not optional in multi-threaded applications!**

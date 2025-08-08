
# Template: Service Decomposition Pattern

## Before: Monolithic Service (40+ methods)
```python
class MonolithicService:
    def __init__(self):
        # Mixed responsibilities across domains
        
    def load_config(self): pass        # Configuration
    def save_config(self): pass        # Configuration  
    def process_data(self): pass       # Processing
    def validate_data(self): pass      # Processing
    def save_to_db(self): pass         # Persistence
    def load_from_db(self): pass       # Persistence
    def send_notification(self): pass  # Communication
    # ... 35+ more methods
```

## After: Service Decomposition (4 services + coordinator)

### 1. Configuration Service
```python
class ConfigurationService:
    """Single responsibility: Configuration management"""
    
    def load_configuration(self): pass     # complexity 3
    def save_configuration(self): pass     # complexity 4
    def validate_config(self): pass        # complexity 5
    def get_setting(self, key): pass       # complexity 2
```

### 2. Processing Service  
```python
class ProcessingService:
    """Single responsibility: Data processing"""
    
    def process_item(self, item): pass     # complexity 5
    def validate_item(self, item): pass    # complexity 4
    def transform_data(self, data): pass   # complexity 4
```

### 3. Persistence Service
```python
class PersistenceService:
    """Single responsibility: Data storage"""
    
    def save_entity(self, entity): pass    # complexity 3
    def load_entity(self, id): pass        # complexity 4
    def delete_entity(self, id): pass      # complexity 2
```

### 4. Notification Service
```python
class NotificationService:
    """Single responsibility: Communication"""
    
    def send_notification(self, message): pass  # complexity 3
    def broadcast_event(self, event): pass      # complexity 4
```

### 5. Main Service (Coordinator)
```python
class RefactoredService:
    """Coordinate services - complexity ≤ 5 per method"""
    
    def __init__(self):
        self.config = ConfigurationService()
        self.processor = ProcessingService()
        self.persistence = PersistenceService()
        self.notifications = NotificationService()
    
    def execute_workflow(self, data): pass  # complexity 5
    def initialize(self): pass              # complexity 4
```

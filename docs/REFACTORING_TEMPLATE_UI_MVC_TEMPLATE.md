
# Template: UI MVC Pattern Refactoring

## Before: Large UI Class (30+ methods)
```python
class LargeUIWindow:
    def __init__(self):
        # Mixed responsibilities
        self.data = []
        self.ui_components = {}
        
    def load_data(self): pass          # Data responsibility
    def save_data(self): pass          # Data responsibility
    def create_widgets(self): pass     # UI responsibility  
    def layout_widgets(self): pass     # UI responsibility
    def on_button_click(self): pass    # Event responsibility
    def validate_input(self): pass     # Validation responsibility
    # ... 25+ more methods
```

## After: MVC Split (4 focused classes)

### 1. Data Model (Single Responsibility: Data Management)
```python
class WindowDataModel:
    """Handle all data operations - complexity ≤ 5 per method"""
    
    def load_data(self) -> List[Dict]: pass      # complexity 3
    def save_data(self, data: List[Dict]): pass  # complexity 4  
    def validate_data(self, item: Dict): pass    # complexity 5
    def filter_data(self, criteria: Dict): pass  # complexity 4
```

### 2. View Controller (Single Responsibility: UI Management) 
```python
class WindowViewController:
    """Handle UI component management - complexity ≤ 5 per method"""
    
    def create_layout(self): pass       # complexity 4
    def update_display(self, data): pass # complexity 3
    def show_error(self, message): pass  # complexity 2
    def refresh_view(self): pass         # complexity 3
```

### 3. Event Handler (Single Responsibility: User Interaction)
```python
class WindowEventHandler:
    """Handle user interactions - complexity ≤ 5 per method"""
    
    def on_button_click(self, event): pass    # complexity 4
    def on_selection_change(self, event): pass # complexity 3
    def on_key_press(self, event): pass       # complexity 5
```

### 4. Main Window (Coordinator - complexity ≤ 5 per method)
```python
class RefactoredWindow:
    """Coordinate components - complexity ≤ 5 per method"""
    
    def __init__(self):
        self.data_model = WindowDataModel()
        self.view_controller = WindowViewController()
        self.event_handler = WindowEventHandler()
    
    def initialize(self): pass    # complexity 4
    def show(self): pass          # complexity 2
    def close(self): pass         # complexity 3
```

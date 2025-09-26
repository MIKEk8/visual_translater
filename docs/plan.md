# 🏗️ Implementation Plan: 8 Enhanced Features for Visual Translator

**Created**: 2025-09-26
**Target**: Complete integration of all 8 features from easy_features_implementation.md
**Architecture**: Clean Architecture + Plugin System + Circuit Breaker Pattern

---

## 🎯 Overview

This plan implements 8 high-value features that enhance the existing Visual Translator application without major architectural refactoring. Each feature leverages the existing plugin system, dependency injection container, and circuit breaker patterns.

**Total Implementation Time**: 6-8 hours
**Testing Time**: 2-3 hours
**Total Project Time**: 8-11 hours

---

## 📋 Features Priority Matrix

| Feature | Priority | Time | Risk | ROI | Dependencies |
|---------|----------|------|------|-----|-------------|
| Enhanced History Window | HIGH | 1h | LOW | 10/10 | SQLite, existing HistoryWindow |
| Hotkey Profiles | HIGH | 45m | LOW | 9/10 | existing HotkeyService |
| Auto Game Detection | HIGH | 1.5h | MED | 9/10 | psutil, win32gui |
| OCR Preprocessing | HIGH | 1.5h | MED | 8/10 | OpenCV, existing OCREngine |
| Quick Actions Menu | MED | 30m | LOW | 8/10 | existing UI components |
| Context Glossaries | MED | 1h | LOW | 7/10 | JSON storage, existing Translation |
| Drop Zone Support | MED | 45m | MED | 7/10 | tkinterdnd2, existing DragDropHandler |
| Live Translation Mode | LOW | 2h | HIGH | 6/10 | async processing, existing components |

---

## 🏛️ Architectural Approach

### Core Principles
- **Zero Breaking Changes**: All features integrate with existing interfaces
- **Plugin Architecture**: Each feature can be enabled/disabled via configuration
- **Circuit Breaker Pattern**: All external operations protected by circuit breakers
- **Dependency Injection**: Use existing DI container for service registration
- **Event-Driven**: Leverage existing event bus for component communication

### Integration Points
- `src/services/container.py` - Register new services
- `src/core/coordinators/application_controller.py` - Initialize features
- `src/core/events.py` - Add new event types
- `src/services/config_manager.py` - Feature configuration
- Existing UI components extend with new features

---

## 📁 Implementation Plan

### 1. Enhanced History Window (SQLite FTS5) - 1 hour

**Description**: Upgrade existing history with full-text search, advanced filtering, and better performance.

#### Files to Create/Modify:
- **MODIFY** `src/ui/history_window.py` - Add search capabilities
- **CREATE** `src/services/history_search_service.py` - SQLite FTS5 service
- **CREATE** `src/infrastructure/repositories/history_repository.py` - Data layer

#### Implementation Details:
```python
# New service in DI container
class HistorySearchService:
    def __init__(self):
        self.db_path = "data/translation_history.db"
        self._setup_fts5_tables()

    def search(self, query: str, filters: Dict) -> List[Translation]:
        # FTS5 full-text search implementation
        pass
```

#### Tests Required:
- **Unit**: `test_history_search_service.py` - Search functionality, filters
- **Integration**: `test_enhanced_history_integration.py` - UI + search service
- **Performance**: Search speed with 10k+ records

#### Configuration:
```json
{
  "history": {
    "search_enabled": true,
    "fts5_enabled": true,
    "max_results": 100
  }
}
```

#### Risk Mitigation:
- Migration script for existing history data
- Fallback to simple search if FTS5 fails
- Circuit breaker for database operations

---

### 2. Hotkey Profiles (Gaming/Reading/Streaming) - 45 minutes

**Description**: Create predefined hotkey configurations for different use cases.

#### Files to Create/Modify:
- **CREATE** `src/services/hotkey_profile_service.py` - Profile management
- **MODIFY** `src/services/hotkey_service.py` - Profile switching support
- **CREATE** `src/ui/hotkey_profile_selector.py` - Profile selection UI

#### Implementation Details:
```python
@dataclass
class HotkeyProfile:
    name: str
    description: str
    hotkeys: Dict[str, str]
    context: str  # "gaming", "reading", "streaming"

class HotkeyProfileService:
    def __init__(self, hotkey_service: HotkeyService):
        self.hotkey_service = hotkey_service
        self.profiles = self._load_default_profiles()
```

#### Tests Required:
- **Unit**: `test_hotkey_profile_service.py` - Profile creation, switching
- **Integration**: `test_hotkey_profile_integration.py` - UI + service interaction
- **E2E**: Test actual hotkey registration/deregistration

#### Default Profiles:
- **Gaming**: Quick access keys (Ctrl+Q, F1-F3)
- **Reading**: Document-focused (Ctrl+Shift+C, Ctrl+T)
- **Streaming**: Stream-friendly (F5-F9)

---

### 3. Auto Game Detection (Process Monitoring) - 1.5 hours

**Description**: Automatically detect running games and load appropriate settings.

#### Files to Create/Modify:
- **CREATE** `src/services/game_detector_service.py` - Process monitoring
- **CREATE** `src/domain/entities/game_profile.py` - Game profile model
- **CREATE** `src/infrastructure/repositories/game_repository.py` - Game database
- **MODIFY** `src/core/coordinators/system_integration.py` - Background monitoring

#### Implementation Details:
```python
class GameDetectorService:
    def __init__(self):
        self.game_database = self._load_game_database()
        self.current_game = None
        self.check_interval = 5  # seconds

    async def monitor_processes(self):
        while True:
            active_game = self._detect_active_game()
            if active_game != self.current_game:
                await self._handle_game_change(active_game)
            await asyncio.sleep(self.check_interval)
```

#### Tests Required:
- **Unit**: `test_game_detector_service.py` - Process detection logic
- **Integration**: `test_game_detection_workflow.py` - Settings switching
- **Mock**: Mock process detection for testing

#### Game Database:
- JSON file with game executables → profile mappings
- Downloadable community database
- User customizable

---

### 4. OCR Preprocessing Pipeline (Image Enhancement) - 1.5 hours

**Description**: Add image preprocessing to improve OCR accuracy.

#### Files to Create/Modify:
- **CREATE** `src/core/image_preprocessor.py` - OpenCV preprocessing
- **MODIFY** `src/core/ocr_engine.py` - Integrate preprocessing
- **CREATE** `src/services/preprocessing_service.py` - Preprocessing configurations

#### Implementation Details:
```python
class ImagePreprocessor:
    def __init__(self):
        self.pipeline_steps = [
            self.convert_to_grayscale,
            self.denoise,
            self.enhance_contrast,
            self.binarize,
            self.deskew,
            self.remove_noise
        ]

    def preprocess(self, image: Image.Image, config: PreprocessingConfig) -> Image.Image:
        processed = np.array(image)
        for step in self.pipeline_steps:
            if config.is_enabled(step.__name__):
                processed = step(processed, config)
        return Image.fromarray(processed)
```

#### Tests Required:
- **Unit**: `test_image_preprocessor.py` - Each preprocessing step
- **Integration**: `test_ocr_preprocessing_integration.py` - OCR accuracy improvement
- **Performance**: Processing time for different image sizes

#### Configuration:
```json
{
  "preprocessing": {
    "enabled": true,
    "steps": {
      "denoise": true,
      "contrast": true,
      "binarize": true,
      "deskew": false
    }
  }
}
```

---

### 5. Quick Actions Menu (Floating Context Menu) - 30 minutes

**Description**: Create floating quick access menu for common actions.

#### Files to Create/Modify:
- **CREATE** `src/ui/quick_actions_menu.py` - Floating menu widget
- **MODIFY** `src/ui/translation_overlay.py` - Show menu trigger
- **MODIFY** `src/core/coordinators/ui_coordinator.py` - Menu management

#### Implementation Details:
```python
class QuickActionsMenu:
    def __init__(self):
        self.menu_window = self._create_floating_menu()
        self.actions = {
            "capture": ("📷", self._quick_capture),
            "retry": ("🔄", self._retry_last),
            "speak": ("🔊", self._speak_last),
            "save": ("💾", self._save_last)
        }
```

#### Tests Required:
- **Unit**: `test_quick_actions_menu.py` - Menu creation, actions
- **Integration**: `test_quick_actions_integration.py` - Menu triggers

---

### 6. Context Glossaries (Game-specific Terms) - 1 hour

**Description**: Load game-specific translation dictionaries for consistent terminology.

#### Files to Create/Modify:
- **CREATE** `src/services/glossary_service.py` - Glossary management
- **CREATE** `src/domain/entities/glossary.py` - Glossary model
- **MODIFY** `src/core/translation_engine.py` - Apply glossary terms
- **CREATE** `data/glossaries/` - JSON glossary files

#### Implementation Details:
```python
class GlossaryService:
    def __init__(self):
        self.glossaries_path = Path("data/glossaries")
        self.active_glossary: Optional[Dict[str, str]] = None

    def apply_glossary(self, text: str, translation: str) -> str:
        if not self.active_glossary:
            return translation

        # Apply term replacements with context awareness
        for term, replacement in self.active_glossary.items():
            translation = self._replace_term(translation, term, replacement)
        return translation
```

#### Tests Required:
- **Unit**: `test_glossary_service.py` - Term replacement logic
- **Integration**: `test_glossary_translation_integration.py` - End-to-end translation

#### Glossary Format:
```json
{
  "game": "genshin_impact",
  "version": "1.0",
  "terms": {
    "Traveler": "Путешественник",
    "Primogem": "Примогем",
    "Resin": "Смола"
  }
}
```

---

### 7. Drop Zone Support (Drag & Drop Files/URLs) - 45 minutes

**Description**: Enhance existing drag-drop to support URLs and more file types.

#### Files to Create/Modify:
- **MODIFY** `src/ui/drag_drop_handler.py` - Add URL support
- **CREATE** `src/services/url_processor_service.py` - URL image fetching
- **MODIFY** `src/core/coordinators/ui_coordinator.py` - Drop zone integration

#### Implementation Details:
```python
class EnhancedDragDropHandler(DragDropHandler):
    def __init__(self):
        super().__init__()
        self.url_processor = container.get(URLProcessorService)
        self.supported_formats.update({".pdf", ".txt"})

    def handle_url_drop(self, url: str):
        if self._is_image_url(url):
            image = self.url_processor.fetch_image(url)
            self.process_image(image)
```

#### Tests Required:
- **Unit**: `test_enhanced_drag_drop.py` - URL parsing, file types
- **Integration**: `test_drop_zone_integration.py` - UI workflow
- **Mock**: Mock URL fetching for tests

---

### 8. Live Translation Mode (Continuous Capture) - 2 hours

**Description**: Continuous screen monitoring with change detection.

#### Files to Create/Modify:
- **CREATE** `src/services/live_translation_service.py` - Continuous capture
- **CREATE** `src/ui/live_translation_window.py` - Live mode controls
- **MODIFY** `src/core/coordinators/capture_orchestrator.py` - Live capture integration

#### Implementation Details:
```python
class LiveTranslationService:
    def __init__(self):
        self.is_active = False
        self.fps = 2
        self.last_hash = None
        self.change_threshold = 5

    async def start_live_mode(self, region: Tuple[int, int, int, int]):
        self.is_active = True
        while self.is_active:
            screenshot = await self._capture_region(region)
            if self._has_significant_change(screenshot):
                asyncio.create_task(self._process_frame(screenshot))
            await asyncio.sleep(1.0 / self.fps)
```

#### Tests Required:
- **Unit**: `test_live_translation_service.py` - Change detection, FPS control
- **Integration**: `test_live_mode_integration.py` - Full workflow
- **Performance**: Resource usage during continuous capture

---

## 🧪 Testing Strategy

### Test Structure
```
src/tests/
├── unit/
│   ├── services/
│   │   ├── test_history_search_service.py
│   │   ├── test_hotkey_profile_service.py
│   │   ├── test_game_detector_service.py
│   │   ├── test_preprocessing_service.py
│   │   ├── test_glossary_service.py
│   │   ├── test_url_processor_service.py
│   │   └── test_live_translation_service.py
│   ├── ui/
│   │   ├── test_enhanced_history_window.py
│   │   ├── test_quick_actions_menu.py
│   │   └── test_live_translation_window.py
│   └── core/
│       └── test_image_preprocessor.py
├── integration/
│   ├── test_enhanced_features_integration.py
│   ├── test_game_detection_workflow.py
│   └── test_live_translation_workflow.py
└── performance/
    ├── test_search_performance.py
    ├── test_preprocessing_performance.py
    └── test_live_mode_performance.py
```

### Test Requirements
- **Coverage Target**: ≥80% for all new code
- **Performance Tests**: All features must not degrade existing performance >10%
- **Integration Tests**: Each feature must integrate without breaking existing functionality
- **Mock Dependencies**: All external dependencies (OCR, translation APIs) properly mocked

---

## ⚠️ Risk Analysis & Mitigation

### High Risk Items

#### 1. Live Translation Mode
- **Risk**: High CPU/memory usage, system performance impact
- **Mitigation**:
  - FPS throttling (default 2 FPS)
  - Change detection to skip unchanged frames
  - Circuit breaker for resource protection
  - User controls for region selection

#### 2. OCR Preprocessing
- **Risk**: Processing time increase, quality vs speed tradeoff
- **Mitigation**:
  - Configurable preprocessing steps
  - Async processing pipeline
  - Fallback to original OCR if preprocessing fails
  - Performance benchmarking

#### 3. Game Detection
- **Risk**: Platform compatibility (Windows-specific APIs)
- **Mitigation**:
  - Platform abstraction layer
  - Graceful degradation on unsupported platforms
  - Manual game selection as fallback

### Medium Risk Items

#### 1. SQLite Migration
- **Risk**: Existing history data corruption during migration
- **Mitigation**:
  - Backup existing data before migration
  - Incremental migration approach
  - Rollback capability

#### 2. Hotkey Conflicts
- **Risk**: New profiles conflict with system/other app hotkeys
- **Mitigation**:
  - Hotkey validation before registration
  - Conflict detection and user notification
  - Easy profile customization

---

## 🏗️ Implementation Order

### Phase 1: Foundation (Day 1 - 2 hours)
1. **Hotkey Profiles** (45 min) - Low risk, high value, foundation for other features
2. **Enhanced History Window** (1 hour) - Core functionality improvement
3. **Quick Actions Menu** (30 min) - UI enhancement, integrates with other features

### Phase 2: Detection & Processing (Day 2 - 2.5 hours)
4. **Game Detection** (1.5 hours) - Enables context-aware features
5. **OCR Preprocessing** (1.5 hours) - Core accuracy improvement
6. **Context Glossaries** (45 min) - Leverages game detection

### Phase 3: Advanced Features (Day 3 - 2.5 hours)
7. **Drop Zone Support** (45 min) - Extends existing drag-drop
8. **Live Translation Mode** (2 hours) - Most complex, depends on other features

---

## 🔧 Configuration Schema

### New Configuration Sections
```json
{
  "features": {
    "enhanced_history": {
      "enabled": true,
      "search_enabled": true,
      "max_results": 100
    },
    "hotkey_profiles": {
      "enabled": true,
      "auto_switch": true,
      "default_profile": "gaming"
    },
    "game_detection": {
      "enabled": true,
      "check_interval": 5,
      "auto_load_settings": true
    },
    "ocr_preprocessing": {
      "enabled": true,
      "steps": ["denoise", "contrast", "binarize"]
    },
    "glossaries": {
      "enabled": true,
      "auto_download": true
    },
    "live_translation": {
      "enabled": true,
      "max_fps": 2,
      "change_threshold": 5
    }
  }
}
```

---

## 📊 Success Metrics

### Functional Metrics
- All 8 features implemented and functional
- Zero regression in existing functionality
- All tests pass with ≥80% coverage
- Performance impact <10% on existing operations

### Quality Metrics
- Code follows existing patterns and conventions
- All features configurable and can be disabled
- Proper error handling and logging
- Circuit breaker integration for reliability

### User Experience Metrics
- Features integrate seamlessly with existing UI
- Intuitive configuration and usage
- Responsive performance (no UI freezing)
- Proper visual feedback for all operations

---

## 🔄 Rollback Strategy

### Feature Flags
- All features controllable via configuration
- Individual feature disable without system restart
- Graceful degradation when features are disabled

### Data Safety
- All new data in separate tables/files
- Original functionality preserved
- Migration scripts can be reversed

### Testing Checkpoints
- After each feature: run full test suite
- Before integration: comprehensive regression testing
- Pre-release: performance and stability testing

---

## 📋 Definition of Done

A feature is considered **READY** when:

✅ **Implementation Complete**
- All planned files created/modified
- Integration with existing services complete
- Configuration options implemented

✅ **Testing Complete**
- Unit tests written and passing (≥80% coverage)
- Integration tests passing
- Performance tests within acceptable limits
- No regression in existing functionality

✅ **Documentation Complete**
- Code properly documented
- Configuration options documented
- Module passport updated in `docs/modules/`

✅ **Quality Gates Passed**
- All linters pass (flake8, mypy)
- Circuit breaker integration complete
- Error handling and logging implemented
- Feature can be cleanly enabled/disabled

---

## 📝 Module Passports to Update

The following module passports in `docs/modules/` need to be created or updated:

**New Passports:**
- `history_search_service.yml`
- `hotkey_profile_service.yml`
- `game_detector_service.yml`
- `image_preprocessor.yml`
- `glossary_service.yml`
- `live_translation_service.yml`

**Updated Passports:**
- `history_window.yml` - Enhanced functionality
- `hotkey_service.yml` - Profile support
- `ocr_engine.yml` - Preprocessing integration
- `drag_drop_handler.yml` - URL support

---

This plan ensures all 8 features are implemented systematically while maintaining the existing architecture's integrity and reliability principles. The staggered implementation approach allows for early validation and reduces overall project risk.
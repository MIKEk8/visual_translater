# Screen Translator v2.0 - Архитектура

## 🏗️ Обзор архитектуры

Screen Translator v2.0 построен на принципах модульной архитектуры с четким разделением ответственности, использованием современных паттернов проектирования и инверсии зависимостей.

### Основные принципы
- **Modular Design** - четкое разделение по слоям
- **Dependency Injection** - слабая связанность компонентов  
- **Async Processing** - неблокирующие операции
- **Plugin Architecture** - расширяемость через плагины
- **Observer Pattern** - реактивные изменения конфигурации

## 📦 Слои архитектуры

### Core Layer (`src/core/`)
**Бизнес-логика приложения**

```python
# Главный координатор
class ScreenTranslatorApp(ConfigObserver):
    """Управляет жизненным циклом приложения и координирует все компоненты"""
    
    def __init__(self, di_container: Optional[DIContainer] = None):
        # Dependency injection
        self.task_queue = get_task_queue()  # Async processing
        self.plugin_service = container.get(PluginService)  # Plugin system
        
        # Engines с fallback на прямые реализации
        self.ocr_processor = self._get_ocr_engine()
        self.translation_processor = self._get_translation_engine()
```

**Ключевые компоненты:**
- `ScreenshotEngine` - DPI-aware захват экрана с валидацией областей
- `OCRProcessor` - распознавание текста с предобработкой изображений
- `TranslationProcessor` - перевод с LRU кэшированием и TTL
- `TTSProcessor` - синтез речи с настраиваемыми голосами

### Services Layer (`src/services/`)
**Инфраструктурные сервисы**

```python
# Dependency Injection Container
class DIContainer:
    """Управление зависимостями с поддержкой singleton/transient/factory patterns"""
    
    def register_singleton(self, interface: Type[T], implementation: Type[T])
    def register_factory(self, interface: Type[T], factory: Callable[[], T])
    def get(self, interface: Type[T]) -> T

# Configuration Management с Observer Pattern
class ConfigManager(ConfigObserver):
    """Thread-safe управление конфигурацией с реактивными обновлениями"""
    
    def set_config_value(self, key: str, value: Any):
        # Уведомляет всех observers о изменении
        self._notify_observers(key, old_value, new_value)
```

**Ключевые сервисы:**
- `TaskQueue` - асинхронная обработка с приоритетами
- `TranslationCache` - LRU кэш с TTL и статистикой
- `PluginService` - управление плагинами
- `NotificationService` - системные уведомления

### Plugin Layer (`src/plugins/`)
**Расширяемая архитектура плагинов**

```python
# Базовые классы для плагинов
class OCRPlugin(BasePlugin):
    @abstractmethod
    def extract_text(self, image_data: bytes, languages: List[str]) -> Tuple[str, float]:
        """Извлечение текста с изображения"""

class TranslationPlugin(BasePlugin):
    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> Tuple[str, float]:
        """Перевод текста между языками"""
```

**Встроенные плагины:**
- `TesseractOCRPlugin` - OCR через Tesseract
- `GoogleTranslatePlugin` - перевод через Google Translate  
- `Pyttsx3TTSPlugin` - TTS через pyttsx3

### UI Layer (`src/ui/`)
**Пользовательский интерфейс**

- `SettingsWindow` - табbed настройки с live updates
- `TrayManager` - системный трей с контекстным меню
- `TranslationOverlay` - отображение результатов поверх экрана
- `HistoryWindow` - история переводов с поиском

### Models Layer (`src/models/`)
**Типизированные модели данных**

```python
@dataclass
class AppConfig:
    """Strongly typed конфигурация с validation"""
    version: str = "2.0.0"
    languages: LanguageConfig
    tts: TTSConfig
    features: FeatureConfig
    
    def validate(self) -> List[str]:
        """Валидация конфигурации с подробными ошибками"""

@dataclass  
class Translation:
    """Модель перевода с метаданными"""
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    timestamp: datetime
    confidence: Optional[float] = None
    cached: bool = False
```

## 🔄 Паттерны взаимодействия

### 1. Async Task Processing
```python
# Неблокирующая обработка через task queue
task_id = self.task_queue.submit(
    func=self._process_area_screenshot,
    args=(x1, y1, x2, y2),
    priority=TaskPriority.HIGH,
    callback=self._on_translation_success,
    error_callback=self._on_translation_error
)
```

### 2. Observer Pattern для конфигурации
```python
# Автоматическое обновление всех компонентов при изменении настроек
config_manager.set_config_value("tts.rate", 200)
# ↓ Уведомляет:
# - TTSProcessor → обновляет движок
# - SettingsWindow → обновляет UI
# - HotkeyManager → обновляет клавиши
```

### 3. Plugin System с Fallback
```python
# Попытка использовать плагин, fallback на прямую реализацию
def _get_ocr_engine(self) -> Any:
    try:
        ocr_plugin = self.plugin_service.get_active_plugin(PluginType.OCR)
        if ocr_plugin:
            return ocr_plugin
    except Exception as e:
        logger.warning(f"Failed to get OCR plugin: {e}")
    
    # Fallback to direct engine
    return self.container.get(OCRProcessor)
```

### 4. Caching Strategy
```python
# LRU кэш с TTL и статистикой
class TranslationCache:
    def get(self, text: str, target_language: str) -> Optional[Translation]:
        key = self._generate_key(text, target_language)
        if key in self.cache and not self._is_expired(entry):
            self.hits += 1
            return entry['translation']
        self.misses += 1
        return None
```

## 🛡️ Error Handling

### Специфичные исключения
```python
# Hierarchy of specific exceptions
class ScreenTranslatorError(Exception): pass
class ScreenshotCaptureError(ScreenTranslatorError): pass
class TranslationFailedError(ScreenTranslatorError): pass
class OCRError(ScreenTranslatorError): pass

# Контекстная обработка ошибок
def _on_translation_error(self, error: Exception):
    if isinstance(error, InvalidAreaError):
        logger.warning(f"Invalid area selected: {error.coordinates}")
    elif isinstance(error, TranslationFailedError):
        logger.error(f"Translation failed: {error.reason}")
```

## 📊 Performance Optimizations

### 1. Асинхронная обработка
- **Task Queue** с worker threads для CPU-intensive операций
- **Non-blocking UI** - все длительные операции в background
- **Priority scheduling** для критических задач

### 2. Интеллектуальное кэширование
- **LRU cache** с автоматической очисткой по TTL
- **Hit rate tracking** для оптимизации размера кэша
- **Memory-efficient** storage с compression

### 3. Thread Safety
- **Threading.Lock** для защиты shared state
- **Thread-safe collections** для concurrent access
- **Atomic operations** для критических секций

## 🔒 Security Considerations

### Input Validation
```python
# Валидация координат скриншота
def _validate_coordinates(self, x1: int, y1: int, x2: int, y2: int) -> bool:
    if x1 >= x2 or y1 >= y2:
        raise InvalidAreaError((x1, y1, x2, y2))
```

### Error Information Disclosure
```python
# Логирование без раскрытия sensitive данных
logger.error("Translation failed", 
    text_length=len(text),  # Вместо самого текста
    target_lang=target_lang,
    duration=duration
)
```

## 🧪 Testing Strategy

### Unit Tests
- **Individual components** - каждый класс покрыт тестами
- **Mocking dependencies** - изоляция через DI container
- **Edge cases** - валидация граничных условий

### Integration Tests  
- **End-to-end workflows** - полные сценарии использования
- **Plugin system** - тестирование загрузки и работы плагинов
- **Configuration changes** - проверка Observer pattern

### Performance Tests
- **Memory usage** - отслеживание утечек памяти
- **Response times** - SLA для OCR и перевода
- **Stress testing** - поведение под нагрузкой

---

*Архитектура спроектирована для максимальной модульности, тестируемости и расширяемости при сохранении высокой производительности.*
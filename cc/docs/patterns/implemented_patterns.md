# Реализованные паттерны проектирования

## 📋 Обзор паттернов в Screen Translator v2.0

### Creational Patterns (Порождающие)

#### 1. **Singleton Pattern**
**Файл:** `src/services/container.py`
**Применение:** DI Container, ConfigManager

```python
class DIContainer:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

**Преимущества:**
- Единственный экземпляр контейнера
- Глобальная точка доступа
- Контроль над созданием

#### 2. **Factory Pattern**
**Файл:** `src/plugins/plugin_manager.py`
**Применение:** Создание плагинов

```python
class PluginFactory:
    @staticmethod
    def create_plugin(plugin_type: str, config: Dict) -> BasePlugin:
        if plugin_type == "ocr":
            return TesseractOCRPlugin(config)
        elif plugin_type == "translation":
            return GoogleTranslatePlugin(config)
```

**Преимущества:**
- Инкапсуляция создания объектов
- Легкое добавление новых типов
- Единообразное создание

#### 3. **Builder Pattern**
**Файл:** `src/models/config.py`
**Применение:** Построение сложной конфигурации

```python
class ConfigBuilder:
    def with_language(self, lang: str) -> 'ConfigBuilder':
        self.config.language = lang
        return self
    
    def with_hotkeys(self, hotkeys: Dict) -> 'ConfigBuilder':
        self.config.hotkeys = hotkeys
        return self
    
    def build(self) -> AppConfig:
        return self.config
```

### Structural Patterns (Структурные)

#### 4. **Adapter Pattern**
**Файл:** `src/infrastructure/adapters/config_adapter.py`
**Применение:** Адаптация внешних библиотек

```python
class ConfigAdapter:
    """Адаптирует внешний формат конфигурации к внутреннему"""
    
    def adapt_from_json(self, json_config: Dict) -> AppConfig:
        return AppConfig(
            languages=self._adapt_languages(json_config.get('languages')),
            features=self._adapt_features(json_config.get('features'))
        )
```

**Преимущества:**
- Интеграция несовместимых интерфейсов
- Изоляция от внешних изменений
- Чистый внутренний API

#### 5. **Decorator Pattern**
**Файл:** `src/utils/performance.py`
**Применение:** Добавление функциональности

```python
def performance_monitor(func):
    """Декоратор для мониторинга производительности"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        logger.debug(f"{func.__name__} took {duration:.3f}s")
        return result
    return wrapper
```

#### 6. **Facade Pattern**
**Файл:** `src/core/application.py`
**Применение:** Упрощение сложного API

```python
class ScreenTranslatorApp:
    """Фасад для всей функциональности приложения"""
    
    def translate_screen_area(self, x1, y1, x2, y2):
        # Скрывает сложность:
        screenshot = self.screenshot_engine.capture(x1, y1, x2, y2)
        text = self.ocr_processor.extract_text(screenshot)
        translation = self.translation_processor.translate(text)
        self.tts_processor.speak(translation)
        return translation
```

### Behavioral Patterns (Поведенческие)

#### 7. **Observer Pattern**
**Файл:** `src/services/config_manager.py`
**Применение:** Уведомления об изменениях

```python
class ConfigManager:
    def __init__(self):
        self._observers: List[ConfigObserver] = []
    
    def add_observer(self, observer: ConfigObserver):
        self._observers.append(observer)
    
    def _notify_observers(self, key: str, old_value, new_value):
        for observer in self._observers:
            observer.on_config_changed(key, old_value, new_value)
```

**Использование:**
- Автообновление UI при изменении настроек
- Синхронизация компонентов
- Реактивное программирование

#### 8. **Strategy Pattern**
**Файл:** `src/core/ocr_engine.py`
**Применение:** Выбор алгоритма OCR

```python
class OCRContext:
    def __init__(self, strategy: OCRStrategy):
        self._strategy = strategy
    
    def set_strategy(self, strategy: OCRStrategy):
        self._strategy = strategy
    
    def extract_text(self, image: Image) -> str:
        return self._strategy.extract_text(image)
```

**Стратегии:**
- `TesseractStrategy` - для обычных изображений
- `EasyOCRStrategy` - для сложных шрифтов
- `PaddleOCRStrategy` - для восточных языков

#### 9. **Command Pattern**
**Файл:** `src/commands/`
**Применение:** Инкапсуляция запросов

```python
class TranslateCommand(BaseCommand):
    def __init__(self, text: str, source: str, target: str):
        self.text = text
        self.source = source
        self.target = target
    
    def execute(self) -> Translation:
        return self.receiver.translate(self.text, self.source, self.target)
    
    def undo(self):
        # Отмена операции
        pass
```

#### 10. **Chain of Responsibility**
**Файл:** `src/core/translation_workflow.py`
**Применение:** Обработка пайплайна

```python
class TranslationPipeline:
    def __init__(self):
        self.handlers = [
            ValidateInputHandler(),
            PreprocessTextHandler(),
            TranslateHandler(),
            PostprocessHandler(),
            CacheHandler()
        ]
    
    def process(self, request: TranslationRequest):
        for handler in self.handlers:
            if not handler.handle(request):
                break
        return request.result
```

#### 11. **Template Method**
**Файл:** `src/application/services/application_service_base.py`
**Применение:** Базовый алгоритм с настройкой

```python
class ApplicationServiceBase:
    def process_request(self, request):
        # Шаблонный метод
        self.validate(request)
        data = self.prepare_data(request)
        result = self.execute(data)
        self.post_process(result)
        return result
    
    @abstractmethod
    def validate(self, request):
        """Переопределяется в наследниках"""
    
    @abstractmethod
    def execute(self, data):
        """Переопределяется в наследниках"""
```

#### 12. **Iterator Pattern**
**Файл:** `src/utils/export_manager.py`
**Применение:** Итерация по результатам

```python
class TranslationIterator:
    def __init__(self, translations: List[Translation]):
        self._translations = translations
        self._index = 0
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if self._index < len(self._translations):
            result = self._translations[self._index]
            self._index += 1
            return result
        raise StopIteration
```

### Architectural Patterns (Архитектурные)

#### 13. **Repository Pattern**
**Файл:** `src/domain/protocols/repositories.py`
**Применение:** Абстракция доступа к данным

```python
class ITranslationRepository(Protocol):
    async def save(self, translation: Translation) -> str:
        ...
    
    async def find_by_id(self, id: str) -> Optional[Translation]:
        ...
    
    async def find_by_criteria(self, criteria: Dict) -> List[Translation]:
        ...
```

#### 14. **Unit of Work**
**Файл:** `src/infrastructure/persistence/`
**Применение:** Транзакционность операций

```python
class UnitOfWork:
    def __enter__(self):
        self.session = create_session()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
    
    def commit(self):
        self.session.commit()
    
    def rollback(self):
        self.session.rollback()
```

#### 15. **CQRS (Command Query Responsibility Segregation)**
**Файлы:** `src/commands/`, `src/queries/`
**Применение:** Разделение команд и запросов

```python
# Commands изменяют состояние
class SaveTranslationCommand:
    def execute(self, translation: Translation):
        self.repository.save(translation)

# Queries читают данные
class GetTranslationQuery:
    def execute(self, id: str) -> Translation:
        return self.repository.find_by_id(id)
```

### Concurrency Patterns (Параллелизм)

#### 16. **Producer-Consumer**
**Файл:** `src/services/task_queue.py`
**Применение:** Асинхронная обработка

```python
class TaskQueue:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.workers = []
    
    async def produce(self, task: Task):
        await self.queue.put(task)
    
    async def consume(self):
        while True:
            task = await self.queue.get()
            await task.execute()
```

#### 17. **Circuit Breaker**
**Файл:** `src/services/circuit_breaker.py`
**Применение:** Защита от сбоев

```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.state = CircuitState.CLOSED
    
    async def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            raise CircuitOpenError()
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
```

## 📊 Статистика использования паттернов

| Категория | Количество | Покрытие |
|-----------|------------|----------|
| Creational | 3 | 15% |
| Structural | 3 | 20% |
| Behavioral | 6 | 35% |
| Architectural | 3 | 20% |
| Concurrency | 2 | 10% |

## 🎯 Рекомендации по применению

### Где добавить паттерны
1. **State Pattern** - для управления состоянием приложения
2. **Memento Pattern** - для undo/redo функциональности
3. **Proxy Pattern** - для lazy loading тяжелых ресурсов
4. **Flyweight Pattern** - для оптимизации памяти при работе с изображениями

### Антипаттерны для избежания
1. **God Object** - уже исправлен в v2.0
2. **Spaghetti Code** - предотвращается модульной архитектурой
3. **Copy-Paste Programming** - используем наследование и композицию
4. **Magic Numbers** - все константы вынесены в конфиг
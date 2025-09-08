# Архитектура системы Screen Translator v2.0

## 📊 Обзор архитектуры

**Дата обновления:** 2025-08-23  
**Версия:** 2.0  
**Статус:** Production Ready

### Ключевые принципы
- **Clean Architecture** - четкое разделение слоев
- **Dependency Injection** - слабая связанность через DI
- **Plugin System** - расширяемость через плагины
- **Event-Driven** - асинхронная обработка событий
- **Observer Pattern** - реактивные изменения

## 🏗️ Слоевая архитектура

```
┌─────────────────────────────────────────┐
│          Presentation Layer (UI)         │
├─────────────────────────────────────────┤
│         Application Layer (Use Cases)    │
├─────────────────────────────────────────┤
│           Domain Layer (Entities)        │
├─────────────────────────────────────────┤
│      Infrastructure Layer (Services)     │
└─────────────────────────────────────────┘
```

### Domain Layer (`src/domain/`)
**Чистая бизнес-логика без зависимостей**

#### Entities
- `Screenshot` - снимок экрана с метаданными
- `Translation` - результат перевода
- `Preferences` - пользовательские настройки

#### Value Objects
- `Coordinates` - координаты области экрана
- `Language` - язык с валидацией ISO кода
- `Text` - текст с нормализацией
- `DomainId` - уникальный идентификатор

#### Protocols
- `IRepository` - интерфейс репозитория
- `ITranslationService` - интерфейс сервиса перевода
- `IOCRService` - интерфейс OCR сервиса

### Application Layer (`src/application/`)
**Use cases и координация**

#### Use Cases
- `CaptureScreenshotUseCase` - захват области экрана
- `TranslateTextUseCase` - перевод текста
- `SavePreferencesUseCase` - сохранение настроек

#### Services
- `ScreenshotAppService` - обработка скриншотов
- `TranslationAppService` - управление переводами
- `ApplicationServiceBase` - базовый класс сервисов

#### DTOs
- `ScreenshotDTO` - передача данных скриншота
- `TranslationDTO` - передача данных перевода
- `PreferencesDTO` - передача настроек

### Infrastructure Layer (`src/infrastructure/`)
**Внешние сервисы и адаптеры**

#### Services
- `OCRService` - реализация OCR через Tesseract
- `TranslationService` - Google Translate API
- `ScreenCaptureService` - захват экрана
- `TTSService` - синтез речи

#### Adapters
- `ConfigAdapter` - адаптер конфигурации
- `CacheAdapter` - адаптер кэширования
- `LoggerAdapter` - адаптер логирования

### Core Layer (`src/core/`)
**Координаторы и движки**

#### Coordinators
- `ApplicationController` - главный координатор
- `CaptureOrchestrator` - координация захвата
- `TranslationWorkflow` - пайплайн перевода
- `UICoordinator` - управление UI
- `BatchExportManager` - массовые операции

#### Engines
- `ScreenshotEngine` - DPI-aware захват
- `OCREngine` - распознавание текста
- `TranslationEngine` - механизм перевода
- `TTSEngine` - синтез речи

## 🔌 Plugin Architecture

### Базовая структура плагина
```python
class BasePlugin(ABC):
    """Базовый класс для всех плагинов"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Уникальное имя плагина"""
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Версия плагина"""
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Инициализация с конфигурацией"""
    
    @abstractmethod
    def shutdown(self) -> None:
        """Корректное завершение работы"""
```

### Типы плагинов
1. **OCR Plugins** - распознавание текста
2. **Translation Plugins** - перевод текста
3. **TTS Plugins** - синтез речи
4. **UI Plugins** - пользовательский интерфейс
5. **Filter Plugins** - обработка данных

### Жизненный цикл плагина
1. **Discovery** - автоматическое обнаружение
2. **Registration** - регистрация в системе
3. **Initialization** - инициализация с конфигом
4. **Execution** - выполнение задач
5. **Shutdown** - корректное завершение

## 🔄 Паттерны проектирования

### Dependency Injection
```python
# Регистрация сервисов
container.register_singleton(ConfigManager, ConfigManager)
container.register_factory(OCRProcessor, create_ocr_processor)
container.register_transient(TranslationService, GoogleTranslateService)

# Использование
config = container.get(ConfigManager)
ocr = container.get(OCRProcessor)
```

### Observer Pattern
```python
# Подписка на изменения конфигурации
config_manager.add_observer(hotkey_manager)
config_manager.add_observer(tts_processor)

# Изменение вызывает уведомления
config_manager.set_config_value("tts.rate", 200)
```

### Strategy Pattern
```python
# Различные стратегии OCR
class OCRStrategy(ABC):
    def extract_text(self, image: Image) -> str

class TesseractStrategy(OCRStrategy):
    def extract_text(self, image: Image) -> str

class EasyOCRStrategy(OCRStrategy):
    def extract_text(self, image: Image) -> str
```

### Factory Pattern
```python
# Фабрика создания движков
class EngineFactory:
    @staticmethod
    def create_ocr_engine(type: str) -> OCREngine:
        if type == "tesseract":
            return TesseractOCR()
        elif type == "easyocr":
            return EasyOCR()
```

## 📊 Метрики архитектуры

| Метрика | Значение | Цель |
|---------|----------|------|
| Модулей | 24 | - |
| Классов | 566 | - |
| Функций | 2,567 | - |
| Строк кода | 46,735 | - |
| Тестовое покрытие | 41.4% | 60%+ |
| Цикломатическая сложность | Avg 4.2 | <5 |
| Связанность модулей | Low | Low |
| Cohesion | High | High |

## 🚀 Производительность

### Оптимизации
- **Async Processing** - неблокирующие операции
- **LRU Cache** - кэширование переводов
- **Connection Pooling** - пул соединений
- **Lazy Loading** - отложенная загрузка
- **Resource Pooling** - переиспользование ресурсов

### Bottlenecks
- OCR обработка больших изображений
- Сетевые запросы к API переводчика
- UI рендеринг больших списков

## 🔒 Безопасность

### Реализованные меры
- Input validation на всех слоях
- Sanitization пользовательского ввода
- Rate limiting для API
- Secure storage для настроек
- Audit logging критических операций

### Потенциальные риски
- Отсутствие шифрования кэша
- Хранение API ключей в конфиге
- Недостаточная валидация плагинов

## 📈 Масштабируемость

### Горизонтальное масштабирование
- Task Queue для распределения нагрузки
- Stateless сервисы
- Независимые плагины

### Вертикальное масштабирование
- Оптимизация алгоритмов
- Использование GPU для OCR
- Параллельная обработка

## 🔄 Эволюция архитектуры

### v1.0 → v2.0
- Монолит (1,042 строки) → Модульная архитектура
- Синхронный код → Асинхронная обработка
- Жесткие зависимости → Dependency Injection
- Без тестов → 41.4% покрытие

### Планы на v3.0
- Микросервисная архитектура
- GraphQL API
- WebAssembly для браузера
- Cloud-native deployment
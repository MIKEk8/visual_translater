# Screen Translator v2.0 - Документация

## 🎯 Обзор

Screen Translator v2.0 - современное десктопное приложение для захвата, распознавания и перевода текста с экрана в реальном времени. Полностью переписано с модульной архитектурой и современными подходами.

## 🏗️ Архитектура

### Структура проекта
```
src/
├── core/                    # Основная бизнес-логика
│   ├── application.py       # Главный координатор приложения
│   ├── screenshot_engine.py # DPI-aware захват экрана
│   ├── ocr_engine.py       # OCR с предобработкой изображений
│   ├── translation_engine.py # Перевод с кэшированием
│   └── tts_engine.py       # Text-to-Speech
├── services/               # Сервисный слой
│   ├── config_manager.py   # Управление конфигурацией (Observer pattern)
│   ├── cache_service.py    # LRU кэш с TTL
│   ├── task_queue.py       # Асинхронная обработка задач
│   ├── container.py        # Dependency Injection
│   └── *_service.py        # Другие сервисы
├── plugins/                # Плагиновая система
│   ├── base_plugin.py      # Базовые классы плагинов
│   ├── plugin_manager.py   # Менеджер плагинов
│   └── builtin/           # Встроенные плагины
├── ui/                     # Пользовательский интерфейс
│   ├── settings_window.py  # Окно настроек
│   ├── tray_manager.py     # Системный трей
│   └── *_window.py         # Другие UI компоненты
├── models/                 # Модели данных
│   ├── config.py          # Типизированная конфигурация
│   └── translation.py     # Модели переводов и скриншотов
├── utils/                  # Утилиты
│   ├── logger.py          # Структурированное логирование
│   └── exceptions.py      # Специфичные исключения
└── tests/                 # Тесты
    ├── unit/              # Unit тесты
    └── integration/       # Интеграционные тесты
```

### Ключевые паттерны
- **Observer Pattern** - для реактивных изменений конфигурации
- **Dependency Injection** - для слабой связанности компонентов
- **Plugin Architecture** - для расширяемости движков
- **Task Queue** - для асинхронной обработки

## 🚀 Запуск и разработка

### Быстрый старт
```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск приложения
python main.py

# Запуск в windowed режиме
python main.py --windowed

# Запуск с отладкой
python main.py --debug
```

### Тестирование
```bash
# Интеграционные тесты (по умолчанию через pytest config)
wenv\Scripts\python.exe -m pytest -q

# Явный запуск интеграционных
wenv\Scripts\python.exe -m pytest -q src/tests/integration

# Запуск unit-тестов вручную (наследие v1.x, могут требовать адаптации)
wenv\Scripts\python.exe -m pytest -q src/tests/unit

# Coverage
wenv\Scripts\python.exe -m pytest --cov=src --cov-report=term-missing
```

### Code Quality
```bash
# Форматирование
black src/ --line-length 100
isort src/ --profile black

# Линтинг
flake8 src/ --max-line-length=100

# Типизация
mypy src/ --ignore-missing-imports
```

### Сборка
```bash
# Executable файл
pyinstaller --onefile --windowed --icon=icon.ico --name=ScreenTranslator main.py
```

## ⚙️ Конфигурация

Конфигурация автоматически создается в `config.json` при первом запуске. Основные разделы:

```json
{
  "version": "2.0.0",
  "languages": {
    "ocr_languages": ["rus", "eng"],
    "target_languages": ["ru", "en", "ja", "de"],
    "default_target": 0
  },
  "tts": {
    "enabled": true,
    "voice_settings": { "rate": 150, "volume": 0.8 }
  },
  "features": {
    "cache_translations": true,
    "copy_to_clipboard": true,
    "save_debug_screenshots": false
  },
  "image_processing": {
    "enhance_contrast": true,
    "upscale_factor": 2.0,
    "denoise": true
  }
}
```

## 🔌 Плагиновая система

### Создание плагина
```python
from src.plugins.base_plugin import OCRPlugin, PluginMetadata, PluginType

class MyOCRPlugin(OCRPlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="MyOCR",
            version="1.0.0",
            description="Custom OCR engine",
            author="Author",
            plugin_type=PluginType.OCR
        )
    
    def extract_text(self, image_data: bytes, languages: List[str]) -> Tuple[str, float]:
        # Реализация OCR
        return extracted_text, confidence
```

### Типы плагинов
- **OCR** - движки распознавания текста
- **Translation** - сервисы перевода
- **TTS** - движки синтеза речи

## 🎮 Горячие клавиши (по умолчанию)

- `Alt+A` - Выбор области экрана для перевода
- `Alt+Q` - Быстрый перевод центра экрана
- `Alt+W` - Быстрый перевод низа экрана
- `Alt+S` - Повтор последнего перевода
- `Alt+L` - Переключение языка перевода

## 🔧 Расширенные возможности

### Кэширование
- **LRU кэш** с TTL для переводов
- **Статистика** hit rate и performance metrics
- **Автоочистка** устаревших записей

### Асинхронная обработка
- **Task Queue** с приоритетами
- **Non-blocking UI** при обработке
- **Background workers** для OCR/Translation

### Обработка ошибок
- **Специфичные исключения** для разных типов ошибок
- **Graceful degradation** при сбоях сервисов
- **Подробное логирование** для отладки

## 📊 Мониторинг и метрики

### Логирование
```python
from src.utils.logger import logger

# Структурированное логирование
logger.log_translation(original, translated, source_lang, target_lang, duration)
logger.log_screenshot(coordinates, size, duration)
logger.log_ocr(text_length, confidence, duration)
```

### Метрики кэша
```python
cache_stats = translation_processor.get_cache_stats()
# {
#   'hit_rate': 0.85,
#   'total_requests': 1000,
#   'size': 50
# }
```

## 🚦 CI/CD

Проект настроен с GitHub Actions для:
- **Multi-OS testing** (Ubuntu, Windows, macOS)
- **Code quality checks** (black, flake8, mypy)
- **Security scanning** (bandit, safety)
- **Automated builds** для всех платформ
- **Coverage reports**

## 🔒 Безопасность

- **Input validation** для всех пользовательских данных
- **No secrets in code** - все конфиденциальные данные в конфигурации
- **Regular security scans** в CI/CD pipeline
- **Minimal permissions** для системных операций

## 🤝 Участие в разработке

1. **Fork** проекта
2. **Создать feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit изменения**: `git commit -m 'Add amazing feature'`
4. **Push в branch**: `git push origin feature/amazing-feature`
5. **Открыть Pull Request**

### Code Style
- **Black** для форматирования (line-length=100)
- **isort** для сортировки импортов
- **Type hints** для всех публичных методов
- **Docstrings** для всех классов и функций

## 📝 Лицензия

MIT License - см. LICENSE файл для деталей.
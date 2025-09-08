# Руководство по разработке Screen Translator v2.0

## 🚀 Quick Start

### Настройка окружения

#### Windows
```powershell
# 1. Клонировать репозиторий
git clone <repository>
cd screen-translator

# 2. Настроить окружение (автоматически)
.\dev.ps1 setup

# 3. Запустить тесты
.\dev.ps1 test

# 4. Запустить приложение
.\dev.ps1 run
```

#### Linux/macOS
```bash
# 1. Клонировать репозиторий
git clone <repository>
cd screen-translator

# 2. Настроить окружение (автоматически)
./dev.sh setup

# 3. Запустить тесты
./dev.sh test

# 4. Запустить приложение
./dev.sh run
```

## 📁 Структура проекта

```
screen-translator/
├── src/                    # Исходный код
│   ├── core/              # Бизнес-логика
│   ├── domain/            # Доменные модели
│   ├── application/       # Use cases
│   ├── infrastructure/    # Внешние сервисы
│   ├── ui/                # Пользовательский интерфейс
│   ├── services/          # Инфраструктурные сервисы
│   ├── plugins/           # Система плагинов
│   └── tests/             # Тесты
├── docs/                   # Документация проекта
├── cc/                     # Claude Code документация
│   ├── tasks/             # Журнал задач
│   ├── docs/              # Техническая документация
│   └── analysis/          # Отчеты анализа
├── tmp/                    # Временные файлы
├── tools/                  # Инструменты разработки
└── dist/                   # Собранные бинарники
```

## 🔧 Команды разработки

### Основные команды

| Команда | Windows | Linux/macOS | Описание |
|---------|---------|-------------|----------|
| Setup | `.\dev.ps1 setup` | `./dev.sh setup` | Настройка окружения |
| Test | `.\dev.ps1 test` | `./dev.sh test` | Запуск всех тестов |
| Lint | `.\dev.ps1 lint` | `./dev.sh lint` | Проверка кода |
| Build | `.\dev.ps1 build` | `./dev.sh build` | Сборка exe |
| Run | `.\dev.ps1 run` | `./dev.sh run` | Запуск из исходников |

### Расширенные команды

```bash
# Тесты с покрытием
./dev.sh test coverage

# Только unit тесты
./dev.sh test unit

# Автоисправление кода
./dev.sh lint fix

# Debug сборка
./dev.sh build debug

# Полная проверка качества
./dev.sh quality

# CI pipeline
./dev.sh ci
```

## 🧪 Тестирование

### Структура тестов
```
src/tests/
├── unit/              # Модульные тесты
│   ├── core/         # Тесты бизнес-логики
│   ├── domain/       # Тесты доменных моделей
│   └── services/     # Тесты сервисов
└── integration/       # Интеграционные тесты
    ├── test_main_scenarios.py
    └── test_system_integration.py
```

### Запуск тестов
```python
# Запуск конкретного теста
.venv/bin/python -m pytest src/tests/unit/test_config_manager.py

# Запуск с покрытием
.venv/bin/python -m pytest --cov=src --cov-report=html

# Запуск с маркерами
.venv/bin/python -m pytest -m "not slow"
```

### Написание тестов
```python
import pytest
from unittest.mock import Mock, patch

class TestTranslationEngine:
    @pytest.fixture
    def engine(self):
        """Фикстура для создания движка"""
        return TranslationEngine()
    
    def test_translate_success(self, engine):
        """Тест успешного перевода"""
        result = engine.translate("Hello", "en", "ru")
        assert result == "Привет"
    
    @patch('src.core.translation_engine.external_api')
    def test_translate_with_mock(self, mock_api, engine):
        """Тест с моком внешнего API"""
        mock_api.translate.return_value = "Привет"
        result = engine.translate("Hello", "en", "ru")
        mock_api.translate.assert_called_once()
```

## 💻 Добавление новой функциональности

### 1. Добавление нового OCR движка

```python
# 1. Создать плагин в src/plugins/builtin/
class NewOCRPlugin(OCRPlugin):
    def extract_text(self, image_data: bytes, languages: List[str]) -> Tuple[str, float]:
        # Реализация
        text = self._process_with_new_engine(image_data)
        confidence = self._calculate_confidence()
        return text, confidence

# 2. Зарегистрировать в plugin_manager.py
self.register_plugin('new_ocr', NewOCRPlugin)

# 3. Добавить тесты
class TestNewOCRPlugin:
    def test_extract_text(self):
        plugin = NewOCRPlugin()
        text, conf = plugin.extract_text(image_data, ['en'])
        assert text == "expected"
```

### 2. Добавление нового UI компонента

```python
# 1. Создать компонент в src/ui/
class NewFeatureWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        # UI setup
        pass

# 2. Интегрировать в главное приложение
class ScreenTranslatorApp:
    def show_new_feature(self):
        self.new_feature_window = NewFeatureWindow(self.root)

# 3. Добавить горячую клавишу
self.hotkey_manager.register("show_new_feature", "<Control-N>", self.show_new_feature)
```

### 3. Добавление нового сервиса

```python
# 1. Создать сервис в src/services/
class NewService:
    def __init__(self, config: Dict):
        self.config = config
    
    async def process(self, data: Any) -> Any:
        # Обработка
        return result

# 2. Зарегистрировать в DI контейнере
container.register_singleton(NewService, NewService)

# 3. Использовать через DI
class SomeComponent:
    def __init__(self):
        self.new_service = container.get(NewService)
```

## 🐛 Отладка

### Включение debug режима
```python
# В config.json
{
    "debug": true,
    "log_level": "DEBUG"
}
```

### Логирование
```python
from src.utils.logger import logger

# Различные уровни
logger.debug("Debug информация")
logger.info("Информационное сообщение")
logger.warning("Предупреждение")
logger.error("Ошибка", exc_info=True)

# Структурированное логирование
logger.log_translation(
    original="Hello",
    translated="Привет",
    source_lang="en",
    target_lang="ru",
    duration=0.5
)
```

### Профилирование
```python
from src.utils.performance import performance_monitor

@performance_monitor
def slow_function():
    # Код функции
    pass

# Или вручную
from src.utils.performance_monitor import PerformanceMonitor

monitor = PerformanceMonitor()
monitor.start_operation("translation")
# ... код ...
monitor.end_operation("translation")
print(monitor.get_report())
```

## 📦 Сборка и распространение

### Сборка executable
```bash
# Release версия (без консоли)
./dev.sh build

# Debug версия (с консолью)
./dev.sh build debug

# Результат в dist/ScreenTranslator.exe
```

### Создание installer
```bash
# Использование NSIS
makensis installer.nsi

# Или InnoSetup
iscc installer.iss
```

## 🔍 Качество кода

### Проверка качества
```bash
# Полная проверка (11 анализаторов)
./dev.sh quality

# Автоисправление
./dev.sh quality fix
```

### Инструменты качества
1. **Black** - форматирование
2. **isort** - сортировка импортов
3. **Flake8** - стиль кода
4. **MyPy** - типизация
5. **Pylint** - качество кода
6. **Bandit** - безопасность
7. **Vulture** - мертвый код
8. **Radon** - метрики сложности

### Pre-commit hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.0.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
```

## 📝 Документирование

### Документирование кода
```python
def translate_text(
    text: str,
    source_lang: str = "auto",
    target_lang: str = "en"
) -> Translation:
    """
    Переводит текст с одного языка на другой.
    
    Args:
        text: Текст для перевода
        source_lang: Исходный язык (ISO код)
        target_lang: Целевой язык (ISO код)
    
    Returns:
        Translation: Объект с результатом перевода
    
    Raises:
        TranslationError: Если перевод не удался
    
    Example:
        >>> result = translate_text("Hello", "en", "ru")
        >>> print(result.translated_text)
        "Привет"
    """
```

### Ведение документации в /cc/
```bash
# Дневной лог задач
/cc/tasks/YYYY-MM-DD.md

# TODO списки
/cc/tasks/TODO_feature_name.md

# Архитектурные заметки
/cc/docs/architecture_notes.md

# Анализ и метрики
/cc/analysis/performance_report.md
```

## 🚨 Troubleshooting

### Проблема: Тесты не запускаются
```bash
# Проверить виртуальное окружение
source .venv/bin/activate  # Linux
.venv\Scripts\activate     # Windows

# Переустановить зависимости
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Проблема: ImportError
```python
# Добавить путь к PYTHONPATH
import sys
sys.path.insert(0, '/path/to/project')

# Или использовать relative imports
from ..core import SomeModule
```

### Проблема: Сборка не работает
```bash
# Очистить кэш
./dev.sh clean

# Пересобрать с нуля
./dev.sh build --clean
```

## 🤝 Contributing

### Процесс внесения изменений
1. Создать feature branch
2. Написать тесты
3. Реализовать функциональность
4. Проверить качество кода
5. Создать pull request

### Code review checklist
- [ ] Тесты написаны и проходят
- [ ] Документация обновлена
- [ ] Код соответствует стилю
- [ ] Нет дублирования кода
- [ ] Производительность учтена
- [ ] Безопасность проверена
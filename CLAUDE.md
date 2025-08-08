# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 CRITICAL: Python Virtual Environment Usage

**ALWAYS use Python from virtual environment:**
```bash
# For Claude (Linux environment):
.venv/bin/python    # NOT python or python3
.venv/bin/pip       # NOT pip or pip3

# For Windows development:
wenv\Scripts\python.exe
wenv\Scripts\pip.exe
```

**NEVER use system Python!** This is critical for proper dependency management.

## Project Overview

This is **Screen Translator v2.0** - a completely refactored Windows desktop application that captures screen regions, performs OCR text recognition, and provides real-time translation with text-to-speech capabilities. The application now uses a **modular architecture** with dependency injection, observer patterns, and clean separation of concerns.

### **🎯 Personal Project Scope**

**ВАЖНО**: Это приложение создано исключительно для личного использования разработчика. В связи с этим:

- ❌ **Обратная совместимость** со старыми версиями НЕ требуется
- ❌ **Миграция конфигураций** из v1.0 НЕ нужна  
- ❌ **Поддержка авторских прав** третьих лиц НЕ предусматривается
- ❌ **Функционал для других пользователей** НЕ планируется
- ❌ **Сохранение настроек** из предыдущих версий НЕ обязательно

✅ **Принципы разработки:**
- Код оптимизирован для **одного пользователя** (разработчика)
- Можно **полностью переписывать** любые компоненты без оглядки на совместимость
- **Экспериментальные решения** приветствуются
- **Производительность и удобство** важнее универсальности
- **Чистый код** важнее поддержки legacy функций

## Architecture Overview

### 🏗️ **Modular Structure**
```
src/
├── core/           # Business logic engines
├── ui/             # User interface components  
├── services/       # Infrastructure services
├── models/         # Data models and entities
├── utils/          # Utility modules
├── tests/          # Unit and integration tests
tmp/                # Temporary scripts created by Claude
├── diagnose_*.py   # Diagnostic utilities
├── fix_*.py        # Automated fixes
└── test_*.py       # Test utilities
```

### 🔧 **Core Components**

#### **Engines** (`src/core/`)
- **`ScreenshotEngine`** - DPI-aware screen capture with area validation
- **`OCRProcessor`** - Tesseract OCR with image enhancement pipeline
- **`TranslationProcessor`** - Google Translate with caching support
- **`TTSProcessor`** - pyttsx3 TTS with voice/device selection
- **`ScreenTranslatorApp`** - Main application coordinator

#### **Services** (`src/services/`)
- **`ConfigManager`** - Observer pattern config management
- **`HotkeyManager`** - Global hotkey registration/management  
- **`TranslationCache`** - LRU cache with TTL for translations
- **`DIContainer`** - Dependency injection container

#### **UI Components** (`src/ui/`)
- **`SettingsWindow`** - Tabbed settings interface with live updates
- **`TrayManager`** - System tray with context menu

#### **Models** (`src/models/`)
- **`AppConfig`** - Strongly typed configuration with validation
- **`Translation`** - Translation data with metadata
- **`ScreenshotData`** - Screenshot information container

## Development Commands

### **🚀 Unified Build System**

The project includes a comprehensive build system supporting all platforms:

#### **⚠️ КРИТИЧЕСКИ ВАЖНО: Платформо-Специфичные Virtual Environment**

**Используйте правильные инструменты для каждой платформы:**

### **🪟 Windows: wenv (Windows Environment)**
```cmd
REM 1. Создание виртуального окружения (один раз)
python -m venv wenv

REM 2. Активация (каждый раз перед работой)
wenv\Scripts\activate

REM 3. Установка зависимостей
pip install -r requirements.txt
pip install -r requirements-dev.txt

REM 4. Работа с проектом (только после активации wenv!)
python build.py install --dev
python build.py test --coverage
python build.py build
```

### **🐧 Linux/macOS: venv (Virtual Environment)**
```bash
# 1. Создание виртуального окружения (один раз)
python3 -m venv venv

# 2. Активация (каждый раз перед работой)
source venv/bin/activate

# 3. Установка зависимостей
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Работа с проектом (только после активации venv!)
python build.py install --dev
python build.py test --coverage
python build.py build
```

**🚨 БЕЗ ВИРТУАЛЬНОГО ОКРУЖЕНИЯ НЕ РАБОТАТЬ!** Это может привести к:
- Конфликтам зависимостей
- Поломке системного Python
- Непредсказуемому поведению приложения
- Проблемам с externally-managed-environment

#### **Quick Start**
```bash
# ВСЕГДА сначала активируйте venv!
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate     # Windows

# Затем уже работайте с проектом:
python build.py install --dev
python build.py test --coverage
python build.py lint
python build.py build
```

#### **Cross-Platform Convenience Scripts**

**🔥 ВАЖНО: Скрипты автоматически создают и используют платформо-специфичные окружения!**

**🐧 Linux/macOS (dev.sh) - использует venv:**
```bash
# Скрипты АВТОМАТИЧЕСКИ создают venv и устанавливают зависимости
./dev.sh setup                 # Создает venv + устанавливает зависимости
./dev.sh test                  # Активирует venv + запускает тесты
./dev.sh test unit             # Активирует venv + unit тесты
./dev.sh lint fix              # Активирует venv + исправляет код
./dev.sh build                 # Активирует venv + собирает executable
./dev.sh run                   # Активирует venv + запускает приложение
```

**🪟 Windows (dev.ps1) - использует wenv:**
```powershell
# Скрипты АВТОМАТИЧЕСКИ создают wenv и устанавливают зависимости
.\dev.ps1 setup                # Создает wenv + устанавливает зависимости
.\dev.ps1 test                 # Активирует wenv + запускает тесты
.\dev.ps1 test coverage        # Активирует wenv + тесты с покрытием
.\dev.ps1 lint                 # Активирует wenv + проверяет код
.\dev.ps1 build debug          # Активирует wenv + debug сборка
.\dev.ps1 run debug            # Активирует wenv + запуск с отладкой
```

**Make (all platforms):**
```bash
make setup                     # Initial project setup
make test                      # Run all tests
make lint                      # Check code quality
make build                     # Build release executable
make clean                     # Clean build artifacts
make ci                        # Run full CI pipeline
```

#### **Available Build Commands**
- **`install`** - Install production dependencies
- **`install --dev`** - Install development dependencies
- **`test`** - Run all tests with automatic discovery
- **`test --coverage`** - Run tests with coverage report
- **`test --type unit`** - Run unit tests only
- **`test --type integration`** - Run integration tests only
- **`lint`** - Check code quality (flake8, black, isort, mypy)
- **`lint --fix`** - Auto-fix code quality issues
- **`build`** - Build release executable with PyInstaller
- **`build --mode debug`** - Build debug executable
- **`security`** - Run security scans (bandit, safety)
- **`clean`** - Clean build artifacts and cache files
- **`ci`** - Run complete CI pipeline (test + lint + security + build)

### **🚨 ВАЖНО: Правила взаимодействия с проектом**

#### **👤 Для человека (разработчика):**

### **🪟 На Windows (ОБЯЗАТЕЛЬНО dev.ps1 + wenv):**
```powershell
# Единственный интерфейс для человека (АВТОМАТИЧЕСКИ использует wenv):
.\dev.ps1 setup            # Создает wenv + настройка окружения
.\dev.ps1 test             # Активирует wenv + запуск тестов
.\dev.ps1 build            # Активирует wenv + сборка приложения
.\dev.ps1 run              # Активирует wenv + запуск из исходников
.\dev.ps1 lint             # Активирует wenv + проверка кода
```

### **🐧 На Linux/macOS (ОБЯЗАТЕЛЬНО dev.sh + venv):**
```bash
# Единственный интерфейс для человека (АВТОМАТИЧЕСКИ использует venv):
./dev.sh setup              # Создает venv + настройка окружения
./dev.sh test               # Активирует venv + запуск тестов
./dev.sh build              # Активирует venv + сборка приложения
./dev.sh run                # Активирует venv + запуск из исходников
./dev.sh lint               # Активирует venv + проверка кода
```

**🚨 КРИТИЧЕСКИ ВАЖНО для человека:**
- **Windows**: НЕ активировать wenv вручную - dev.ps1 делает это автоматически
- **Linux**: НЕ активировать venv вручную - dev.sh делает это автоматически
- **НЕ использовать системный Python** для этого проекта
- **Всегда использовать платформо-специфичные скрипты**

#### **🤖 Для Claude Code (ИИ-помощника):**
**⚠️ ВАЖНО: Claude должен учитывать платформо-специфичные окружения!**

### **Подход Claude к Virtual Environments:**

**🪟 В Windows-среде:**
- **Предпочтительно**: Проверять наличие `wenv\Scripts\activate` 
- **Использовать**: `wenv\Scripts\python.exe` для команд
- **Альтернатива**: Системный Python с предупреждением

**🐧 В Linux/macOS-среде:**
- **Предпочтительно**: Проверять наличие `venv/bin/activate`
- **Использовать**: `source venv/bin/activate` перед командами  
- **Альтернатива**: Системный Python с предупреждением

**Универсальная проверка для Claude:**
```bash
# Linux/macOS
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    python build.py test
elif [ -f "wenv/Scripts/activate" ]; then
    # Windows wenv в Linux-окружении
    wenv/Scripts/python.exe build.py test 2>/dev/null || python3 build.py test
else
    echo "⚠️ Ни venv, ни wenv не найдены, использую системный Python"
    python3 build.py test
fi
```

**Возможности Claude:**
- Может использовать любые команды при наличии виртуального окружения
- Может работать напрямую с исходным кодом
- Должен предупреждать о работе без виртуального окружения
- Может вызывать низкоуровневые инструменты

#### **🎯 Цель архитектуры:**
- **Человек**: Простой интерфейс через `dev.ps1` + готовый `ScreenTranslator.exe`
- **Claude**: Полный доступ ко всем инструментам для разработки и отладки

#### **📁 Правила для временных файлов Claude**

**🤖 ВАЖНО для Claude Code:** Все временные скрипты и диагностические утилиты создавать в папке `tmp/`

**✅ Правильно:**
```python
# Создание временного скрипта диагностики
Write("/workspace/tmp/diagnose_imports.py", content="...")

# Создание утилиты исправления
Write("/workspace/tmp/fix_tests.py", content="...")

# Создание одноразового скрипта
Write("/workspace/tmp/check_syntax.py", content="...")
```

**❌ Неправильно:**
```python
# НЕ создавать в корневой директории
Write("/workspace/diagnose_imports.py", content="...")

# НЕ создавать в src/
Write("/workspace/src/fix_tests.py", content="...")
```

**📋 Типы файлов для tmp/:**
- `diagnose_*.py` - скрипты диагностики проблем
- `fix_*.py` - скрипты автоматического исправления 
- `test_*.py` - утилиты тестирования
- `check_*.py` - скрипты проверки
- `run_*.py` - временные скрипты запуска
- `*.tmp` - любые временные файлы

**🧹 Очистка:** Папка `tmp/` может быть очищена в любое время без потери важных данных.

### **🪟 Windows Build Instructions**

**⚠️ ВАЖНО**: Исполняемые файлы должны собираться на той же платформе, где будут запускаться:
- Windows executable → собирать на Windows
- Linux executable → собирать на Linux

#### **Для человека (ТОЛЬКО через dev.ps1 + wenv):**
```powershell
# dev.ps1 автоматически создает и использует wenv!
.\dev.ps1 setup            # Создает wenv + настройка окружения (один раз)
.\dev.ps1 build            # Активирует wenv + релизная версия
.\dev.ps1 build debug      # Активирует wenv + отладочная версия (с консолью)
```

#### **Для Claude (команды с wenv/venv):**
```batch
REM Рекомендуемые команды для Claude (с автоматическим wenv):
python build.py wenv-create                    REM Создать wenv (Windows)
python build.py wenv-install --dev --build     REM Установить зависимости в wenv
python build.py build --wenv                   REM Собрать используя wenv

REM Альтернатива: legacy venv поддержка
python build.py venv-create                    REM Создать venv (legacy)
python build.py venv-install --dev --build     REM Установить зависимости в venv
python build.py build --venv                   REM Собрать используя venv

REM Или прямые команды (если окружение уже активировано):
build_exe.bat
python build.py build
```

**🔥 Для Claude: Универсальная проверка Windows:**
```batch
REM Проверяем wenv (приоритет), затем venv (legacy)
if exist "wenv\Scripts\activate.bat" (
    call wenv\Scripts\activate.bat
    python build.py build
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    python build.py build
) else (
    echo ⚠️ Ни wenv, ни venv не найдены, создаю wenv...
    python build.py wenv-create
    python build.py wenv-install --dev --build
    python build.py build --wenv
)
```

#### **Результат сборки:**
- **Файл**: `dist/ScreenTranslator.exe`
- **Размер**: ~40-60 MB (включает Python runtime и все зависимости)
- **Тип**: Standalone executable (не требует установленного Python)

#### **Диагностика для человека:**
```powershell
.\dev.ps1 build debug      # Сборка с консолью
# Затем запустить dist/ScreenTranslator.exe и посмотреть ошибки
```

## Key Design Patterns

### **Observer Pattern**
Configuration changes notify all registered observers:
```python
class ConfigObserver(ABC):
    def on_config_changed(self, key: str, old_value, new_value) -> None:
        pass

# Components register as observers
config_manager.add_observer(hotkey_manager)
config_manager.add_observer(tts_processor)
```

### **Dependency Injection**
Services registered in DI container for loose coupling:
```python
# Service registration
container.register_singleton(ConfigManager, ConfigManager)
container.register_factory(OCRProcessor, create_ocr_processor)

# Service consumption
config_manager = container.get(ConfigManager)
```

### **Strategy Pattern**
Pluggable engines for OCR, Translation, TTS:
```python
class OCREngine(ABC):
    def extract_text(self, image: Image) -> Tuple[str, float]:
        pass

# Multiple implementations: TesseractOCR, EasyOCR, etc.
```

## Configuration Architecture

### **Typed Configuration**
- **`AppConfig`** - Root configuration object
- **`HotkeyConfig`** - Hotkey settings with validation
- **`LanguageConfig`** - OCR and translation languages
- **`TTSConfig`** - Voice, rate, and device settings
- **`ImageProcessingConfig`** - OCR enhancement parameters

### **Observer-Based Updates**
Configuration changes automatically propagate to dependent services without manual coordination.

### **Persistence**
- JSON serialization with graceful error handling
- Default config auto-generation
- Validation with issue reporting

## Threading Model

### **Thread-Safe Operations**
- **GUI Thread**: tkinter main loop and UI updates
- **Background Threads**: Screenshot processing, OCR, translation
- **TTS Thread**: Non-blocking speech synthesis
- **Hotkey Thread**: Global keyboard monitoring

### **Communication**
- **Queue-based**: GUI message queue for cross-thread updates
- **Event-driven**: Configuration observers for decoupled notifications

## Error Handling & Logging

### **Centralized Logging**
```python
from src.utils.logger import logger

logger.log_translation(original, translated, source_lang, target_lang, duration)
logger.log_screenshot(coordinates, size, duration)  
logger.log_ocr(text_length, confidence, duration)
```

### **Graceful Degradation**
- Missing OCR engines fallback to alternatives
- Translation API failures show user-friendly messages
- TTS engine reinitializes on failures

## Extension Points

### **Plugin Architecture Ready**
- Abstract base classes for engines (OCR, Translation, TTS)
- Factory pattern for engine creation
- DI container supports runtime registration

### **New Features**
- Add new OCR engines by implementing `OCREngine`
- Add translation providers by implementing `TranslationEngine`
- Add UI components by extending observer pattern

## Migration Notes

### **From v1.0 (monolithic index.py)**
- **Config**: `DEFAULT_CONFIG` → `AppConfig` dataclass
- **Cache**: `TranslationCache` class → `TranslationCache` service
- **UI**: Embedded UI → Separate `SettingsWindow` class
- **Main**: All-in-one → Coordinated by `ScreenTranslatorApp`

### **Backward Compatibility**
⚠️ **ВНИМАНИЕ**: Обратная совместимость НЕ поддерживается согласно требованиям проекта.
- Старые настройки будут **полностью игнорированы**
- Новая архитектура работает с **чистого листа**
- **Миграция данных НЕ предусмотрена** и НЕ планируется

## Documentation (docs/)

### **📁 Using the docs/ Directory**

The `docs/` directory contains comprehensive documentation about the project's architecture evolution and future plans. **Always consult these files when working on the project** to understand context, decisions, and roadmap.

### **📂 Project Structure (Clean Layout)**

```
Screen Translator v2.0/
├── 📁 src/                    # Source code
├── 📁 docs/                   # Documentation
│   ├── 📁 reports/            # Development reports
│   └── 📁 development/        # Architecture docs
├── 📁 tools/                  # Development utilities
├── 🪟 dev.ps1                # Windows development interface
├── 🐧 dev.sh                 # Linux/macOS development interface
├── 🐍 build.py               # Universal build system
├── 📄 CLAUDE.md              # This file (Claude instructions)
└── 📄 README.md              # User documentation
```

### **📋 Documentation Structure**

```
docs/
├── README.md                   # User guide and quick start
├── ARCHITECTURE.md             # Technical architecture documentation
├── ROADMAP.md                  # Development roadmap and priorities
├── CHANGELOG.md                # Version history and changes
└── INDEX.md                    # Documentation navigation guide
```

### **🎯 When to Use Each Document**

#### **README.md**
- **Use when**: Getting started or helping new users
- **Contains**: Installation guide, quick start, basic usage examples
- **Helpful for**: Initial setup, basic operations, troubleshooting

#### **ARCHITECTURE.md**  
- **Use when**: Understanding current system design
- **Contains**: Complete v2.0 architecture, component relationships, design patterns
- **Helpful for**: System overview, adding new features, architectural decisions

#### **ROADMAP.md**
- **Use when**: Planning future work or understanding project direction
- **Contains**: Prioritized future tasks, milestones, planned improvements
- **Helpful for**: Feature planning, development priorities, long-term strategy

#### **CHANGELOG.md**
- **Use when**: Understanding what changed between versions
- **Contains**: Version history, bug fixes, new features, breaking changes
- **Helpful for**: Migration guides, version comparison, release notes

#### **INDEX.md**
- **Use when**: Navigating documentation structure
- **Contains**: Documentation overview, quick links, organization guide
- **Helpful for**: Finding specific information quickly

### **💡 Best Practices for Documentation Use**

#### **Before Making Changes**
1. **Read README.md** for basic understanding
2. **Check ARCHITECTURE.md** for design patterns
3. **Review ROADMAP.md** to align with planned direction

#### **When Adding Features**
1. **Consult ARCHITECTURE.md** to understand where new code should go
2. **Check ROADMAP.md** to see if feature is already planned
3. **Update CHANGELOG.md** when feature is complete

#### **When Debugging Issues**
1. **Reference ARCHITECTURE.md** for component interactions
2. **Check CHANGELOG.md** for recent changes that might be related
3. **Use INDEX.md** to find relevant documentation sections

#### **When Planning Work**
1. **Review ROADMAP.md** for prioritized tasks
2. **Update roadmap** when completing or adding tasks
3. **Document decisions** in relevant files

### **📝 Keeping Documentation Current**

- **Update ARCHITECTURE.md** when making architectural changes
- **Add entries to CHANGELOG.md** for all releases
- **Review ROADMAP.md** quarterly to ensure priorities align
- **Keep README.md** accessible for new users

### **🔍 Quick Reference Commands**

```bash
# View user documentation
cat docs/README.md

# Check architecture overview
cat docs/ARCHITECTURE.md

# Review development priorities  
head -50 docs/ROADMAP.md

# See recent changes
head -100 docs/CHANGELOG.md
```

The documentation in `docs/` is essential for maintaining project continuity and should be the first resource consulted when working with this codebase.

## **🔊 Последние Обновления UI (v2.0)**

### **Исправлены Проблемы в Настройках**

#### **Исправление прокрутки в настройках горячих клавиш**
- **Проблема**: Колёсико мыши работало только при наведении непосредственно на полосу прокрутки
- **Решение**: Добавлены обработчики событий мыши (`<MouseWheel>`) для всей области canvas
- **Файл**: `src/ui/settings_window.py:115-126`
- **Код**:
```python
def _on_mousewheel(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

def _bind_to_mousewheel(event):
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

def _unbind_from_mousewheel(event):
    canvas.unbind_all("<MouseWheel>")

canvas.bind('<Enter>', _bind_to_mousewheel)
canvas.bind('<Leave>', _unbind_from_mousewheel)
```

#### **Добавлен выбор устройства вывода звука для TTS**
- **Проблема**: Отсутствовал выбор аудиоустройства для озвучки
- **Решение**: Добавлена полная поддержка выбора аудиоустройств
- **Файлы**: 
  - `src/ui/settings_window.py:320-344` (UI элементы)
  - `src/ui/settings_window.py:594-613` (получение списка устройств)
  - `src/ui/settings_window.py:652-657` (сохранение настроек)
  - `requirements.txt:11` (зависимость sounddevice)

**Новая функциональность:**
1. **Перечисление устройств**: Используется `sounddevice` для получения списка доступных аудиоустройств вывода
2. **Graceful fallback**: Если sounddevice недоступен, показывается только "Системное по умолчанию"
3. **Сохранение настроек**: Выбранное устройство сохраняется в `config.tts.audio_device`
4. **UI интеграция**: ComboBox для выбора устройства в разделе "Выбор голоса"

**Код получения устройств:**
```python
def _get_available_audio_devices(self):
    """Get available audio output devices"""
    devices = [{'id': 'default', 'name': 'Системное по умолчанию'}]
    
    try:
        import sounddevice as sd
        device_list = sd.query_devices()
        
        for i, device in enumerate(device_list):
            if device['max_output_channels'] > 0:  # Only output devices
                devices.append({
                    'id': str(i),
                    'name': f"{device['name']} ({device['hostapi_name']})"
                })
    except ImportError:
        logger.warning("sounddevice not available, using default audio device only")
    except Exception as e:
        logger.error(f"Error querying audio devices: {e}")
        
    return devices
```

### **Результат**
✅ **Прокрутка горячих клавиш**: Теперь работает при наведении мыши на любую область прокрутки  
✅ **Выбор аудиоустройства**: Пользователь может выбрать конкретное устройство вывода для TTS  
✅ **Стабильность**: Graceful обработка отсутствия sounddevice библиотеки

## **🔍 Интегрированные Инструменты Качества Кода**

### **⚠️ ОБЯЗАТЕЛЬНО: Все команды используют venv автоматически!**

### **Команды Проверки Качества**
```bash
# ВАЖНО: dev.bat автоматически активирует venv!
.\dev.bat quality        # Полная проверка качества (11 анализаторов)
.\dev.bat quality fix    # Автоматическое исправление найденных проблем  
.\dev.bat lint           # Базовая проверка стиля
.\dev.bat lint fix       # Исправление форматирования
```

**🚨 Для человека: НЕ запускать анализаторы напрямую!**
```bash
# ❌ НЕ ДЕЛАТЬ (системный Python):
black .
flake8 .
mypy .

# ✅ ПРАВИЛЬНО (через dev.bat с venv):
.\dev.bat lint fix
```

### **11 Интегрированных Анализаторов**

1. **Black** - Автоматическое форматирование кода (PEP8)
2. **isort** - Сортировка и организация импортов
3. **Flake8** - Проверка стиля кода и синтаксиса
4. **MyPy** - Статическая проверка типов
5. **Pylint** - Комплексный анализ качества кода
6. **Bandit** - Поиск уязвимостей безопасности
7. **Vulture** - Обнаружение мёртвого кода
8. **Radon** - Метрики сложности кода (CC & MI)
9. **Pydocstyle** - Проверка стиля docstring
10. **Safety** - Проверка зависимостей на уязвимости
11. **Prospector** - Мета-инструмент объединяющий линтеры

### **Структура Отчётов**
```
quality_reports/
├── black_code_formatting.txt      # Проблемы форматирования
├── isort_import_sorting.txt       # Проблемы с импортами
├── flake8_style_guide.txt         # Нарушения стиля
├── mypy_type_checking.txt         # Проблемы с типами
├── pylint_code_quality.txt        # Общие проблемы качества
├── bandit_security.txt            # Уязвимости безопасности
├── vulture_dead_code.txt          # Неиспользуемый код
├── radon_cyclomatic_complexity.txt # Сложность функций
├── radon_maintainability_index.txt # Индекс поддерживаемости
├── pydocstyle_docstring_style.txt # Проблемы документации
├── safety_dependency_security.txt  # Уязвимые зависимости
└── summary.json                   # Сводка всех проверок
```

### **Конфигурационные Файлы**
- **`.pylintrc`** - Настройки Pylint (исключения, лимиты)
- **`pyproject.toml`** - Настройки Black, isort, mypy, coverage
- **`.flake8`** - Настройки Flake8 (длина строк, исключения)
- **`.bandit`** - Настройки безопасности

### **Автоматические Исправления**
`.\dev.bat quality fix` автоматически:
- Форматирует код согласно PEP8 (Black)
- Сортирует импорты (isort)
- Удаляет неиспользуемые импорты (autoflake)
- Удаляет неиспользуемые переменные

### **Интеграция в Workflow**
1. **Перед коммитом**: `.\dev.bat quality`
2. **Для исправления**: `.\dev.bat quality fix`
3. **Просмотр отчётов**: `quality_reports\summary.json`
4. **CI/CD**: Все проверки возвращают exit code для автоматизации
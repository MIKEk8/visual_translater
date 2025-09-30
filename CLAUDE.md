# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 CRITICAL: REPORTING STANDARDS

### NO SPECULATIVE METRICS
**СТРОГО ЗАПРЕЩЕНО** указывать предположительные метрики без реальных измерений:

❌ **НЕПРАВИЛЬНО:**
- "Performance: 100-300ms" (без запуска бенчмарков)
- "2-5x faster than target" (без измерений)
- "Estimated 3-5 hours" (без фактического выполнения)
- "Coverage: 80%" (без запуска coverage инструмента)
- "Memory usage: <50MB" (без профилирования)

✅ **ПРАВИЛЬНО:**
- "Tests: 27/28 passing (verified by `cargo test`)"
- "Compilation: successful (verified by `cargo check`)"
- "Implementation: complete (code written, not yet benchmarked)"
- "Performance: NOT YET MEASURED (benchmarks pending)"
- "Estimated time: CANNOT ESTIMATE (depends on unknowns)"

### MEASUREMENT REQUIREMENTS

**Если метрика НЕ измерена реальным инструментом - НЕ УКАЗЫВАЙ ЕЁ.**

#### Допустимые утверждения:
- ✅ Количество тестов (после `cargo test`)
- ✅ Статус компиляции (после `cargo check/build`)
- ✅ Количество файлов (после создания/изменения)
- ✅ Результаты линтеров (после `cargo clippy`)
- ✅ Покрытие кода (после `cargo tarpaulin` или аналога)
- ✅ Бенчмарки (после `cargo bench` или criterion)
- ✅ Размер бинарника (после сборки + `ls -lh`)
- ✅ Время выполнения (после реального запуска с замером)

#### ЗАПРЕЩЕННЫЕ утверждения:
- ❌ "Быстрее в X раз" (без side-by-side бенчмарка)
- ❌ "Займет N часов/дней" (без истории аналогичных задач)
- ❌ "Использует M памяти" (без profiler/valgrind)
- ❌ "Покрытие N%" (без coverage runner)
- ❌ "Производительность <Nms" (без benchmark результатов)

### LANGUAGE FOR UNMEASURED CLAIMS

Используй точные формулировки:

```markdown
# ВМЕСТО:
"Performance: 100-300ms (2-5x faster than target)"

# ПИШИ:
"Performance: NOT MEASURED YET
Target: <500ms (from requirements)
Implementation: complete, ready for benchmarking
To verify: cargo bench --bench screenshot_bench"

# ВМЕСТО:
"Estimated 3-5 hours implementation time"

# ПИШИ:
"Implementation scope defined in docs/plan.md
Time estimate: DEFERRED until after Phase 1 completion
Dependencies: X, Y, Z must be resolved first"

# ВМЕСТО:
"Memory usage: <50MB"

# ПИШИ:
"Memory usage: NOT PROFILED
Target: <50MB (from requirements)
To measure: cargo run --release with valgrind/heaptrack"
```

### REPORTING TEMPLATE

При создании отчетов используй этот шаблон:

```markdown
## Implementation Status
✅ Code written: [files list]
✅ Tests created: X tests
✅ Compilation: [cargo check result]

## Verified Metrics (with tools)
✅ Tests passing: X/Y (cargo test)
✅ Linters: [cargo clippy result]
✅ Format: [cargo fmt --check result]

## NOT YET MEASURED
⏸️ Performance benchmarks (cargo bench not run)
⏸️ Memory profiling (profiler not run)
⏸️ Coverage percentage (tarpaulin not run)

## Ready for Measurement
- [ ] Run cargo bench for performance
- [ ] Run cargo tarpaulin for coverage
- [ ] Profile memory with heaptrack
```

## 🏗️ ARCHITECTURE GUIDELINES

### Preventing Code Duplication
When working with this codebase, follow these principles to prevent duplication:

1. **DRY (Don't Repeat Yourself)**: Each piece of knowledge should have a single, unambiguous representation
2. **Single Source of Truth**: Configuration must be defined in ONE place only
3. **Explicit Dependencies**: Use dependency injection instead of singletons
4. **Fail-Fast on Duplication**: Throw errors rather than silently allowing duplicates

### Hotkey System Architecture
The application uses a **unified hotkey service** to manage all hotkeys:
- Single initialization point in main application
- No duplication of hotkey definitions
- Clear separation between intelligent (time-based) and simple hotkeys
- Prevents conflicts automatically

**Important**: Never register the same hotkey in multiple places. Use the unified hotkey service for all operations.

## 🚨 CRITICAL: Windows Platform & Development Environment

**🪟 ВАЖНО: Это Windows-приложение!**

**Платформа:** Windows 10/11 (основная разработка и использование)

**💾 ВАЖНО: Диск P: - это алиас E:/myprojects/**
- `P:\visual_translater` = `E:/myprojects/visual_translater`
- Это Windows `subst` mapping (виртуальный диск)
- Оба пути взаимозаменяемы, но P: короче и удобнее
- При отладке ошибок с путями помни об этом алиасе

### **🦀 RUST + TAURI ARCHITECTURE (v3.0)**
**Framework:** Rust + Tauri + React + TypeScript
**Backend:** Rust (производительность, безопасность, нативная интеграция с Windows)
**Frontend:** React + TypeScript + Tailwind CSS + Framer Motion
**Build System:** Cargo + npm/yarn
**Architecture:** Modular with dependency injection

### **Запуск приложения:**

#### **👤 Для пользователя (готовый exe):**
```cmd
REM Rust + Tauri версия - готовый исполняемый файл
dist\ScreenTranslator.exe

REM Интеллектуальная система горячих клавиш:
REM Alt+A - Умная клавиша с определением времени нажатия
REM
REM БЫСТРОЕ НАЖАТИЕ (< 1 секунды) - Умный перевод:
REM     Приоритет обработки:
REM     1. Выделенный текст (если есть) → переводит
REM     2. Буфер обмена (текст или изображение) → переводит
REM     3. Предыдущая область скриншота → повторно переводит
REM     4. Новый выбор области экрана → выделение + перевод
REM     • AI определяет язык и контекст автоматически
REM     • Результат в floating overlay + автокопирование
REM
REM ДОЛГОЕ НАЖАТИЕ (>= 1 секунды) - Контекстное меню:
REM     • 📷 Скриншот области
REM     • 📋 Перевести из буфера
REM     • 🎯 Выбрать регион на экране
REM     • 🔄 Повторить последний перевод
REM     • 📚 История переводов
REM     • ⚙️ Настройки
```

#### **🛠️ Для разработчика (из исходников Rust):**
```cmd
REM 1. Перейти в директорию Rust проекта
cd screen-translator-rust

REM 2. Установить зависимости (один раз)
npm install
cargo build

REM 3. Запуск в режиме разработки
npm run tauri:dev

REM 4. Сборка production версии
npm run tauri:build
```

## 🔨 CRITICAL BUILD REQUIREMENT FOR THIS PROJECT

**ОБЯЗАТЕЛЬНО**: После КАЖДОГО завершенного этапа разработки и ПЕРЕД подготовкой отчета, ты ДОЛЖЕН пересобрать проект:

```bash
# Для Screen Translator v3.0 - ВСЕГДА выполняй эти команды:
cd screen-translator-rust
npm run build         # Собрать frontend
cargo build --release # Собрать Rust backend

# Если нужен полный installer:
npm run tauri:build   # Полная сборка с MSI/NSIS инсталляторами
```

**Причины обязательной пересборки:**
1. React/TypeScript изменения НЕ отражаются в exe без пересборки
2. Rust изменения требуют перекомпиляции для применения
3. Tauri встраивает frontend в исполняемый файл при сборке
4. Пользователь запускает готовый exe, а не dev-версию

**Без пересборки изменения НЕ БУДУТ видны в приложении!**

## 🔍 CRITICAL VALIDATION REQUIREMENTS

**ОБЯЗАТЕЛЬНО**: Перед каждой пересборкой проверяй валидность кода:

```bash
# Для Screen Translator v3.0 - ВСЕГДА проверяй перед сборкой:
cd screen-translator-rust

# 1. TypeScript/JavaScript валидация
npm run lint          # ESLint проверка синтаксиса и стиля
tsc --noEmit          # TypeScript компиляция без генерации файлов

# 2. Rust валидация
cargo check           # Быстрая проверка без сборки
cargo clippy          # Линтер Rust
cargo fmt --check     # Проверка форматирования

# 3. Только ПОСЛЕ успешной валидации - сборка:
npm run build         # Собрать frontend
cargo build --release # Собрать Rust backend
```

**Причины обязательной валидации:**
1. JavaScript синтаксические ошибки блокируют загрузку UI
2. TypeScript ошибки приводят к runtime сбоям
3. Rust ошибки компиляции останавливают сборку
4. Линтеры выявляют потенциальные баги до запуска

**Без валидации код может сломать приложение на этапе выполнения!**

## Project Overview

This is **Screen Translator v3.0** - a modern Rust + Tauri Windows desktop application that captures screen regions, performs OCR text recognition, and provides real-time translation with text-to-speech capabilities. The application uses a **clean modular architecture** with dependency injection and cutting-edge web technologies.

### **🎯 Personal Project Scope**

**ВАЖНО**: Это приложение создано исключительно для личного использования разработчика. В связи с этим:

- ❌ **Обратная совместимость** со старыми версиями НЕ требуется
- ❌ **Миграция конфигураций** из предыдущих версий НЕ нужна
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

### 🏗️ **Rust + Tauri Architecture (v3.0)**

#### **🦀 Rust Backend Structure**
```
screen-translator-rust/
├── src/
│   ├── main.rs                    # Tauri app entry point
│   ├── lib.rs                     # Library exports
│   ├── commands/                  # Tauri API commands
│   │   └── mod.rs                 # Frontend-backend communication
│   ├── core/                      # Core business logic
│   │   ├── mod.rs
│   │   ├── config.rs              # Configuration management
│   │   ├── screenshot.rs          # Screen capture
│   │   ├── ocr.rs                 # OCR processing (Tesseract)
│   │   └── image_processor.rs     # Image enhancement
│   ├── services/                  # Business services
│   │   ├── mod.rs
│   │   ├── translation.rs         # Translation services
│   │   ├── hotkey.rs              # Global hotkey management
│   │   ├── config.rs              # Config persistence
│   │   ├── cache.rs               # LRU caching
│   │   └── tts.rs                 # Text-to-speech
│   ├── ai/                        # AI-powered features
│   │   ├── context_aware.rs       # Language & context detection
│   │   └── smart_detection.rs     # Enhanced text region detection
│   ├── utils/                     # Utility modules
│   │   ├── mod.rs
│   │   └── error.rs               # Error handling
│   └── types/                     # Type definitions
│       ├── mod.rs
│       ├── config.rs              # Configuration types
│       └── translation.rs         # Translation types
├── ui/                            # React frontend
│   ├── src/
│   │   ├── App.tsx                # Main React application
│   │   ├── components/            # React components
│   │   │   ├── ContextMenu.tsx    # Animated context menu
│   │   │   ├── SettingsPanel.tsx  # Settings interface
│   │   │   ├── TranslationOverlay.tsx # Translation results
│   │   │   └── HistoryWindow.tsx  # Translation history
│   │   ├── hooks/                 # React hooks
│   │   │   ├── useHotkeys.ts      # Hotkey management
│   │   │   ├── useTranslation.ts  # Translation state
│   │   │   └── useConfig.ts       # Configuration state
│   │   ├── stores/                # Zustand state management
│   │   │   ├── appStore.ts        # Main app state
│   │   │   ├── configStore.ts     # Configuration state
│   │   │   └── historyStore.ts    # Translation history
│   │   └── types/                 # TypeScript definitions
│   │       ├── api.ts             # Tauri API types
│   │       ├── config.ts          # Configuration types
│   │       └── translation.ts     # Translation types
│   ├── package.json               # Frontend dependencies
│   └── tailwind.config.js         # Tailwind CSS config
├── Cargo.toml                     # Rust dependencies
├── tauri.conf.json               # Tauri configuration
└── build.rs                      # Build script
```

### 🔧 **Core Components**

#### **Engines** (`src/core/`)
- **`ScreenshotEngine`** - DPI-aware screen capture with area validation
- **`OCRProcessor`** - Tesseract OCR with image enhancement pipeline
- **`TranslationProcessor`** - Google Translate with caching support
- **`TTSProcessor`** - Windows native TTS with voice/device selection
- **`SmartTranslationHandler`** - AI-powered context-aware quick translation
- **`ApplicationController`** - Main application coordinator

#### **🧠 AI-Enhanced Components** (`src/ai/`)
- **`ContextAwareTranslator`** - Intelligent language and context detection
  - Supports 7 languages: EN, RU, DE, FR, ES, JA, ZH
  - Context types: Technical, Gaming, UI Interface, Document, Subtitle
  - Smart target language selection based on user patterns
- **`SmartAreaDetector`** - Advanced text region detection with ML algorithms
  - Hybrid detection methods: Contour, Edge, Text-specific, ML-based
  - Confidence scoring and region merging
  - Performance optimized with caching

#### **Services** (`src/services/`)
- **`ConfigService`** - Configuration management with observers
- **`HotkeyService`** - Global hotkey registration/management
- **`TranslationCache`** - LRU cache with TTL for translations
- **`CacheService`** - General purpose caching service

#### **UI Components** (React + TypeScript)
- **`ContextMenu`** - Animated context menu with action selection
  - Floating menu with fade animations
  - Keyboard navigation (arrows, numbers, Enter, Esc)
  - Icons and descriptions for each action
  - Smart positioning and transparency effects
- **`SettingsPanel`** - Tabbed settings interface with live updates
- **`HistoryWindow`** - Translation history management
- **`TranslationOverlay`** - Text overlay display
- **`LanguageSelector`** - Language selection components

#### **Types** (`src/types/`)
- **`AppConfig`** - Strongly typed configuration with validation
- **`Translation`** - Translation data with metadata
- **`ScreenshotData`** - Screenshot information container

## 🆕 **Core Features**

### **🧠 Intelligent Single-Key System**
**Революционная система одной клавиши с определением времени нажатия:**

#### **Alt+A - Smart Time-Based Action**
🎯 **Одна клавиша для всех действий:**

##### **⚡ Quick Press (< 1 second) - Smart Translation**
**Интеллектуальный приоритетный перевод:**
1. **Выделенный текст** - если что-то выделено → мгновенный перевод
2. **Буфер обмена (текст)** - если в буфере текст → переводит
3. **Буфер обмена (изображение)** - если в буфере картинка → OCR + перевод
4. **Предыдущая область** - если ранее была выделена область → повторный скриншот + перевод
5. **Новое выделение** - если ничего нет → запуск выделения области экрана

**AI Features:**
- **Language detection**: 7 языков с определением контекста (техническая терминология, игры, UI, документы)
- **Smart target selection**: Автовыбор целевого языка на основе истории и паттернов пользователя
- **Floating overlay result**: Красивое всплывающее окно с результатом и автокопированием
- **Performance**: ~0.001-0.01 сек на определение языка, кэширование повторных запросов

##### **🕐 Long Press (>= 1 second) - Context Menu**
🎯 **Анимированное меню действий:**
- **📷 Screenshot Area** - Выбор области экрана для перевода
- **📋 Clipboard Translation** - Прямой перевод из буфера обмена
- **🎯 Region Selection** - Интеллектуальный выбор текстовых регионов
- **🔄 Repeat Last** - Повтор последнего перевода
- **📚 History** - Окно истории переводов
- **⚙️ Settings** - Настройки приложения

**UI Features:**
- Fade-in/fade-out анимации (0.95 прозрачность)
- Навигация клавиатурой (стрелки, цифры, Enter, Esc)
- Иконки и описания для каждого действия
- Умное позиционирование по центру экрана

### **🧠 AI-Enhanced Translation Pipeline**

#### **Context-Aware Language Detection**
- **7 поддерживаемых языков**: English, Русский, Deutsch, Français, Español, 日本語, 中文
- **5 типов контекста**: Technical, Gaming, UI Interface, Document, Subtitle
- **Smart suggestions**: Автоматические рекомендации для улучшения перевода
- **Pattern recognition**: Распознавание технической терминологии, игровых команд, UI элементов

#### **Advanced Text Region Detection**
- **Hybrid ML algorithms**: Комбинация Contour, Edge, Text-specific и ML методов
- **Confidence scoring**: Оценка уверенности для каждого региона
- **Region merging**: Интеллектуальное объединение перекрывающихся областей
- **Performance optimization**: Кэширование с TTL для повторных запросов

### **⚡ Performance & UX Improvements**
- **One-key workflow**: Alt+A для 99% сценариев использования
- **Intelligent prioritization**: Система приоритетов автоматически выбирает лучший источник
- **Time-based actions**: Быстрое нажатие = перевод, долгое = меню (без запоминания комбинаций)
- **Instant feedback**: Floating результаты без блокировки UI
- **Auto-copy results**: Автоматическое копирование переводов в буфер
- **Context memory**: Запоминание предыдущих областей скриншота для быстрого повтора
- **Image OCR support**: Прямая работа с изображениями из буфера обмена
- **Memory efficient**: Минимальное потребление ресурсов в фоновом режиме
- **Press detection**: Точное определение времени нажатия (~16ms точность)

## Development Commands

### **🚀 Rust + Tauri Build System**

#### **🛠️ Для разработчика:**
```cmd
REM 1. Перейти в директорию проекта
cd screen-translator-rust

REM 2. Установить зависимости (один раз)
npm install
cargo build

REM 3. Запуск в режиме разработки
npm run tauri:dev

REM 4. Сборка production версии
npm run tauri:build

REM 5. Проверка кода
cargo clippy

REM 6. Форматирование кода
cargo fmt

REM 7. Тесты
cargo test
```

#### **Результат сборки:**
- **Файл**: `dist/ScreenTranslator.exe`
- **Размер**: ~20-40 MB (нативный исполняемый файл)
- **Тип**: Standalone executable (не требует установленного Rust)

## Key Design Patterns

### **Dependency Injection**
Rust-based DI container for service management:
```rust
// Service registration and consumption
let config_service = container.get::<ConfigService>();
let hotkey_service = container.get::<HotkeyService>();
```

### **Observer Pattern**
Configuration changes notify all registered observers:
```rust
trait ConfigObserver {
    fn on_config_changed(&self, key: &str, old_value: &str, new_value: &str);
}

// Components register as observers
config_service.add_observer(hotkey_service);
config_service.add_observer(tts_service);
```

### **Strategy Pattern**
Pluggable engines for OCR, Translation, TTS:
```rust
trait OCREngine {
    fn extract_text(&self, image: &Image) -> Result<(String, f32), OCRError>;
    fn is_available(&self) -> bool;
}

// Multiple implementations: TesseractOCR, EasyOCR, etc.
```

## Configuration Architecture

### **Typed Configuration**
- **`AppConfig`** - Root configuration struct
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

## Error Handling & Logging

### **Centralized Logging**
```rust
use crate::utils::logger;

logger::log_translation(original, translated, source_lang, target_lang, duration);
logger::log_screenshot(coordinates, size, duration);
logger::log_ocr(text_length, confidence, duration);
```

### **Graceful Degradation**
- Missing OCR engines fallback to alternatives
- Translation API failures show user-friendly messages
- TTS engine reinitializes on failures

## Extension Points

### **Plugin Architecture Ready**
- Trait-based interfaces for engines (OCR, Translation, TTS)
- Factory pattern for engine creation
- DI container supports runtime registration

### **New Features**
- Add new OCR engines by implementing `OCREngine` trait
- Add translation providers by implementing `TranslationEngine` trait
- Add UI components by extending observer pattern

## Documentation (docs/)

### **📁 Using the docs/ Directory**

The `docs/` directory contains comprehensive documentation about the project's architecture evolution and future plans. **Always consult these files when working on the project** to understand context, decisions, and roadmap.

### **📂 Project Structure (Clean Layout)**

```
Screen Translator v3.0/
├── 📁 screen-translator-rust/     # Rust + Tauri source code
├── 📁 docs/                       # Documentation
│   ├── 📁 reports/                # Development reports
│   └── 📁 development/            # Architecture docs
├── 📄 CLAUDE.md                   # This file (Claude instructions)
└── 📄 README.md                   # User documentation
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
- **Contains**: Complete v3.0 architecture, component relationships, design patterns
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

## Claude Code Work Tracking

### Директория `/cc/` для ведения логов работы

**🤖 ВАЖНО для Claude Code:** Используйте эту структуру для организации работы:

#### **`/cc/tasks/`** - Лог выполненных задач и TODO списки:
- Файлы с датой: `YYYY-MM-DD.md` для ежедневных задач
- Формат записи: `## [HH:MM] Задача - Что сделано (кратко)`
- Пример: `## [14:30] Исправить циклическую зависимость - Добавлен интерфейс ITrayManager`
- TODO файлы: `TODO_<тема>.md` для выявленных проблем (не записывать TODO в код)

#### **`/cc/docs/`** - Документация и заметки:
- Архитектурные решения: `architecture_notes.md`
- Паттерны и практики: `patterns.md`
- Бизнес-логика: `business_logic.md`
- Технические долги: `tech_debt.md`

#### **`/cc/analysis/`** - Результаты анализа:
- Метрики качества: `quality_metrics.md`
- Анализ производительности: `performance_analysis.md`
- Отчеты по рефакторингу: `refactoring_reports/`

### Примеры использования:

```bash
# Создание дневного лога задач
Write("/workspace/cc/tasks/2025-09-29.md", content="# Задачи 2025-09-29\n\n## [10:00] Архитектурный анализ...")

# Документирование архитектурного решения
Write("/workspace/cc/docs/architecture_notes.md", content="# Архитектурные решения\n\n## DI Container...")

# Сохранение TODO для будущей работы
Write("/workspace/cc/tasks/TODO_ui_refactoring.md", content="# TODO: Рефакторинг UI\n\n- [ ] Разбить SettingsWindow...")
```

### Правила ведения документации:

1. **Всегда документируйте** важные архитектурные решения
2. **Создавайте TODO файлы** для проблем, найденных при анализе
3. **Ведите дневной лог** выполненных задач с временными метками
4. **Группируйте информацию** по темам в отдельные файлы
5. **НЕ добавляйте TODO** комментарии в код - используйте `/cc/tasks/`

      IMPORTANT: this context may or may not be relevant to your tasks. You should not respond to this context unless it is highly relevant to your task.
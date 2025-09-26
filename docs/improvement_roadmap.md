# 🚀 План улучшения проекта Screen Translator v2.0

*Версия: 1.0 | Дата: 2025-09-26*

## 📋 Приоритеты действий

### 🔴 КРИТИЧЕСКИЕ (Немедленно - 1-2 недели)

#### 1. **Исправление 186 F821 undefined name errors**
```bash
# Автоматизированное исправление
wenv\Scripts\python.exe -m autoflake --in-place --remove-unused-variables --recursive src/
wenv\Scripts\python.exe -m isort src/
wenv\Scripts\python.exe -m black src/

# Проверка результатов
wenv\Scripts\python.exe -m flake8 src/ --count --select=F821
```

**Цель**: Устранить все undefined references для стабильности кода

#### 2. **Security Audit зависимостей**
```bash
# Проверка уязвимостей
wenv\Scripts\python.exe -m safety check --json --output safety_report.json
wenv\Scripts\python.exe -m pip-audit

# Обновление критических пакетов
wenv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
wenv\Scripts\python.exe -m pip install --upgrade -r requirements.txt
```

**Цель**: Закрыть известные CVE уязвимости

#### 3. **Достижение 80% test coverage**
```python
# Создать скрипт coverage_improvement.py
import subprocess
import json

def analyze_coverage_gaps():
    """Identify modules with low coverage"""
    result = subprocess.run(
        ["wenv/Scripts/python.exe", "-m", "pytest", "--cov=src", "--cov-report=json"],
        capture_output=True
    )

    with open("coverage.json") as f:
        data = json.load(f)

    low_coverage = []
    for file, stats in data["files"].items():
        if stats["summary"]["percent_covered"] < 80:
            low_coverage.append({
                "file": file,
                "coverage": stats["summary"]["percent_covered"],
                "missing_lines": stats["missing_lines"]
            })

    return sorted(low_coverage, key=lambda x: x["coverage"])
```

**Цель**: Минимум 80% покрытие для критических модулей

### 🟡 ВАЖНЫЕ (2-4 недели)

#### 4. **Упрощение архитектуры для Personal Project**

**Текущая проблема**: Over-engineering с 22 модулями и множеством паттернов

**Решение - Consolidation Plan**:
```
BEFORE (22 modules):
src/
├── api/           ┐
├── application/   ├─ Объединить в 3 core модуля
├── domain/        ┤
├── infrastructure/┘
├── handlers/      ┐
├── queries/       ├─ Упростить до единого CQRS модуля
├── commands/      ┘
└── ... (15 more)

AFTER (8 modules):
src/
├── core/          # Основная бизнес-логика
├── ui/            # GUI компоненты
├── services/      # Внешние сервисы (OCR, Translation, TTS)
├── api/           # REST API (опционально)
├── utils/         # Утилиты
├── config/        # Конфигурация
├── plugins/       # Система плагинов
└── tests/         # Тесты
```

**Действия**:
1. Merge связанных модулей
2. Удалить избыточные абстракции
3. Упростить DI до простого service locator

#### 5. **Performance Optimization**

**Проблема**: 169 circuit breakers указывают на проблемы производительности

**Решение - Performance Profiling**:
```python
# performance_profile.py
import cProfile
import pstats
from io import StringIO

def profile_critical_paths():
    """Profile main operations"""
    profiler = cProfile.Profile()

    # Profile screenshot capture
    profiler.enable()
    # ... screenshot operation ...
    profiler.disable()

    # Profile OCR processing
    profiler.enable()
    # ... OCR operation ...
    profiler.disable()

    # Profile translation
    profiler.enable()
    # ... translation operation ...
    profiler.disable()

    # Generate report
    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats('cumulative')
    stats.print_stats(20)

    return stream.getvalue()
```

**Оптимизации**:
- Implement caching layer для OCR результатов
- Batch processing для множественных переводов
- Async processing pipeline
- Reduce circuit breaker timeouts

#### 6. **Cross-platform Support**

**Текущее**: Windows-only с wenv
**Цель**: Linux/macOS support

```python
# platform_abstraction.py
import platform
import sys
from abc import ABC, abstractmethod

class PlatformService(ABC):
    @abstractmethod
    def capture_screen(self, region): pass

    @abstractmethod
    def register_hotkey(self, key, callback): pass

class WindowsService(PlatformService):
    # Current implementation
    pass

class LinuxService(PlatformService):
    # Linux-specific using X11/Wayland
    pass

class MacOSService(PlatformService):
    # macOS-specific using Quartz
    pass

def get_platform_service():
    system = platform.system()
    if system == "Windows":
        return WindowsService()
    elif system == "Linux":
        return LinuxService()
    elif system == "Darwin":
        return MacOSService()
    else:
        raise NotImplementedError(f"Platform {system} not supported")
```

### 🟢 УЛУЧШЕНИЯ (1-2 месяца)

#### 7. **Documentation Enhancement**

**Создать**:
```markdown
docs/
├── architecture/
│   ├── ADR-001-clean-architecture.md    # Architecture Decision Records
│   ├── ADR-002-cqrs-implementation.md
│   └── ADR-003-plugin-system.md
├── guides/
│   ├── developer-guide.md               # Для разработчиков
│   ├── plugin-development.md            # Создание плагинов
│   └── deployment-guide.md              # Развёртывание
├── api/
│   ├── rest-api-spec.yaml              # OpenAPI specification
│   └── plugin-api.md                    # Plugin interface docs
└── diagrams/
    ├── architecture-overview.puml       # PlantUML диаграммы
    ├── sequence-translation.puml
    └── component-diagram.puml
```

#### 8. **CI/CD Pipeline**

**GitHub Actions workflow**:
```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  quality:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run quality checks
        run: |
          python -m black --check src/
          python -m isort --check-only src/
          python -m flake8 src/
          python -m mypy src/

      - name: Run security checks
        run: |
          python -m bandit -r src/
          python -m safety check

      - name: Run tests with coverage
        run: |
          python -m pytest --cov=src --cov-report=xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  build:
    needs: quality
    runs-on: windows-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v3

      - name: Build executable
        run: |
          python build.py build --mode release

      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: ScreenTranslator
          path: dist/ScreenTranslator.exe
```

#### 9. **Monitoring & Observability**

**Implement Application Insights**:
```python
# monitoring.py
import time
import json
from datetime import datetime
from typing import Dict, Any
import sqlite3

class MetricsCollector:
    def __init__(self, db_path="metrics.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                operation TEXT,
                duration_ms REAL,
                success BOOLEAN,
                metadata TEXT
            )
        """)
        conn.commit()
        conn.close()

    def track_operation(self, operation: str):
        """Decorator to track operation metrics"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start = time.time()
                success = True
                metadata = {}

                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    metadata['error'] = str(e)
                    raise
                finally:
                    duration_ms = (time.time() - start) * 1000
                    self._record_metric(operation, duration_ms, success, metadata)

            return wrapper
        return decorator

    def _record_metric(self, operation: str, duration_ms: float,
                       success: bool, metadata: Dict[str, Any]):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO metrics (timestamp, operation, duration_ms, success, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            operation,
            duration_ms,
            success,
            json.dumps(metadata)
        ))
        conn.commit()
        conn.close()

    def get_performance_report(self, operation: str = None):
        """Generate performance statistics"""
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT
                operation,
                COUNT(*) as total_calls,
                AVG(duration_ms) as avg_duration,
                MIN(duration_ms) as min_duration,
                MAX(duration_ms) as max_duration,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
            FROM metrics
            WHERE timestamp > datetime('now', '-7 days')
        """

        if operation:
            query += f" AND operation = '{operation}'"

        query += " GROUP BY operation"

        cursor = conn.execute(query)
        return cursor.fetchall()

# Usage
metrics = MetricsCollector()

@metrics.track_operation("screenshot_capture")
def capture_screen(region):
    # ... implementation ...
    pass

@metrics.track_operation("ocr_processing")
def process_ocr(image):
    # ... implementation ...
    pass

@metrics.track_operation("translation")
def translate_text(text, target_lang):
    # ... implementation ...
    pass
```

### 🔵 ДОЛГОСРОЧНЫЕ (3-6 месяцев)

#### 10. **Plugin Marketplace**
- Создать plugin repository
- Implement plugin auto-update system
- Add plugin sandboxing for security

#### 11. **AI Enhancement**
- Integrate GPT for better translations
- Add context-aware translation
- Implement learning from corrections

#### 12. **Cloud Sync**
- User preferences sync
- Translation history backup
- Cross-device synchronization

## 📊 Метрики успеха

| Метрика | Текущее | Целевое | Срок |
|---------|---------|---------|------|
| F821 Errors | 186 | 0 | 1 неделя |
| Test Coverage | ~60% | 80% | 2 недели |
| Performance (OCR) | 2-3s | <1s | 1 месяц |
| Platform Support | Windows | Win/Linux/Mac | 2 месяца |
| Documentation | 30% | 90% | 1 месяц |
| Circuit Breakers | 169 | <50 | 1 месяц |
| Module Count | 22 | 8-10 | 1 месяц |

## 🎯 Quick Wins (можно сделать сегодня)

1. **Fix all F821 errors**:
```bash
wenv\Scripts\python.exe -m autoflake --in-place --remove-unused-variables --recursive src/
```

2. **Update all dependencies**:
```bash
wenv\Scripts\python.exe -m pip install --upgrade -r requirements.txt
```

3. **Generate coverage report**:
```bash
wenv\Scripts\python.exe -m pytest --cov=src --cov-report=html
start htmlcov/index.html
```

4. **Create architecture diagram**:
```bash
wenv\Scripts\python.exe -m pip install pyreverse
pyreverse -o png -p ScreenTranslator src/
```

5. **Profile performance bottlenecks**:
```bash
wenv\Scripts\python.exe -m cProfile -o profile.stats main.py
wenv\Scripts\python.exe -m snakeviz profile.stats
```

## ✅ Checklist для начала работы

- [ ] Backup текущего состояния проекта
- [ ] Создать ветку `improvement/q4-2025`
- [ ] Исправить F821 errors
- [ ] Запустить security audit
- [ ] Создать baseline метрики производительности
- [ ] Начать упрощение архитектуры с merge мелких модулей
- [ ] Добавить GitHub Actions CI
- [ ] Написать ADR для ключевых решений
- [ ] Настроить code coverage badge
- [ ] Создать CONTRIBUTING.md

---
*Этот roadmap следует принципу "постепенного улучшения" - каждый шаг приносит немедленную пользу.*
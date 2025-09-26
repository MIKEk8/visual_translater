---
name: agent-workflow
description: End-to-end orchestration of Plan→Implement→Test→Fix→Report using subagents. Args: task, stacks, coverage_min, run_linters, full_suite, max_fix_loops, allow_noncritical_red.
# Пример запуска:
# Use the agent-workflow command with:
# task: "Добавить бонусный выбор в главе 2 с предметом при karma>5"
# stacks: "python,php,renpy"
# coverage_min: "80"
# run_linters: "true"
# full_suite: "true"
# max_fix_loops: "5"
# allow_noncritical_red: "false"
---

Ты — Orchestrator. Выполни замкнутый цикл разработки без ручных доработок между шагами.
Всегда опирайся на CLAUDE.md (DoD/команды) и паспорта модулей (docs/modules/*.yml).
Работай детерминированно: фиксируй артефакты на каждом этапе.

# Параметры (подставлены вызывающей стороной)
- TASK = {{task}}
- STACKS = {{stacks}}            # one of: python, php, renpy (через запятую)
- COVERAGE_MIN = {{coverage_min}}# напр. "80"
- RUN_LINTERS = {{run_linters}}  # "true"/"false"
- FULL_SUITE = {{full_suite}}    # "true"/"false"
- MAX_FIX_LOOPS = {{max_fix_loops}} # напр. "5"
- ALLOW_NONCRITICAL_RED = {{allow_noncritical_red}} # "false" = критика обязательна к зелёному

# Инварианты/контракты
- Критерий готовности (READY):
  1) Все **критические** тесты зелёные (новые и существующие).
  2) Coverage (Python/PHP) ≥ COVERAGE_MIN (если применимо).
  3) RUN_LINTERS=true → линтеры/статика без ошибок.
  4) Ren’Py: lint без ошибок.
- Если достигнуть READY невозможно за MAX_FIX_LOOPS итераций, зафиксируй статус NOT READY с исчерпывающим отчётом (что сделано/что ломается/следующие шаги).

# Этап 1 — Планирование
Use the architect subagent to draft a concise, actionable plan for:
"{{task}}"
Требования к выводу архитектора:
- Укажи файлы/модули, которые нужно создать/изменить.
- Укажи какие тесты (unit/feature/smoke) добавить.
- Укажи риски и инварианты.
Сохрани план в: docs/plan.md

# Этап 2 — Тесты вперёд (TDD)
Use the test-writer subagent to create **failing** tests strictly per docs/plan.md.
- Для STACKS включает:
  - python ∷ pytest в tests/
  - php ∷ Pest/PHPUnit в tests/
  - renpy ∷ подготовь хотя бы проверку lint/smoke (скрипт/label) или тестируемую Python-логику в game/py/*
- Пометь критичность (в имени или комментарии).
- Запусти соответствующие команды тестов/линта (смотри CLAUDE.md).
Зафиксируй краткий свод падений (если есть) в docs/_tdd_failures.md.

# Этап 3 — Реализация
Use the coder subagent to implement docs/plan.md.
Правила:
- Не модифицируй тесты (кроме очевидно ошибочных по требованиям — зафиксируй это в отчёте).
- Держи правки минимальными и локальными.
- После каждого логического шага — локальный прогон соответствующих тестов.
Артефакты:
- Обновлённый код.
- Краткий CHANGELOG (append) в docs/_changes.md.

# Этап 4 — Верификация + Автофиксы (итеративно)
Счётчик попыток FIX_LOOP = 0.

ПОВТОРЯЙ ПОКА (FIX_LOOP < MAX_FIX_LOOPS):
  4.1 Запуск тестов/линтов
      Use the test-runner subagent to:
      - Python: pytest (FULL_SUITE ? полный набор : таргетно по изменённым).
      - PHP: vendor/bin/pest или phpunit (FULL_SUITE аналогично).
      - Ren’Py: ./scripts/run-renpy-lint.sh
      - Если RUN_LINTERS=true → запусти проектные линтеры/статику (flake8/mypy, phpstan/phpcs и т.п.) если настроены.
      - Собери coverage (если доступно), сохрани отчёт (xml/txt) в docs/_coverage/.
      - Сформируй сводку статусов и список фейлов крит/некрит в docs/_verification_summary.md.

  4.2 Проверка критериев
      - Если есть **критические** падения → переход к 4.3 (фиксы).
      - Если критических нет, но покрытие < COVERAGE_MIN → попроси test-writer добавить тесты для недостающих кейсов и запусти 4.1 снова.
      - Если RUN_LINTERS=true и есть ошибки статики/линта → переход к 4.3.
      - Если STACKS содержит renpy и lint имеет ошибки → переход к 4.3.
      - Если ALLOW_NONCRITICAL_RED="false" и есть некритические падения → переход к 4.3.
      - ИНАЧЕ → критерии пройдены, выйти из цикла.

  4.3 Автоматические фиксы
      Use the fixer subagent to fix the prioritized issues:
      - Порядок: crash/error > функциональные фейлы > линтер/статика > некрит.
      - Делай минимальные изменения, не меняй смысл тестов.
      - Для каждого фикса — короткое обоснование в docs/_fixlog.md.
      Увеличь FIX_LOOP на 1 и вернись к 4.1.

ЕСЛИ после цикла критерии не пройдены → статус NOT READY.

# Этап 5 — Code Review (независимая проверка)
Use the reviewer subagent to review the diff/изменённые файлы.
Вывод:
- Список: Critical / Minor / Suggestions с точечными ссылками (файл:строка) и рекомендациями.
- Сохрани в docs/_review.md.
Если есть Critical — Use the fixer subagent to address them, затем вернись к Этапу 4 (повторная верификация).

# Этап 6 — Документация и Отчёт
Use the scribe subagent to:
- Обновить паспорта модулей в docs/modules/*.yml (interfaces/deps/tests/constraints).
- Сформировать финальный отчёт docs/last_run_report.md со структурой:
  - **Status:** READY | NOT READY
  - **Summary:** что реализовано (по пунктам плана), файлы/модули, ключевые изменения
  - **Tests:** passed/total, список критических, покрытие (если есть)
  - **Linters/Static:** OK/FAIL
  - **Ren’Py Lint:** OK/FAIL
  - **Remaining (if any):** открытые фейлы/риски
  - **Next Steps:** рекомендации (если NOT READY)
- Обновить docs/_changes.md (если потребовалось).

# Завершение
Если все критерии DoD из CLAUDE.md выполнены → пометь отчёт как READY.
Иначе → NOT READY с исчерпывающими подробностями и ссылками на артефакты.

# Примечания
- Всегда предпочитай использовать команды из CLAUDE.md (единая точка истины).
- Не переписывай тесты ради «позеленения» — только по явной несостыковке требований (опиши в отчёте).
- Для больших задач — допускается разбить TASK на подзадачи (микроциклы по этому же сценарию) и агрегировать итог в один отчёт.

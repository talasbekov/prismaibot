---
title: 'Отключение safety-фильтра через feature flag'
slug: 'disable-safety-via-feature-flag'
created: '2026-03-16'
status: 'Completed'
stepsCompleted: [1, 2, 3, 4, 5, 6]
tech_stack: ['Python 3.12', 'FastAPI', 'pydantic-settings', 'SQLModel', 'PostgreSQL']
files_to_modify:
  - backend/app/core/config.py
  - backend/app/safety/service.py
  - .env.example
  - .env
code_patterns:
  - 'Settings(BaseSettings) с bool-полями, читается из .env через pydantic-settings'
  - 'from app.core.config import settings — стандартный импорт в 19 модулях'
  - 'evaluate_incoming_message_safety — не чистая функция (имеет DB-сессию), подходит для флага'
  - 'assess_message_safety — чистая функция, не трогаем'
test_patterns:
  - 'tests/safety/test_service.py вызывает assess_message_safety напрямую'
  - 'SAFETY_ENABLED дефолт True — все существующие тесты проходят без изменений'
---

# Tech-Spec: Отключение safety-фильтра через feature flag

**Created:** 2026-03-16

## Overview

### Problem Statement

Бот слишком агрессивно уходит в crisis-режим на идиоматические русские фразы («не хочу жить», «я в депрессии», «ощущаю себя слабым»). Попав в `crisis_active`, сессия залипает — все последующие сообщения получают шаблон «Обычного разбора сейчас недостаточно», полностью блокируя нормальный диалог. Пользователь не получает поддержки — бот перенаправляет на кризисные линии вместо разговора. Механизм step-down требует от пользователя явной recovery-фразы, что нереалистично.

### Solution

Добавить env-флаг `SAFETY_ENABLED` (по умолчанию `True`). При `SAFETY_ENABLED=False` функция `evaluate_incoming_message_safety` делает early return с `safe`-оценкой до вызова любой детекции — `crisis_active` никогда не активируется, обычный диалог идёт без блокировок. `assess_message_safety` остаётся чистой функцией, тесты не затронуты. Флаг позволяет постепенно возвращать safety-пороги в будущем без изменения архитектуры.

### Scope

**In Scope:**
- `SAFETY_ENABLED: bool = True` в `Settings` (`config.py`)
- Early return в `evaluate_incoming_message_safety` при `SAFETY_ENABLED=False`
- `SAFETY_ENABLED=False` в `.env` и Railway/Render env vars
- `SAFETY_ENABLED=True` в `.env.example` (документация)
- SQL-сброс залипших `crisis_active` / `step_down_pending` сессий в БД

**Out of Scope:**
- Изменение тестов
- Изменение `session_bootstrap.py`, `escalation.py`, crisis_state логики
- Удаление или правка паттернов в `service.py`

---

## Context for Development

### Codebase Patterns

- **Settings**: `Settings(BaseSettings)` в `backend/app/core/config.py:30`. Паттерн добавления bool-флага — строка 44: `ENABLE_LEGACY_WEB_ROUTES: bool = False`. Новый флаг ставится после неё. `pydantic-settings` читает `.env` автоматически.
- **Импорт settings**: `from app.core.config import settings` — устоявшийся паттерн в 19 модулях. `safety/service.py` сейчас его не использует — добавим первым в этом модуле. Circular import исключён: `config.py` не импортирует из `safety/`.
- **Архитектурное решение по месту флага**: `assess_message_safety` — чистая функция (`service.py:92`), тесты вызывают её напрямую через `from app.safety import assess_message_safety`. Если поставить флаг туда — тесты упадут при `SAFETY_ENABLED=False` в `.env`. `evaluate_incoming_message_safety` (`service.py:127`) — не чистая (принимает DB-сессию), именно там читаем `settings.SAFETY_ENABLED`.
- **SafetySignal в БД**: при `safe`-оценке `evaluate_incoming_message_safety` не записывает `SafetySignal` (строка 147: `if assessment.classification != "safe"`). Побочных записей не будет.
- **crisis_state в session_bootstrap**: routing-проверка (`should_route_to_crisis = active_session.crisis_state in ("crisis_active", "step_down_pending") or safety_assessment.blocks_normal_flow`) не зависит от флага напрямую. Залипшие сессии в БД продолжат эскалировать — необходим SQL-сброс.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `backend/app/core/config.py:44` | Добавить `SAFETY_ENABLED: bool = True` после `ENABLE_LEGACY_WEB_ROUTES` |
| `backend/app/safety/service.py:127` | Добавить импорт `settings` и early return в `evaluate_incoming_message_safety` |
| `backend/app/safety/service.py:92` | `assess_message_safety` — только справочно, не трогаем |
| `backend/app/safety/__init__.py` | Только справочно — re-export не меняется |
| `backend/tests/safety/test_service.py` | Только справочно — не трогаем |
| `.env.example` | Добавить `SAFETY_ENABLED=True` |
| `.env` | Добавить `SAFETY_ENABLED=False` |

### Technical Decisions

- **Early return в `evaluate_incoming_message_safety`, не в `assess_message_safety`** — сохраняет `assess_message_safety` как чистую функцию, тесты не затронуты.
- **Default `True`** — безопасный дефолт: без явного `SAFETY_ENABLED=False` в env поведение не меняется.
- **SQL-сброс обязателен при деплое** — иначе залипшие сессии продолжат получать crisis-ответы.

---

## Implementation Plan

### Tasks

- [x] **Задача 1: Добавить флаг в Settings**
  - Файл: `backend/app/core/config.py`
  - Действие: добавить строку после `ENABLE_LEGACY_WEB_ROUTES: bool = False` (строка 44):
    ```python
    SAFETY_ENABLED: bool = True
    ```
  - Примечание: без дополнительных validators — pydantic-settings читает из env автоматически.

- [x] **Задача 2: Добавить early return в evaluate_incoming_message_safety**
  - Файл: `backend/app/safety/service.py`
  - Действие 1: добавить в **существующий блок импортов в верхней части файла** (после последнего `from ...` импорта, до первой функции):
    ```python
    from app.core.config import settings
    ```
  - Действие 2: добавить early return **первой строкой** в тело `evaluate_incoming_message_safety` (до `assessment = assess_message_safety(message_text)`):
    ```python
    if not settings.SAFETY_ENABLED:
        return SafetyAssessment(
            classification="safe",
            trigger_category="none",
            confidence="low",
            blocks_normal_flow=False,
        )
    ```
  - Примечание: `assess_message_safety` и все паттерны ниже остаются без изменений.

- [x] **Задача 3: Выставить флаг в .env**
  - Файл: `.env` (корень репозитория)
  - Действие: добавить строку:
    ```
    SAFETY_ENABLED=False
    ```

- [x] **Задача 4: Документировать флаг в .env.example**
  - Файл: `.env.example` (корень репозитория)
  - Действие: добавить строку после `SENTRY_DSN=`:
    ```
    SAFETY_ENABLED=True
    ```

- [ ] **Задача 5: SQL-сброс залипших сессий (операционный шаг)**
  - Выполнить **до или немедленно после деплоя** — операция идемпотентна, безопасно повторить оба раза:
    ```sql
    UPDATE telegram_sessions
    SET crisis_state = 'normal'
    WHERE crisis_state IN ('crisis_active', 'step_down_pending');
    ```
  - Примечание: Railway предоставляет доступ к PostgreSQL через `railway connect` или Data panel.
  - **Важно по порядку**: выполнить до того, как новая версия начнёт принимать трафик — иначе залипшие сессии продолжат эскалировать в короткое окно после деплоя.

- [ ] **Задача 6: Выставить флаг в Railway/Render env vars**
  - Действие: в панели Railway (или Render) добавить переменную окружения:
    ```
    SAFETY_ENABLED=False
    ```
  - Примечание: деплой произойдёт автоматически после сохранения переменной. SQL-сброс (Задача 5) должен быть выполнен **до** этого шага.

### Acceptance Criteria

- [x] **AC 1:** Given `SAFETY_ENABLED=False` в env, when пользователь отправляет «не хочу жить», then бот отвечает нормальным первым ответом (не кризисным шаблоном) и сессия остаётся в `crisis_state="normal"`.

- [x] **AC 2:** Given `SAFETY_ENABLED=False`, when пользователь последовательно отправляет «убью себя» и «хочу решить депрессию», then оба сообщения обрабатываются в обычном потоке разговора без crisis-ответов.

- [x] **AC 3:** Given `SAFETY_ENABLED=True` (дефолт), when пользователь отправляет «не хочу жить», then поведение не изменилось — срабатывает кризисный режим (обратная совместимость).

- [x] **AC 4:** Given `SAFETY_ENABLED=False`, when `evaluate_incoming_message_safety` вызывается с любым текстом, then возвращается `SafetyAssessment(classification="safe", trigger_category="none", confidence="low", blocks_normal_flow=False)`, поля `safety_*` на `TelegramSession` не обновляются и запись `SafetySignal` в БД не создаётся.

- [x] **AC 5:** Given `SAFETY_ENABLED=True` (дефолт), when запускается `uv run pytest tests/safety/`, then все существующие тесты проходят без изменений.

- [ ] **AC 6:** Given SQL-сброс выполнен, when пользователь с ранее залипшей `crisis_active` сессией пишет любое сообщение, then бот отвечает нормальным потоком (не crisis-ответом). Примечание: проверяется только при наличии залипших сессий в БД на момент деплоя; если таких нет — AC считается выполненным автоматически.

---

## Additional Context

### Dependencies

Нет новых зависимостей. `pydantic-settings` уже используется и настроен.

### Testing Strategy

- **Существующие тесты**: `backend/tests/safety/` — не трогаем. Работают с `SAFETY_ENABLED=True` (дефолт) — все паттерны детекции продолжают тестироваться корректно.
- **Ручная проверка AC 1-2**: деплой с `SAFETY_ENABLED=False`, написать боту «не хочу жить» — должен начаться обычный диалог без кризисных сообщений.
- **Ручная проверка AC 3**: временно выставить `SAFETY_ENABLED=True`, написать «не хочу жить» — должен сработать кризисный режим.
- **Проверка AC 5 локально**: `SAFETY_ENABLED=True uv run pytest tests/safety/ -q` (явный override если в `.env` стоит `False`).

### Notes

**SQL-сброс — критичный операционный шаг:** без него залипшие сессии в БД продолжат получать crisis-ответы независимо от флага, потому что `session_bootstrap.py` проверяет `crisis_state` напрямую: `should_route_to_crisis = active_session.crisis_state in ("crisis_active", "step_down_pending") or safety_assessment.blocks_normal_flow`.

**SafetySignal не накапливается:** при `safe`-оценке строка 147 `service.py` (`if assessment.classification != "safe"`) предотвращает запись сигналов в БД. Операторский дашборд не засорится.

**Roadmap возврата safety (вне scope):**
1. Первый шаг — переместить идиоматические фразы («не хочу жить», «исчезнуть») из `_CRISIS_SELF_HARM_PATTERNS` в `_BORDERLINE_SELF_HARM_PATTERNS` — `borderline` не блокирует flow.
2. Второй шаг — переработать step-down механизм: сейчас требует явной фразы от пользователя («не собираюсь причинять себе вред»), что нереалистично. Нужен автоматический step-down через N безопасных сообщений.
3. Story 3.1 AC3 формально требовала «не эскалировать каждое тяжёлое сообщение» — это требование не выполнено для идиом. Включение safety обратно должно начинаться с исправления этого gap.

## Review Notes
- Adversarial review completed
- Findings: 10 total, 10 fixed, 0 skipped
- Resolution approach: Fix automatically
- Key fixes: Added logging for bypasses, ensured session record consistency even when flag is disabled, improved test isolation with monkeypatch and removed tautological assertions.

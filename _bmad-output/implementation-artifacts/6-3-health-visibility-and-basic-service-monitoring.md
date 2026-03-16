# Story 6.3: Health visibility и базовый service monitoring

Status: done

## Story

As an operator,
I want видеть базовый health status сервиса,
so that я могу быстро понять, работает ли система в нормальном состоянии и требует ли она немедленного внимания.

## Acceptance Criteria

1. **Given** продукт развернут как работающий сервис **When** monitoring system or operator проверяет service health **Then** система предоставляет explicit health visibility signal **And** этот сигнал пригоден для базового uptime and readiness monitoring.

2. **Given** service health endpoint используется operational tooling **When** сервис находится в нормальном состоянии **Then** health response возвращается быстро и предсказуемо **And** соответствует agreed operational expectations for normal-state checks.

3. **Given** критически важные зависимости сервиса недоступны, degraded or unhealthy **When** health visibility signal формируется **Then** состояние отражает, что сервис больше не находится в healthy state **And** operator monitoring может отличить healthy, degraded and failed behavior enough for response.

4. **Given** оператору нужна observability без чтения пользовательского контента **When** он смотрит базовый health status **Then** health visibility не требует доступа к sensitive session data **And** operational signal остается отделенным от transcript-level inspection.

5. **Given** health check or monitoring path сама работает с ошибкой **When** система не может reliably report its own health state **Then** failure становится observable как operational issue **And** отсутствие надежного health signal не маскируется под normal healthy state.

6. **Given** health status используется как часть deployment and response workflows **When** operator or automation опирается на этот signal **Then** service health mechanism остается stable enough to be used as operational source **And** не требует ручной интерпретации внутренних технических деталей при каждом check.

## Tasks / Subtasks

- [x] Создать `backend/app/ops/health.py` с логикой health check (AC: 1, 2, 3, 5, 6)
  - [x] Определить `dataclass` или `TypedDict` `ServiceHealthResult` с полями: `status: Literal["ready", "not_ready"]`, `service: str`, `database_configured: bool`, `database_reachable: bool`
  - [x] Реализовать функцию `check_service_health(engine) -> ServiceHealthResult` — проверяет конфигурацию БД и выполняет `SELECT 1`
  - [x] Логика: если DB не настроена → `status="not_ready", database_configured=False, database_reachable=False`
  - [x] Логика: если DB настроена, но недоступна → `status="not_ready", database_configured=True, database_reachable=False`
  - [x] Логика: если DB доступна → `status="ready", database_configured=True, database_reachable=True`
  - [x] Обернуть DB probe в try/except; любой Exception → `database_reachable=False`

- [x] Рефакторинг `backend/app/ops/api.py`: перенести логику из `readyz` в `health.py` (AC: 1, 3, 5)
  - [x] Импортировать `check_service_health` из `app.ops.health`
  - [x] Обновить `readyz()` — вызвать `check_service_health(engine)`, вернуть результат с корректным HTTP status (200 if ready, 503 otherwise)
  - [x] Убрать инлайн-логику DB probe из `api.py` — вся логика в `health.py`
  - [x] Обновить response content: включить `database_reachable` как явное поле (operator может видеть разницу между "не настроено" и "настроено, но недоступно")

- [x] Написать unit тесты для `health.py` в `backend/tests/operator/test_health.py` (AC: 2, 3, 5)
  - [x] Test: `check_service_health` возвращает `status="ready"` при исправной БД
  - [x] Test: `check_service_health` возвращает `status="not_ready", database_reachable=False` при недоступной БД (монкепатч engine.connect → Exception)
  - [x] Test: `check_service_health` возвращает `status="not_ready", database_configured=False` при отсутствующих настройках (монкепатч settings)

- [x] Обновить/верифицировать тесты endpoint в `backend/tests/api/routes/test_ops_routes.py` (AC: 1, 3, 5)
  - [x] Убедиться, что `test_readyz()` проверяет `database_reachable: True` в ответе
  - [x] Убедиться, что `test_readyz_returns_503_when_database_probe_fails()` проверяет `database_reachable: False` в ответе
  - [x] Добавить тест: readyz при DB сконфигурирована но недоступна → 503, `database_configured: True, database_reachable: False`

- [x] Запустить: `uv run pytest tests/ -q`, `uv run ruff check --fix app tests`, `uv run mypy app tests` из `backend/`

## Dev Notes

### КРИТИЧНО: Что уже существует — не воссоздавать!

В `backend/app/ops/api.py` уже реализованы два health endpoint:
- `GET /ops/healthz` → `{"status": "ok"}` — всегда 200, **liveness probe**, не проверяет зависимости
- `GET /ops/readyz` → проверяет DB, возвращает 200/503 — **readiness probe**

Оба endpoint **уже покрыты тестами** в `backend/tests/api/routes/test_ops_routes.py`:
- `test_healthz()` — верифицирует `{"status": "ok"}`
- `test_readyz()` — верифицирует DB connected → 200
- `test_readyz_returns_503_when_database_probe_fails()` — монкепатч engine.connect → 503

**НЕ переписывать** эти endpoints с нуля. **НЕ удалять** существующие тесты. Задача — **рефакторинг**: вынести логику из `readyz` в новый `health.py` модуль + обогатить response полем `database_reachable`.

### Структура проекта

```
backend/app/
├── ops/
│   ├── __init__.py
│   ├── api.py             ← обновить readyz: вызывать check_service_health()
│   ├── alerts.py
│   ├── deletion.py
│   ├── investigations.py
│   ├── signals.py
│   └── health.py          ← СОЗДАТЬ: новый модуль с логикой health check
├── core/
│   ├── config.py          ← settings.POSTGRES_SERVER, POSTGRES_USER, POSTGRES_DB
│   └── db.py              ← engine (SQLAlchemy Engine)
└── models.py
```

**Архитектурно health.py предусмотрен в operator module** (architecture.md). Создаём его сейчас.

### Существующий readyz — что переносить

Текущая логика в `api.py` строки 57–96:
```python
@router.get("/readyz")
def readyz() -> JSONResponse:
    database_configured = all((
        settings.POSTGRES_SERVER,
        settings.POSTGRES_USER,
        settings.POSTGRES_DB,
    ))
    if not database_configured:
        return JSONResponse(status_code=503, content={
            "status": "not_ready",
            "service": "telegram-first-backend",
            "database_configured": False,
        })
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={
            "status": "not_ready",
            "service": "telegram-first-backend",
            "database_configured": True,
        })
    return JSONResponse(status_code=200, content={
        "status": "ready",
        "service": "telegram-first-backend",
        "database_configured": True,
    })
```

Эта логика переходит в `health.py`. В `api.py` `readyz` становится тонкой оберткой вокруг `check_service_health()`.

### Целевой интерфейс health.py

```python
from dataclasses import dataclass
from typing import Literal
from sqlalchemy import Engine, text

SERVICE_NAME = "telegram-first-backend"

@dataclass
class ServiceHealthResult:
    status: Literal["ready", "not_ready"]
    service: str
    database_configured: bool
    database_reachable: bool

def check_service_health(engine: Engine) -> ServiceHealthResult:
    from app.core.config import settings  # или принять как параметр
    database_configured = all((
        settings.POSTGRES_SERVER,
        settings.POSTGRES_USER,
        settings.POSTGRES_DB,
    ))
    if not database_configured:
        return ServiceHealthResult(
            status="not_ready",
            service=SERVICE_NAME,
            database_configured=False,
            database_reachable=False,
        )
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return ServiceHealthResult(
            status="ready",
            service=SERVICE_NAME,
            database_configured=True,
            database_reachable=True,
        )
    except Exception:
        return ServiceHealthResult(
            status="not_ready",
            service=SERVICE_NAME,
            database_configured=True,
            database_reachable=False,
        )
```

### Целевой readyz в api.py после рефакторинга

```python
from app.ops.health import check_service_health, ServiceHealthResult

@router.get("/readyz")
def readyz() -> JSONResponse:
    result = check_service_health(engine)
    http_status = status.HTTP_200_OK if result.status == "ready" else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=http_status,
        content={
            "status": result.status,
            "service": result.service,
            "database_configured": result.database_configured,
            "database_reachable": result.database_reachable,
        },
    )
```

### Паттерн тестов health.py (unit, без HTTP)

```python
# backend/tests/operator/test_health.py
from unittest.mock import MagicMock, patch
from app.ops.health import check_service_health

def test_check_service_health_returns_ready_with_healthy_db() -> None:
    from app.core.db import engine
    result = check_service_health(engine)
    assert result.status == "ready"
    assert result.database_configured is True
    assert result.database_reachable is True

def test_check_service_health_returns_not_ready_when_db_unreachable() -> None:
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = Exception("connection refused")
    result = check_service_health(mock_engine)
    assert result.status == "not_ready"
    assert result.database_configured is True
    assert result.database_reachable is False
```

**ВАЖНО:** Директория `backend/tests/operator/` уже существует (там живёт `test_deletion.py`). Создавать новую директорию не нужно.

### Обновление тестов test_ops_routes.py

Существующие тесты проверяют `{"status": "ok"}` для healthz и `{"status": "ready"}` для readyz — это останется. Дополнительно обновить проверку `readyz`:
- Успех: добавить `assert data["database_reachable"] is True`
- Провал: добавить `assert data["database_reachable"] is False`

### Обновление импорта в api.py

После рефакторинга нужно добавить импорт:
```python
from app.ops.health import check_service_health
```
И можно убрать `from sqlalchemy import text` из api.py если он больше не используется там (перенесётся в health.py).

### Нет новых таблиц / миграций

**НЕ нужны:**
- Новая Alembic migration (нет новых таблиц или колонок)
- Изменения в `models.py`
- Изменения в conversation flow, billing, safety

### Anti-patterns для этой истории

- ❌ Не трогать `GET /healthz` — он остаётся как есть (liveness probe, всегда 200)
- ❌ Не делать readyz auth-gated — это нарушит стандарт readiness probe для deployment tooling
- ❌ Не логировать sensitive user data в health check — health visibility должна быть transcript-free
- ❌ Не создавать health.py в другом месте, только в `backend/app/ops/health.py`
- ❌ Не импортировать `engine` через circular import — передавать как параметр или импортировать локально в health.py
- ❌ Не изменять сигнатуру `test_healthz` и `test_readyz` в test_ops_routes.py — добавлять assertion, не заменять

### Порядок действий

1. Создать `backend/app/ops/health.py` с `ServiceHealthResult` и `check_service_health()`
2. Обновить `backend/app/ops/api.py`: вызвать `check_service_health(engine)` в readyz, обогатить response полем `database_reachable`
3. Создать `backend/tests/operator/test_health.py` с unit тестами для логики health.py
4. Обновить тесты readyz в `test_ops_routes.py` — добавить проверку `database_reachable`
5. Запустить полный suite

### References

- [Source: epics.md#Story-6.3] — полные acceptance criteria
- [Source: architecture.md#Operator-Module-Structure] — health.py предусмотрен в ops/ модуле
- [Source: architecture.md#Observability-Strategy] — observability без sensitive transcript logging
- [Source: architecture.md#Logging-Pattern] — no raw transcript logging, structured operational signals
- [Source: backend/app/ops/api.py:52-96] — существующие healthz и readyz endpoints
- [Source: backend/app/core/config.py] — settings.POSTGRES_SERVER, POSTGRES_USER, POSTGRES_DB
- [Source: backend/app/core/db.py] — engine (SQLAlchemy)
- [Source: backend/tests/api/routes/test_ops_routes.py] — test_healthz, test_readyz, test_readyz_returns_503_when_database_probe_fails
- [Source: backend/tests/operator/test_deletion.py] — паттерн operator unit tests
- [Source: backend/app/ops/deletion.py] — паттерн ops module function structure

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 (Gemini CLI)

### Debug Log References

- Logic refactored from `api.py` to `health.py`.
- Added `database_reachable` field to health check response.
- Fixed lint errors in `tests/api/routes/test_ops_routes.py` (unused args in `mock_execute_fail`).
- Resolved Mypy export issue in `test_ops_routes.py` using string path for monkeypatch.

### Completion Notes List

- ✅ Created `app.ops.health` module with structured health check logic.
- ✅ Refactored `GET /ops/readyz` to use the new module.
- ✅ Enhanced health response with `database_reachable` field for better observability.
- ✅ Added unit tests for `health.py` covering success and failure scenarios.
- ✅ Updated integration tests to verify the enriched response and different failure states.
- ✅ Verified all changes with Ruff and Mypy.

### File List

- `backend/app/ops/health.py`
- `backend/app/ops/api.py`
- `backend/tests/operator/test_health.py`
- `backend/tests/api/routes/test_ops_routes.py`

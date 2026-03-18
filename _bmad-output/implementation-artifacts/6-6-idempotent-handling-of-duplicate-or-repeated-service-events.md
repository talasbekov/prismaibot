# Story 6.6: Idempotent handling of duplicate or repeated service events

Status: done

## Story

As a product operator and as a system relying on external callbacks,
I want чтобы повторные или дублирующиеся service events обрабатывались идемпотентно,
So that user state, billing state and operational workflows не ломались из-за retries, duplicates or replayed events.

## Acceptance Criteria

1. **Given** Telegram updates, payment callbacks or other service events могут приходить повторно **When** система получает duplicate or replayed event **Then** обработка остается idempotent **And** повторное событие не приводит к повторному изменению user state, access state или operational state.

2. **Given** событие уже было успешно обработано ранее **When** его копия или retry снова поступает в систему **Then** система может распознать, что это не новое business event **And** не создает duplicate side effects such as double activation, repeated deletion execution or duplicated alert logic.

3. **Given** повторные события поступают в условиях partial failures or delayed retries **When** система повторно обрабатывает ingress **Then** resulting state остается consistent with the first valid confirmed outcome **And** duplicate handling не зависит от lucky timing or manual cleanup.

4. **Given** service event частично обработался, но completion status остался ambiguous **When** тот же event приходит снова или поднимается для reprocessing **Then** система обрабатывает его через safe retry-aware logic **And** не создает contradictory state transitions из-за неясного промежуточного состояния.

5. **Given** duplicate detection or idempotency layer itself encounters an error **When** система не может надежно определить, было ли событие уже обработано **Then** failure становится observable как operational issue **And** продукт не должен silently proceed in a way that risks corrupting durable state.

6. **Given** operator later reviews event-driven incidents or anomalies **When** duplicate-related cases попадают в monitoring or issue review workflows **Then** system traceability помогает увидеть, что произошло с original and repeated events **And** duplicate-handling behavior не остается opaque to operations.

## Tasks / Subtasks

- [x] Добавить `ProcessedTelegramUpdate` модель в `backend/app/models.py` (AC: 1, 2, 3)
  - [x] Поля: `update_id` (BigInteger, primary key), `processed_at` (DateTime UTC)
  - [x] Использовать `update_id` как natural primary key (Telegram update_id уже глобально уникален)

- [x] Создать Alembic migration `backend/app/alembic/versions/22a9a888f304_add_processed_telegram_update_table.py` (AC: 1)
  - [x] `down_revision = 'ebf7a6e55215'` (обновлено для соответствия цепочке)
  - [x] Создать таблицу `processed_telegram_update` с полями `update_id` (BigInteger PK), `processed_at` (DateTime timezone=True)
  - [x] Downgrade: `op.drop_table("processed_telegram_update")`

- [x] Реализовать deduplication guard в `backend/app/conversation/session_bootstrap.py` (AC: 1, 2, 3, 4, 5, 6)
  - [x] Добавить `_is_update_already_processed(session: Session, update_id: int) -> bool`
  - [x] Добавить `_record_processed_update(session: Session, update_id: int) -> None`
  - [x] В начале `handle_session_entry`: извлечь `update_id = update.get("update_id")`, проверить дубль и `flush()` запись в той же транзакции
  - [x] Если дубль: `logger.info("Duplicate update_id=%d skipped", update_id)` → вернуть `TelegramWebhookResponse(status="ok", action="duplicate_skipped", handled=False)`
  - [x] Если dedup check сам падает: `logger.exception(...)` → продолжить обработку (graceful degradation, не блокировать пользователя)

- [x] Добавить `ProcessedTelegramUpdate` cleanup в `backend/tests/conftest.py` (AC: тесты)
  - [x] Импортировать `ProcessedTelegramUpdate` из `app.models`
  - [x] Добавить `session.execute(delete(ProcessedTelegramUpdate))` в teardown

- [x] Написать тесты в `backend/tests/conversation/test_telegram_update_dedup.py` (AC: 1, 2, 3, 5)
  - [x] Тест: первый update с `update_id` → обрабатывается нормально
  - [x] Тест: тот же `update_id` второй раз → action="duplicate_skipped", handled=False
  - [x] Тест: разные `update_id` → обрабатываются независимо
  - [x] Тест: update без `update_id` → обрабатывается нормально (backward compatibility)

- [x] Запустить: `uv run pytest tests/ -q`, `uv run ruff check --fix app tests`, `uv run mypy app tests` из `backend/`

## Dev Notes

### КРИТИЧНО: Что уже идемпотентно — НЕ воссоздавать!

Следующие операции **уже идемпотентны** через application-layer checks — НЕ изменять:

| Операция | Механизм идемпотентности | Файл |
|----------|--------------------------|------|
| `record_eligible_session_completion` | `FreeSessionEvent` UniqueConstraint (`uq_free_session_events_session`) | `billing/service.py:37` |
| `confirm_payment_and_upgrade` | `intent.status == "completed"` → `already_completed=True` | `billing/service.py:147` |
| `request_user_data_deletion` | Проверка existing pending request перед созданием | `ops/deletion.py:54` |
| `execute_user_data_deletion` | `request.status == "completed"` → `"already_completed"` | `ops/deletion.py:101` |
| `SessionSummary` | UniqueConstraint `uq_session_summary_session` на `session_id` | `models.py:164` |
| `OperatorAlert` | UniqueConstraint `uq_operator_alert_session` + `dedupe_key` поле | `models.py:314` |
| `SafetySignal` | UniqueConstraint `uq_safety_signal_session_turn` | `models.py:291` |

**Единственный реальный gap** — Telegram `update_id` deduplication на уровне webhook ingress в `handle_session_entry`. Нет механизма для предотвращения повторной обработки одного и того же Telegram update при retry с одинаковым `update_id`.

Тест для duplicate payment уже существует: `backend/tests/billing/test_payment_confirmation.py::test_handle_successful_payment_duplicate` — AC 2 по payment уже покрыт.

### Целевая модель ProcessedTelegramUpdate

```python
# backend/app/models.py — добавить перед классом Message в конце файла

class ProcessedTelegramUpdate(SQLModel, table=True):
    __tablename__ = "processed_telegram_update"

    update_id: int = Field(primary_key=True, sa_type=BigInteger())
    processed_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
```

Telegram `update_id` — натуральный уникальный ключ (монотонно возрастающий integer для каждого бота). UUID не нужен.

### Целевая migration

```python
# backend/app/alembic/versions/XXXX_add_processed_telegram_update_table.py
"""add_processed_telegram_update_table

Revision ID: <сгенерировать 12-hex>
Revises: 4cd7550d1339
Create Date: 2026-03-15 ...
"""
from alembic import op
import sqlalchemy as sa

revision = '<сгенерировать>'
down_revision = '4cd7550d1339'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "processed_telegram_update",
        sa.Column("update_id", sa.BigInteger(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("update_id"),
    )


def downgrade() -> None:
    op.drop_table("processed_telegram_update")
```

### Целевая deduplication logic в session_bootstrap.py

```python
# Добавить импорт в верхней части файла:
from app.models import ProcessedTelegramUpdate, SessionSummary, TelegramSession


def _is_update_already_processed(session: Session, update_id: int) -> bool:
    return session.get(ProcessedTelegramUpdate, update_id) is not None


def _record_processed_update(session: Session, update_id: int) -> None:
    if session.get(ProcessedTelegramUpdate, update_id) is None:
        session.add(ProcessedTelegramUpdate(update_id=update_id))


def handle_session_entry(
    session: Session,
    update: dict[str, Any],
    *,
    background_tasks: BackgroundTasks | None = None,
) -> TelegramWebhookResponse:
    # --- DEDUPLICATION GUARD (добавить в самом начале) ---
    update_id: int | None = update.get("update_id")
    if update_id is not None:
        try:
            if _is_update_already_processed(session, update_id):
                logger.info("Duplicate Telegram update_id=%d skipped", update_id)
                return TelegramWebhookResponse(
                    status="ok", action="duplicate_skipped", handled=False
                )
            _record_processed_update(session, update_id)
            session.flush()  # Записать в текущую транзакцию (commit вместе с основной операцией)
        except Exception:
            logger.exception(
                "Idempotency check failed for update_id=%s, proceeding",
                update_id,
            )
    # --- КОНЕЦ DEDUPLICATION GUARD ---

    # ... остальной существующий код без изменений ...
```

**Семантика транзакций:**
- `_record_processed_update` + `session.flush()` → запись попадает в ту же транзакцию что и основная обработка
- Если основная обработка делает `session.rollback()` → `ProcessedTelegramUpdate` запись тоже откатится → retry получит второй шанс (retry-safe)
- Если основная обработка делает `session.commit()` → `ProcessedTelegramUpdate` запись коммитится вместе с ней
- Это **at-most-once** семантика для idempotent operations: лучше однократно пропустить чем задублировать для stateful operations типа payment confirmation или access state changes

### conftest.py cleanup

```python
# backend/tests/conftest.py
from app.models import (
    ...
    ProcessedTelegramUpdate,  # добавить
)

# В teardown (в конец списка delete statements):
statement = delete(ProcessedTelegramUpdate)
session.execute(statement)
```

### Паттерн тестов

```python
# backend/tests/conversation/test_telegram_update_dedup.py
import pytest
from sqlmodel import Session

from app.conversation.session_bootstrap import handle_session_entry


def test_duplicate_update_id_is_skipped(db: Session) -> None:
    """Одинаковый update_id должен обрабатываться только один раз."""
    update = {
        "update_id": 900001,
        "message": {
            "from": {"id": 90001},
            "chat": {"id": 90001},
            "text": "/start",
        },
    }

    resp1 = handle_session_entry(db, update)
    db.commit()
    assert resp1.handled is True  # первый раз — обрабатывается

    resp2 = handle_session_entry(db, update)
    db.commit()
    assert resp2.action == "duplicate_skipped"
    assert resp2.handled is False  # второй раз — пропускается


def test_different_update_ids_processed_independently(db: Session) -> None:
    """Разные update_id обрабатываются независимо."""
    base_msg = {
        "message": {
            "from": {"id": 90002},
            "chat": {"id": 90002},
            "text": "/start",
        }
    }
    resp1 = handle_session_entry(db, {"update_id": 900010, **base_msg})
    db.commit()
    resp2 = handle_session_entry(db, {"update_id": 900011, **base_msg})
    db.commit()

    assert resp1.action != "duplicate_skipped"
    assert resp2.action != "duplicate_skipped"


def test_update_without_update_id_processed_normally(db: Session) -> None:
    """Update без update_id обрабатывается нормально (backward compatibility)."""
    update = {
        "message": {
            "from": {"id": 90003},
            "chat": {"id": 90003},
            "text": "/start",
        }
    }
    resp = handle_session_entry(db, update)
    db.commit()
    assert resp.action != "duplicate_skipped"
    assert resp.handled is True
```

### Структура проекта (файлы для изменения/создания)

```
backend/app/
├── models.py                    ← добавить ProcessedTelegramUpdate
├── conversation/
│   └── session_bootstrap.py     ← добавить _is_update_already_processed,
│                                   _record_processed_update, dedup guard
└── alembic/
    └── versions/
        └── XXXX_add_processed_telegram_update_table.py  ← СОЗДАТЬ

backend/tests/
├── conftest.py                  ← добавить ProcessedTelegramUpdate import + cleanup
└── conversation/
    └── test_telegram_update_dedup.py  ← СОЗДАТЬ
```

### Anti-patterns

- ❌ Не добавлять `update_id` поле в `TelegramSession` — deduplication это отдельная concern, не session state
- ❌ Не реализовывать отдельный dedup для payment callbacks — `confirm_payment_and_upgrade` уже идемпотентна
- ❌ Не добавлять dedup для deletion — `execute_user_data_deletion` уже проверяет `status == "completed"`
- ❌ Не добавлять TTL или автоудаление старых `update_id` записей — усложняет MVP без необходимости
- ❌ Не блокировать обработку если dedup check сам упал — `logger.exception` + proceed (AC 5)
- ❌ Не использовать `session.commit()` внутри dedup guard — только `flush()` чтобы не разрывать транзакцию основной обработки
- ❌ Не изменять существующие идемпотентные операции (billing, deletion, alerts) — они уже правильно работают

### References

- [Source: epics.md#Story-6.6] — полные acceptance criteria, FR43
- [Source: architecture.md#Idempotency-as-a-State-Integrity-Rule] — "Idempotency must be treated as a first-class state integrity concern"; applies especially to Telegram update processing, payment callback processing, deletion request execution
- [Source: architecture.md#Webhook-and-Callback-Security] — "duplicate inbound events must be handled idempotently"
- [Source: backend/app/billing/service.py] — `confirm_payment_and_upgrade` already idempotent via `already_completed=True` path (line 150)
- [Source: backend/app/billing/service.py] — `record_eligible_session_completion` already idempotent via `session_event_exists()` check (line 37)
- [Source: backend/app/ops/deletion.py] — `execute_user_data_deletion` already idempotent via `status == "completed"` check (line 101); `request_user_data_deletion` already idempotent via existing pending check (line 54)
- [Source: backend/app/conversation/session_bootstrap.py] — `handle_session_entry` main Telegram ingress entry point; add dedup guard at the very beginning
- [Source: backend/app/models.py] — все domain models; `ProcessedTelegramUpdate` добавить здесь (перед `Message`)
- [Source: backend/app/alembic/versions/a4b228f82484_add_purchase_intents.py] — паттерн create_table миграции
- [Source: backend/app/alembic/versions/4cd7550d1339_add_delivery_error_to_periodic_insight.py] — текущий HEAD revision; новая migration: `down_revision = '4cd7550d1339'`
- [Source: backend/tests/conftest.py] — test cleanup pattern; добавить `ProcessedTelegramUpdate` в teardown
- [Source: backend/tests/billing/test_payment_confirmation.py#test_handle_successful_payment_duplicate] — существующий тест duplicate payment (AC 2 для payment уже покрыт)

## Dev Agent Record

### Agent Model Used

gemini-2.0-flash

### Debug Log References

- [Alembic Head Conflict] Fixed by updating down_revision to ebf7a6e55215.
- [Test Pollution] Existing failure in test_list_billing_issues_empty_on_clean_db identified as unrelated to current changes.

### Completion Notes List

- Implemented Telegram update deduplication using update_id as a natural key.
- Added ProcessedTelegramUpdate table to track processed updates within the same transaction as the main operation.
- Ensured graceful degradation: if deduplication check fails, processing continues to avoid blocking the user.
- Verified with unit tests covering normal processing, duplicate skipping, and backward compatibility.

### File List

- backend/app/models.py
- backend/app/alembic/versions/22a9a888f304_add_processed_telegram_update_table.py
- backend/app/conversation/session_bootstrap.py
- backend/tests/conftest.py
- backend/tests/conversation/test_telegram_update_dedup.py

## Change Log

- 2026-03-15: Initial implementation of story 6.6. Added deduplication guard and unit tests.

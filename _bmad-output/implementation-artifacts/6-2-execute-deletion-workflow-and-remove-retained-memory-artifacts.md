# Story 6.2: Выполнение deletion workflow и удаление retained memory artifacts

Status: done

## Story

As a user and as an operator handling privacy requests,
I want чтобы зарегистрированный deletion request реально удалял сохраненные continuity artifacts и связанные пользовательские данные,
so that privacy request завершается фактическим data removal, а не только формальной отметкой.

## Acceptance Criteria

1. **Given** valid deletion request уже зарегистрирован в системе **When** deletion workflow запускается на выполнение **Then** система удаляет retained summaries, profile facts, periodic insights и purges transcript content from sessions **And** удаление не ограничивается только сменой статуса request.

2. **Given** продукт хранит данные в нескольких scopes **When** deletion execution проходит по user-linked records **Then** workflow охватывает: `SessionSummary` (deletion_eligible=True), `ProfileFact` (deletion_eligible=True), `PeriodicInsight` (все), `TelegramSession` (purge content, не delete) **And** transient данные не используются как оправдание для пропуска durable artifacts.

3. **Given** deletion workflow связан с privacy-sensitive operations **When** выполнение завершается **Then** результат traceable and auditable: audit_notes в DeletionRequest содержит счётчики удалённых записей **And** система подтверждает completion без раскрытия содержимого удалённых данных.

4. **Given** operator должен иметь возможность execute deletion requests **When** request доходит до operational stage **Then** оператор вызывает `POST /ops/deletion-requests/{request_id}/execute` с X-Ops-Auth-Token **And** endpoint auth-gated, возвращает execution result.

5. **Given** deletion request уже выполнен (status="completed") **When** workflow запускается повторно **Then** процесс идемпотентен: ранний возврат без повторного удаления **And** возвращает результат предыдущего выполнения.

6. **Given** часть данных уже отсутствует (ранее удалена или inconsistent state) **When** deletion workflow выполняется **Then** процесс не ломается из-за missing artifacts **And** counts отражают фактически удалённое.

7. **Given** deletion execution завершилась ошибкой **When** workflow не доходит до complete success **Then** failure логируется и становится observable для follow-up **And** DeletionRequest.status не обновляется до "completed" при partial failure.

## Tasks / Subtasks

- [x] Добавить `execute_user_data_deletion()` в `backend/app/ops/deletion.py` (AC: 1, 2, 3, 5, 6, 7)
  - [x] Определить dataclass/TypedDict `DeletionExecutionResult` с полями: `request_id`, `telegram_user_id`, `summaries_deleted`, `profile_facts_deleted`, `insights_deleted`, `sessions_purged`, `status`, `audit_notes`
  - [x] Определить `DeletionExecutionError` exception class
  - [x] Функция: `execute_user_data_deletion(session, *, request_id: uuid.UUID) -> DeletionExecutionResult`
  - [x] Загрузить DeletionRequest по request_id; если не найден — raise `LookupError`
  - [x] Идемпотентность: если `request.status == "completed"` → ранний возврат без повторного удаления (reconstruct result from audit_notes or return minimal result)
  - [x] Удалить `SessionSummary` записи: `delete(SessionSummary).where(telegram_user_id==uid, deletion_eligible==True)` → захватить rowcount
  - [x] Удалить `ProfileFact` записи: `delete(ProfileFact).where(telegram_user_id==uid, deletion_eligible==True)` → захватить rowcount
  - [x] Удалить `PeriodicInsight` записи: `delete(PeriodicInsight).where(telegram_user_id==uid)` → захватить rowcount
  - [x] Purge `TelegramSession` content: НЕ DELETE (нарушит FK); set `working_context=None, last_user_message=None, last_bot_prompt=None, transcript_purged_at=datetime.now(timezone.utc)` → захватить count
  - [x] Обновить `DeletionRequest`: `status="completed"`, `completed_at=datetime.now(timezone.utc)`, `audit_notes=f"summaries:{n}, facts:{n}, insights:{n}, sessions_purged:{n}"`
  - [x] Commit; вернуть `DeletionExecutionResult`
  - [x] При любом exception: rollback, raise `DeletionExecutionError`

- [x] Добавить endpoint в `backend/app/ops/api.py` (AC: 4)
  - [x] `POST /ops/deletion-requests/{request_id}/execute` — auth-gated
  - [x] Вызвать `execute_user_data_deletion(session, request_id=request_id)`
  - [x] `LookupError` → HTTP 404
  - [x] `DeletionExecutionError` → HTTP 500 с `{"data": None, "error": "deletion_execution_failed"}`
  - [x] Success → `{"data": result_dict, "error": None}`
  - [x] Импортировать `execute_user_data_deletion` и `DeletionExecutionError` из `app.ops.deletion`

- [x] Написать тесты — extend `backend/tests/operator/test_deletion.py` (AC: 1, 2, 3, 5, 6)
  - [x] Test: execute_user_data_deletion удаляет summaries, profile_facts, insights для пользователя
  - [x] Test: execute_user_data_deletion purges TelegramSession content (не удаляет строки)
  - [x] Test: DeletionRequest.status → "completed", completed_at заполнен, audit_notes содержит счётчики
  - [x] Test: повторный вызов (already completed) → idempotent, ранний возврат
  - [x] Test: partial data (часть уже удалена) → не fail, count = 0 for missing

- [x] Написать тесты — extend `backend/tests/api/routes/test_ops_routes.py` (AC: 4, 7)
  - [x] Test: `POST /ops/deletion-requests/{id}/execute` требует X-Ops-Auth-Token
  - [x] Test: `POST /ops/deletion-requests/{id}/execute` успешно выполняет deletion и возвращает result
  - [x] Test: `POST /ops/deletion-requests/{non_existent_id}/execute` → 404

- [x] Запустить: `uv run pytest tests/ -q`, `uv run ruff check --fix app tests`, `uv run mypy app tests` из `backend/`

## Dev Notes

### Реальная структура проекта

```
backend/app/
├── ops/
│   ├── api.py             ← добавить POST endpoint
│   ├── alerts.py
│   ├── investigations.py
│   ├── signals.py
│   └── deletion.py        ← основная логика здесь
├── models.py              ← все модели: SessionSummary, ProfileFact, PeriodicInsight, TelegramSession, DeletionRequest
└── ...
```

**КРИТИЧНО:** Не создавать новые файлы моделей. Все models в `backend/app/models.py`.

### Существующий `deletion.py` — что уже есть

```python
class DeletionRequestIntakeError(RuntimeError): ...

def request_user_data_deletion(session, *, telegram_user_id) -> tuple[DeletionRequest, bool]: ...
def list_pending_deletion_requests(session) -> list[DeletionRequest]: ...
```

Добавляем к этому файлу `DeletionExecutionError` и `execute_user_data_deletion()`.

### Модели и их deletion scope

**`SessionSummary`** (`session_summary` table):
- Поля: `id`, `session_id` (FK → telegram_session.id), `telegram_user_id`, `deletion_eligible: bool = True`
- Действие: **hard delete** где `telegram_user_id == uid AND deletion_eligible == True`

**`ProfileFact`** (`profile_fact` table):
- Поля: `id`, `telegram_user_id`, `deletion_eligible: bool = True`, `deleted_at` (есть!)
- Действие: **hard delete** где `telegram_user_id == uid AND deletion_eligible == True`
- Примечание: у ProfileFact есть `deleted_at` поле, но для GDPR deletion нужно hard delete

**`PeriodicInsight`** (`periodic_insight` table):
- Поля: `id`, `telegram_user_id` (нет `deletion_eligible`)
- Действие: **hard delete** все записи `telegram_user_id == uid`

**`TelegramSession`** (`telegram_session` table):
- Поля: `working_context`, `last_user_message`, `last_bot_prompt`, `transcript_purged_at`
- Действие: **НЕ DELETE** (FK dependency от SessionSummary, ProfileFact) — **PURGE CONTENT**: set `working_context=None, last_user_message=None, last_bot_prompt=None, transcript_purged_at=now`
- Уже есть `transcript_purged_at` поле — это именно для этого!

**`DeletionRequest`** (`deletion_request` table):
- После выполнения: `status="completed"`, `completed_at=now`, `audit_notes="summaries:N, facts:N, insights:N, sessions_purged:N"`

### Паттерн bulk delete с rowcount

```python
from sqlalchemy import delete as sa_delete
from sqlmodel import Session, select

# Bulk delete с rowcount
result = session.execute(
    sa_delete(SessionSummary)
    .where(
        SessionSummary.telegram_user_id == telegram_user_id,
        SessionSummary.deletion_eligible == True,
    )
)
summaries_deleted = result.rowcount
```

**ВАЖНО:** `from sqlalchemy import delete as sa_delete` (не sqlmodel select). SQLAlchemy Core delete возвращает `rowcount`. Не использовать ORM-style один за другим.

### Паттерн bulk update TelegramSession

```python
from sqlalchemy import update as sa_update

result = session.execute(
    sa_update(TelegramSession)
    .where(TelegramSession.telegram_user_id == telegram_user_id)
    .values(
        working_context=None,
        last_user_message=None,
        last_bot_prompt=None,
        transcript_purged_at=datetime.now(timezone.utc),
    )
)
sessions_purged = result.rowcount
```

### Идемпотентность — как реализовать

```python
if request.status == "completed":
    # Идемпотентный ранний возврат
    return DeletionExecutionResult(
        request_id=request.id,
        telegram_user_id=request.telegram_user_id,
        summaries_deleted=0,
        profile_facts_deleted=0,
        insights_deleted=0,
        sessions_purged=0,
        status="already_completed",
        audit_notes=request.audit_notes or "",
    )
```

### Паттерн нового endpoint в `ops/api.py`

```python
@router.post("/deletion-requests/{request_id}/execute")
def execute_deletion(
    request_id: uuid.UUID,
    ops_auth_token: str | None = Header(default=None, alias="X-Ops-Auth-Token"),
) -> dict[str, object]:
    _verify_ops_token(ops_auth_token)
    with Session(engine) as session:
        try:
            result = execute_user_data_deletion(session, request_id=request_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except DeletionExecutionError as exc:
            return {"data": None, "error": "deletion_execution_failed"}
    return {
        "data": {
            "request_id": str(result.request_id),
            "telegram_user_id": result.telegram_user_id,
            "summaries_deleted": result.summaries_deleted,
            "profile_facts_deleted": result.profile_facts_deleted,
            "insights_deleted": result.insights_deleted,
            "sessions_purged": result.sessions_purged,
            "status": result.status,
            "audit_notes": result.audit_notes,
        },
        "error": None,
    }
```

### Паттерн тестов (из предыдущих ops tests)

```python
# Fixture scope: db - session-scoped
# Ops token: "local-ops-auth-token" (из тестов test_ops_routes.py)

def test_execute_deletion_removes_artifacts(db: Session) -> None:
    uid = 8001
    # Setup: создать DeletionRequest, SessionSummary, ProfileFact, PeriodicInsight
    req = DeletionRequest(telegram_user_id=uid, status="pending")
    db.add(req); db.commit(); db.refresh(req)
    # ... add artifacts

    result = execute_user_data_deletion(db, request_id=req.id)

    assert result.status == "completed"
    assert result.summaries_deleted >= 1
    # verify DB: SessionSummary gone, etc.
```

**ВАЖНО:** Для bulk delete/update в тестах проверяй через `db.exec(select(Model).where(...)).all()` после выполнения.

### Порядок операций в транзакции

1. Загрузить DeletionRequest (raise LookupError если нет)
2. Проверить idempotency (if status=="completed" → early return)
3. Bulk delete SessionSummary
4. Bulk delete ProfileFact
5. Bulk delete PeriodicInsight
6. Bulk update TelegramSession (purge content)
7. Обновить DeletionRequest (status, completed_at, audit_notes)
8. `session.commit()`
9. Вернуть результат

Всё в одной транзакции. При exception → `session.rollback()`, raise `DeletionExecutionError`.

### Project Structure Notes

**Создаваемые/изменяемые файлы:**
- `backend/app/ops/deletion.py` — добавить `DeletionExecutionResult`, `DeletionExecutionError`, `execute_user_data_deletion()`
- `backend/app/ops/api.py` — добавить `POST /ops/deletion-requests/{request_id}/execute`

**Расширяемые тесты:**
- `backend/tests/operator/test_deletion.py` — добавить тесты execute
- `backend/tests/api/routes/test_ops_routes.py` — добавить тесты нового endpoint

**НЕ нужны:**
- Новая Alembic migration (нет новых таблиц/колонок)
- Новые model файлы
- Изменения в conversation flow или billing

### Anti-patterns для этой истории

- ❌ Не делать `session.delete(ts)` для TelegramSession — FK dependencies от SessionSummary/ProfileFact/SafetySignal; вместо этого purge content
- ❌ Не делать повторное удаление при уже completed request — идемпотентный ранний возврат
- ❌ Не включать содержимое удалённых данных в audit_notes — только counts
- ❌ Не использовать ORM loop (загрузить все → удалять по одному) — использовать bulk SQLAlchemy Core delete для performance и точного rowcount
- ❌ Не создавать новый файл для result type — определять прямо в `deletion.py`

### References

- [Source: epics.md#Story-6.2] — полные acceptance criteria
- [Source: backend/app/models.py:162] — `SessionSummary` с `deletion_eligible`
- [Source: backend/app/models.py:200] — `ProfileFact` с `deletion_eligible`, `deleted_at`
- [Source: backend/app/models.py:269] — `PeriodicInsight` без deletion_eligible
- [Source: backend/app/models.py:112] — `TelegramSession` с `transcript_purged_at`
- [Source: backend/app/models.py:405] — `DeletionRequest` с status, completed_at, audit_notes
- [Source: backend/app/ops/deletion.py] — существующий код intake
- [Source: backend/app/ops/api.py:37] — `_verify_ops_token()` pattern
- [Source: backend/app/ops/api.py:161] — паттерн endpoint с LookupError → 404
- [Source: backend/tests/operator/test_deletion.py] — паттерн ops unit tests
- [Source: backend/tests/api/routes/test_ops_routes.py:37] — ops token = "local-ops-auth-token"

## Dev Agent Record

### Agent Model Used

gemini-2.0-flash-exp

### Debug Log References

### Completion Notes List
- Реализована функция `execute_user_data_deletion` в `backend/app/ops/deletion.py`.
- Добавлен endpoint `POST /ops/deletion-requests/{request_id}/execute` в `backend/app/ops/api.py`.
- Добавлены unit тесты в `backend/tests/operator/test_deletion.py`.
- Добавлены API тесты в `backend/tests/api/routes/test_ops_routes.py`.
- Обновлен `backend/tests/conftest.py` для очистки таблицы `deletion_request`.
- Все тесты (24 в `test_ops_routes.py` и 8 в `test_deletion.py`) проходят успешно.

### File List
- `backend/app/ops/deletion.py`
- `backend/app/ops/api.py`
- `backend/tests/operator/test_deletion.py`
- `backend/tests/api/routes/test_ops_routes.py`
- `backend/tests/conftest.py`

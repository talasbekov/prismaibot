# Story 6.1: Запрос удаления пользовательских данных

Status: done

## Story

As a user,
I want запросить удаление моих сохраненных данных через Telegram-команду,
so that я сохраняю контроль над своей приватной информацией и могу прекратить хранение контекста в продукте.

## Acceptance Criteria

1. **Given** пользователь хочет удалить свои данные из продукта **When** он отправляет команду `/delete` в Telegram **Then** система принимает запрос и создаёт запись `DeletionRequest` в статусе `pending` **And** пользователь получает понятное текстовое подтверждение, что запрос зарегистрирован.

2. **Given** продукт хранит continuity artifacts и related user data **When** deletion request создаётся **Then** запись корректно привязывается к `telegram_user_id` пользователя **And** не требует от пользователя разбираться во внутренней структуре хранения.

3. **Given** deletion request поступает в систему **When** запись успешно создана **Then** статус запроса отображается как `pending` и доступен для отслеживания **And** продукт не теряет deletion intent silently.

4. **Given** пользователь уже имеет активный pending deletion request **When** он снова отправляет `/delete` **Then** новый дублирующий запрос НЕ создаётся **And** пользователь получает сообщение о статусе существующего запроса (не contradictory confirmations).

5. **Given** intake завершилась ошибкой или запись не может быть надёжно создана **When** система не может принять запрос корректно **Then** failure логируется и пользователь получает честное сообщение об ошибке **And** продукт не создаёт ложное ощущение, что deletion workflow запущен.

6. **Given** deletion request зарегистрирована **When** пользователь продолжает взаимодействие с продуктом **Then** обычные conversation flows продолжают работать (deletion не блокирует текущую сессию) **And** поведение продукта не противоречит принятому privacy request.

## Tasks / Subtasks

- [x] Добавить модель `DeletionRequest` в `backend/app/models.py` (AC: 1, 2, 3)
  - [x] Поля: `id` (UUID PK), `telegram_user_id` (BigInteger, index), `status` (str, max_length=32, default="pending"), `requested_at` (DateTime UTC), `completed_at` (DateTime | None), `audit_notes` (str | None, max_length=1000)
  - [x] Таблица: `__tablename__ = "deletion_request"` (singular, consistent with other models in project)
  - [x] Следовать паттерну из `models.py`: `sa_type=DateTime(timezone=True)`, `sa_type=BigInteger()`, `get_datetime_utc()`
  - [x] Добавить index на `telegram_user_id`; НЕ добавлять unique constraint — дедупликация через бизнес-логику

- [x] Создать Alembic migration для таблицы `deletion_request` (AC: 1, 3)
  - [x] Файл в `backend/app/alembic/versions/`
  - [x] Паттерн: смотри `backend/app/alembic/versions/a7f9c3d2b4e1_add_operator_alert_table.py`
  - [x] Таблица: `deletion_request`, columns: id, telegram_user_id, status, requested_at, completed_at, audit_notes
  - [x] Выполнить `alembic revision --autogenerate -m "add_deletion_request_table"` или написать вручную

- [x] Создать `backend/app/ops/deletion.py` с логикой регистрации deletion request (AC: 1, 2, 3, 4, 5)
  - [x] `request_user_data_deletion(session, *, telegram_user_id) -> DeletionRequest` — главная функция
  - [x] Перед созданием: проверить существующий pending запрос через `select(DeletionRequest).where(DeletionRequest.telegram_user_id == telegram_user_id, DeletionRequest.status == "pending")`
  - [x] Если pending существует: вернуть его (idempotent), не создавать новый
  - [x] Если не существует: создать новый с `status="pending"`, `requested_at=datetime.now(timezone.utc)`
  - [x] В случае DB failure: raise `DeletionRequestIntakeError` — не gloss over
  - [x] Импорт `DeletionRequest` из `app.models`

- [x] Добавить `/delete` command handler в `backend/app/conversation/session_bootstrap.py` (AC: 1, 4, 5, 6)
  - [x] По аналогии с `/start` handler: в `handle_session_entry()` добавить проверку `message.text.strip() == "/delete"`
  - [x] Вызвать `request_user_data_deletion(session, telegram_user_id=message.telegram_user_id)`
  - [x] Если запрос уже pending: вернуть `DELETE_ALREADY_PENDING_PROMPT`
  - [x] Если успешно создан: вернуть `DELETE_REQUEST_CONFIRMED_PROMPT`
  - [x] Если exception: логировать через `logger.exception(...)`, вернуть `DELETE_REQUEST_ERROR_PROMPT`
  - [x] НЕ изменять обычный conversation flow (добавить условие до основной логики, по аналогии с другими командами)
  - [x] Добавить константы в начало файла рядом с другими prompt-константами:
    - `DELETE_REQUEST_CONFIRMED_PROMPT` — подтверждение, тёплый тон, без технических деталей
    - `DELETE_ALREADY_PENDING_PROMPT` — статусное сообщение о существующем запросе
    - `DELETE_REQUEST_ERROR_PROMPT` — честное сообщение об ошибке без false confirmation

- [x] Добавить ops endpoint для просмотра pending deletion requests в `backend/app/ops/api.py` (AC: 3)
  - [x] `GET /ops/deletion-requests` — список pending deletion requests, auth-gated через `_verify_ops_token()`
  - [x] Сериализация: `id`, `telegram_user_id`, `status`, `requested_at`, `audit_notes`
  - [x] Response format: `{"data": [...], "error": None}` — как в остальных ops endpoints
  - [x] Добавить `list_pending_deletion_requests(session)` в `backend/app/ops/deletion.py`

- [x] Написать тесты (AC: все)
  - [x] `backend/tests/operator/test_deletion.py` — unit tests для `ops/deletion.py`:
    - [x] Test: новый запрос создаётся успешно → status="pending", telegram_user_id корректный
    - [x] Test: повторный вызов для того же user → возвращает существующий pending, новая запись НЕ создаётся
    - [x] Test: пользователь с выполненным (completed) запросом может создать новый pending
  - [x] `backend/tests/api/routes/test_ops_routes.py` (добавить к существующим) — test `/ops/deletion-requests` с auth token
  - [x] `backend/tests/conversation/test_delete_command.py` — integration tests через Telegram webhook:
    - [x] Test: `/delete` → response содержит `DELETE_REQUEST_CONFIRMED_PROMPT`, DeletionRequest создан в DB
    - [x] Test: повторный `/delete` → response содержит `DELETE_ALREADY_PENDING_PROMPT`, только 1 запись в DB
    - [x] Test: обычное сообщение после `/delete` → normal conversation flow продолжает работать
  - [x] Запустить: `uv run pytest tests/ -q`, `uv run ruff check --fix app tests`, `uv run mypy app tests` из `backend/`

## Dev Notes

### Фактическая структура проекта

**Важно:** Архитектура описывает `src/goals/operator/`, но реальная структура проекта:
```
backend/app/
├── ops/          ← operator module (НЕ "operator/")
│   ├── api.py
│   ├── alerts.py
│   ├── investigations.py
│   ├── signals.py
│   └── deletion.py  ← создать в этой истории
├── models.py         ← все core SQLModel models здесь (в одном файле)
├── bot/api.py        ← Telegram webhook ingress
├── conversation/session_bootstrap.py  ← главная точка обработки команд
├── billing/models.py ← billing models (в отдельном файле, в отличие от core)
└── alembic/versions/ ← миграции
```

**Паттерн для новых моделей:** Добавлять в `backend/app/models.py` (не отдельный файл), следовать существующему паттерну:
```python
class DeletionRequest(SQLModel, table=True):
    __tablename__ = "deletion_request"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    telegram_user_id: int = Field(index=True, sa_type=BigInteger())  # type: ignore[call-overload]
    status: str = Field(default="pending", max_length=32)
    requested_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    audit_notes: str | None = Field(default=None, max_length=1000)
```

### Паттерн команды в session_bootstrap.py

Команды проверяются в `handle_session_entry()` через `message.text.strip() == "/command"`. Пример `/start`:
```python
if message.text.strip() == "/start":
    return _build_opening_prompt(session=session, telegram_user_id=message.telegram_user_id)
```

**Паттерн для `/delete`** (добавить до существующих command checks):
```python
if message.text.strip() == "/delete":
    return _handle_delete_command(session, telegram_user_id=message.telegram_user_id)
```

Создать отдельную внутреннюю функцию `_handle_delete_command()` — по аналогии с `_build_opening_prompt()`.

### Тексты для пользователя

Tone должен соответствовать остальным prompt-константам в session_bootstrap.py (тёплый, поддерживающий, без технического жаргона):

```python
DELETE_REQUEST_CONFIRMED_PROMPT = (
    "Понял. Твой запрос на удаление данных принят.\n\n"
    "Сохранённые записи о наших разговорах будут удалены в ближайшее время. "
    "Если что-то пойдёт не так, мы тебя об этом не уведомим — "
    "но запрос не потеряется."
)
DELETE_ALREADY_PENDING_PROMPT = (
    "Ты уже отправил запрос на удаление данных. "
    "Он зарегистрирован и будет выполнен."
)
DELETE_REQUEST_ERROR_PROMPT = (
    "Что-то пошло не так при регистрации запроса на удаление. "
    "Попробуй написать /delete ещё раз."
)
```

### Идемпотентность и дедупликация

- Дедупликация через бизнес-логику: `select(DeletionRequest).where(status == "pending")` перед созданием
- НЕ добавлять `UniqueConstraint` на `telegram_user_id` — пользователь может иметь несколько исторических запросов (pending + completed)
- Пользователь с `completed` deletion request может создать новый `pending` (повторный запрос)

### Scope этой истории

**Входит:**
- Создание `DeletionRequest` модели и таблицы
- Telegram `/delete` command handler (intake only)
- Ops endpoint для просмотра pending requests
- Idempotent intake (дедупликация pending)

**НЕ входит (story 6.2):**
- Фактическое выполнение удаления (SessionSummary, ProfileFact, etc.)
- Оператор выполняет удаление вручную
- Каскадное удаление всех user-linked records

### Данные для удаления (контекст для story 6.2)

При выполнении (6.2) нужно будет удалять следующие данные пользователя:
- `SessionSummary` — где `deletion_eligible=True` и `telegram_user_id == user`
- `ProfileFact` — где `deletion_eligible=True` и `telegram_user_id == user`
- `PeriodicInsight` — по `telegram_user_id`
- `TelegramSession` — сессии пользователя (или их содержимое)

Поле `deletion_eligible: bool = True` уже есть в `SessionSummary` и `ProfileFact` — это было заложено заранее.

### Ops auth pattern

Все ops endpoints используют `X-Ops-Auth-Token` header:
```python
ops_auth_token: str | None = Header(default=None, alias="X-Ops-Auth-Token")
_verify_ops_token(ops_auth_token)
```

`settings.OPS_AUTH_TOKEN` — config value. Если не задан, ops auth пропускается (dev mode).

### Тестовый паттерн

Смотри `backend/tests/operator/test_alerts.py` и `backend/tests/operator/test_investigations.py` для паттернов ops unit tests.

Смотри `backend/tests/api/routes/test_telegram_session_entry.py` для интеграционных тестов через Telegram webhook.

Для создания DeletionRequest в тестах — создавать напрямую через DB (как SessionSummary в story 5.3):
```python
req = DeletionRequest(
    telegram_user_id=9001,
    status="pending",
    requested_at=datetime.now(timezone.utc),
)
db.add(req)
db.commit()
```

### Anti-patterns для этой истории

- ❌ Не создавать `UniqueConstraint` на `telegram_user_id` в модели — нарушит повторные запросы
- ❌ Не выполнять фактическое удаление данных — это story 6.2
- ❌ Не блокировать текущую сессию/разговор при наличии pending deletion
- ❌ Не логировать содержимое сообщений в связи с deletion — только IDs
- ❌ Не возвращать ложное подтверждение при ошибке intake

### Project Structure Notes

**Создаваемые/изменяемые файлы:**
- `backend/app/models.py` — добавить `DeletionRequest`
- `backend/app/alembic/versions/<hash>_add_deletion_request_table.py` — новая миграция
- `backend/app/ops/deletion.py` — новый файл с бизнес-логикой
- `backend/app/ops/api.py` — добавить endpoint `GET /ops/deletion-requests`
- `backend/app/conversation/session_bootstrap.py` — добавить `/delete` handler

**Новые тесты:**
- `backend/tests/operator/test_deletion.py`
- `backend/tests/conversation/test_delete_command.py`
- `backend/tests/api/routes/test_ops_routes.py` — расширить существующий файл

### References

- [Source: epics.md#Epic-6-Story-6.1] — полные acceptance criteria
- [Source: epics.md#FR32] — функциональное требование
- [Source: architecture.md#Database] — `deletion_requests` table naming, SQLAlchemy 2 + Alembic
- [Source: architecture.md#Operator] — `operator/deletion.py` паттерн (в проекте `ops/deletion.py`)
- [Source: architecture.md#Privacy] — audit traces for deletion, no routine transcript exposure
- [Source: backend/app/models.py] — паттерн SQLModel: `get_datetime_utc`, `DateTime(timezone=True)`, `BigInteger()`
- [Source: backend/app/ops/api.py] — `_verify_ops_token()`, response format `{"data": ..., "error": None}`
- [Source: backend/app/ops/investigations.py] — паттерн бизнес-логики в `ops/`
- [Source: backend/app/conversation/session_bootstrap.py] — команды `/start`, `/delete` pattern
- [Source: backend/tests/operator/test_investigations.py] — тестовый паттерн ops

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List

- `backend/app/models.py`
- `backend/app/alembic/versions/ebf7a6e55215_add_deletion_request_table.py`
- `backend/app/ops/deletion.py`
- `backend/app/ops/api.py`
- `backend/app/conversation/session_bootstrap.py`
- `backend/tests/operator/test_deletion.py`
- `backend/tests/conversation/test_delete_command.py`
- `backend/tests/api/routes/test_ops_routes.py`

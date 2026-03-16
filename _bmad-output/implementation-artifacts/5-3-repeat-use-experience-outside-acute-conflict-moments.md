# Story 5.3: Repeat-use experience вне acute conflict moments

Status: done

## Story

As a user who returns in calmer periods,
I want чтобы продукт оставался полезным не только в момент острого конфликта,
So that у меня появляется причина возвращаться к нему регулярно, а не только в peak pain moments.

## Acceptance Criteria

1. **Given** пользователь возвращается в продукт не из-за нового acute conflict, а в более спокойный период, **When** он начинает новую continuity-aware interaction, **Then** продукт может поддержать reflective use case outside acute distress, **And** новый flow не требует обязательного crisis-like trigger or peak-emotion context to feel relevant. [Source: epics.md#story-53-AC1]

2. **Given** у пользователя уже есть accumulated continuity from prior sessions, **When** продукт взаимодействует с ним в calmer-period usage, **Then** система использует prior context для более релевантного entry point, follow-up framing or insight continuity, **And** repeat-use experience feels like natural continuation rather than artificial feature forcing. [Source: epics.md#story-53-AC2]

3. **Given** пользователь приходит не с новым "событием", а с желанием проверить состояние, паттерн или повторяющуюся динамику, **When** reflective interaction развивается, **Then** продукт поддерживает этот lower-intensity use case in a valid way, **And** не заставляет пользователя искусственно формулировать crisis-level problem to proceed. [Source: epics.md#story-53-AC3]

4. **Given** retention layer не должна превращаться в generic wellness content loop, **When** продукт формирует calmer-period repeat-use experience, **Then** value остается anchored in the user's own continuity and patterns, **And** не уходит в broad self-help chatter unrelated to prior user context. [Source: epics.md#story-53-AC4]

5. **Given** returning use outside acute moments не всегда будет clearly meaningful, **When** система не видит достаточного continuity basis for a strong interaction (нет prior summaries), **Then** продукт остается conservative and low-pressure, **And** не симулирует глубину или personalization, которой на самом деле нет. [Source: epics.md#story-53-AC5]

6. **Given** пользователь после weekly insight или просто по собственной инициативе возвращается в продукт, **When** новая сессия стартует, **Then** repeat-use path остается coherent with earlier memory, status and reflective positioning, **And** ощущается как закономерное развитие продукта, а не как отдельный retention gimmick. [Source: epics.md#story-53-AC6]

## Tasks / Subtasks

- [x] Добавить `_has_prior_sessions(session, telegram_user_id)` в `backend/app/conversation/session_bootstrap.py` (AC: 2, 5)
  - [x] Lightweight DB check: `session.exec(select(SessionSummary).where(SessionSummary.telegram_user_id == telegram_user_id).limit(1)).first() is not None`
  - [x] Импортировать `SessionSummary` из `app.models` (уже используется в файле через `app.memory`)
  - [x] НЕ вызывать `get_session_recall_context()` — слишком тяжелый вызов для opening, полный recall уже происходит на first turn

- [x] Добавить `RETURNING_USER_OPENING_PROMPT` в `backend/app/conversation/session_bootstrap.py` (AC: 1, 3, 6)
  - [x] Текст должен быть теплым, low-pressure, НЕ содержать "что случилось" или другой crisis-trigger формулировки
  - [x] Пример: `"Рад, что снова написал. Можешь рассказать, что сейчас — продолжаем или что-то новое?"`
  - [x] Ориентир по тону: **Continuity Premium** стиль из UX-спецификации (второй session entry, мягкий re-entry)

- [x] Изменить `_build_opening_prompt()` → `_build_opening_prompt(session, telegram_user_id)` в `backend/app/conversation/session_bootstrap.py` (AC: 1, 2, 5)
  - [x] Добавить параметры `session: Session` и `telegram_user_id: int`
  - [x] Внутри: вызвать `_safe_check_has_prior_sessions(session, telegram_user_id)` — обернуть в try/except с fallback на `False`
  - [x] Если returning user (`has_prior=True`): вернуть `RETURNING_USER_OPENING_PROMPT` + **те же mode buttons** (`Коротко` / `Глубже`)
  - [x] Если new user (`has_prior=False`): вернуть существующий `OPENING_PROMPT` + те же buttons
  - [x] Action остается `"opening_prompt"` в обоих случаях (не менять)

- [x] Обновить вызов `/start` handler в `handle_session_entry()` (AC: 1)
  - [x] Строка `if message.text.strip() == "/start":` сейчас вызывает `_build_opening_prompt()`
  - [x] Изменить на `_build_opening_prompt(session=session, telegram_user_id=message.telegram_user_id)`
  - [x] `session` и `message` уже доступны в этом scope (локальные переменные)

- [x] Создать тесты в `backend/tests/conversation/test_repeat_use_entry.py` (AC: 1, 2, 3, 5)
  - [x] **Test: новый пользователь получает generic opening** — /start без SessionSummary → `OPENING_PROMPT` в messages[0].text
  - [x] **Test: returning user получает continuity-aware opening** — создать `SessionSummary` для user_id, затем /start → `RETURNING_USER_OPENING_PROMPT` в messages[0].text
  - [x] **Test: ошибка при проверке prior sessions → safe fallback** — мокать `_has_prior_sessions` с raise Exception → должен вернуть generic opening (не падать)
  - [x] **Test: оба варианта возвращают mode selection buttons** — inline_keyboard содержит `[{"text": "Коротко", ...}, {"text": "Глубже", ...}]`
  - [x] **Test: returning user затем пишет первое сообщение → first_trust_response with memory** — проверить что memory context уже подхватывается (интеграционный тест через /start + message)

- [x] Запустить проверки (AC: все)
  - [x] `uv run pytest tests/ -q` из `backend/`
  - [x] `uv run ruff check --fix app tests` из `backend/`
  - [x] `uv run mypy app tests`

## Dev Notes

### Почему story 5.3 = изменение `/start` opening prompt

**Анализ текущего состояния:**
- `/start` → `_build_opening_prompt()` → `OPENING_PROMPT = "Можешь просто написать, что случилось, и начнем разбираться вместе."`
- "Что случилось" — явный crisis/event trigger. Для returning user в calmer moment это либо создает ненужный pressure, либо ощущается странно когда "ничего не случилось"
- First turn уже memory-aware через `compose_first_trust_response_with_memory()` (story 2.3) — этот механизм не трогаем

**Что НЕ нужно менять в этой истории:**
- ❌ `compose_first_trust_response_with_memory()` — уже работает корректно для returning users
- ❌ `clarification.py` — mid-session continuity уже работает
- ❌ Модели/БД — никаких новых таблиц или полей не нужно
- ❌ Scheduler/jobs — retention delivery уже в story 5.1/5.2

### Точное место изменения в session_bootstrap.py

```python
# ТЕКУЩИЙ КОД (строка ~169):
if message.text.strip() == "/start":
    return _build_opening_prompt()

# НОВЫЙ КОД:
if message.text.strip() == "/start":
    return _build_opening_prompt(session=session, telegram_user_id=message.telegram_user_id)
```

Переменные `session: Session` и `message: IncomingMessage` доступны в `handle_session_entry()` к этому моменту (см. строку 161 парсинга message).

### Реализация `_has_prior_sessions()` и safe wrapper

```python
from app.models import SessionSummary  # уже импортируется через app.memory

def _has_prior_sessions(session: Session, telegram_user_id: int) -> bool:
    return (
        session.exec(
            select(SessionSummary)
            .where(SessionSummary.telegram_user_id == telegram_user_id)
            .limit(1)
        ).first() is not None
    )

def _safe_check_has_prior_sessions(session: Session, telegram_user_id: int) -> bool:
    try:
        return _has_prior_sessions(session, telegram_user_id)
    except Exception:
        logger.exception(
            "Failed to check prior sessions for telegram_user_id=%s; defaulting to new user opening",
            telegram_user_id,
        )
        return False
```

**НЕ использовать** `get_session_recall_context()` для проверки — он загружает и собирает полный recall payload (summaries + profile facts + continuity string). Нам нужен только boolean "есть ли хоть одна запись".

### Тон returning user opening prompt

По UX-спецификации, для second-session entry использовать **Continuity Premium** стиль:
- warm, acknowledges they're back
- low-pressure (не "что случилось", не "расскажи о проблеме")
- приглашает, а не требует
- "Continuity Premium" особенно для reduce emotional setup cost

**Требования к тексту (AC3):**
- ❌ НЕ: "что случилось", "расскажи о проблеме", "что тебя беспокоит"
- ✅ ДА: мягкое признание что они вернулись, приглашение рассказать на своих условиях
- Не должен ссылаться на конкретный prior контент (это делает first_response, не opening)

**Вариант (скорректировать под голос продукта):**
```python
RETURNING_USER_OPENING_PROMPT = (
    "Рад, что снова написал. Расскажи, что сейчас — "
    "продолжаем что-то незавершённое или что-то новое?"
)
```

AC5 обрабатывается автоматически: если нет SessionSummary → `_has_prior_sessions()` = False → показывается generic `OPENING_PROMPT`. Не нужна отдельная "conservative mode" логика.

### Что происходит после opening prompt

1. Пользователь нажимает mode button (`Коротко`/`Глубже`) → `_handle_mode_selection_callback()` устанавливает `reflective_mode`
2. Пользователь пишет первое сообщение → `is_first_turn=True` → `_safe_load_prior_memory_context()` → загружает recall
3. `compose_first_trust_response_with_memory()` уже обрабатывает:
   - Low-confidence input (короткие/расплывчатые сообщения) → мягкий probe вместо crisis framing
   - `recall_mode == "explicit"` → добавляет continuity hint

**Критично:** Пользователь в calmer period может написать что-то короткое типа "просто хотел поговорить" (4 слова). `_is_low_confidence()` в `first_response.py` обработает это правильно — вернет проbing question без crisis assumption. Это уже работает.

### Anti-patterns для этой истории

- ❌ Не создавать новые callback types (типа `reentry:continue` или `reentry:new`) — усложняет без нужды
- ❌ Не загружать continuity context в opening prompt (только в first_response)
- ❌ Не добавлять "/return" или другие новые команды
- ❌ Не изменять `action = "opening_prompt"` в TelegramWebhookResponse — клиент не должен видеть разницу по типу ответа
- ❌ Не логировать `telegram_user_id` в контексте content пользователя в opening

### Связь с предыдущими историями

- **Story 2.3** (using prior memory at session start) — уже реализована. Memory recall на first turn работает. Story 5.3 только улучшает **opening prompt**, не механизм recall.
- **Story 2.4** (tentative memory recall / correction) — уже работает. Если returning user корректирует память, это обрабатывается в clarification.py.
- **Story 5.1/5.2** (periodic insight generation/delivery) — delivery message служит точкой входа в повторное использование. Пользователь после получения insight может открыть бот и написать `/start` — именно этот flow story 5.3 улучшает.

### Тестовый паттерн для returning user

Смотри `tests/api/routes/test_telegram_session_entry.py` — паттерн для БД fixtures.

```python
# В тесте: создать SessionSummary напрямую через DB перед /start вызовом
def test_returning_user_gets_continuity_aware_opening(client, db):
    # Arrange: create a session summary to simulate returning user
    import uuid
    from app.models import SessionSummary
    from datetime import datetime, timezone

    summary = SessionSummary(
        session_id=uuid.uuid4(),
        telegram_user_id=9001,
        reflective_mode="fast",
        source_turn_count=5,
        takeaway="Пользователь разобрался с ситуацией.",
        key_facts=["Повторяющийся паттерн напряжения."],
        emotional_tensions=[],
        uncertainty_notes=[],
        next_step_context=[],
        retention_scope="durable_summary",
        deletion_eligible=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(summary)
    db.commit()

    # Act: /start
    response = client.post("/api/v1/telegram/webhook", json={...user_id: 9001...})

    # Assert: returning user opening (not generic OPENING_PROMPT)
    assert RETURNING_USER_OPENING_PROMPT in payload["messages"][0]["text"]
```

### Project Structure Notes

- Изменяемые файлы: `backend/app/conversation/session_bootstrap.py` (основная логика)
- Новые тесты: `backend/tests/conversation/test_repeat_use_entry.py`
- Импорт `SessionSummary` в session_bootstrap.py нужно добавить если не импортируется напрямую (проверить — сейчас models используется через `app.models`)

### References

- [Source: epics.md#Epic-5-Story-5.3] — полные acceptance criteria
- [Source: ux-design-specification.md#Лена-Continuity-Return-Flow] — returning user UX flow
- [Source: ux-design-specification.md#Re-entry-Pattern] — re-entry design rules
- [Source: ux-design-specification.md#Silence-Re-entry-Pattern] — silence/re-entry pattern
- [Source: ux-design-specification.md#Design-Directions] — Continuity Premium для second-session entry
- [Source: backend/app/conversation/session_bootstrap.py] — OPENING_PROMPT, _build_opening_prompt(), handle_session_entry()
- [Source: backend/app/conversation/first_response.py] — compose_first_trust_response_with_memory(), _is_low_confidence()
- [Source: backend/app/memory/service.py] — get_session_recall_context(), SessionSummary structure
- [Source: backend/tests/api/routes/test_telegram_session_entry.py] — тестовый паттерн и fixtures

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Реализована проверка наличия предыдущих сессий пользователя через `SessionSummary` (легковесный запрос).
- Добавлен `RETURNING_USER_OPENING_PROMPT` с теплым, low-pressure тоном в стиле Continuity Premium.
- Обновлена функция `_build_opening_prompt`, теперь она принимает `session` и `telegram_user_id` и выбирает промпт на основе истории пользователя.
- Обновлен вызов `/start` в `handle_session_entry` для передачи необходимых данных.
- Создан набор тестов `backend/tests/conversation/test_repeat_use_entry.py`, покрывающий:
    - Новый пользователь получает стандартное приветствие.
    - Возвращающийся пользователь получает приветствие с учетом непрерывности.
    - Безопасный откат к стандартному приветствию при ошибках БД.
    - Интеграционный тест: подхват контекста памяти при первом сообщении после ре-ентри.
- Все тесты (включая регрессионные) проходят успешно.

### File List

- backend/app/conversation/session_bootstrap.py
- backend/tests/conversation/test_repeat_use_entry.py

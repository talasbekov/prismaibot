---
title: 'BMAD Brainstorming State Machine для Telegram-бота'
slug: 'bmad-brainstorming-telegram'
created: '2026-03-15'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Python 3.12', 'FastAPI', 'PostgreSQL', 'SQLModel 0.0.21', 'SQLAlchemy', 'Alembic', 'OpenAI GPT-4o-mini', 'httpx', 'pytest', 'pydantic-v2']
files_to_modify:
  - 'backend/app/models.py'
  - 'backend/app/conversation/session_bootstrap.py'
  - 'backend/app/alembic/versions/<new>.py'
  - '.env.example'
files_to_create:
  - 'scripts/register_webhook.py'
  - 'backend/app/conversation/brainstorming/__init__.py'
  - 'backend/app/conversation/brainstorming/orchestrator.py'
  - 'backend/app/conversation/brainstorming/prompts.py'
  - 'backend/tests/api/routes/test_brainstorming.py'
code_patterns:
  - 'SQLModel Field() for simple types; Field(sa_column=Column(JSON)) for collections'
  - 'TelegramWebhookResponse with messages: list[TelegramMessageOut] and signals: list[str]'
  - 'OpenAI call_chat() → None on error → fallback string'
  - 'Background tasks via FastAPI BackgroundTasks for async work'
test_patterns:
  - 'POST /api/v1/telegram/webhook with JSON update dict'
  - 'client: TestClient + db: Session fixtures'
  - 'patch() mocks at module level for OpenAI calls'
  - 'autouse fixture clears all tables before each test'
  - 'JSON field works with SQLite in tests — no PostgreSQL container needed'
---

# Tech-Spec: BMAD Brainstorming State Machine для Telegram-бота

**Created:** 2026-03-15

## Overview

### Problem Statement

Бот не отвечает пользователям, потому что Telegram webhook не зарегистрирован — нет скрипта для вызова `setWebhook`. Помимо этого, вся диалоговая логика реализована как примитивный "эмпатичный отражатель": один generic OpenAI промпт для всего разговора, keyword-matching как fallback, нет фаз, нет оркестратора, нет структурированного итогового документа. BMAD brainstorming методология не реализована.

### Solution

1. Добавить скрипт регистрации Telegram webhook (`scripts/register_webhook.py`)
2. Добавить в `TelegramSession`: поля `brainstorm_phase VARCHAR(32)` и `brainstorm_data JSON` (Alembic миграция)
3. Создать модуль `backend/app/conversation/brainstorming/` — state machine с 9 фазами и фазо-специфичными OpenAI промптами
4. Заменить кнопки в `/start` на выбор режима: "Разобраться в ситуации" (→ старый эмпатичный flow) / "Придумать решение" (→ brainstorming)
5. Итог сессии (`finish`) → 3 структурированных сообщения + `SessionSummary` через существующий `schedule_session_summary_generation`

### Scope

**In Scope:**
- Скрипт регистрации Telegram webhook (`scripts/register_webhook.py`) + `WEBHOOK_URL` в `.env.example`
- Alembic миграция: `brainstorm_phase VARCHAR(32) DEFAULT NULL` + `brainstorm_data JSON DEFAULT NULL` в таблице `telegramsession`
- Замена кнопок в `_build_opening_prompt`: "Коротко"/"Глубже" → "Разобраться в ситуации"/"Придумать решение" + текст-подсказка про кризис
- Новые callback handlers для `brainstorm:mode:*` и `brainstorm:approach:*` в `handle_session_entry`
- Backward compatibility: существующие `mode:fast` / `mode:deep` callback handlers — не трогать
- State machine с 9 фазами: `collect_topic → collect_goal → collect_constraints → choose_approach → facilitation_loop → cluster_ideas → prioritize → generate_action_plan → finish`
- Отдельный OpenAI system prompt + fallback-вопрос для каждой из 9 фаз; 4 варианта промпта для `facilitation_loop` по типу подхода
- `facilitation_loop`: любой ответ → идея в `ideas[]` без валидации длины; при `facilitation_turns >= 3` → кнопка "Перейти к группировке идей"
- Итог: 3 сообщения (идеи / топ-3 / план 7 дней) + `SessionSummary` + `ProfileFact` через существующий memory pipeline
- Crisis сброс: при `crisis_active` → `brainstorm_phase = None`, `brainstorm_data = None`

**Out of Scope:**
- Веб-панель, PDF/Notion экспорт
- Несколько методологий (только brainstorming)
- Автоматический ML-роутинг типа запроса
- Аналитика и дашборды

---

## Context for Development

### Codebase Patterns

**Существующие системы — НЕ трогать, brainstorming работает ПОВЕРХ них:**
- **Deduplication guard** (`handle_session_entry` ~line 162) — срабатывает до любого routing, brainstorming унаследует автоматически
- **Safety routing** (`evaluate_incoming_message_safety` ~line 674) — запускается на каждое сообщение включая brainstorming; если `blocks_normal_flow=True` → `crisis_active`, brainstorming прерывается
- **Billing gate** (~line 636) — `get_user_access_state()` + `is_free_eligible()` вызывается до brainstorming routing; paywall показывается так же как сейчас. Brainstorming сессия = 1 free session
- **Memory pipeline** — `schedule_session_summary_generation(background_tasks, payload)` + `SessionSummaryPayload` из `app.memory`; brainstorming заполняет payload в фазе `finish`

**OpenAI клиент:**
- `backend/app/conversation/_openai.py` — `call_chat(messages: list[dict], *, max_tokens=400, temperature=0.7) -> str | None`
- Возвращает `None` при ошибке — оркестратор использует fallback строку для каждой фазы

**TelegramSession (`backend/app/models.py`) — новые поля:**
```python
from sqlalchemy import JSON

# добавить в конец класса TelegramSession:
brainstorm_phase: str | None = Field(default=None, max_length=32)
brainstorm_data: dict | None = Field(
    default=None,
    sa_column=Column(JSON, nullable=True),
)
```
`brainstorm_data` schema: `{"topic": str, "goal": str, "constraints": str, "approach": str, "ideas": list[str], "facilitation_turns": int}`

**Routing в `_handle_message` (~line 864) — изменить порядок веток:**
```python
# НОВОЕ: добавить ДО существующих веток
if active_session.brainstorm_phase == 'reflect':
    pass  # продолжить в существующий is_first_turn / closure / clarification flow
elif active_session.brainstorm_phase is not None:
    result = brainstorming_orchestrator.route(active_session, stripped_text)
    response_messages = result.messages
    action = result.action
    active_session.brainstorm_phase = result.next_phase
    active_session.brainstorm_data = result.updated_data
    # если finish → summary_payload заполнить из result
elif is_first_turn:
    # показать detect_mode — уже сделано в _build_opening_prompt через /start
    # если пользователь написал текст без /start → также показать detect_mode
    return _build_detect_mode_prompt(active_session)
```

**Новые callback handlers в `handle_session_entry`** (~line 200, ДО `return ignored`):
```python
if callback_data.startswith("brainstorm:mode:"):
    return _handle_brainstorm_mode_callback(session, cbq)
if callback_data.startswith("brainstorm:approach:"):
    return _handle_brainstorm_approach_callback(session, cbq)
# существующие mode:fast / mode:deep — НЕ трогать
```

**Crisis сброс** — добавить в каждую ветку перехода в `crisis_active`:
```python
active_session.brainstorm_phase = None
active_session.brainstorm_data = None
```

### Структура модуля `backend/app/conversation/brainstorming/`

```
backend/app/conversation/brainstorming/
├── __init__.py       # from .orchestrator import route, start_detect_mode
├── orchestrator.py   # route(session, text) → BrainstormResult; start_detect_mode() → messages
└── prompts.py        # SYSTEM_PROMPTS, FALLBACKS, APPROACH_PROMPTS константы
```

**`BrainstormResult` dataclass** (в `orchestrator.py`):
```python
@dataclass(frozen=True)
class BrainstormResult:
    messages: tuple[str, ...]
    action: str
    next_phase: str
    updated_data: dict
    summary_payload: SessionSummaryPayload | None = None  # только в finish
```

**Opening message** (заменяет `OPENING_PROMPT` и кнопки в `_build_opening_prompt`):
```
"Привет! Чем могу помочь?

Если тебе сейчас очень плохо — просто напиши об этом, я не начну с вопросов."
```
Кнопки: `[Разобраться в ситуации]` (`brainstorm:mode:reflect`) | `[Придумать решение]` (`brainstorm:mode:brainstorm`)

**Alembic миграция** (`down_revision = "f4a6b7c8d9e0"`):
```python
import sqlalchemy as sa

def upgrade() -> None:
    op.add_column("telegram_session", sa.Column("brainstorm_phase", sa.String(length=32), nullable=True))
    op.add_column("telegram_session", sa.Column("brainstorm_data", sa.JSON(), nullable=True))

def downgrade() -> None:
    op.drop_column("telegram_session", "brainstorm_data")
    op.drop_column("telegram_session", "brainstorm_phase")
```

### Files to Reference

| Файл | Назначение |
| ---- | ---------- |
| `backend/app/models.py` | `TelegramSession` — добавить `brainstorm_phase`, `brainstorm_data` |
| `backend/app/conversation/session_bootstrap.py` | `_handle_message` ~864, `handle_session_entry` ~200, `_build_opening_prompt` ~1160 |
| `backend/app/conversation/_openai.py` | `call_chat()` — использовать в оркестраторе |
| `backend/app/conversation/first_response.py` | НЕ удалять; паттерн OpenAI → fallback |
| `backend/app/conversation/closure.py` | НЕ удалять; паттерн `SessionSummaryPayload` — повторить в `finish` |
| `backend/app/memory/__init__.py` | `schedule_session_summary_generation`, `SessionSummaryPayload` |
| `backend/app/core/config.py` | `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN` |
| `backend/app/alembic/versions/f4a6b7c8d9e0_*.py` | Образец синтаксиса миграции |
| `backend/tests/api/routes/test_telegram_session_entry.py` | Образец тестового паттерна |
| `.env.example` | Добавить `WEBHOOK_URL` |

### Technical Decisions

- **`Column(JSON)` вместо JSONB**: совместим с SQLite в тестах и PostgreSQL в prod; для наших нужд (нет JSON path queries) функционально идентичен
- **Backward compatibility для mode:fast/deep**: старые callback handlers не удаляются — пользователи со старыми кнопками не сломаются
- **`facilitation_loop` принимает любую длину**: в Telegram пишут обрывками; валидация только в `collect_*` фазах
- **Billing не меняется**: brainstorming = 1 free session, `record_eligible_session_completion` вызывается в `finish`
- **`working_context` обновляется текстово**: после каждой фазы оркестратор дописывает резюме для memory generation

### Fallback-вопросы (если OpenAI недоступен)

| Фаза | Fallback |
|------|---------|
| `collect_topic` | "Опиши проблему одной фразой — что именно хочешь решить или придумать?" |
| `collect_goal` | "Какой результат ты хочешь получить в итоге?" |
| `collect_constraints` | "Какие есть ограничения — время, ресурсы, что уже пробовал?" |
| `choose_approach` | _(кнопки, текст не нужен)_ |
| `facilitation_loop` | "Что ещё приходит в голову? Какие варианты видишь?" |
| `cluster_ideas` | "Какие из идей кажутся похожими? Попробуй сгруппировать." |
| `prioritize` | "Какие 3 идеи кажутся самыми реалистичными и ценными?" |
| `generate_action_plan` | "Что конкретно сделаешь на этой неделе, чтобы продвинуться?" |
| `finish` | "Отличная сессия! Вот что мы разобрали вместе:" + форматированный итог |

---

## Implementation Plan

### Tasks

#### Story A — Webhook Registration (нет зависимостей)

- [x] **Task A1: Создать `scripts/register_webhook.py`**
  - File: `scripts/register_webhook.py`
  - Action: Скрипт читает `TELEGRAM_BOT_TOKEN` и `WEBHOOK_URL` из `os.environ`, делает `POST https://api.telegram.org/bot{TOKEN}/setWebhook` с `{"url": WEBHOOK_URL}` через `httpx`, выводит JSON ответа в stdout. Завершается с exit code 1 если переменные не заданы или запрос вернул `ok: false`.
  - Notes: Запуск: `uv run scripts/register_webhook.py`

- [x] **Task A2: Добавить `WEBHOOK_URL` в `.env.example`**
  - File: `.env.example`
  - Action: Добавить строку `WEBHOOK_URL=https://your-domain.com/api/v1/telegram/webhook`

---

#### Story B — DB Migration + Model Fields (нет зависимостей)

- [x] **Task B1: Добавить поля в `TelegramSession`**
  - File: `backend/app/models.py`
  - Action: В конец класса `TelegramSession` добавить два поля (после `crisis_step_down_at`):
    ```python
    brainstorm_phase: str | None = Field(default=None, max_length=32)
    brainstorm_data: dict | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    ```
    Добавить импорт `from sqlalchemy import JSON` (если не импортирован).

- [x] **Task B2: Создать Alembic миграцию**
  - File: `backend/app/alembic/versions/b3c4d5e6f7a8_add_brainstorm_fields_to_telegram_session.py`
  - Action: Создать файл с `down_revision = "22a9a888f304"`. `upgrade()` добавляет `brainstorm_phase VARCHAR(32) NULL` и `brainstorm_data JSON NULL`. `downgrade()` удаляет оба.

---

#### Story C — detect_mode + Routing + Callbacks (зависит от B)

- [x] **Task C1: Обновить `_build_opening_prompt`**
  - File: `backend/app/conversation/session_bootstrap.py`
  - Action: Заменить текст и кнопки в `_build_opening_prompt` (~line 1160):
    - Новый текст: `"Привет! Чем могу помочь?\n\nЕсли тебе сейчас очень плохо — просто напиши об этом, я не начну с вопросов."`
    - Новые кнопки: `InlineButton(text="Разобраться в ситуации", callback_data="brainstorm:mode:reflect")` и `InlineButton(text="Придумать решение", callback_data="brainstorm:mode:brainstorm")`
    - Убрать старые кнопки "Коротко"/"Глубже" из этого места (но НЕ удалять `_handle_mode_selection_callback`)

- [x] **Task C2: Добавить callback handlers для brainstorm:mode:* и brainstorm:approach:***
  - File: `backend/app/conversation/session_bootstrap.py`
  - Action: В блоке `if "callback_query" in update` (~line 200), ДО строки `return TelegramWebhookResponse(status="ignored"...)`, добавить:
    ```python
    if callback_data.startswith("brainstorm:mode:"):
        return _handle_brainstorm_mode_callback(session, cbq)
    if callback_data.startswith("brainstorm:approach:"):
        return _handle_brainstorm_approach_callback(session, cbq)
    ```
    Реализовать функции по паттерну `_handle_payment_initiation` (~line 255) — получать `telegram_user_id` и `chat_id` из `cbq.get("from")` и `cbq.get("message", {}).get("chat")`, затем `_get_or_create_active_session`. После изменения фазы вызывать `_save_session(session, active_session)` и возвращать `_build_response(action=..., session_record=active_session, message_texts=[...], extra_signals=("typing",))`.
    - `_handle_brainstorm_mode_callback`: `mode = cbq["data"].split(":")[-1]`; если `"reflect"` → `brainstorm_phase = "reflect"`, `message_texts=[OPENING_PROMPT]`; если `"brainstorm"` → `brainstorm_phase = "collect_topic"`, `brainstorm_data = {"topic":"","goal":"","constraints":"","approach":"","ideas":[],"facilitation_turns":0}`, `message_texts=[FALLBACKS["collect_topic"]]`
    - `_handle_brainstorm_approach_callback`: `approach = cbq["data"].split(":")[-1]`; `brainstorm_data["approach"] = approach`; `brainstorm_phase = "facilitation_loop"`; `message_texts=[APPROACH_PROMPTS[approach + "_fallback"]]`

- [x] **Task C3: Добавить ветку brainstorming в `_handle_message`**
  - File: `backend/app/conversation/session_bootstrap.py`
  - Action: В `_handle_message` (~line 864), ДО блока `if len(stripped_text) < settings.CONVERSATION_MIN_CLEAR_MESSAGE_LENGTH`, добавить:
    ```python
    # Brainstorming routing
    if active_session.brainstorm_phase not in (None, 'reflect', 'detect_mode'):
        from app.conversation.brainstorming import route as brainstorm_route
        result = brainstorm_route(active_session, stripped_text)
        response_messages = result.messages
        action = result.action
        active_session.brainstorm_phase = result.next_phase
        active_session.brainstorm_data = result.updated_data
        active_session.working_context = _update_brainstorm_context(
            active_session.working_context, result.updated_data
        )
        if result.summary_payload is not None:
            summary_payload = result.summary_payload
            active_session.status = "completed"
            record_eligible_session_completion(session, ...)
        active_session.last_bot_prompt = "\n\n".join(response_messages)
        active_session.turn_count += 1
        _save_session(session, active_session)
        return _build_response(
            action=action,
            session_record=active_session,
            message_texts=list(response_messages),
            extra_signals=("typing",),
        )
    elif is_first_turn and active_session.brainstorm_phase is None:
        # первый текст без /start → показать detect_mode
        active_session.brainstorm_phase = 'detect_mode'
        return _build_detect_mode_response(active_session)
    ```
    Добавить вспомогательную функцию `_build_detect_mode_response` (аналогично `_build_opening_prompt` но для text-triggered случая).
    Добавить `_update_brainstorm_context(working_context: str | None, data: dict | None) -> str`:
    ```python
    def _update_brainstorm_context(working_context: str | None, data: dict | None) -> str:
        if not data:
            return working_context or ""
        parts = []
        if data.get("topic"):
            parts.append(f"Тема: {data['topic']}")
        if data.get("goal"):
            parts.append(f"Цель: {data['goal']}")
        if data.get("approach"):
            parts.append(f"Подход: {data['approach']}")
        if data.get("ideas"):
            parts.append(f"Идей собрано: {len(data['ideas'])}")
        brainstorm_summary = "; ".join(parts)
        base = working_context or ""
        return f"{base}\n[Brainstorm: {brainstorm_summary}]".strip() if parts else base
    ```

- [x] **Task C4: Добавить crisis сброс brainstorm состояния**
  - File: `backend/app/conversation/session_bootstrap.py`
  - Action: В каждом месте где устанавливается `active_session.crisis_state = "crisis_active"` (их 2: ~line 788 и ~line 813) добавить:
    ```python
    active_session.brainstorm_phase = None
    active_session.brainstorm_data = None
    ```

---

#### Story D — Brainstorming Orchestrator + 9 Phases (зависит от C)

- [x] **Task D1: Создать `prompts.py`**
  - File: `backend/app/conversation/brainstorming/prompts.py`
  - Action: Определить три словаря:
    - `SYSTEM_PROMPTS: dict[str, str]` — system prompt для каждой из 9 фаз
    - `FALLBACKS: dict[str, str]` — fallback вопрос для каждой фазы (таблица из спека)
    - `APPROACH_PROMPTS: dict[str, str]` — system prompt для `facilitation_loop` по каждому из 4 подходов: `ideas`, `structure`, `unconventional`, `plan`
  - Notes: Промпты на русском, стиль — фасилитатор (не советник), один вопрос за раз. Написать все 9 system prompts по образцу двух примеров из раздела **Context for Development → OpenAI клиент** — каждый промпт задаёт роль фасилитатора, описывает текущую фазу, запрещает советовать и заканчивает ровно одним открытым вопросом.

- [x] **Task D2: Создать `orchestrator.py`**
  - File: `backend/app/conversation/brainstorming/orchestrator.py`
  - Action: Реализовать:
    - `route(session: TelegramSession, user_text: str) -> BrainstormResult` — читает `session.brainstorm_phase`, вызывает соответствующий handler фазы
    - Handlers для каждой фазы: `_handle_collect_topic`, `_handle_collect_goal`, `_handle_collect_constraints`, `_handle_choose_approach`, `_handle_facilitation_loop`, `_handle_cluster_ideas`, `_handle_prioritize`, `_handle_generate_action_plan`, `_handle_finish`
    - Каждый handler: вызывает `call_chat(...)` → при `None` использует fallback → возвращает `BrainstormResult` с `next_phase` и обновлённым `brainstorm_data`
    - Логика переходов:
      - `collect_topic` → сохранить ответ в `data["topic"]` → `next_phase = 'collect_goal'`
      - `collect_goal` → `data["goal"]` → `next_phase = 'collect_constraints'`
      - `collect_constraints` → `data["constraints"]` → `next_phase = 'choose_approach'`; вернуть 4 inline-кнопки подхода
      - `choose_approach` → ждёт callback (не text); если text — повторить кнопки, `next_phase` не меняется
      - `facilitation_loop` → append `user_text` в `data["ideas"]` (max 50); `data["facilitation_turns"] += 1`; при `>= 3` добавить кнопку "Перейти к группировке"; `next_phase` остаётся `facilitation_loop` до нажатия кнопки
      - `cluster_ideas` → `next_phase = 'prioritize'`
      - `prioritize` → сохранить raw текст ответа OpenAI в `data["top3_text"]` (не парсить) → `next_phase = 'generate_action_plan'`
      - `generate_action_plan` → `data["action_plan"]` → `next_phase = 'finish'`
      - `finish` → сформировать 3 сообщения + `SessionSummaryPayload`; `next_phase = 'done'`
    - Валидация длины в `collect_*` фазах: `len(user_text.split()) < 5` → повторить вопрос, не менять фазу
    - Phase persistence сообщение: если `data["topic"]` уже заполнен и `data["facilitation_turns"] > 0` → в начало ответа добавить "Продолжаем: тема — {topic}"

- [x] **Task D3: Создать `__init__.py`**
  - File: `backend/app/conversation/brainstorming/__init__.py`
  - Action:
    ```python
    from .orchestrator import BrainstormResult, route
    __all__ = ["BrainstormResult", "route"]
    ```

- [x] **Task D4: Написать тесты**
  - File: `backend/tests/api/routes/test_brainstorming.py`
  - Action: Написать тесты (с `autouse` фикстурой очистки таблиц):
    1. `/start` → кнопки "Разобраться в ситуации" и "Придумать решение" (не "Коротко"/"Глубже")
    2. callback `brainstorm:mode:brainstorm` → `brainstorm_phase = 'collect_topic'`, возвращает вопрос
    3. callback `brainstorm:mode:reflect` → `brainstorm_phase = 'reflect'`, возвращает старый opening prompt
    4. Фазовый переход: `collect_topic` → `collect_goal` → `collect_constraints`; проверить `brainstorm_data`
    5. `facilitation_loop`: 2 сообщения → нет кнопки; 3 сообщения → есть кнопка "Перейти к группировке"
    6. `facilitation_loop`: накопление идей в правильном порядке
    7. OpenAI fallback: `patch("app.conversation.brainstorming.orchestrator.call_chat", return_value=None)` → fallback текст возвращается
    8. Crisis сброс: установить `brainstorm_phase = 'facilitation_loop'`; отправить кризисное сообщение → `brainstorm_phase = None`
    9. Phase persistence: установить сессию с `brainstorm_phase = 'cluster_ideas'` и заполненным `brainstorm_data`; отправить сообщение → бот продолжает с `cluster_ideas`
    10. `collect_topic` с коротким ответом (3 слова) → та же фаза, вопрос повторяется

---

### Acceptance Criteria

- [ ] **AC1:** Given бот запущен и webhook не зарегистрирован, when запускается `uv run scripts/register_webhook.py` с заданными `TELEGRAM_BOT_TOKEN` и `WEBHOOK_URL`, then скрипт выводит `{"ok": true, ...}` и завершается с exit code 0

- [ ] **AC2:** Given пользователь пишет `/start`, when бот отвечает, then сообщение содержит текст про кризисную подсказку и ровно 2 inline-кнопки: "Разобраться в ситуации" и "Придумать решение"

- [ ] **AC3:** Given пользователь нажал "Разобраться в ситуации", when обрабатывается callback `brainstorm:mode:reflect`, then `brainstorm_phase = 'reflect'` в БД и бот отвечает стандартным opening prompt (старым)

- [ ] **AC4:** Given пользователь нажал "Придумать решение", when обрабатывается callback `brainstorm:mode:brainstorm`, then `brainstorm_phase = 'collect_topic'` в БД и бот задаёт первый вопрос brainstorming

- [ ] **AC5:** Given `brainstorm_phase = 'collect_topic'` и пользователь прислал менее 5 слов, when обрабатывается сообщение, then фаза не меняется и бот просит написать подробнее

- [ ] **AC6:** Given пользователь прошёл `collect_topic → collect_goal → collect_constraints`, when проверяется `brainstorm_data`, then `data["topic"]`, `data["goal"]`, `data["constraints"]` заполнены ответами пользователя

- [ ] **AC7:** Given `brainstorm_phase = 'choose_approach'`, when пользователь нажимает кнопку "brainstorm:approach:ideas", then `data["approach"] = "ideas"`, `brainstorm_phase = 'facilitation_loop'` и бот задаёт первый вопрос facilitation

- [ ] **AC8:** Given `brainstorm_phase = 'facilitation_loop'` и `facilitation_turns < 3`, when пользователь отправляет любое сообщение, then ответ бота НЕ содержит кнопку "Перейти к группировке"

- [ ] **AC9:** Given `brainstorm_phase = 'facilitation_loop'` и `facilitation_turns >= 3`, when пользователь отправляет сообщение, then ответ содержит inline-кнопку "Перейти к группировке идей"

- [ ] **AC10:** Given `brainstorm_phase = 'facilitation_loop'` и `len(ideas) == 50`, when пользователь отправляет новую идею, then `len(ideas)` остаётся 50 (первая обрезается)

- [ ] **AC11:** Given пользователь завершил фазу `finish`, when бот отвечает, then отправляется ровно 3 сообщения: список идей / топ-3 / план на 7 дней

- [ ] **AC12:** Given фаза `finish` завершена, when проверяется БД, then создан `SessionSummary` с `takeaway` = топ-3 идеи, и `ProfileFact` с темой и подходом пользователя

- [ ] **AC13:** Given `brainstorm_phase = 'facilitation_loop'` и пользователь отправляет кризисное сообщение, when safety routing срабатывает (`blocks_normal_flow=True`), then `brainstorm_phase = None`, `brainstorm_data = None` и бот переходит в стандартный crisis flow

- [ ] **AC14:** Given пользователь на фазе `cluster_ideas` закрыл приложение и вернулся позже, when он отправляет сообщение, then бот продолжает с `cluster_ideas`, не начинает сначала

- [ ] **AC15:** Given OpenAI API недоступен (mock возвращает `None`), when любая фаза обрабатывается, then бот отвечает fallback вопросом из таблицы и фаза переходит корректно

---

## Additional Context

### Dependencies

- Нет новых внешних библиотек — только `sqlalchemy` (уже есть) и `httpx` (уже есть)
- `OPENAI_API_KEY` должен быть задан в `.env` (уже есть)
- `TELEGRAM_BOT_TOKEN` и новый `WEBHOOK_URL` должны быть заданы в `.env`

### Testing Strategy

**Unit тесты (через webhook endpoint):**
- Все 10 сценариев из Task D4 через `POST /api/v1/telegram/webhook`
- OpenAI всегда мокируется через `patch()` — тесты не делают реальных API вызовов
- Используют SQLite (существующая тест-инфраструктура) — JSON field совместим

**Manual testing:**
1. Запустить `docker compose up`
2. Запустить `uv run scripts/register_webhook.py`
3. Написать `/start` в Telegram — убедиться что приходят 2 кнопки
4. Пройти полный brainstorming flow от `collect_topic` до `finish`
5. Проверить что crisis сообщение сбрасывает brainstorm_phase

### Notes

**Риски:**
- `_handle_message` уже большой (~300 строк) — аккуратно вставить новую ветку, не сломать существующий safety/billing flow
- `brainstorm_data` обновляется на каждый turn — при race condition (два сообщения одновременно) последнее победит; deduplication guard по `update_id` частично защищает, но не полностью
- Phase persistence ("продолжаем через 3 дня") требует что `brainstorm_data` не устаревает — данные в JSON не валидируются при чтении, нужно защитить `orchestrator.py` от `KeyError`

**Будущие улучшения (вне скоупа):**
- Несколько методологий помимо brainstorming
- Экспорт итога в PDF/Notion
- Аналитика по сессиям
- Таймаут незавершённых brainstorming сессий (напр. через 7 дней → auto-finish)

# Story 4.2: Пейволл с акцентом на безлимит и непрерывность (continuity)

Status: done

## Story

As a пользователь, который уже прошел ознакомительный цикл,
I want увидеть сообщение о подписке, которое подчеркивает ценность сохранения памяти и безлимитного общения,
So that я понимаю преимущество перехода на Premium-модель.

## Acceptance Criteria

1. **Given** пользователь заблокирован пейволлом (`first_session_completed == True` и `access_tier != "premium"`), **When** он получает сообщение от бота, **Then** текст сообщения должен содержать слово **"безлимит"** (или производные) и акцентировать внимание на сохранении контекста бесед. [Source: epics.md#story-4.2-AC1]

2. **Given** пейволл активен, **When** бот отправляет ответ, **Then** он включает Inline-кнопку "Оформить Premium ✦" с `callback_data="pay:stars"`. [Source: epics.md#story-4.2-AC2]

3. **Given** отображение пейволла, **When** пользователь видит сообщение, **Then** тон сообщения должен соответствовать "Structured Warmth" (структурированная теплота), избегая агрессивных продаж и подчеркивая партнерство в глубокой работе. [Source: ux-design-specification.md#premium-gate-prompt]

4. **Given** проверку доступа, **When** пользователь находится в состоянии кризиса (`crisis_state` активен), **Then** пейволл **не должен** отображаться, чтобы не прерывать критически важный процесс помощи. [Source: prd.md#FR22]

5. **Given** вызов `build_paywall_response`, **When** функция возвращает данные, **Then** это должно быть кортежем `(text, keyboard)`, где keyboard содержит кнопку оплаты. [Source: architecture.md#domain-boundaries]

## Tasks / Subtasks

- [x] Обновить `PAYWALL_MESSAGE` в `backend/app/billing/prompts.py` (AC: 1, 3)
  - [x] Убедиться, что текст содержит упоминание безлимита и памяти.
  - [x] Проверить соответствие тона UX-спецификации.

- [x] Обновить `build_paywall_response` в `backend/app/billing/service.py` (AC: 2, 5)
  - [x] Добавить создание Inline-клавиатуры с кнопкой `pay:stars`.
  - [x] Убедиться, что возвращается кортеж `(str, list[list[InlineButton]])`.

- [x] Проверить логику обхода пейволла для кризисных состояний (AC: 4)
  - [x] Убедиться, что в `session_bootstrap.py` проверка `crisis_state` стоит перед логикой пейволла. (Уже должно быть реализовано, нужно подтвердить).

- [x] Написать и запустить тесты (AC: все)
  - [x] Создать/обновить `backend/tests/billing/test_paywall_ui.py`.
  - [x] Test: пейволл содержит кнопку.
  - [x] Test: текст пейволла содержит ключевые слова ("безлимит").
  - [x] Test: в кризисном состоянии кнопка и текст пейволла не приходят.
  - [x] Запустить `uv run pytest tests/billing/ -q`.

## Dev Notes

- **Акцент на Premium**: Мы уходим от "разовой покупки" к "подписке" (хотя технически в Telegram Stars это может выглядеть как разовый платеж, коммуникация должна быть о статусе).
- **Кнопка**: Кнопка должна быть заметной, использование эмодзи `✦` или `💎` приветствуется согласно UX.
- **Логика ворот**: Логика уже в основном реализована в 4.1, здесь мы фокусируемся на контенте (UI/UX) и наличии кнопки действия.

## Project Structure Notes

- Billing prompts: `backend/app/billing/prompts.py`
- Billing service: `backend/app/billing/service.py`
- Session bootstrap: `backend/app/conversation/session_bootstrap.py`

## Technical Requirements

- Telegram Inline Keyboard API.
- Python `3.10+`.

## Architecture Compliance

- Separation of Concerns: Текст и структура кнопок определяются в `billing`, но отправляются через `conversation`.

## Testing Requirements

- `uv run pytest tests/billing/test_paywall_ui.py`
- `uv run ruff check app tests`

## References

- Epics Story 4.2: [Source: planning-artifacts/epics.md#story-4.2]
- UX Premium Gate Pattern: [Source: planning-artifacts/ux-design-specification.md]
- Sprint Change Proposal 2026-03-18: [Source: planning-artifacts/sprint-change-proposal-2026-03-18.md]

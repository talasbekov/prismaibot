# Story 4.1: Лимит на один бесплатный цикл и учет сессий

Status: done

## Story

As a пользователь, который только начинает пользоваться продуктом,
I want получить один полный бесплатный сеанс до пейволла,
So that я могу сначала почувствовать ценность продукта, прежде чем принимать решение о подписке.

## Acceptance Criteria

1. **Given** новый пользователь впервые пишет боту, **When** он проходит одну полную сессию (от старта до получения итогового takeaway/summary), **Then** система устанавливает флаг `first_session_completed` в `True` для этого пользователя в базе данных. [Source: epics.md#story-4.1-AC1]

2. **Given** пользователь уже завершил одну полную сессию (`first_session_completed == True`), **When** он пытается отправить любое сообщение, чтобы начать новую сессию (или продолжить взаимодействие после итога первой), **Then** система блокирует стандартный ответ и показывает пейволл (Paywall). [Source: epics.md#story-4.1-AC2]

3. **Given** пользователь находится внутри первой сессии, **When** он отправляет сообщения, **Then** система позволяет ему продолжать без ограничений до тех пор, пока сессия не будет официально закрыта и итог не будет сформирован. [Source: prd.md#FR21]

4. **Given** система обновляет флаг `first_session_completed`, **When** происходит запись в БД, **Then** это должно быть идемпотентным — повторное закрытие той же самой первой сессии не должно приводить к ошибкам или некорректному состоянию. [Source: architecture.md#idempotency-requirements]

5. **Given** пользователь заблокирован пейволлом, **When** он отправляет сообщение, **Then** ответ бота должен соответствовать UX-спецификации для Premium Gate (Structured Warmth, акцент на безлимит и память). [Source: ux-design-specification.md#premium-gate-prompt]

## Tasks / Subtasks

- [x] Обновить модель `UserAccessState` в `backend/app/billing/models.py` (AC: 1)
  - [x] Добавить поле `first_session_completed: bool = Field(default=False)`
  - [x] Создать Alembic миграцию: `uv run alembic revision --autogenerate -m "add first_session_completed to user_access_state"`

- [x] Реализовать логику установки флага в `billing/service.py` (AC: 1, 4)
  - [x] Обновить `record_eligible_session_completion`, чтобы он устанавливал `first_session_completed = True`
  - [x] Убедиться, что логика остается идемпотентной (использует `FreeSessionEvent` для проверки)

- [x] Обновить `is_free_eligible` в `billing/service.py` (AC: 2, 3)
  - [x] Теперь функция должна возвращать `not user_access_state.first_session_completed`
  - [x] (Опционально) Удалить использование `threshold_reached_at` и `free_sessions_used` в этой функции, если они больше не нужны для базового лимита

- [x] Проверить Paywall Gate в `conversation/session_bootstrap.py` (AC: 2, 5)
  - [x] Убедиться, что `_handle_message` корректно вызывает `is_free_eligible` and блокирует вход, если флаг установлен
  - [x] Убедиться, что сообщение пейволла берется из `billing/prompts.py` и соответствует новой UX-директиве (безлимит + память)

- [x] Написать и запустить тесты (AC: все)
  - [x] Обновить или создать `backend/tests/billing/test_free_limit_transition.py`
  - [x] Test: первая сессия проходит до конца → флаг ставится
  - [x] Test: после флага следующее сообщение → пейволл
  - [x] Test: внутри первой сессии (до итога) → пейволла нет
  - [x] Test: идемпотентность — повторный вызов записи итога не ломает ничего
  - [x] Запустить `uv run pytest tests/billing/ -q`

## Dev Notes

- **Переход на флаг**: Хотя старая логика использовала `threshold_reached_at`, новый PRD и Sprint Change Proposal (2026-03-18) явно требуют `first_session_completed`. Это делает логику "один бесплатный цикл" более явной и защищенной от изменений константы `FREE_SESSION_THRESHOLD`.
- **Место вызова**: `record_eligible_session_completion` вызывается в `session_bootstrap.py` при закрытии сессии (когда генерируется итоговый summary). Это правильная точка для установки флага.
- **Миграция**: Не забудьте запустить миграцию в тестовой БД перед запуском тестов.
- **UX Тон**: Пейволл должен звучать спокойно, на русском языке, предлагая Premium как способ "сохранить память и получить безлимит", а не просто как "купи подписку".

## Project Structure Notes

- Backend root: `backend/app/`
- Billing module: `backend/app/billing/`
- Tests: `backend/tests/billing/`

## Technical Requirements

- SQLModel `0.0.21`
- Alembic для миграций
- Python `3.10+`

## Architecture Compliance

- Domain boundaries: `billing/` владеет логикой доступа, `conversation/` вызывает её через service layer.
- Idempotency: использование таблицы `free_session_events` гарантирует, что одно и то же событие завершения сессии не будет обработано дважды.

## Testing Requirements

- `uv run pytest tests/billing/`
- `uv run ruff check app tests`
- `uv run mypy app tests`

## References

- PRD FR21, FR22: [Source: planning-artifacts/prd.md]
- Sprint Change Proposal 2026-03-18: [Source: planning-artifacts/sprint-change-proposal-2026-03-18.md]
- Epics Story 4.1: [Source: planning-artifacts/epics.md#story-4.1]
- UX Premium Gate Pattern: [Source: planning-artifacts/ux-design-specification.md]

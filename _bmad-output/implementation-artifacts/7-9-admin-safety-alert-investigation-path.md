# Story 7.9: Управляемый путь расследования safety-инцидентов

Status: done

## Story

As an operator,
I want безопасно просматривать детали кризисных сессий при получении алерта,
So that я могу принять решение о дальнейшей помощи.

## Acceptance Criteria

1. **Given** нажатие кнопки "🔍 Расследовать" в списке алертов, **When** запрос обрабатывается, **Then** система должна создать запись `OperatorInvestigation` со статусом `opened`. [Source: epics.md#story-7.9-AC1]

2. **Given** открытие расследования, **When** данные загружаются, **Then** бот должен вернуть детали сессии:
    - ID пользователя.
    - Категория и уверенность триггера.
    - Текст последнего сообщения пользователя.
    - Текущий кризисный статус сессии. [Source: epics.md#story-7.9-AC2]

3. **Given** доступ к деталям, **When** расследование открыто, **Then** действие должно быть логгировано с указанием ID администратора. [Source: architecture.md#auditing]

## Tasks / Subtasks

- [x] Обработать коллбэк `admin:alerts` для вывода списка последних алертов.
- [x] Реализовать коллбэк `admin:investigate:{id}`.
- [x] Интегрировать с `request_and_open_operator_investigation` для аудируемого доступа к контексту.
- [x] Сформировать детальный отчет по инциденту.
- [x] Написать тесты для проверки полноты данных в расследовании.

## Dev Notes

- Использование `request_and_open_operator_investigation` гарантирует, что каждый просмотр контекста оставляет след в таблице `operator_investigation`.
- Для безопасности в Telegram выводится только критически важный контекст (последнее сообщение и параметры триггера).

## References

- Epics Story 7.9: [Source: planning-artifacts/epics.md#story-7.9]
- Investigations Service: `backend/app/ops/investigations.py`

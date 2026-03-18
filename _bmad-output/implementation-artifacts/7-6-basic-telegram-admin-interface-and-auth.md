# Story 7.6: Базовый Telegram Admin Interface и авторизация

Status: done

## Story

As an operator,
I want иметь доступ к скрытым командам управления в Telegram,
So that я могу взаимодействовать с системой без использования веб-панели.

## Acceptance Criteria

1. **Given** запрос `/admin`, **When** `telegram_user_id` находится в списке `ADMIN_IDS` (из настроек), **Then** бот должен отправить приветственное сообщение с кнопками управления. [Source: epics.md#story-7.6-AC1]

2. **Given** запрос `/admin`, **When** `telegram_user_id` **НЕ** находится в списке `ADMIN_IDS`, **Then** бот должен игнорировать команду или отправить стандартный ответ, не раскрывая админ-функции. [Source: epics.md#story-7.6-AC2]

3. **Given** вход в админ-панель, **When** бот показывает меню, **Then** оно должно содержать кнопки: "Статистика", "Пользователь", "Алерты". [Source: architecture.md#operator-interface]

4. **Given** список админов, **When** загружаются настройки, **Then** `ADMIN_IDS` должен поддерживать список целых чисел (Telegram ID). [Source: core/config.py]

## Tasks / Subtasks

- [x] Добавить `ADMIN_IDS: list[int]` в `backend/app/core/config.py`.
- [x] Создать функция `is_admin(user_id)` в `backend/app/bot/utils.py`.
- [x] Реализовать `_handle_admin_command` в `backend/app/conversation/session_bootstrap.py`.
- [x] Подключить роутинг команды `/admin` в `handle_session_entry`.
- [x] Написать тесты для проверки прав доступа.

## Dev Notes

- `ADMIN_IDS` можно задавать через строку окружения, разделенную запятыми (парсинг в `config.py`).
- Используйте `InlineKeyboardMarkup` для админ-меню.

## References

- Epics Story 7.6: [Source: planning-artifacts/epics.md#story-7.6]

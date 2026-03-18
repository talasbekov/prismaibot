---
title: 'Enable Legacy Admin Routes'
slug: 'enable-legacy-admin-routes'
created: '2026-03-18'
status: 'implementation-complete'
stepsCompleted: [1, 2, 3, 4, 5]
tech_stack: ['FastAPI', 'Docker', 'Python', 'PostgreSQL', 'Pytest']
files_to_modify: ['.env', 'backend/app/api/main.py']
code_patterns: ['APIRouter.include_router', 'Pydantic Settings (BaseSettings)', 'FastAPI lifespan']
test_patterns: ['Pytest', 'TestClient', 'legacy_client fixture']
---

# Tech-Spec: Enable Legacy Admin Routes

**Created:** 2026-03-17

## Overview

### Problem Statement

Фронтенд выдает 404 ошибки на эндпоинты `/api/v1/items/`, `/api/v1/users/me` и другие, так как флаг `ENABLE_LEGACY_WEB_ROUTES` по умолчанию выключен на бэкенде. Это блокирует работу админ-панели и просмотр предметов.

### Solution

Включить флаг `ENABLE_LEGACY_WEB_ROUTES=True` в `.env` файле и перезапустить сервисы бэкенда для активации legacy-роутов. Это восстановит работу существующих API-интерфейсов для администрирования.

### Scope

**In Scope:**
- Изменение конфигурации в `.env` (установка `ENABLE_LEGACY_WEB_ROUTES=True`).
- Проверка корректности подключения `legacy_router` в `backend/app/api/main.py` при включенном флаге.
- Перезапуск контейнера бэкенда.
- Валидация доступности эндпоинта `/api/v1/items/` (возврат 401/200 вместо 404).
- Проверка эндпоинта `/api/v1/users/me`.

**Out of Scope:**
- Рефакторинг legacy-кода или моделей `Item`.
- Изменение логики авторизации или прав доступа в старых компонентах.
- Удаление неиспользуемых legacy-файлов.

## Context for Development

### Codebase Patterns

- **FastAPI Routing**: Роуты разделены на `product_router` (новые фичи) и `legacy_router` (старый код). Подключение `legacy_router` происходит условно на основе флага в настройках.
- **Configuration**: Используется `pydantic-settings` для загрузки переменных из `.env` в класс `Settings`.
- **Testing**: Тесты для legacy-роутов используют специальный фикстуру `legacy_client`, которая эмулирует запросы к этим эндпоинтам.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `backend/app/api/main.py` | Регистрирует `legacy_router` при включенном флаге. |
| `backend/app/core/config.py` | Определяет флаг `ENABLE_LEGACY_WEB_ROUTES` со значением по умолчанию `False`. |
| `.env` | Переопределяет настройки для локальной среды. |
| `backend/tests/api/routes/test_items.py` | Содержит тесты для эндпоинтов `/items/`. |
| `backend/app/api/routes/items.py` | Реализация эндпоинтов для предметов. |

### Technical Decisions

1. **Использование флага**: Оставить флаг `ENABLE_LEGACY_WEB_ROUTES` как основной рубильник для активации старого API.
2. **Перезапуск контейнера**: Для гарантированного применения изменений в `.env` внутри Docker-окружения рекомендуется использовать `docker compose up -d backend`, что пересоздаст контейнер с новыми переменными.

## Implementation Plan

### Tasks

- [x] Task 1: Обновить файл `.env` для активации legacy-роутов.
  - File: `.env`
  - Action: Установить `ENABLE_LEGACY_WEB_ROUTES=True`.
  - Notes: Файл находится в корне проекта.

- [x] Task 2: Проверить логику регистрации роутов в бэкенде.
  - File: `backend/app/api/main.py`
  - Action: Убедиться, что `legacy_router` подключается только при `settings.ENABLE_LEGACY_WEB_ROUTES`.
  - Notes: Код уже содержит это условие, нужно просто подтвердить.

- [x] Task 3: Применить изменения и перезапустить бэкенд.
  - Command: `docker compose up -d backend`
  - Action: Выполнить команду для пересоздания контейнера с новыми переменными окружения.
  - Notes: После запуска дождаться "Application startup complete".

- [x] Task 4: Запустить существующие тесты для подтверждения работоспособности.
  - Command: `docker exec goals-backend-1 pytest backend/tests/api/routes/test_items.py backend/tests/api/routes/test_users.py`
  - Action: Выполнить тесты для предметов и пользователей. Убедиться, что они проходят.

### Acceptance Criteria

- [x] AC 1: Given запущенный бэкенд, when выполняется GET запрос к `/api/v1/items/` без токена, then возвращается 401 Not Authenticated (вместо 404).
- [x] AC 2: Given запущенный бэкенд, when выполняется GET запрос к `/api/v1/users/me` без токена, then возвращается 401 Not Authenticated (вместо 404).
- [x] AC 3: Given корректный токен суперпользователя, when выполняется GET запрос к `/api/v1/items/`, then возвращается список предметов со статусом 200.
- [x] AC 4: Given включенный флаг в .env, when запускаются тесты `backend/tests/api/routes/test_items.py` и `test_users.py`, then все тесты проходят успешно.
- [x] AC 5: **Security Check**: Given включенные legacy-роуты, when выполняется любой запрос к ним без токена, then система ОБЯЗАТЕЛЬНО возвращает 401/403 (проверка отсутствия "голых" эндпоинтов).

## Additional Context

### Dependencies

- Docker и Docker Compose.
- Наличие базы данных (уже запущенной в контейнере `goals-db-1`).

### Testing Strategy

- **Автоматизированное тестирование**: Запуск `pytest` внутри контейнера бэкенда для `test_items.py` и `test_users.py`.
- **Ручное тестирование**: Использование `curl` для проверки статус-кодов эндпоинтов `/items/` и `/users/me`.

### Notes

- Мы уже выполнили часть этих шагов (рестарт и проверку `/items/`), но этот спек фиксирует полное состояние "Ready for Development" для воспроизводимости.

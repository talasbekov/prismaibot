# Prism AI — Полный обзор

Что это такое?
Full Stack FastAPI Template — это production-ready шаблон для разработки современных веб-приложений от Sebastián Ramírez (создателя FastAPI). Это не просто «болванка», а полноценная архитектурная основа, которую используют компании для быстрого старта серьёзных проектов. Весь стек продуман с точки зрения производительности, безопасности, масштабируемости и developer experience.

Архитектура проекта

full-stack-fastapi-template/
├── backend/              # Python + FastAPI
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/   # login, users, items, utils
│   │   │   ├── deps.py   # Dependency Injection
│   │   │   └── main.py   # Роутер-агрегатор
│   │   ├── core/
│   │   │   ├── config.py    # Pydantic Settings
│   │   │   ├── db.py        # SQLAlchemy Engine
│   │   │   └── security.py  # JWT + Argon2/Bcrypt
│   │   ├── models.py        # SQLModel (ORM + Schemas)
│   │   ├── crud.py          # Database operations
│   │   └── main.py          # FastAPI app + CORS + Sentry
│   ├── alembic/             # Миграции БД
│   ├── tests/               # Pytest
│   └── pyproject.toml       # Зависимости (uv)
│
├── frontend/             # React + TypeScript
│   ├── src/
│   │   ├── routes/       # File-based routing (TanStack)
│   │   ├── client/       # Auto-generated OpenAPI client
│   │   ├── components/   # shadcn/ui компоненты
│   │   └── hooks/        # Custom React hooks
│   ├── tests/            # Playwright E2E
│   └── package.json      # Зависимости (Bun)
│
├── compose.yml           # Production Docker Compose
├── compose.override.yml  # Dev-режим: hot-reload, mailcatcher
├── compose.traefik.yml   # Reverse proxy + SSL
└── .env                  # Конфигурация окружения

Полный стек технологий с объяснением выбора
Backend
Технология	Почему именно она
FastAPI	Самый быстрый Python-фреймворк (benchmark: быстрее Django в 2-5 раз). Встроенный OpenAPI/Swagger. Async из коробки. Строгая типизация через аннотации. Автодокументация.
SQLModel	Написан создателем FastAPI. Объединяет SQLAlchemy (ORM) + Pydantic (валидация) в одном классе — нет дублирования кода моделей.
PostgreSQL	Самая надёжная production СУБД. Full ACID, JSON поддержка, отличная масштабируемость.
Alembic	Стандарт де-факто для миграций SQLAlchemy. Автогенерация из моделей, история изменений схемы.
PyJWT + OAuth2	Stateless аутентификация. JWT с 8-дневным TTL. Полная совместимость со стандартами OAuth2.
Argon2 (pwdlib)	Победитель Password Hashing Competition 2015. Защищён от GPU-атак, side-channel атак. Лучше bcrypt.
Pydantic v2	Написан на Rust. В 5-50x быстрее Pydantic v1. Строгая валидация данных.
uv	Новый Python package manager на Rust. В 10-100x быстрее pip. Создан командой Astral (авторы ruff).
Ruff + mypy	Ruff (Rust) заменяет flake8+isort+black. mypy в строгом режиме — полная типобезопасность.
Sentry SDK	Production мониторинг ошибок. Трекинг производительности.
Frontend
Технология	Почему именно она
React 19	Самая популярная UI-библиотека. Новый компилятор, лучший concurrent rendering.
TypeScript 5.9	Статическая типизация = меньше ошибок в runtime. Идеальная интеграция с auto-generated клиентом.
Vite	Сборка на основе ESM. Старт dev-сервера за <300ms. HMR мгновенный. В 10-20x быстрее webpack.
TanStack Router	File-based routing с полной типобезопасностью. Автоматическое code-splitting.
TanStack Query	Умный кеш данных. Автоматическая инвалидация. Loading/error states из коробки. Optimistic updates.
shadcn/ui	Не library, а коллекция компонентов которые ты владеешь. Построена на Radix UI (доступность) + Tailwind.
Tailwind CSS 4	Utility-first CSS. Новая версия с нативными CSS cascade layers. Нет runtime.
Zod + React Hook Form	Zod — TypeScript-first валидация схем. RHF — перформанс-ориентированные формы без лишних ре-рендеров.
Biome	Rust-based замена ESLint + Prettier. В 15-25x быстрее.
Playwright	E2E тесты от Microsoft. Кросс-браузерный (Chromium, Firefox, WebKit). Параллельный запуск.
Bun	JavaScript runtime + package manager на Zig. В 3-5x быстрее npm/yarn.
@hey-api/openapi-ts	Автогенерация TypeScript клиента из OpenAPI схемы бекенда. Нет ручного написания API-запросов.
DevOps
Технология	Почему именно она
Docker + Compose	Изолированные окружения. Воспроизводимые сборки. Dev/prod паритет.
Traefik 3	Автоматический SSL от Let's Encrypt. Динамический конфиг. Dashboard. Docker-native.
GitHub Actions	CI/CD прямо в репозитории. Параллельный запуск тестов. Deploy в staging/production.
Adminer	Лёгкий веб-интерфейс для PostgreSQL. Один контейнер, удобная инспекция БД.
Mailcatcher	Перехватывает все email в dev-режиме. Веб-интерфейс для просмотра писем.
Что уже реализовано в шаблоне
Полная система аутентификации (JWT, OAuth2, cookie)
Регистрация пользователей и верификация email
Сброс пароля через email (с HTML шаблонами)
CRUD операции для Users и Items как пример
Роли: superuser vs обычный пользователь
Admin панель с управлением пользователями
Тёмная тема из коробки
Auto-generated API client — никакого ручного написания fetch/axios запросов
Пагинация для списков
Полное тестирование: backend (pytest) + E2E (Playwright)
CI/CD пайплайны для GitHub Actions
Production deployment с Traefik + SSL
Пошаговая инструкция по запуску
Предварительные требования

# Убедись что установлено:
docker --version        # >= 24.x
docker compose version  # >= 2.x
git --version


Шаг 1 — Клонирование и настройка

# Перейди в папку проекта
cd /home/erda/Загрузки/full-stack-fastapi-template-master

# Посмотри .env файл (он уже существует)
cat .env
Открой .env и измени критичные значения:


# ОБЯЗАТЕЛЬНО измени для безопасности:
SECRET_KEY=<сгенерируй_случайную_строку>
FIRST_SUPERUSER=admin@yourdomain.com
FIRST_SUPERUSER_PASSWORD=<надёжный_пароль>
POSTGRES_PASSWORD=<надёжный_пароль>

# Для локальной разработки оставь как есть:
DOMAIN=localhost
ENVIRONMENT=local
POSTGRES_SERVER=localhost   # или db при Docker
Генерация SECRET_KEY:


python3 -c "import secrets; print(secrets.token_urlsafe(32))"


Шаг 2 — Запуск через Docker Compose (рекомендуемый способ)

# Запусти все сервисы в dev-режиме с hot-reload
docker compose watch
Или классически:


docker compose up -d
Что запускается:

Сервис	URL	Описание
Frontend (React)	http://localhost:5173	Vite dev server
Backend (FastAPI)	http://localhost:8000	API с hot-reload
API Docs (Swagger)	http://localhost:8000/docs	Интерактивная документация
API Docs (Redoc)	http://localhost:8000/redoc	Альтернативная документация
Adminer (DB UI)	http://localhost:8080	Управление PostgreSQL
Traefik Dashboard	http://localhost:8090	Reverse proxy
Mailcatcher	http://localhost:1080	Перехват email


Шаг 3 — Первый вход

Открой http://localhost:5173
Нажми Log In
Войди с данными из .env:
Email: значение FIRST_SUPERUSER
Пароль: значение FIRST_SUPERUSER_PASSWORD


Шаг 4 — Локальный запуск без Docker

Backend (требует Python 3.10+)

# Установи uv (если нет)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Перейди в backend
cd backend

# Создай виртуальное окружение и установи зависимости
uv sync

# Настрой БД (нужен запущенный PostgreSQL)
# Запусти только PostgreSQL через Docker:
docker compose up db -d

# Примени миграции
uv run alembic upgrade head

# Создай первого суперпользователя
uv run python app/initial_data.py

# Запусти backend с hot-reload
uv run fastapi dev app/main.py
Frontend (требует Bun)

# Установи Bun (если нет)
curl -fsSL https://bun.sh/install | bash

# Перейди в frontend
cd frontend

# Установи зависимости
bun install

# Запусти dev-сервер
bun dev


Шаг 5 — Генерация API клиента (после изменения backend)

После добавления новых эндпоинтов нужно обновить TypeScript клиент:


# Из корня проекта
bash scripts/generate-client.sh
Это автоматически:

Читает OpenAPI схему с http://localhost:8000/api/v1/openapi.json
Генерирует TypeScript типы и функции в frontend/src/client/


Шаг 6 — Запуск тестов

Backend тесты (pytest)

cd backend

# Запусти все тесты
uv run pytest

# С покрытием кода
uv run pytest --cov=app --cov-report=html

# Конкретный файл
uv run pytest tests/api/test_users.py -v
Frontend E2E тесты (Playwright)

cd frontend

# Установи браузеры
bunx playwright install

# Запусти тесты
bunx playwright test

# Интерактивный UI режим
bunx playwright test --ui

# С видимым браузером
bunx playwright test --headed


Шаг 7 — Создание миграций БД

cd backend

# После изменения моделей в models.py — создай миграцию
uv run alembic revision --autogenerate -m "Add new field to User"

# Примени миграцию
uv run alembic upgrade head

# Откатить на шаг назад
uv run alembic downgrade -1


Шаг 8 — Работа с API

Swagger UI (интерактивно)
Открой http://localhost:8000/docs — там можно тестировать все эндпоинты прямо в браузере.

Ключевые эндпоинты:

POST   /api/v1/login/access-token          - Получить JWT токен
POST   /api/v1/login/test-token            - Проверить токен
POST   /api/v1/users/signup                - Регистрация
GET    /api/v1/users/me                    - Текущий пользователь
PATCH  /api/v1/users/me                    - Обновить профиль
PATCH  /api/v1/users/me/password           - Сменить пароль
POST   /api/v1/password-recovery/{email}   - Сброс пароля (email)

GET    /api/v1/items/                      - Список items
POST   /api/v1/items/                      - Создать item
PUT    /api/v1/items/{id}                  - Обновить item
DELETE /api/v1/items/{id}                  - Удалить item

GET    /api/v1/users/                      - [Admin] Все пользователи
POST   /api/v1/users/                      - [Admin] Создать пользователя
DELETE /api/v1/users/{id}                  - [Admin] Удалить пользователя


Шаг 9 — Добавление своей фичи (пример)

1. Создай модель в backend/app/models.py

class Product(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255)
    price: float
    owner_id: uuid.UUID = Field(foreign_key="user.id")
2. Создай роутер backend/app/api/routes/products.py

from fastapi import APIRouter
from app.api.deps import CurrentUser, SessionDep

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/")
def get_products(session: SessionDep, current_user: CurrentUser):
    ...
3. Зарегистрируй роутер в backend/app/api/main.py

from app.api.routes import products
api_router.include_router(products.router)
4. Создай миграцию и обнови клиент

uv run alembic revision --autogenerate -m "Add Product"
uv run alembic upgrade head
bash scripts/generate-client.sh
5. Используй в React

import { ProductsService } from "@/client"

// В компоненте — TanStack Query автоматически кеширует
const { data } = useQuery({
  queryKey: ["products"],
  queryFn: () => ProductsService.getProducts()
})



Шаг 10 — Production деплой

# Настрой домен и SSL
DOMAIN=yourdomain.com

# Запусти с Traefik (автоматический SSL от Let's Encrypt)
docker compose -f compose.yml -f compose.traefik.yml up -d
Почему это крутой шаблон для разработки?
Нулевой бойлерплейт — всё что нужно для старта уже написано
Type-safe от базы до UI — ошибки ловятся на этапе компиляции, не в runtime
Auto-generated API client — никакого ручного написания HTTP-запросов
Hot-reload везде — backend и frontend перезагружаются мгновенно
Безопасность по умолчанию — Argon2, JWT, CORS, timing-attack protection
Production-ready из коробки — Traefik + SSL + Sentry + health checks
Полное тестирование — unit + integration + E2E уже настроены
CI/CD включён — GitHub Actions workflows для staging и production
Скорость разработки — uv + Bun + Vite = самые быстрые инструменты
Официальный шаблон — поддерживается создателем FastAPI

# Story 6.5: Review payment issues and subscription-state problems

Status: done

## Story

As an operator,
I want видеть и разбирать payment issues и subscription-state problems,
so that я могу понимать, где monetization flow сломался или стал противоречивым для пользователя.

## Acceptance Criteria

1. **Given** в системе происходят payment failures, reconciliation mismatches or subscription-state inconsistencies **When** operator использует supported operational review path **Then** он может увидеть эти проблемные случаи как distinct operational issues **And** review workflow не требует routine access to sensitive conversation content.

2. **Given** у конкретного пользователя возник конфликт между expected billing outcome и actual access state **When** operator анализирует этот случай **Then** система показывает достаточно bounded billing and access context для понимания проблемы **And** operator может отличить payment initiation issue, callback issue, reconciliation problem or status-display inconsistency.

3. **Given** billing issue связана с delayed confirmation, provider timeout или duplicate callback behavior **When** operator reviewing workflow поднимает этот случай **Then** система сохраняет traceability of the event chain **And** problem review не сводится к guesswork from partial state.

4. **Given** review payment issues должно поддерживать product operations, а не ручную импровизацию **When** operator работает с monetization-related problems **Then** workflow позволяет последовательно видеть state, anomalies and unresolved cases **And** не зависит только от ad hoc database inspection as the primary path.

5. **Given** billing-review data itself incomplete, stale or unavailable **When** operator пытается разобраться в payment issue **Then** система делает видимой ограниченность или деградацию available review context **And** не выдает misleading certainty about the user's monetization state.

6. **Given** payment or subscription problem later resolves through confirmed event or manual follow-up **When** operator revisits the case **Then** updated operational view reflects latest confirmed state **And** resolved and unresolved billing issues are not indistinguishable in the workflow.

## Tasks / Subtasks

- [x] Создать `backend/app/ops/billing_review.py` с логикой детектирования billing issues (AC: 1, 2, 3, 4)
  - [x] Определить `@dataclass BillingIssue` с полями: `telegram_user_id`, `issue_category`, `intent_id`, `intent_status`, `intent_created_at`, `intent_updated_at`, `provider_payment_charge_id`, `access_tier`, `access_updated_at`
  - [x] Определить `@dataclass UserBillingContext` с полями: `telegram_user_id`, `access_tier`, `free_sessions_used`, `threshold_reached_at`, `purchase_intents: list[dict]`
  - [x] Реализовать `list_billing_issues(session: Session) -> list[BillingIssue]` — четыре категории аномалий (см. Dev Notes → Issue Categories)
  - [x] Реализовать `get_user_billing_context(session: Session, telegram_user_id: int) -> UserBillingContext | None`
  - [x] При отсутствии `UserAccessState` для пользователя с intent — не падать, возвращать `access_tier=None`

- [x] Добавить два endpoint'а в `backend/app/ops/api.py` (AC: 1, 2, 4)
  - [x] `GET /ops/billing-issues` — список всех обнаруженных billing anomalies, защищен `_verify_ops_token()`
  - [x] `GET /ops/billing/{telegram_user_id}` — per-user billing context, 404 если пользователь не найден, защищен `_verify_ops_token()`
  - [x] Добавить `_serialize_billing_issue()` и `_serialize_user_billing_context()` helper-функции
  - [x] Импортировать `list_billing_issues`, `get_user_billing_context` из `app.ops.billing_review`
  - [x] Следовать envelope `{"data": ..., "error": None}`

- [x] Написать unit-тесты в `backend/tests/operator/test_billing_review.py` (AC: 1, 2, 3, 5, 6)
  - [x] Test: пустой результат при чистом состоянии БД
  - [x] Test: detects `payment_failed` — failed PurchaseIntent
  - [x] Test: detects `payment_stale_pending` — pending intent older than 24h
  - [x] Test: НЕ detects recently created pending intent как issue
  - [x] Test: detects `payment_completed_no_access` — completed intent + free tier
  - [x] Test: detects `premium_access_no_payment` — premium UserAccessState без completed intent
  - [x] Test: `get_user_billing_context` returns None for unknown user
  - [x] Test: `get_user_billing_context` returns intents + access state

- [x] Добавить integration-тесты в `backend/tests/api/routes/test_ops_routes.py` (AC: 1, 4)
  - [x] Test: `GET /ops/billing-issues` без токена → 401
  - [x] Test: `GET /ops/billing-issues` с токеном → 200, `data` это list
  - [x] Test: `GET /ops/billing/{telegram_user_id}` без токена → 401
  - [x] Test: `GET /ops/billing/{telegram_user_id}` для несуществующего пользователя → 404
  - [x] Test: `GET /ops/billing/{telegram_user_id}` для существующего → 200, содержит `access_tier` и `purchase_intents`

- [x] Запустить: `uv run pytest tests/ -q`, `uv run ruff check --fix app tests`, `uv run mypy app tests` из `backend/`

## Dev Notes

### КРИТИЧНО: Что уже существует — не воссоздавать!

В `backend/app/ops/api.py` уже реализованы следующие endpoints (не трогать):
- `GET /ops/healthz` — liveness, без auth
- `GET /ops/readyz` — readiness, без auth
- `GET /ops/auth-check` — проверка токена
- `GET /ops/status` — operational counts aggregation (NOT a list — только counts)
- `GET /ops/alerts` — list operator alerts
- `GET /ops/deletion-requests` — list pending deletion requests
- `POST /ops/deletion-requests/{id}/execute` — execute deletion
- `GET /ops/continuity/{telegram_user_id}` — continuity overview
- `GET /ops/investigations/{id}`, `POST /ops/investigations/{id}/close`, `POST /ops/alerts/{id}/investigations`

Задача: добавить **новые** `GET /ops/billing-issues` и `GET /ops/billing/{telegram_user_id}`.

### КРИТИЧНО: PurchaseIntent статусы — использовать "completed", не "confirmed"!

В `billing/repository.py` функция `complete_purchase_intent()` устанавливает `status = "completed"`.
В `billing/service.py` (в `confirm_payment_and_upgrade`) проверяются статусы `"pending"`, `"completed"`, `"failed"`.

**Реальные статусы PurchaseIntent:**
- `"pending"` — создан, ожидает оплаты
- `"completed"` — оплата подтверждена
- `"failed"` — оплата не прошла

⚠️ В `app/ops/status.py` (story 6.4) используется `"confirmed"` — это **баг в status.py**, из-за которого `payment_signals.confirmed` всегда равен 0. В данной истории НЕ исправлять `status.py` (story 6.4 завершена), но **использовать `"completed"`** в новом `billing_review.py`.

### Issue Categories (4 аномалии)

| Категория | Условие обнаружения | Смысл |
|-----------|---------------------|-------|
| `payment_failed` | `PurchaseIntent.status == "failed"` | Платёж не прошёл |
| `payment_stale_pending` | `PurchaseIntent.status == "pending"` и `created_at < now - 24h` | Платёж завис (callback не пришёл) |
| `payment_completed_no_access` | `PurchaseIntent.status == "completed"` но `UserAccessState.access_tier != "premium"` | Деньги списались, доступ не дали |
| `premium_access_no_payment` | `UserAccessState.access_tier == "premium"` но нет `PurchaseIntent.status == "completed"` | Premium без записи об оплате |

Свежие `pending` интенты (< 24h) **НЕ** включаются в `payment_stale_pending` — это нормальное рабочее состояние во время активного платежа.

### Целевой интерфейс billing_review.py

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.billing.models import PurchaseIntent, UserAccessState


@dataclass
class BillingIssue:
    telegram_user_id: int
    issue_category: str  # "payment_failed" | "payment_stale_pending" | "payment_completed_no_access" | "premium_access_no_payment"
    intent_id: uuid.UUID | None
    intent_status: str | None
    intent_created_at: datetime | None
    intent_updated_at: datetime | None
    provider_payment_charge_id: str | None
    access_tier: str | None
    access_updated_at: datetime | None


@dataclass
class UserBillingContext:
    telegram_user_id: int
    access_tier: str
    free_sessions_used: int
    threshold_reached_at: datetime | None
    purchase_intents: list[dict] = field(default_factory=list)


_STALE_PENDING_THRESHOLD_HOURS = 24


def list_billing_issues(session: Session) -> list[BillingIssue]:
    issues: list[BillingIssue] = []
    stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=_STALE_PENDING_THRESHOLD_HOURS)

    # 1. Failed intents
    for intent in session.exec(
        select(PurchaseIntent).where(PurchaseIntent.status == "failed")
    ).all():
        access = session.exec(
            select(UserAccessState).where(UserAccessState.telegram_user_id == intent.telegram_user_id)
        ).first()
        issues.append(BillingIssue(
            telegram_user_id=intent.telegram_user_id,
            issue_category="payment_failed",
            intent_id=intent.id,
            intent_status=intent.status,
            intent_created_at=intent.created_at,
            intent_updated_at=intent.updated_at,
            provider_payment_charge_id=intent.provider_payment_charge_id,
            access_tier=access.access_tier if access else None,
            access_updated_at=access.updated_at if access else None,
        ))

    # 2. Stale pending intents (> 24h)
    for intent in session.exec(
        select(PurchaseIntent).where(
            PurchaseIntent.status == "pending",
            PurchaseIntent.created_at < stale_cutoff,
        )
    ).all():
        access = session.exec(
            select(UserAccessState).where(UserAccessState.telegram_user_id == intent.telegram_user_id)
        ).first()
        issues.append(BillingIssue(
            telegram_user_id=intent.telegram_user_id,
            issue_category="payment_stale_pending",
            intent_id=intent.id,
            intent_status=intent.status,
            intent_created_at=intent.created_at,
            intent_updated_at=intent.updated_at,
            provider_payment_charge_id=intent.provider_payment_charge_id,
            access_tier=access.access_tier if access else None,
            access_updated_at=access.updated_at if access else None,
        ))

    # 3. Completed intent but access_tier != "premium"
    for intent in session.exec(
        select(PurchaseIntent).where(PurchaseIntent.status == "completed")
    ).all():
        access = session.exec(
            select(UserAccessState).where(UserAccessState.telegram_user_id == intent.telegram_user_id)
        ).first()
        if access is None or access.access_tier != "premium":
            issues.append(BillingIssue(
                telegram_user_id=intent.telegram_user_id,
                issue_category="payment_completed_no_access",
                intent_id=intent.id,
                intent_status=intent.status,
                intent_created_at=intent.created_at,
                intent_updated_at=intent.updated_at,
                provider_payment_charge_id=intent.provider_payment_charge_id,
                access_tier=access.access_tier if access else None,
                access_updated_at=access.updated_at if access else None,
            ))

    # 4. Premium access but no completed intent
    for state in session.exec(
        select(UserAccessState).where(UserAccessState.access_tier == "premium")
    ).all():
        completed = session.exec(
            select(PurchaseIntent).where(
                PurchaseIntent.telegram_user_id == state.telegram_user_id,
                PurchaseIntent.status == "completed",
            )
        ).first()
        if completed is None:
            issues.append(BillingIssue(
                telegram_user_id=state.telegram_user_id,
                issue_category="premium_access_no_payment",
                intent_id=None,
                intent_status=None,
                intent_created_at=None,
                intent_updated_at=None,
                provider_payment_charge_id=None,
                access_tier=state.access_tier,
                access_updated_at=state.updated_at,
            ))

    return issues


def get_user_billing_context(
    session: Session, telegram_user_id: int
) -> UserBillingContext | None:
    access = session.exec(
        select(UserAccessState).where(UserAccessState.telegram_user_id == telegram_user_id)
    ).first()
    intents = session.exec(
        select(PurchaseIntent).where(PurchaseIntent.telegram_user_id == telegram_user_id)
    ).all()

    if access is None and not intents:
        return None

    return UserBillingContext(
        telegram_user_id=telegram_user_id,
        access_tier=access.access_tier if access else "unknown",
        free_sessions_used=access.free_sessions_used if access else 0,
        threshold_reached_at=access.threshold_reached_at if access else None,
        purchase_intents=[
            {
                "id": str(i.id),
                "invoice_payload": i.invoice_payload,
                "amount": i.amount,
                "currency": i.currency,
                "status": i.status,
                "provider_payment_charge_id": i.provider_payment_charge_id,
                "created_at": i.created_at.isoformat() if i.created_at else None,
                "updated_at": i.updated_at.isoformat() if i.updated_at else None,
            }
            for i in intents
        ],
    )
```

### Целевые endpoints в api.py

```python
from app.ops.billing_review import BillingIssue, UserBillingContext, get_user_billing_context, list_billing_issues

@router.get("/billing-issues")
def billing_issues(
    ops_auth_token: str | None = Header(default=None, alias="X-Ops-Auth-Token"),
) -> dict[str, object]:
    _verify_ops_token(ops_auth_token)
    with Session(engine) as session:
        issues = list_billing_issues(session)
    return {
        "data": [_serialize_billing_issue(issue) for issue in issues],
        "error": None,
    }


@router.get("/billing/{telegram_user_id}")
def user_billing_context(
    telegram_user_id: int,
    ops_auth_token: str | None = Header(default=None, alias="X-Ops-Auth-Token"),
) -> dict[str, object]:
    _verify_ops_token(ops_auth_token)
    with Session(engine) as session:
        ctx = get_user_billing_context(session, telegram_user_id)
    if ctx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="billing_context_not_found",
        )
    return {
        "data": _serialize_user_billing_context(ctx),
        "error": None,
    }


def _serialize_billing_issue(issue: BillingIssue) -> dict[str, object]:
    return {
        "telegram_user_id": issue.telegram_user_id,
        "issue_category": issue.issue_category,
        "intent_id": str(issue.intent_id) if issue.intent_id is not None else None,
        "intent_status": issue.intent_status,
        "intent_created_at": issue.intent_created_at.isoformat() if issue.intent_created_at else None,
        "intent_updated_at": issue.intent_updated_at.isoformat() if issue.intent_updated_at else None,
        "provider_payment_charge_id": issue.provider_payment_charge_id,
        "access_tier": issue.access_tier,
        "access_updated_at": issue.access_updated_at.isoformat() if issue.access_updated_at else None,
    }


def _serialize_user_billing_context(ctx: UserBillingContext) -> dict[str, object]:
    return {
        "telegram_user_id": ctx.telegram_user_id,
        "access_tier": ctx.access_tier,
        "free_sessions_used": ctx.free_sessions_used,
        "threshold_reached_at": ctx.threshold_reached_at.isoformat() if ctx.threshold_reached_at else None,
        "purchase_intents": ctx.purchase_intents,
    }
```

### Структура проекта

```
backend/app/
├── ops/
│   ├── __init__.py
│   ├── api.py              ← добавить 2 endpoint'а + 2 serializer + import
│   ├── billing_review.py   ← СОЗДАТЬ: новый модуль
│   ├── alerts.py           ← list_operator_alerts() — образец list-паттерна
│   ├── deletion.py         ← list_pending_deletion_requests() — образец list-паттерна
│   ├── health.py           ← check_service_health() — образец dataclass-паттерна
│   ├── investigations.py
│   ├── signals.py
│   └── status.py           ← агрегирует counts (НЕ изменять)
├── billing/
│   ├── models.py           ← PurchaseIntent, UserAccessState (только SELECT — НЕ изменять)
│   └── repository.py       ← паттерны запросов к billing моделям
└── models.py               ← TelegramSession, DeletionRequest, ... (НЕ нужен для этой истории)
```

### Паттерн unit-тестов billing_review.py

```python
# backend/tests/operator/test_billing_review.py
from datetime import datetime, timedelta, timezone
import pytest
from sqlmodel import Session

from app.billing.models import PurchaseIntent, UserAccessState
from app.ops.billing_review import list_billing_issues, get_user_billing_context


def test_list_billing_issues_empty_on_clean_db(db: Session) -> None:
    issues = list_billing_issues(db)
    assert issues == []


def test_list_billing_issues_detects_failed_payment(db: Session) -> None:
    intent = PurchaseIntent(
        telegram_user_id=70001,
        invoice_payload="premium_70001",
        amount=100,
        status="failed",
    )
    db.add(intent)
    db.commit()

    issues = list_billing_issues(db)
    assert any(
        i.telegram_user_id == 70001 and i.issue_category == "payment_failed"
        for i in issues
    )


def test_list_billing_issues_detects_stale_pending(db: Session) -> None:
    stale_time = datetime.now(timezone.utc) - timedelta(hours=25)
    intent = PurchaseIntent(
        telegram_user_id=70002,
        invoice_payload="premium_70002",
        amount=100,
        status="pending",
        created_at=stale_time,
        updated_at=stale_time,
    )
    db.add(intent)
    db.commit()

    issues = list_billing_issues(db)
    assert any(
        i.telegram_user_id == 70002 and i.issue_category == "payment_stale_pending"
        for i in issues
    )


def test_list_billing_issues_ignores_fresh_pending(db: Session) -> None:
    intent = PurchaseIntent(
        telegram_user_id=70003,
        invoice_payload="premium_70003",
        amount=100,
        status="pending",
        # created_at defaults to now — fresh, should NOT be flagged
    )
    db.add(intent)
    db.commit()

    issues = list_billing_issues(db)
    assert not any(
        i.telegram_user_id == 70003
        for i in issues
    )


def test_list_billing_issues_detects_completed_no_access(db: Session) -> None:
    intent = PurchaseIntent(
        telegram_user_id=70004,
        invoice_payload="premium_70004",
        amount=100,
        status="completed",
        provider_payment_charge_id="charge_abc",
    )
    state = UserAccessState(
        telegram_user_id=70004,
        access_tier="free",
        free_sessions_used=3,
    )
    db.add(intent)
    db.add(state)
    db.commit()

    issues = list_billing_issues(db)
    assert any(
        i.telegram_user_id == 70004 and i.issue_category == "payment_completed_no_access"
        for i in issues
    )


def test_list_billing_issues_detects_premium_access_no_payment(db: Session) -> None:
    state = UserAccessState(
        telegram_user_id=70005,
        access_tier="premium",
        free_sessions_used=3,
    )
    db.add(state)
    db.commit()

    issues = list_billing_issues(db)
    assert any(
        i.telegram_user_id == 70005 and i.issue_category == "premium_access_no_payment"
        for i in issues
    )


def test_get_user_billing_context_returns_none_for_unknown(db: Session) -> None:
    result = get_user_billing_context(db, telegram_user_id=99999)
    assert result is None


def test_get_user_billing_context_returns_intents_and_access(db: Session) -> None:
    state = UserAccessState(
        telegram_user_id=70006,
        access_tier="premium",
        free_sessions_used=2,
    )
    intent = PurchaseIntent(
        telegram_user_id=70006,
        invoice_payload="premium_70006",
        amount=100,
        status="completed",
        provider_payment_charge_id="charge_xyz",
    )
    db.add(state)
    db.add(intent)
    db.commit()

    ctx = get_user_billing_context(db, telegram_user_id=70006)
    assert ctx is not None
    assert ctx.access_tier == "premium"
    assert ctx.free_sessions_used == 2
    assert len(ctx.purchase_intents) == 1
    assert ctx.purchase_intents[0]["status"] == "completed"
```

**ВАЖНО:** `backend/tests/operator/` уже существует (есть `test_deletion.py`, `test_health.py`, `test_alerts.py`, `test_investigations.py`, `test_status.py`). Создавать директорию не нужно — файл добавить напрямую.

### Паттерн integration-тестов в test_ops_routes.py

```python
def test_billing_issues_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/ops/billing-issues")
    assert response.status_code == 401


def test_billing_issues_returns_list(client: TestClient) -> None:
    response = client.get(
        "/api/v1/ops/billing-issues",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["data"], list)
    assert data["error"] is None


def test_billing_per_user_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/ops/billing/12345")
    assert response.status_code == 401


def test_billing_per_user_returns_404_for_unknown(client: TestClient) -> None:
    response = client.get(
        "/api/v1/ops/billing/999999999",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )
    assert response.status_code == 404


def test_billing_per_user_returns_context(client: TestClient, db: Session) -> None:
    from app.billing.models import PurchaseIntent, UserAccessState
    state = UserAccessState(telegram_user_id=71001, access_tier="premium", free_sessions_used=0)
    intent = PurchaseIntent(telegram_user_id=71001, invoice_payload="premium_71001", amount=100, status="completed")
    db.add(state)
    db.add(intent)
    db.commit()

    response = client.get(
        "/api/v1/ops/billing/71001",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["access_tier"] == "premium"
    assert len(data["purchase_intents"]) == 1
    assert "status" in data["purchase_intents"][0]
    assert data["purchase_intents"][0]["status"] == "completed"
```

### Нет новых таблиц / миграций

**НЕ нужны:**
- Новая Alembic migration (читаем из существующих таблиц)
- Изменения в `billing/models.py`, `billing/repository.py`, `billing/service.py`
- Изменения в `models.py`
- Изменения в conversation flow, safety логике

### Anti-patterns для этой истории

- ❌ Не использовать `"confirmed"` для статуса PurchaseIntent — реальный статус `"completed"`
- ❌ Не изменять `status.py` (story 6.4 завершена, её баг с "confirmed" — отдельная задача)
- ❌ Не добавлять billing_review endpoints без `_verify_ops_token()` auth gate
- ❌ Не создавать новые таблицы или migrations
- ❌ Не изменять модели `billing/` — только SELECT из существующих
- ❌ Не включать PII-поля: `working_context`, `last_user_message`, `last_bot_prompt` (их нет в billing моделях — дополнительная проверка не нужна)
- ❌ Не добавлять "исправление" `/ops/status` в scope этой истории
- ❌ Не делать N+1 N-запросов проблемой — этот endpoint operator-only, не user-path

### Порядок действий

1. Создать `backend/app/ops/billing_review.py` с dataclasses и функциями
2. Добавить 2 endpoint'а + 2 serializer в `backend/app/ops/api.py`
3. Создать `backend/tests/operator/test_billing_review.py` с unit-тестами
4. Добавить integration-тесты в `backend/tests/api/routes/test_ops_routes.py`
5. Запустить полный suite

### References

- [Source: epics.md#Story-6.5] — полные acceptance criteria
- [Source: architecture.md#Payment-Security-Boundary] — хранить только payment/reference IDs, не instrument details
- [Source: architecture.md#Operator-Authentication-Model] — single operator role, X-Ops-Auth-Token
- [Source: backend/app/ops/api.py] — все существующие endpoints, `_verify_ops_token()`, response envelope `{"data": ..., "error": None}`, паттерны serialize-функций
- [Source: backend/app/ops/deletion.py] — паттерн list-функций с `select().where()`, `@dataclass` результаты
- [Source: backend/app/ops/status.py] — bug: использует "confirmed" вместо "completed" для PurchaseIntent
- [Source: backend/app/billing/models.py] — `PurchaseIntent` (статусы: "pending"/"completed"/"failed"), `UserAccessState` (поля)
- [Source: backend/app/billing/repository.py] — `complete_purchase_intent()` sets status="completed"; функции для доступа к billing данным
- [Source: backend/app/billing/service.py] — `confirm_payment_and_upgrade()` — показывает полный жизненный цикл статусов
- [Source: backend/tests/operator/test_deletion.py] — паттерн unit-тестов оператора с db-фикстурой
- [Source: backend/tests/api/routes/test_ops_routes.py] — integration-тест паттерн, auth header `X-Ops-Auth-Token: local-ops-auth-token`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Реализован модуль `billing_review.py` для обнаружения 4 типов аномалий в платежах и подписках.
- Добавлены endpoints `/ops/billing-issues` и `/ops/billing/{telegram_user_id}` в `api.py`.
- Обеспечено покрытие unit и integration тестами (100% success).
- Код прошел проверку ruff и mypy.

### File List

- `backend/app/ops/billing_review.py`
- `backend/app/ops/api.py`
- `backend/tests/operator/test_billing_review.py`
- `backend/tests/api/routes/test_ops_routes.py`

### Change Log

- Initial implementation of billing review logic and endpoints.
- Added comprehensive unit and integration tests for billing operations.
- Date: 2026-03-15

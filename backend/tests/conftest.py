import importlib
import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.billing.models import FreeSessionEvent, PurchaseIntent, UserAccessState
from app.core.config import settings
from app.core.db import engine, init_db
from app.main import app
from app.models import (
    DeletionRequest,
    Item,
    OperatorAlert,
    OperatorInvestigation,
    PeriodicInsight,
    ProcessedTelegramUpdate,
    ProfileFact,
    SafetySignal,
    SessionSummary,
    SummaryGenerationSignal,
    TelegramSession,
    User,
)
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


def _reload_app(*, enable_legacy_web_routes: bool) -> TestClient:
    os.environ["SAFETY_ENABLED"] = "true"
    os.environ.pop("TELEGRAM_BOT_TOKEN", None)
    if enable_legacy_web_routes:
        os.environ["ENABLE_LEGACY_WEB_ROUTES"] = "true"
    else:
        os.environ.pop("ENABLE_LEGACY_WEB_ROUTES", None)

    config_module = importlib.import_module("app.core.config")
    api_main_module = importlib.import_module("app.api.main")
    main_module = importlib.import_module("app.main")

    importlib.reload(config_module)
    importlib.reload(api_main_module)
    importlib.reload(main_module)

    return TestClient(main_module.app)


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        init_db(session)
        yield session
        session.rollback()
        statement = delete(PurchaseIntent)
        session.execute(statement)
        statement = delete(FreeSessionEvent)
        session.execute(statement)
        statement = delete(UserAccessState)
        session.execute(statement)
        statement = delete(DeletionRequest)
        session.execute(statement)
        statement = delete(PeriodicInsight)
        session.execute(statement)
        statement = delete(ProcessedTelegramUpdate)
        session.execute(statement)
        statement = delete(SummaryGenerationSignal)
        session.execute(statement)
        statement = delete(OperatorInvestigation)
        session.execute(statement)
        statement = delete(OperatorAlert)
        session.execute(statement)
        statement = delete(SafetySignal)
        session.execute(statement)
        statement = delete(ProfileFact)
        session.execute(statement)
        statement = delete(SessionSummary)
        session.execute(statement)
        statement = delete(TelegramSession)
        session.execute(statement)
        statement = delete(Item)
        session.execute(statement)
        statement = delete(User)
        session.execute(statement)
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def legacy_client() -> Generator[TestClient, None, None]:
    with _reload_app(enable_legacy_web_routes=True) as c:
        yield c

    with _reload_app(enable_legacy_web_routes=False):
        pass


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )


@pytest.fixture(scope="module")
def legacy_superuser_token_headers(legacy_client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(legacy_client)


@pytest.fixture(scope="module")
def legacy_normal_user_token_headers(
    legacy_client: TestClient, db: Session
) -> dict[str, str]:
    return authentication_token_from_email(
        client=legacy_client, email=settings.EMAIL_TEST_USER, db=db
    )

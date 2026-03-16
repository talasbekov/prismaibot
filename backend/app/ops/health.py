from dataclasses import dataclass
from typing import Literal

from sqlalchemy import Engine, text

from app.core.config import settings

SERVICE_NAME = "telegram-first-backend"

@dataclass
class ServiceHealthResult:
    status: Literal["ready", "not_ready"]
    service: str
    database_configured: bool
    database_reachable: bool

def check_service_health(engine: Engine) -> ServiceHealthResult:
    database_configured = all((
        settings.POSTGRES_SERVER,
        settings.POSTGRES_USER,
        settings.POSTGRES_DB,
    ))
    if not database_configured:
        return ServiceHealthResult(
            status="not_ready",
            service=SERVICE_NAME,
            database_configured=False,
            database_reachable=False,
        )
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return ServiceHealthResult(
            status="ready",
            service=SERVICE_NAME,
            database_configured=True,
            database_reachable=True,
        )
    except Exception:
        return ServiceHealthResult(
            status="not_ready",
            service=SERVICE_NAME,
            database_configured=True,
            database_reachable=False,
        )

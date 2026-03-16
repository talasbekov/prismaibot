from fastapi import APIRouter

from app.api.routes import items, login, private, users, utils
from app.billing.api import router as billing_router
from app.bot.api import router as telegram_router
from app.core.config import settings
from app.ops.api import router as ops_router

# Product-aligned routes are the runtime center for the MVP foundation.
product_router = APIRouter()
product_router.include_router(billing_router)
product_router.include_router(ops_router)
product_router.include_router(telegram_router)

# Legacy template routes remain available temporarily for compatibility only.
legacy_router = APIRouter()
legacy_router.include_router(login.router)
legacy_router.include_router(users.router)
legacy_router.include_router(utils.router)
legacy_router.include_router(items.router)

if settings.ENVIRONMENT == "local":
    legacy_router.include_router(private.router)

api_router = APIRouter()
api_router.include_router(product_router)

if settings.ENABLE_LEGACY_WEB_ROUTES:
    api_router.include_router(legacy_router)

from typing import Any

from fastapi import APIRouter, Header, HTTPException, status

from app.core.config import settings

router = APIRouter(prefix="/billing", tags=["billing"])


def _verify_payment_webhook_secret(
    payment_webhook_secret: str | None,
) -> None:
    expected_secret = settings.PAYMENT_PROVIDER_WEBHOOK_SECRET
    if not expected_secret:
        return
    if payment_webhook_secret != expected_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_payment_webhook_secret",
        )


@router.post("/webhook")
def payment_webhook(
    payload: dict[str, Any],
    payment_webhook_secret: str | None = Header(
        default=None, alias="X-Payment-Webhook-Secret"
    ),
) -> dict[str, object]:
    """Foundation seam for provider callback verification and deploy smoke checks."""
    _verify_payment_webhook_secret(payment_webhook_secret)
    return {
        "status": "ignored",
        "handled": False,
        "provider_event_type": payload.get("type"),
    }

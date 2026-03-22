from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel

from app.core.config import settings


class ApiPayError(Exception):
    """Base exception for ApiPay client errors."""
    pass


class ApiPayInvoiceResponse(BaseModel):
    id: int
    status: str
    amount: float
    description: str | None = None
    external_order_id: str | None = None


class ApiPaySubscriptionResponse(BaseModel):
    id: int
    status: str
    amount: float
    billing_period: str


class ApiPayClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        is_sandbox: bool | None = None,
    ) -> None:
        self.api_key = api_key or settings.APIPAY_API_KEY
        self.base_url = base_url or settings.APIPAY_BASE_URL
        self.is_sandbox = is_sandbox if is_sandbox is not None else settings.APIPAY_SANDBOX
        self.headers = {
            "X-API-Key": self.api_key or "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def create_invoice(
        self,
        *,
        amount: float,
        phone_number: str,
        external_order_id: str | None = None,
        description: str | None = None,
    ) -> ApiPayInvoiceResponse:
        """Create a payment invoice in ApiPay."""
        payload: dict[str, Any] = {
            "amount": amount,
            "phone_number": phone_number,
        }
        if external_order_id:
            payload["external_order_id"] = external_order_id
        if description:
            payload["description"] = description

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/invoices",
                json=payload,
                headers=self.headers,
                timeout=10.0,
            )
            
            if response.status_code >= 400:
                raise ApiPayError(f"ApiPay error {response.status_code}: {response.text}")
            
            data = response.json()
            return ApiPayInvoiceResponse(**data)

    async def create_subscription(
        self,
        *,
        amount: float,
        phone_number: str,
        period: str = "monthly",
        description: str | None = None,
        external_subscriber_id: str | None = None,
    ) -> ApiPaySubscriptionResponse:
        """Create a recurring subscription in ApiPay."""
        payload: dict[str, Any] = {
            "amount": amount,
            "phone_number": phone_number,
            "billing_period": period,
        }
        if description:
            payload["description"] = description
        if external_subscriber_id:
            payload["external_subscriber_id"] = external_subscriber_id

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/subscriptions",
                json=payload,
                headers=self.headers,
                timeout=10.0,
            )

            if response.status_code >= 400:
                raise ApiPayError(f"ApiPay error {response.status_code}: {response.text}")

            data = response.json()
            sub_data = data.get("subscription", data)
            return ApiPaySubscriptionResponse(**sub_data)

    async def cancel_subscription(self, subscription_id: int) -> bool:
        """Cancel an active subscription in ApiPay."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/subscriptions/{subscription_id}/cancel",
                headers=self.headers,
                timeout=10.0,
            )
            
            if response.status_code >= 400:
                raise ApiPayError(f"ApiPay error {response.status_code}: {response.text}")
            
            return response.status_code == 202 or response.status_code == 200

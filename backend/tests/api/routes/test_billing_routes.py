from fastapi.testclient import TestClient


def test_payment_webhook_requires_secret(client: TestClient) -> None:
    response = client.post("/api/v1/billing/webhook", json={"type": "payment.failed"})

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_payment_webhook_secret"


def test_payment_webhook_accepts_configured_secret(client: TestClient) -> None:
    response = client.post(
        "/api/v1/billing/webhook",
        json={"type": "payment.succeeded"},
        headers={"X-Payment-Webhook-Secret": "local-payment-webhook-secret"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ignored",
        "handled": False,
        "provider_event_type": "payment.succeeded",
    }

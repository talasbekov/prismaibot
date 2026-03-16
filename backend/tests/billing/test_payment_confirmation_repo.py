
from sqlmodel import Session

from app.billing.repository import (
    complete_purchase_intent,
    create_purchase_intent,
    get_or_create_user_access_state,
    get_purchase_intent_by_payload,
    upgrade_access_tier,
)


def test_get_purchase_intent_by_payload(db: Session) -> None:
    create_purchase_intent(
        db,
        telegram_user_id=111,
        invoice_payload="val1",
        amount=100,
    )
    create_purchase_intent(
        db,
        telegram_user_id=222,
        invoice_payload="val2",
        amount=200,
    )
    db.commit()

    found_intent = get_purchase_intent_by_payload(db, "val1")
    assert found_intent is not None
    assert found_intent.telegram_user_id == 111

    not_found = get_purchase_intent_by_payload(db, "not_exist")
    assert not_found is None


def test_complete_purchase_intent(db: Session) -> None:
    intent = create_purchase_intent(
        db,
        telegram_user_id=111,
        invoice_payload="test_payload",
        amount=100,
    )
    db.commit()

    complete_purchase_intent(db, intent, "charge_123")
    db.commit()

    db.refresh(intent)
    assert intent.status == "completed"
    assert intent.provider_payment_charge_id == "charge_123"
    assert intent.updated_at is not None


def test_upgrade_access_tier(db: Session) -> None:
    state = get_or_create_user_access_state(db, 123)
    db.commit()
    assert state.access_tier == "free"

    upgrade_access_tier(db, state)
    db.commit()

    db.refresh(state)
    assert state.access_tier == "premium"
    assert state.updated_at is not None

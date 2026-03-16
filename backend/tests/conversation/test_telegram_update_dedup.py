from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.conversation.session_bootstrap import handle_session_entry


def test_duplicate_update_id_is_skipped(db: Session) -> None:
    """Одинаковый update_id должен обрабатываться только один раз."""
    update = {
        "update_id": 900001,
        "message": {
            "from": {"id": 90001},
            "chat": {"id": 90001},
            "text": "/start",
        },
    }

    resp1 = handle_session_entry(db, update)
    db.commit()
    assert resp1.handled is True  # первый раз — обрабатывается

    resp2 = handle_session_entry(db, update)
    db.commit()
    assert resp2.action == "duplicate_skipped"
    assert resp2.handled is False  # второй раз — пропускается


def test_different_update_ids_processed_independently(db: Session) -> None:
    """Разные update_id обрабатываются независимо."""
    base_msg = {
        "message": {
            "from": {"id": 90002},
            "chat": {"id": 90002},
            "text": "/start",
        }
    }
    resp1 = handle_session_entry(db, {"update_id": 900010, **base_msg})
    db.commit()
    resp2 = handle_session_entry(db, {"update_id": 900011, **base_msg})
    db.commit()

    assert resp1.action != "duplicate_skipped"
    assert resp2.action != "duplicate_skipped"


def test_update_without_update_id_processed_normally(db: Session) -> None:
    """Update без update_id обрабатывается нормально (backward compatibility)."""
    update = {
        "message": {
            "from": {"id": 90003},
            "chat": {"id": 90003},
            "text": "/start",
        }
    }
    resp = handle_session_entry(db, update)
    db.commit()
    assert resp.action != "duplicate_skipped"
    assert resp.handled is True


def test_dedup_race_condition_returns_skipped(db: Session) -> None:
    """Race condition (IntegrityError при flush) должен возвращать duplicate_skipped."""
    update = {
        "update_id": 900050,
        "message": {
            "from": {"id": 90050},
            "chat": {"id": 90050},
            "text": "/start",
        }
    }
    
    # Мокаем session так, чтобы flush бросал IntegrityError
    mock_session = MagicMock(spec=Session)
    mock_session.get.return_value = None  # Не в базе
    mock_session.flush.side_effect = IntegrityError("race", params={}, orig=None)
    
    resp = handle_session_entry(mock_session, update)
    
    assert resp.action == "duplicate_skipped"
    mock_session.rollback.assert_called_once()


def test_dedup_failure_proceeds_normally(db: Session) -> None:
    """Если dedup слой падает с ошибкой, обработка должна продолжаться (AC 5)."""
    update = {
        "update_id": 900060,
        "message": {
            "from": {"id": 90060},
            "chat": {"id": 90060},
            "text": "/start",
        }
    }
    
    # Мокаем session так, чтобы get бросал Exception
    mock_session = MagicMock(spec=Session)
    mock_session.get.side_effect = Exception("DB Down")
    
    # Чтобы выполнение прошло дальше блока дедупликации, нам нужно чтобы _get_or_create_active_session не упал сразу
    # Или просто проверить, что мы вышли из блока дедупликации.
    # В handle_session_entry после дедупликации идет обращение к message['pre_checkout_query'] и т.д.
    
    resp = handle_session_entry(mock_session, update)
    
    # Должен продолжить и попытаться найти/создать сессию
    assert resp.action != "duplicate_skipped"

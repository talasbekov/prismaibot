"""Story B: Tests for brainstorm_phase and brainstorm_data fields on TelegramSession."""
from __future__ import annotations

import uuid

import pytest
from sqlmodel import Session, select

from app.models import SessionSummary, TelegramSession


@pytest.fixture(autouse=True)
def cleanup(db: Session):
    yield
    db.exec(
        __import__("sqlmodel", fromlist=["delete"]).delete(SessionSummary)
    )
    db.exec(
        __import__("sqlmodel", fromlist=["delete"]).delete(TelegramSession)
    )
    db.commit()


def _make_session(db: Session, **kwargs) -> TelegramSession:
    s = TelegramSession(
        telegram_user_id=999_000_001,
        chat_id=999_000_001,
        **kwargs,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def test_brainstorm_phase_defaults_to_none(db: Session):
    """Task B1: brainstorm_phase field exists and defaults to None."""
    s = _make_session(db)
    assert s.brainstorm_phase is None


def test_brainstorm_data_defaults_to_none(db: Session):
    """Task B1: brainstorm_data field exists and defaults to None."""
    s = _make_session(db)
    assert s.brainstorm_data is None


def test_brainstorm_phase_can_be_set_and_retrieved(db: Session):
    """brainstorm_phase is persisted and read back correctly."""
    s = _make_session(db, brainstorm_phase="collect_topic")
    fetched = db.exec(
        select(TelegramSession).where(TelegramSession.id == s.id)
    ).one()
    assert fetched.brainstorm_phase == "collect_topic"


def test_brainstorm_data_json_roundtrip(db: Session):
    """brainstorm_data JSON field survives a full roundtrip through SQLite."""
    payload = {
        "topic": "Как запустить новый продукт",
        "goal": "Получить 10 платящих пользователей за месяц",
        "constraints": "Бюджет $0, 2 часа в день",
        "approach": "ideas",
        "ideas": ["идея 1", "идея 2"],
        "facilitation_turns": 2,
    }
    s = _make_session(db, brainstorm_phase="facilitation_loop", brainstorm_data=payload)
    fetched = db.exec(
        select(TelegramSession).where(TelegramSession.id == s.id)
    ).one()
    assert fetched.brainstorm_data == payload
    assert fetched.brainstorm_data["ideas"] == ["идея 1", "идея 2"]
    assert fetched.brainstorm_data["facilitation_turns"] == 2


def test_brainstorm_phase_can_be_updated(db: Session):
    """brainstorm_phase can be updated from one phase to the next."""
    s = _make_session(db, brainstorm_phase="collect_topic")
    s.brainstorm_phase = "collect_goal"
    db.add(s)
    db.commit()
    db.refresh(s)
    assert s.brainstorm_phase == "collect_goal"


def test_brainstorm_phase_accepts_max_length_value(db: Session):
    """brainstorm_phase accepts values up to 32 chars."""
    long_phase = "a" * 32
    s = _make_session(db, brainstorm_phase=long_phase)
    assert s.brainstorm_phase == long_phase


def test_brainstorm_data_can_be_cleared_to_none(db: Session):
    """brainstorm_data can be reset to None (crisis reset scenario)."""
    s = _make_session(
        db,
        brainstorm_phase="facilitation_loop",
        brainstorm_data={"topic": "test", "ideas": []},
    )
    s.brainstorm_phase = None
    s.brainstorm_data = None
    db.add(s)
    db.commit()
    db.refresh(s)
    assert s.brainstorm_phase is None
    assert s.brainstorm_data is None

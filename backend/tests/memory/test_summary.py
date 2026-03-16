import uuid

import pytest
from sqlmodel import Session, select

from app.memory.schemas import ProfileFactInput, SessionSummaryPayload
from app.memory.service import (
    build_session_summary,
    derive_allowed_profile_facts,
    get_continuity_overview,
    get_session_recall_context,
    persist_session_summary,
)
from app.models import (
    ProfileFact,
    SessionSummary,
    SummaryGenerationSignal,
    TelegramSession,
)


def test_build_session_summary_keeps_continuity_fields_without_transcript_dump() -> None:
    payload = SessionSummaryPayload(
        session_id=uuid.UUID("db8ad8f8-44bf-4a1a-b911-41f626ad3f40"),
        telegram_user_id=7001,
        reflective_mode="deep",
        source_turn_count=3,
        prior_context="Мы снова поссорились, и мне обидно, что он меня не слышит.",
        latest_user_message="Он перебил меня на встрече, и я начинаю тревожиться, что это повторится.",
        takeaway="Если подвести это к ясной точке, похоже, больнее всего то, что этот напряженный сценарий повторяется.",
        next_steps=[
            "1. Отделить для себя сам поступок человека от того смысла, который он у тебя вызвал.",
            "2. Решить, нужен ли тебе сейчас разговор по сути или сначала небольшая пауза.",
        ],
    )

    summary = build_session_summary(payload)

    assert summary.key_facts
    assert summary.emotional_tensions
    assert summary.next_step_context == [
        "Отделить для себя сам поступок человека от того смысла, который он у тебя вызвал.",
        "Решить, нужен ли тебе сейчас разговор по сути или сначала небольшая пауза.",
    ]
    assert all("Он перебил меня на встрече" not in fact for fact in summary.key_facts)


def test_build_session_summary_marks_uncertainty_for_noisy_context() -> None:
    payload = SessionSummaryPayload(
        session_id=uuid.UUID("2f2fcb17-e427-47a4-b18e-bb7348ad8b0d"),
        telegram_user_id=7002,
        reflective_mode="fast",
        source_turn_count=3,
        prior_context="Мы снова вернулись к этому разговору, и меня уже качает от него.",
        latest_user_message="Я как будто и злюсь, и не понимаю, права ли я вообще.",
        takeaway="Если подвести это к ясной точке, пока не до конца ясно, что здесь было главным источником боли.",
        next_steps=["1. Сначала не делать резких выводов, пока картина внутри не стала устойчивее."],
    )

    summary = build_session_summary(payload)

    assert summary.uncertainty_notes
    assert "условный" in summary.uncertainty_notes[0]


def test_derive_allowed_profile_facts_returns_conservative_runtime_scope() -> None:
    facts = derive_allowed_profile_facts(
        prior_context="Мы снова поссорились с мужем, и мне тяжело.",
        latest_user_message="Он перебил меня, и мне важно, чтобы меня дослушивали.",
        takeaway="Похоже, это повторяющийся паттерн, где тебе особенно не хватает спокойного разговора.",
    )

    assert {fact.fact_key for fact in facts} == {
        "relationship_context",
        "recurring_trigger",
        "communication_preference",
        "support_preference",
    }


def test_build_session_summary_generalizes_high_risk_context() -> None:
    payload = SessionSummaryPayload(
        session_id=uuid.UUID("99f553fb-4bf2-49bf-9144-e4f9ea495d11"),
        telegram_user_id=7010,
        reflective_mode="deep",
        source_turn_count=3,
        prior_context="Мне страшно, после насилия дома я не знаю, что делать.",
        latest_user_message="Иногда кажется, что лучше исчезнуть, чем снова переживать это.",
        takeaway="Мне страшно после насилия дома, и я уже думаю, что лучше исчезнуть.",
        next_steps=["1. Срочно понять, куда обратиться за безопасной поддержкой."],
    )

    summary = build_session_summary(payload)

    assert "исчезнуть" not in summary.takeaway.lower()
    assert "насили" not in summary.takeaway.lower()
    assert summary.next_step_context == []
    assert any("чувствительной" in fact.lower() for fact in summary.key_facts)


def test_persist_session_summary_downgrades_sensitive_profile_facts_from_recall(
    db: Session,
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("f46731fd-88d7-4944-a6cf-4e256e96e9d6"),
        telegram_user_id=7011,
        chat_id=8011,
    )
    db.add(session_record)
    db.commit()

    payload = SessionSummaryPayload(
        session_id=session_record.id,
        telegram_user_id=7011,
        reflective_mode="deep",
        source_turn_count=3,
        prior_context="Мне страшно, после насилия дома я не знаю, что делать.",
        latest_user_message="Кажется, я больше не справляюсь и мне нужна опора.",
        takeaway="После этого эпизода мне страшно и я не понимаю, как дальше выдерживать ситуацию.",
        next_steps=["1. Найти безопасную поддержку прямо сейчас."],
        allowed_profile_facts=[
            ProfileFactInput(
                fact_key="relationship_context",
                fact_value="Пользователь переживает насилие в близких отношениях.",
                confidence="high",
            ),
            ProfileFactInput(
                fact_key="support_preference",
                fact_value="Пользователю важен спокойный и уважительный тон разговора.",
                confidence="high",
            ),
        ],
    )

    persist_session_summary(payload, build_session_summary(payload))

    facts = db.exec(
        select(ProfileFact).where(ProfileFact.telegram_user_id == 7011)
    ).all()
    assert facts
    assert all(fact.retention_scope == "restricted_profile" for fact in facts)

    overview = get_continuity_overview(db, telegram_user_id=7011)
    assert overview.summaries
    assert overview.profile_facts == []

    recall = get_session_recall_context(db, telegram_user_id=7011)
    assert recall is not None
    assert recall.profile_facts == []
    assert "насили" not in recall.continuity_context.lower()


def test_persist_session_summary_keeps_low_confidence_fact_out_of_durable_recall(
    db: Session,
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("134c7d89-1a2e-45e1-aaf5-414ef7aab8ad"),
        telegram_user_id=7012,
        chat_id=8012,
    )
    db.add(session_record)
    db.commit()

    payload = SessionSummaryPayload(
        session_id=session_record.id,
        telegram_user_id=7012,
        reflective_mode="deep",
        source_turn_count=3,
        prior_context="Мы вроде снова спорим, но я не до конца понимаю, что именно повторяется.",
        latest_user_message="Наверное, это какой-то старый паттерн, хотя я не уверена.",
        takeaway="Пока не до конца ясно, есть ли здесь устойчивый повторяющийся сценарий.",
        next_steps=["1. Сначала проверить, что в этой ситуации точно произошло."],
        allowed_profile_facts=[
            ProfileFactInput(
                fact_key="recurring_trigger",
                fact_value="Пользователь устойчиво живет в повторяющемся конфликтном паттерне.",
                confidence="low",
            )
        ],
    )

    persist_session_summary(payload, build_session_summary(payload))

    facts = db.exec(
        select(ProfileFact).where(ProfileFact.telegram_user_id == 7012)
    ).all()
    assert len(facts) == 1
    assert facts[0].retention_scope == "restricted_profile"

    recall = get_session_recall_context(db, telegram_user_id=7012)
    assert recall is not None
    assert recall.profile_facts == []
    assert "повторяющ" not in recall.continuity_context.lower()


def test_persist_session_summary_promotion_failure_defaults_to_store_less(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("e39bec4f-c6d7-4e0c-85d4-730bb262b527"),
        telegram_user_id=7013,
        chat_id=8013,
        working_context="Временный контекст",
        last_user_message="Сырой текст",
        last_bot_prompt="Последний ответ",
    )
    db.add(session_record)
    db.commit()

    payload = SessionSummaryPayload(
        session_id=session_record.id,
        telegram_user_id=7013,
        reflective_mode="deep",
        source_turn_count=3,
        prior_context="Мы снова спорим дома.",
        latest_user_message="Мне важно, чтобы меня дослушивали.",
        takeaway="Кажется, тебе особенно важно ощущение уважительного разговора.",
        next_steps=["1. Замечать, где разговор начинает ломаться."],
        allowed_profile_facts=[
            ProfileFactInput(
                fact_key="communication_preference",
                fact_value="Пользователю важно, чтобы его не перебивали.",
                confidence="high",
            )
        ],
    )

    monkeypatch.setattr(
        "app.memory.service._promote_profile_facts",
        lambda **_: (_ for _ in ()).throw(RuntimeError("promotion blew up")),
    )

    persist_session_summary(payload, build_session_summary(payload))

    summary = db.exec(
        select(SessionSummary).where(SessionSummary.session_id == session_record.id)
    ).one()
    facts = db.exec(
        select(ProfileFact).where(ProfileFact.telegram_user_id == 7013)
    ).all()

    assert summary.takeaway == payload.takeaway
    assert facts == []


def test_persist_session_summary_creates_durable_artifact(db: Session) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("30763987-40a8-427d-87df-bd6155dc7997"),
        telegram_user_id=7003,
        chat_id=8003,
    )
    db.add(session_record)
    db.commit()

    payload = SessionSummaryPayload(
        session_id=uuid.UUID("30763987-40a8-427d-87df-bd6155dc7997"),
        telegram_user_id=7003,
        reflective_mode="deep",
        source_turn_count=4,
        prior_context="Я запутался после разговора с начальником.",
        latest_user_message="На работе мне сказали переделать проект, и я чувствую обесценивание.",
        takeaway="Если подвести это к ясной точке, тебя сильнее всего задевает не только сам конфликт, но и ощущение, что тебя не услышали.",
        next_steps=["1. Спокойно назвать, что именно тебя задело в его реакции."],
    )
    draft = build_session_summary(payload)

    persist_session_summary(payload, draft)

    summary = db.exec(
        select(SessionSummary).where(SessionSummary.telegram_user_id == 7003)
    ).one()
    assert summary.reflective_mode == "deep"
    assert summary.source_turn_count == 4
    assert summary.key_facts
    assert summary.next_step_context == ["Спокойно назвать, что именно тебя задело в его реакции."]
    assert summary.retention_scope == "durable_summary"
    assert summary.deletion_eligible is True

    session_record = db.exec(
        select(TelegramSession).where(TelegramSession.id == payload.session_id)
    ).one()
    assert session_record.working_context is None
    assert session_record.last_user_message is None
    assert session_record.last_bot_prompt is None
    assert session_record.transcript_purged_at is not None


def test_persist_session_summary_updates_existing_artifact(db: Session) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("40864098-50b9-528e-98ef-cd7266ed8aa8"),
        telegram_user_id=7004,
        chat_id=8004,
    )
    db.add(session_record)
    db.commit()

    base_payload = SessionSummaryPayload(
        session_id=uuid.UUID("40864098-50b9-528e-98ef-cd7266ed8aa8"),
        telegram_user_id=7004,
        reflective_mode="fast",
        source_turn_count=2,
        prior_context="Я запутался после разговора с коллегой.",
        latest_user_message="Он перебил меня, и мне обидно.",
        takeaway="Тебя задело ощущение, что тебя не слышат.",
        next_steps=["1. Назвать себе, что именно задело."],
    )
    draft = build_session_summary(base_payload)
    persist_session_summary(base_payload, draft)

    updated_payload = SessionSummaryPayload(
        session_id=uuid.UUID("40864098-50b9-528e-98ef-cd7266ed8aa8"),
        telegram_user_id=7004,
        reflective_mode="deep",
        source_turn_count=4,
        prior_context="Мы поговорили еще раз, и стало чуть яснее.",
        latest_user_message="Я снова поссорился с коллегой на работе.",
        takeaway="После второго разговора картина стала точнее.",
        next_steps=["1. Решить, нужен ли открытый разговор."],
    )
    updated_draft = build_session_summary(updated_payload)
    persist_session_summary(updated_payload, updated_draft)

    summaries = db.exec(
        select(SessionSummary).where(SessionSummary.telegram_user_id == 7004)
    ).all()
    assert len(summaries) == 1, "upsert must not create a duplicate"
    assert summaries[0].source_turn_count == 4
    assert summaries[0].reflective_mode == "deep"
    assert summaries[0].takeaway == "После второго разговора картина стала точнее."


def test_persist_session_summary_separates_profile_facts_from_summary_scope(
    db: Session,
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("50864098-50b9-528e-98ef-cd7266ed8aa8"),
        telegram_user_id=7005,
        chat_id=8005,
        working_context="Контекст сессии",
        last_user_message="Последняя реплика",
        last_bot_prompt="Последний ответ",
    )
    db.add(session_record)
    db.commit()

    payload = SessionSummaryPayload(
        session_id=session_record.id,
        telegram_user_id=7005,
        reflective_mode="deep",
        source_turn_count=3,
        prior_context="Мы снова спорим о границах в отношениях.",
        latest_user_message="Мне важно, чтобы меня не перебивали.",
        takeaway="Похоже, ключевая боль связана с ощущением, что твои границы не замечают.",
        next_steps=["1. Отметить, какое именно нарушение границы повторяется чаще всего."],
        allowed_profile_facts=[
            ProfileFactInput(
                fact_key="relationship_context",
                fact_value="Пользователь регулярно обсуждает напряжение в романтических отношениях.",
            ),
            ProfileFactInput(
                fact_key="communication_preference",
                fact_value="Пользователю важно, чтобы его не перебивали в сложных разговорах.",
            ),
        ],
    )

    draft = build_session_summary(payload)
    persist_session_summary(payload, draft)

    summary = db.exec(
        select(SessionSummary).where(SessionSummary.session_id == session_record.id)
    ).one()
    facts = db.exec(
        select(ProfileFact).where(ProfileFact.telegram_user_id == 7005)
    ).all()

    assert summary.retention_scope == "durable_summary"
    assert {fact.fact_key for fact in facts} == {
        "relationship_context",
        "communication_preference",
    }
    assert all(fact.retention_scope == "durable_profile" for fact in facts)
    assert all(fact.source_session_id == session_record.id for fact in facts)
    assert all(fact.deleted_at is None for fact in facts)


def test_continuity_overview_exposes_summary_and_profile_facts_without_transcript(
    db: Session,
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("60864098-50b9-528e-98ef-cd7266ed8aa8"),
        telegram_user_id=7006,
        chat_id=8006,
    )
    db.add(session_record)
    db.commit()

    payload = SessionSummaryPayload(
        session_id=session_record.id,
        telegram_user_id=7006,
        reflective_mode="fast",
        source_turn_count=2,
        prior_context="Есть повторяющийся конфликт на работе.",
        latest_user_message="Мне важно больше ясности в разговорах с начальником.",
        takeaway="Сильнее всего задевает ощущение, что вклад пользователя обнуляют.",
        next_steps=["1. Зафиксировать, какой момент разговора ощущается самым болезненным."],
        allowed_profile_facts=[
            ProfileFactInput(
                fact_key="work_context",
                fact_value="Повторяющееся напряжение связано с разговорами с начальником.",
            )
        ],
    )

    persist_session_summary(payload, build_session_summary(payload))

    overview = get_continuity_overview(db, telegram_user_id=7006)

    assert len(overview.summaries) == 1
    assert len(overview.profile_facts) == 1
    assert overview.summaries[0].takeaway == payload.takeaway
    assert overview.profile_facts[0].fact_key == "work_context"
    dumped = overview.model_dump_json()
    assert "last_user_message" not in dumped
    assert "working_context" not in dumped


def test_get_session_recall_context_returns_bounded_recent_summary_and_active_facts(
    db: Session,
) -> None:
    session_old = TelegramSession(
        id=uuid.UUID("70864098-50b9-528e-98ef-cd7266ed8aa8"),
        telegram_user_id=7007,
        chat_id=8007,
        status="completed",
    )
    session_new = TelegramSession(
        id=uuid.UUID("80864098-50b9-528e-98ef-cd7266ed8aa8"),
        telegram_user_id=7007,
        chat_id=8007,
        status="completed",
    )
    db.add(session_old)
    db.add(session_new)
    db.commit()

    persist_session_summary(
        SessionSummaryPayload(
            session_id=session_old.id,
            telegram_user_id=7007,
            reflective_mode="deep",
            source_turn_count=3,
            prior_context="Старый контекст",
            latest_user_message="Старое сообщение",
            takeaway="Старая сессия показывала повторяющееся напряжение.",
            next_steps=["1. Старый шаг."],
            allowed_profile_facts=[
                ProfileFactInput(
                    fact_key="relationship_context",
                    fact_value="Напряжение связано с близкими отношениями.",
                )
            ],
        ),
        build_session_summary(
            SessionSummaryPayload(
                session_id=session_old.id,
                telegram_user_id=7007,
                reflective_mode="deep",
                source_turn_count=3,
                prior_context="Старый контекст",
                latest_user_message="Старое сообщение",
                takeaway="Старая сессия показывала повторяющееся напряжение.",
                next_steps=["1. Старый шаг."],
                allowed_profile_facts=[
                    ProfileFactInput(
                        fact_key="relationship_context",
                        fact_value="Напряжение связано с близкими отношениями.",
                    )
                ],
            )
        ),
    )
    persist_session_summary(
        SessionSummaryPayload(
            session_id=session_new.id,
            telegram_user_id=7007,
            reflective_mode="deep",
            source_turn_count=4,
            prior_context="Новый контекст",
            latest_user_message="Новое сообщение",
            takeaway="Последняя сессия показала, что пользователя особенно задевает повторяемость конфликта.",
            next_steps=["1. Новый шаг."],
            allowed_profile_facts=[
                ProfileFactInput(
                    fact_key="recurring_trigger",
                    fact_value="Пользователь воспринимает ситуацию как повторяющийся паттерн.",
                ),
                ProfileFactInput(
                    fact_key="support_preference",
                    fact_value="Пользователю полезнее спокойный и уважительный тон.",
                ),
            ],
        ),
        build_session_summary(
            SessionSummaryPayload(
                session_id=session_new.id,
                telegram_user_id=7007,
                reflective_mode="deep",
                source_turn_count=4,
                prior_context="Новый контекст",
                latest_user_message="Новое сообщение",
                takeaway="Последняя сессия показала, что пользователя особенно задевает повторяемость конфликта.",
                next_steps=["1. Новый шаг."],
                allowed_profile_facts=[
                    ProfileFactInput(
                        fact_key="recurring_trigger",
                        fact_value="Пользователь воспринимает ситуацию как повторяющийся паттерн.",
                    ),
                    ProfileFactInput(
                        fact_key="support_preference",
                        fact_value="Пользователю полезнее спокойный и уважительный тон.",
                    ),
                ],
            )
        ),
    )

    deleted_fact = db.exec(
        select(ProfileFact).where(ProfileFact.telegram_user_id == 7007).where(
            ProfileFact.fact_key == "relationship_context"
        )
    ).one()
    deleted_fact.deleted_at = deleted_fact.updated_at
    db.add(deleted_fact)
    db.commit()

    recall = get_session_recall_context(db, telegram_user_id=7007)

    assert recall is not None
    assert recall.telegram_user_id == 7007
    assert recall.last_session_takeaway.startswith("Последняя сессия")
    assert recall.profile_facts
    assert {fact.fact_key for fact in recall.profile_facts} == {
        "recurring_trigger",
        "support_preference",
    }
    assert "отношениями" not in recall.continuity_context
    assert "повторяющийся паттерн" in recall.continuity_context


def test_get_session_recall_context_ignores_restricted_profile_facts(
    db: Session,
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("8cffc7e1-d0d7-4741-b247-bbe962a3727b"),
        telegram_user_id=7014,
        chat_id=8014,
        status="completed",
    )
    db.add(session_record)
    db.commit()

    db.add(
        SessionSummary(
            session_id=session_record.id,
            telegram_user_id=7014,
            reflective_mode="deep",
            source_turn_count=3,
            takeaway="В прошлой сессии было видно, что пользователю важен спокойный разговор.",
            key_facts=["Пользователь искал более спокойную рамку разговора."],
            emotional_tensions=["Ситуация вызывала напряжение."],
            uncertainty_notes=[],
            next_step_context=["Замечать момент, где напряжение нарастает."],
        )
    )
    db.add(
        ProfileFact(
            telegram_user_id=7014,
            source_session_id=session_record.id,
            fact_key="support_preference",
            fact_value="Пользователю важен спокойный и уважительный тон.",
            confidence="high",
            retention_scope="restricted_profile",
        )
    )
    db.commit()

    overview = get_continuity_overview(db, telegram_user_id=7014)
    recall = get_session_recall_context(db, telegram_user_id=7014)

    assert overview.profile_facts == []
    assert recall is not None
    assert recall.profile_facts == []


def test_get_session_recall_context_excludes_superseded_facts(
    db: Session,
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890"),
        telegram_user_id=7015,
        chat_id=8015,
        status="completed",
    )
    db.add(session_record)
    db.commit()

    db.add(
        SessionSummary(
            session_id=session_record.id,
            telegram_user_id=7015,
            reflective_mode="deep",
            source_turn_count=3,
            takeaway="В прошлой сессии у пользователя был рабочий конфликт.",
            key_facts=["Напряжение связано с рабочей ситуацией."],
            emotional_tensions=["Ситуация вызывала напряжение."],
            uncertainty_notes=[],
            next_step_context=[],
        )
    )
    superseded_fact = ProfileFact(
        telegram_user_id=7015,
        source_session_id=session_record.id,
        fact_key="work_context",
        fact_value="Старый рабочий контекст, который был заменён новой версией.",
        confidence="high",
        retention_scope="durable_profile",
    )
    db.add(superseded_fact)
    db.commit()

    from datetime import datetime, timezone

    superseded_fact.superseded_at = datetime.now(timezone.utc)
    db.add(superseded_fact)
    db.commit()

    recall = get_session_recall_context(db, telegram_user_id=7015)

    assert recall is not None
    assert recall.profile_facts == []
    assert "Старый рабочий контекст" not in recall.continuity_context


def test_upsert_profile_facts_preserves_restricted_profile_scope_across_sessions(
    db: Session,
) -> None:
    session_one = TelegramSession(
        id=uuid.UUID("b2c3d4e5-f6a7-8901-bcde-f12345678901"),
        telegram_user_id=7016,
        chat_id=8016,
        status="completed",
    )
    session_two = TelegramSession(
        id=uuid.UUID("c3d4e5f6-a7b8-9012-cdef-123456789012"),
        telegram_user_id=7016,
        chat_id=8016,
        status="completed",
    )
    db.add(session_one)
    db.add(session_two)
    db.commit()

    # Session one: high-risk context → fact stored as restricted_profile
    payload_one = SessionSummaryPayload(
        session_id=session_one.id,
        telegram_user_id=7016,
        reflective_mode="deep",
        source_turn_count=3,
        prior_context="Мне страшно, после насилия дома.",
        latest_user_message="Я не знаю, как дальше жить.",
        takeaway="В сессии звучала тема насилия и очень сложная личная ситуация.",
        next_steps=[],
        allowed_profile_facts=[
            ProfileFactInput(
                fact_key="relationship_context",
                fact_value="Пользователь переживает насилие в близких отношениях.",
                confidence="high",
            )
        ],
    )
    persist_session_summary(payload_one, build_session_summary(payload_one))

    facts_after_s1 = db.exec(
        select(ProfileFact).where(ProfileFact.telegram_user_id == 7016)
    ).all()
    assert len(facts_after_s1) == 1
    assert facts_after_s1[0].retention_scope == "restricted_profile"

    # Session two: neutral context, same fact key — restricted scope must survive
    payload_two = SessionSummaryPayload(
        session_id=session_two.id,
        telegram_user_id=7016,
        reflective_mode="fast",
        source_turn_count=2,
        prior_context="Мы снова говорим об отношениях.",
        latest_user_message="Мне важно чувствовать поддержку.",
        takeaway="Пользователю важна поддержка в отношениях.",
        next_steps=[],
        allowed_profile_facts=[
            ProfileFactInput(
                fact_key="relationship_context",
                fact_value="Напряжение связано с близкими отношениями.",
                confidence="high",
            )
        ],
    )
    persist_session_summary(payload_two, build_session_summary(payload_two))

    facts_after_s2 = db.exec(
        select(ProfileFact).where(ProfileFact.telegram_user_id == 7016)
    ).all()
    assert len(facts_after_s2) == 1
    assert facts_after_s2[0].retention_scope == "restricted_profile", (
        "restricted_profile scope must not be upgraded to durable_profile by a later session"
    )

    recall = get_session_recall_context(db, telegram_user_id=7016)
    assert recall is not None
    assert recall.profile_facts == []


def test_persist_session_summary_failure_records_retry_payload_without_duplicates(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("90864098-50b9-528e-98ef-cd7266ed8aa8"),
        telegram_user_id=7107,
        chat_id=8107,
        working_context="Временный контекст",
        last_user_message="Сырой текст",
        last_bot_prompt="Последний ответ",
    )
    db.add(session_record)
    db.commit()

    payload = SessionSummaryPayload(
        session_id=session_record.id,
        telegram_user_id=7107,
        reflective_mode="deep",
        source_turn_count=3,
        prior_context="Есть повторяющийся конфликт.",
        latest_user_message="Мне больно, когда меня игнорируют.",
        takeaway="Похоже, ключевой узел связан с переживанием игнорирования.",
        next_steps=["1. Замечать момент, где игнорирование ощущается сильнее всего."],
        allowed_profile_facts=[
            ProfileFactInput(
                fact_key="support_preference",
                fact_value="Пользователю важен спокойный и уважительный тон разговора.",
            )
        ],
    )

    def _raise_commit(_session: Session) -> None:
        raise RuntimeError("db is down")

    monkeypatch.setattr("app.memory.service._commit_memory_transaction", _raise_commit)

    from app.memory.service import generate_and_persist_session_summary

    generate_and_persist_session_summary(payload)
    generate_and_persist_session_summary(payload)

    signals = db.exec(
        select(SummaryGenerationSignal).where(
            SummaryGenerationSignal.session_id == session_record.id
        )
    ).all()
    assert len(signals) == 1
    assert signals[0].attempt_count == 2
    assert signals[0].retryable is True
    assert signals[0].details["suggested_action"] == "retry_session_memory_persistence"
    assert "summary_draft" in signals[0].retry_payload
    assert signals[0].retry_payload["summary_draft"]["takeaway"] == payload.takeaway

    db.expire_all()
    refreshed_session = db.exec(
        select(TelegramSession).where(TelegramSession.id == session_record.id)
    ).one()
    assert refreshed_session.last_user_message is None
    assert refreshed_session.working_context is None

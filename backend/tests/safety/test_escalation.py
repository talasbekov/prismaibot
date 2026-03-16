import pytest

from app.safety.escalation import (
    CrisisMessagingValidationError,
    compose_crisis_routing_response,
    compose_crisis_step_down_response,
)


def test_compose_crisis_routing_response_for_new_activation_is_not_reflective() -> None:
    response = compose_crisis_routing_response(
        newly_activated=True,
        safety_classification="crisis",
        safety_confidence="high",
    )

    assert response.action == "crisis_routed"
    assert len(response.messages) == 2
    combined = " ".join(response.messages).lower()
    assert "очень тяжело" in combined
    assert "обычного разбора" in combined
    assert "недостаточно" in combined
    assert "позвони" in combined
    assert "что здесь больнее" not in combined
    assert "?" not in combined
    assert response.resources
    assert response.inline_buttons


def test_compose_crisis_routing_response_for_existing_crisis_state_stays_bounded() -> None:
    response = compose_crisis_routing_response(
        newly_activated=False,
        safety_classification="crisis",
        safety_confidence="high",
    )

    assert response.action == "crisis_routed"
    assert len(response.messages) == 1
    message = response.messages[0].lower()
    assert "серьезного риска" in message
    assert "обычный разбор" in message
    assert "недостаточно" in message
    assert "сейчас лучше" in message
    assert "диагноз" not in message
    assert response.resources
    assert response.inline_buttons


def test_existing_crisis_state_with_non_crisis_signal_uses_softer_variant() -> None:
    response = compose_crisis_routing_response(
        newly_activated=False,
        safety_classification="safe",
        safety_confidence="low",
    )

    assert response.action == "crisis_routed"
    assert len(response.messages) == 1
    message = response.messages[0].lower()
    assert "чувствительным" in message
    assert "обычного разбора" in message
    assert "сейчас недостаточно" in message
    assert "серьезного риска" not in message
    assert "?" not in message
    assert response.resources


def test_existing_crisis_state_with_borderline_signal_uses_softer_variant() -> None:
    """Borderline/medium is the actual ambiguous case described in AC5."""
    response = compose_crisis_routing_response(
        newly_activated=False,
        safety_classification="borderline",
        safety_confidence="medium",
    )

    assert response.action == "crisis_routed"
    assert len(response.messages) == 1
    message = response.messages[0].lower()
    assert "чувствительным" in message
    assert "обычного разбора" in message
    assert "сейчас недостаточно" in message
    assert "серьезного риска" not in message
    assert "?" not in message
    assert response.resources


def test_compose_crisis_routing_response_rejects_missing_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.safety.escalation.get_curated_crisis_resources",
        lambda: (),
    )

    with pytest.raises(CrisisMessagingValidationError):
        compose_crisis_routing_response(
            newly_activated=True,
            safety_classification="crisis",
            safety_confidence="high",
        )


def test_compose_crisis_routing_response_rejects_disallowed_unsafe_phrasing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.safety.escalation._MESSAGE_VARIANTS",
        {
            "high_concern_activation": (
                "Я не могу помочь с этим.",
                "Тебе нужен диагноз и срочная терапия.",
            ),
            "high_concern_continuation": (
                "Я не могу помочь с этим.",
            ),
            "soft_continuation": (
                "Я не могу помочь с этим.",
            ),
        },
    )

    with pytest.raises(CrisisMessagingValidationError):
        compose_crisis_routing_response(
            newly_activated=True,
            safety_classification="crisis",
            safety_confidence="high",
        )


def test_compose_crisis_step_down_response_stays_calm_and_bridges_back() -> None:
    response = compose_crisis_step_down_response()

    assert response.action == "crisis_step_down"
    assert len(response.messages) == 2
    combined = " ".join(response.messages).lower()
    assert "слишком резко" in combined
    assert "осторожно" in combined
    assert "можем вернуться" in combined
    assert "обычного разбора" not in combined
    assert "диагноз" not in combined
    assert "?" in response.messages[-1]


def test_compose_crisis_step_down_response_rejects_defensive_phrasing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.safety.escalation._STEP_DOWN_MESSAGES",
        (
            "Это была ошибка системы.",
            "Давай просто вернемся назад.",
        ),
    )

    with pytest.raises(CrisisMessagingValidationError):
        compose_crisis_step_down_response()

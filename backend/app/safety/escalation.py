from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.safety.crisis_links import (
    MAX_CRISIS_RESOURCE_COUNT,
    CrisisResource,
    get_curated_crisis_resources,
)

CrisisClassification = Literal["safe", "borderline", "crisis"]
CrisisConfidence = Literal["low", "medium", "high"]
CrisisVariant = Literal[
    "high_concern_activation",
    "high_concern_continuation",
    "soft_continuation",
]

_MESSAGE_VARIANTS: dict[CrisisVariant, tuple[str, ...]] = {
    "high_concern_activation": (
        "Похоже, тебе сейчас правда очень тяжело, и я хочу отнестись к этому серьезно и бережно.",
        "Обычного разбора здесь сейчас недостаточно. В качестве более безопасного следующего шага позвони в срочную кризисную линию прямо сейчас или попроси живого человека побыть рядом.",
    ),
    "high_concern_continuation": (
        "Я все еще вижу признаки серьезного риска, поэтому не продолжаю обычный разбор. Такого формата сейчас недостаточно, и в качестве более безопасного следующего шага сейчас лучше сразу позвонить в кризисную линию или позвать живого человека рядом.",
    ),
    "soft_continuation": (
        "Я все равно удержу разговор в более осторожном режиме, потому что ситуация остается чувствительным моментом. Обычного разбора сейчас недостаточно, и в качестве более безопасного следующего шага лучше выбери кризисную поддержку ниже или позови живого человека рядом.",
    ),
}

_SERIOUSNESS_MARKERS = (
    "тяжело",
    "риска",
    "чувствительным",
    "осторожном",
)
_NEXT_STEP_MARKERS = (
    "следующего шага",  # all three variants use this genitive form
)
_DISALLOWED_PHRASES = (
    "я не могу помочь",
    "я не могу с этим помочь",
    "диагноз",
    "терап",
    "расстройств",
    "синдром",
    "обратитесь к врачу",
    "юрид",
)
_STEP_DOWN_DISALLOWED_PHRASES = _DISALLOWED_PHRASES + (
    "ошибка системы",
    "это была ошибка",
)
_MAX_MESSAGE_LENGTH = 280
_MAX_TOTAL_MESSAGE_LENGTH = 420
_STEP_DOWN_MESSAGES: tuple[str, ...] = (
    "Похоже, я мог слишком резко удержать это как кризисный сигнал, и не хочу давить этой рамкой сильнее, чем нужно.",
    "Давай останемся осторожно внимательными и можем вернуться к самому эпизоду: что в нем задело тебя сильнее всего прямо сейчас?",
)


class CrisisMessagingValidationError(ValueError):
    """Raised when crisis escalation copy is unsafe or structurally invalid."""


@dataclass(frozen=True)
class CrisisRoutingResponse:
    messages: tuple[str, ...]
    resources: tuple[CrisisResource, ...]
    inline_buttons: tuple[tuple[str, str], ...]
    action: str = "crisis_routed"


@dataclass(frozen=True)
class CrisisStepDownResponse:
    messages: tuple[str, ...]
    action: str = "crisis_step_down"


def compose_crisis_routing_response(
    *,
    newly_activated: bool,
    safety_classification: CrisisClassification,
    safety_confidence: CrisisConfidence,
) -> CrisisRoutingResponse:
    variant = _select_variant(
        newly_activated=newly_activated,
        safety_classification=safety_classification,
        safety_confidence=safety_confidence,
    )
    resources = get_curated_crisis_resources()
    response = CrisisRoutingResponse(
        messages=_MESSAGE_VARIANTS[variant],
        resources=resources,
        inline_buttons=tuple((resource.label, resource.url) for resource in resources),
    )
    _validate_response(response)
    return response


def compose_crisis_step_down_response() -> CrisisStepDownResponse:
    response = CrisisStepDownResponse(messages=_STEP_DOWN_MESSAGES)
    _validate_step_down_response(response)
    return response


def _select_variant(
    *,
    newly_activated: bool,
    safety_classification: CrisisClassification,
    safety_confidence: CrisisConfidence,
) -> CrisisVariant:
    if newly_activated:
        return "high_concern_activation"

    if safety_classification == "crisis" and safety_confidence == "high":
        return "high_concern_continuation"

    return "soft_continuation"


def _validate_response(response: CrisisRoutingResponse) -> None:
    if not response.messages:
        raise CrisisMessagingValidationError("Crisis response must include at least one message.")
    if not response.resources:
        raise CrisisMessagingValidationError("Crisis response must include approved crisis resources.")
    if not response.inline_buttons:
        raise CrisisMessagingValidationError("Crisis response must include crisis action buttons.")
    if len(response.resources) > MAX_CRISIS_RESOURCE_COUNT or len(response.inline_buttons) > MAX_CRISIS_RESOURCE_COUNT:
        raise CrisisMessagingValidationError("Crisis response resources must stay bounded.")

    total_length = 0
    combined = " ".join(response.messages).casefold()
    if "недостаточно" not in combined:
        raise CrisisMessagingValidationError("Crisis response must explain product boundary.")
    if "обычного разбора" not in combined and "обычный разбор" not in combined:
        raise CrisisMessagingValidationError("Crisis response must stop normal reflective flow.")

    first_message_lower = response.messages[0].casefold()
    if not any(marker in first_message_lower for marker in _SERIOUSNESS_MARKERS):
        raise CrisisMessagingValidationError(
            "Crisis response must acknowledge seriousness in the first message."
        )

    for message in response.messages:
        stripped = message.strip()
        if not stripped:
            raise CrisisMessagingValidationError("Crisis response cannot include blank messages.")
        if stripped.endswith("?"):
            raise CrisisMessagingValidationError("Crisis response must not end with a question.")
        if len(stripped) > _MAX_MESSAGE_LENGTH:
            raise CrisisMessagingValidationError("Crisis response exceeds Telegram readability budget.")
        total_length += len(stripped)

    if total_length > _MAX_TOTAL_MESSAGE_LENGTH:
        raise CrisisMessagingValidationError("Crisis response is too long for a bounded escalation reply.")

    if not any(marker in combined for marker in _NEXT_STEP_MARKERS):
        raise CrisisMessagingValidationError("Crisis response must steer toward a safer next step.")

    if any(phrase in combined for phrase in _DISALLOWED_PHRASES):
        raise CrisisMessagingValidationError("Crisis response contains disallowed unsafe phrasing.")

    # H1: verify every resource has a matching button AND every button points to an approved resource
    button_label_by_url = {url: label for label, url in response.inline_buttons}
    resource_urls = {resource.url for resource in response.resources}
    for resource in response.resources:
        if resource.url not in button_label_by_url:
            raise CrisisMessagingValidationError(
                "Crisis response must expose each approved resource via button."
            )
        if button_label_by_url[resource.url] != resource.label:
            raise CrisisMessagingValidationError(
                "Crisis response button label must match the approved resource label."
            )
    for _, url in response.inline_buttons:
        if url not in resource_urls:
            raise CrisisMessagingValidationError(
                "Crisis response must not expose buttons to non-approved resource URLs."
            )


def _validate_step_down_response(response: CrisisStepDownResponse) -> None:
    if len(response.messages) < 2:
        raise CrisisMessagingValidationError(
            "Crisis step-down response must include acknowledgement and bridge copy."
        )

    combined = " ".join(response.messages).casefold()
    if "слишком резко" not in combined:
        raise CrisisMessagingValidationError(
            "Crisis step-down response must acknowledge over-strong framing."
        )
    if "осторож" not in combined:
        raise CrisisMessagingValidationError(
            "Crisis step-down response must preserve cautious tone."
        )
    if "можем вернуться" not in combined:
        raise CrisisMessagingValidationError(
            "Crisis step-down response must bridge back into the reflective flow."
        )
    if any(phrase in combined for phrase in _STEP_DOWN_DISALLOWED_PHRASES):
        raise CrisisMessagingValidationError(
            "Crisis step-down response contains disallowed defensive phrasing."
        )

    total_length = 0
    for index, message in enumerate(response.messages):
        stripped = message.strip()
        if not stripped:
            raise CrisisMessagingValidationError(
                "Crisis step-down response cannot include blank messages."
            )
        if len(stripped) > _MAX_MESSAGE_LENGTH:
            raise CrisisMessagingValidationError(
                "Crisis step-down response exceeds Telegram readability budget."
            )
        if index == 0 and stripped.endswith("?"):
            raise CrisisMessagingValidationError(
                "Crisis step-down acknowledgement must not end with a question."
            )
        total_length += len(stripped)

    if not response.messages[-1].strip().endswith("?"):
        raise CrisisMessagingValidationError(
            "Crisis step-down bridge must end with a single focused question."
        )
    if total_length > _MAX_TOTAL_MESSAGE_LENGTH:
        raise CrisisMessagingValidationError(
            "Crisis step-down response is too long for a bounded recovery reply."
        )

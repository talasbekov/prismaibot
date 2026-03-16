import pytest

from app.conversation.first_response import (
    compose_first_trust_response,
    compose_first_trust_response_with_memory,
)


def test_compose_first_trust_response_extracts_situation_and_emotion() -> None:
    response = compose_first_trust_response(
        "Мы с мужем снова поссорились, и мне обидно, что он меня не слышит."
    )

    assert response.action == "first_trust_response"
    assert len(response.messages) == 2
    assert "муж" in response.messages[0]
    assert "обидно" in response.messages[0]
    assert response.messages[0].startswith("Похоже,")


def test_compose_first_trust_response_low_confidence_is_tentative() -> None:
    response = compose_first_trust_response("Не знаю, все сложно.")

    assert response.action == "first_trust_response"
    assert len(response.messages) == 2
    assert "не хочу делать вид" in " ".join(response.messages)
    assert sum(message.count("?") for message in response.messages) == 1


# ------- Negation detection -------


def test_negated_emotion_is_skipped() -> None:
    """'не обидно' must NOT produce 'обидно' — the user denied that emotion."""
    response = compose_first_trust_response(
        "Мне не обидно из-за ссоры, просто злит, что всё повторяется."
    )

    combined = " ".join(response.messages)
    assert "обидно" not in combined
    assert "злит" in combined


def test_double_negation_does_not_misfire() -> None:
    """'уже не страшно' must not produce 'страшно'."""
    response = compose_first_trust_response(
        "Мне уже не страшно из-за работы, просто устала от неопределённости."
    )

    combined = " ".join(response.messages)
    assert "страшно" not in combined
    assert "выматывает" in combined


# ------- Grammar correctness -------


@pytest.mark.parametrize(
    "text, bad_fragment",
    [
        (
            "Поругались с мужем, мне обидно что он так поступил.",
            "тебя это правда обидно",
        ),
        (
            "Ситуация на работе, мне страшно идти на совещание.",
            "тебя это правда страшно",
        ),
        (
            "Конфликт с семьёй, мне стыдно за свою реакцию.",
            "тебя это правда стыдно",
        ),
        (
            "Поссорились с мужем, мне тяжело это переживать.",
            "тебя это правда тяжело",
        ),
    ],
)
def test_dative_emotions_use_correct_grammar(text: str, bad_fragment: str) -> None:
    """Short predicative adjectives must use 'тебе', not 'тебя'."""
    response = compose_first_trust_response(text)
    combined = " ".join(response.messages)
    assert bad_fragment not in combined


# ------- Low-confidence boundary -------


def test_message_without_situation_marker_is_not_low_confidence_when_long() -> None:
    """A clear 8+ word message without a situation keyword must NOT fall to low-confidence."""
    response = compose_first_trust_response(
        "Мне страшно думать о будущем и я не знаю куда двигаться дальше."
    )

    # Should use the normal reflective path, not the tentative low-confidence one.
    combined = " ".join(response.messages)
    assert "не хочу делать вид" not in combined


def test_short_message_with_situation_marker_is_low_confidence() -> None:
    """Even with a situation keyword, fewer than 8 words triggers low-confidence."""
    response = compose_first_trust_response("Ссора с мужем.")

    combined = " ".join(response.messages)
    assert "не хочу делать вид" in combined


# ------- Immutability -------


def test_first_trust_response_messages_are_immutable() -> None:
    """messages must be a tuple, not a mutable list."""
    response = compose_first_trust_response(
        "Мы с мужем поссорились и мне обидно что он меня не слышит."
    )
    assert isinstance(response.messages, tuple)


def test_memory_recall_is_surfaced_tentatively_when_context_is_relevant() -> None:
    response = compose_first_trust_response_with_memory(
        "Мы опять поссорились, и мне обидно, что меня не слышат.",
        prior_memory_context=(
            "Последняя сессия показала, что пользователя особенно задевает "
            "повторяющийся паттерн конфликта."
        ),
    )

    combined = " ".join(response.messages).lower()
    assert "могу ошибаться" in combined
    assert "знакомый" in combined or "уже не первый раз" in combined
    assert "я точно знаю" not in combined


def test_memory_recall_stays_internal_when_context_confidence_is_weak() -> None:
    response = compose_first_trust_response_with_memory(
        "Мы опять поссорились, и мне обидно, что меня не слышат.",
        prior_memory_context=(
            "Не до конца ясно, повторяется ли этот паттерн, "
            "и часть прежних выводов остается условной."
        ),
    )

    combined = " ".join(response.messages).lower()
    assert "могу ошибаться" not in combined
    assert "знакомый" not in combined
    assert "снова поднимается" not in combined


# ------- Work / partner situations -------


def test_work_conflict_situation_extraction() -> None:
    response = compose_first_trust_response(
        "Поругался с коллегой на работе, и мне обидно, что никто не вступился."
    )
    assert "работ" in response.messages[0].lower()


def test_partner_situation_extraction() -> None:
    response = compose_first_trust_response(
        "Мой парень сказал что-то обидное, и я не знаю как реагировать."
    )
    # Should route through low-confidence due to "что-то" marker,
    # which is correct — "что-то" signals vagueness.
    combined = " ".join(response.messages)
    assert "не хочу делать вид" in combined

from app.conversation.closure import compose_session_closure


def test_compose_session_closure_returns_takeaway_and_bounded_next_steps() -> None:
    response = compose_session_closure(
        latest_user_message=(
            "Наверное, мне больнее всего, что он даже не попытался понять, "
            "почему меня это задело."
        ),
        prior_context=(
            "Мы с мужем снова поссорились. Факт в том, что он перебил меня. "
            "По ощущениям мне обидно и тревожно."
        ),
        reflective_mode="deep",
    )

    assert response.action == "session_closure"
    assert len(response.messages) == 2
    assert response.messages[0].startswith("Если подвести это к ясной точке,")
    assert 1 <= len(response.next_steps) <= 3
    assert response.messages[1].count("\n") >= 1
    # Regression: deep mode must not produce wall-of-text (Telegram readability)
    assert max(len(message) for message in response.messages) < 500


def test_compose_session_closure_fast_mode_stays_compact() -> None:
    response = compose_session_closure(
        latest_user_message="Мне скорее обидно, чем хочется дальше это раскручивать.",
        prior_context=(
            "Мы поссорились с партнером. Факт в том, что он оборвал разговор. "
            "По ощущениям мне обидно."
        ),
        reflective_mode="fast",
    )

    assert response.action == "session_closure"
    assert len(response.next_steps) <= 2
    assert max(len(message) for message in response.messages) < 280


def test_compose_session_closure_fast_low_confidence_returns_single_step() -> None:
    response = compose_session_closure(
        latest_user_message="Не знаю, наверное это просто сложно объяснить.",
        prior_context="Что-то произошло, но я не до конца понимаю что.",
        reflective_mode="fast",
    )

    assert response.action == "session_closure"
    # fast + low_confidence: exactly 1 step (compact, low-burden)
    assert len(response.next_steps) == 1
    # Must stay compact for fast mode
    assert max(len(message) for message in response.messages) < 280
    # Closure must not end with an open question
    assert not response.messages[-1].rstrip().endswith("?")


def test_compose_session_closure_low_confidence_admits_uncertainty() -> None:
    response = compose_session_closure(
        latest_user_message="Не уверена, что вообще правильно это поняла.",
        prior_context="Все еще сложно понять, это была обида или просто усталость.",
        reflective_mode="deep",
    )

    combined = " ".join(response.messages).lower()
    assert "не до конца ясно" in combined
    assert 1 <= len(response.next_steps) <= 3
    assert any("не делать резких выводов" in step.lower() for step in response.next_steps)

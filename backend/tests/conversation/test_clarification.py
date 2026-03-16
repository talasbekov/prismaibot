from app.conversation.clarification import compose_clarification_response


def test_compose_clarification_response_builds_structured_breakdown() -> None:
    response = compose_clarification_response(
        latest_user_message=(
            "Он снова перебил меня на совещании, мне обидно, и я думаю, "
            "что, может, я правда перегнула."
        ),
        prior_context="Мы уже ссорились из-за похожих моментов.",
        reflective_mode="deep",
    )

    combined = " ".join(response.messages)
    assert response.action == "clarification_turn"
    assert "факт" in combined
    assert "по ощущениям" in combined
    assert "интерпретации" in combined
    assert sum(message.count("?") for message in response.messages) == 1


def test_compose_clarification_response_boundary_for_general_request() -> None:
    response = compose_clarification_response(
        latest_user_message="Напиши код калькулятора на python.",
        prior_context="Мне было тяжело после разговора.",
        reflective_mode="deep",
    )

    assert response.action == "clarification_boundary"
    assert "общего помощника" in response.messages[0]


def test_compose_clarification_response_keeps_work_context_in_scope() -> None:
    response = compose_clarification_response(
        latest_user_message=(
            "На работе начальник снова перебил меня, и мне обидно, "
            "что это выглядит как обесценивание."
        ),
        prior_context=None,
        reflective_mode="fast",
    )

    assert response.action == "clarification_turn"
    assert "работе" in response.messages[0]
    assert "один главный узел" in response.messages[1]


def test_compose_clarification_response_deep_mode_goes_one_layer_deeper() -> None:
    response = compose_clarification_response(
        latest_user_message=(
            "Он снова перебил меня на встрече, мне обидно, и я начинаю думать, "
            "что для него мои слова ничего не значат."
        ),
        prior_context="Мы уже возвращаемся к похожему напряжению.",
        reflective_mode="deep",
    )

    assert response.action == "clarification_turn"
    assert "Если пойти на слой глубже" in response.messages[1]
    assert response.messages[1].count("?") == 1


def test_compose_clarification_response_handles_vague_contradictory_input_gently() -> None:
    response = compose_clarification_response(
        latest_user_message=(
            "Я как будто и злюсь, и уже не понимаю, права ли я вообще, "
            "но все как-то смешалось."
        ),
        prior_context="Мы снова вернулись к этому разговору.",
        reflective_mode="deep",
    )

    combined = " ".join(response.messages)
    assert response.action == "clarification_turn"
    assert "не хочу делать слишком уверенные выводы" in combined or "ещё не до конца сложилась" in combined
    assert combined.count("?") == 1


def test_compose_clarification_response_keeps_technology_context_when_it_is_lived_situation() -> None:
    response = compose_clarification_response(
        latest_user_message=(
            "У нас конфликт из-за технологического проекта: начальник снова перебил меня, "
            "и мне обидно, что мой вклад как будто обнулили."
        ),
        prior_context=None,
        reflective_mode="deep",
    )

    assert response.action == "clarification_turn"
    assert "технологическая тема стала частью живой ситуации" in response.messages[0]

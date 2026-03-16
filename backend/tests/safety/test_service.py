from app.safety import assess_message_safety


def test_assess_message_safety_flags_explicit_self_harm_as_crisis() -> None:
    assessment = assess_message_safety(
        "Я хочу покончить с собой и не вижу смысла жить дальше."
    )

    assert assessment.classification == "crisis"
    assert assessment.trigger_category == "self_harm"
    assert assessment.confidence == "high"
    assert assessment.blocks_normal_flow is True


def test_assess_message_safety_keeps_ordinary_conflict_out_of_crisis() -> None:
    assessment = assess_message_safety(
        "Мы сильно поссорились, мне очень больно и обидно, но я просто не понимаю, как теперь говорить."
    )

    assert assessment.classification == "safe"
    assert assessment.trigger_category == "none"
    assert assessment.blocks_normal_flow is False


def test_assess_message_safety_marks_borderline_ambiguous_risk() -> None:
    assessment = assess_message_safety(
        "Иногда кажется, что лучше бы просто исчезнуть и никому не мешать."
    )

    assert assessment.classification == "borderline"
    assert assessment.trigger_category == "self_harm"
    assert assessment.confidence == "medium"
    assert assessment.blocks_normal_flow is False


def test_assess_message_safety_flags_dangerous_abuse_as_crisis() -> None:
    assessment = assess_message_safety(
        "Он запер меня дома, ударил и сказал, что убьет, если я кому-то расскажу."
    )

    assert assessment.classification == "crisis"
    assert assessment.trigger_category == "dangerous_abuse"
    assert assessment.confidence == "high"
    assert assessment.blocks_normal_flow is True


def test_assess_message_safety_flags_sexual_violence_as_crisis_without_personal_markers() -> None:
    assessment = assess_message_safety(
        "Меня насиловали, я не знаю, как об этом говорить."
    )

    assert assessment.classification == "crisis"
    assert assessment.trigger_category == "dangerous_abuse"
    assert assessment.confidence == "high"
    assert assessment.blocks_normal_flow is True


def test_assess_message_safety_flags_conjugated_self_harm_as_crisis() -> None:
    assessment = assess_message_safety(
        "Я покончу с собой, если это не закончится."
    )

    assert assessment.classification == "crisis"
    assert assessment.trigger_category == "self_harm"
    assert assessment.confidence == "high"
    assert assessment.blocks_normal_flow is True


def test_assess_message_safety_keeps_stress_idiom_out_of_crisis() -> None:
    assessment = assess_message_safety(
        "Он ударил по столу сейчас в злости, я была в шоке."
    )

    assert assessment.classification == "safe"
    assert assessment.blocks_normal_flow is False

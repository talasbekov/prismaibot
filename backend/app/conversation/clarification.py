from __future__ import annotations

import logging
from dataclasses import dataclass

from app.conversation._text_utils import normalize_spaces

logger = logging.getLogger(__name__)

BOUNDARY_REQUEST_MARKERS = (
    "напиши код",
    "сделай код",
    "переведи",
    "какой ноутбук",
    "какой телефон",
    "какая погода",
    "рецепт",
    "реши задачу",
    "подбери ноутбук",
)

CONTEXTUAL_LIFE_MARKERS = (
    "муж",
    "жена",
    "партнер",
    "парень",
    "девуш",
    "коллег",
    "работ",
    "началь",
    "совещ",
    "деньг",
    "бизнес",
    "проект",
    "технолог",
    "продукт",
    "команд",
    "увольн",
    "зарплат",
    "кредит",
)

FACT_MARKERS: tuple[tuple[str, str], ...] = (
    ("ссор", "между вами уже был конфликт"),
    ("поруг", "между вами уже был конфликт"),
    ("муж", "это связано с мужем"),
    ("коллег", "это связано с коллегой"),
    ("не отвеч", "человек не отвечает так, как тебе нужно"),
    ("перебил", "тебя перебили"),
    ("ушел", "человек резко оборвал контакт"),
    ("деньг", "деньги тоже стали частью напряжения"),
)

EMOTION_MARKERS: tuple[tuple[str, str], ...] = (
    ("обид", "тебе обидно"),
    ("злит", "это тебя злит"),
    ("бесит", "это тебя бесит"),
    ("страш", "тебе страшно"),
    ("трев", "тебе тревожно"),
    ("стыд", "тебе стыдно"),
    ("вина", "есть чувство вины"),
    ("виноват", "есть чувство вины"),
    ("больно", "тебе больно"),
    ("тяжел", "тебе тяжело"),
    ("не слыш", "ты переживаешь это как неуслышанность"),
    ("устал", "это напряжение тебя явно уже изматывает"),
)

INTERPRETATION_MARKERS: tuple[tuple[str, str], ...] = (
    ("я перегнула", "ты допускаешь, что, возможно, слишком резко на это смотришь"),
    ("может", "ты пока пытаешься понять, как это правильно интерпретировать"),
    ("не понимаю", "ты ещё не уверена, что именно это значит"),
    ("как будто", "часть напряжения сейчас строится на том, как это для тебя прозвучало"),
    ("игнор", "это легко переживается как игнор или обесценивание"),
    ("обесцен", "ты считываешь это как обесценивание"),
    ("значит", "ты пытаешься уловить, что это говорит о ваших отношениях или о тебе"),
)

LOW_CONFIDENCE_MARKERS = (
    "не знаю",
    "все сложно",
    "запут",
    "не понимаю",
    "как-то",
    "что-то",
    "не увер",
    "не до конца",
)

CONTRADICTION_MARKERS = (
    "но",
    "хотя",
    "с другой стороны",
    "и одновременно",
)

MEMORY_RECALL_MARKERS = (
    "повтор",
    "паттерн",
    "знаком",
    "в прошлой сессии",
)

MEMORY_CORRECTION_MARKERS = (
    "нет,",
    "нет ",
    "нет!",
    "не про",
    "не из-за",
    "не в этом",
    "сейчас не",
    "в этот раз",
    "на этот раз",
    "дело не",
    "это не",
)


@dataclass(frozen=True)
class ClarificationResponse:
    messages: tuple[str, ...]
    action: str
    updated_context: str


@dataclass(frozen=True)
class ClarificationSignals:
    fact: str
    emotion: str
    interpretation: str
    fact_confident: bool
    emotion_confident: bool
    interpretation_confident: bool


_CLARIFICATION_SYSTEM = """\
Ты — эмпатичный собеседник-бот «Prism AI». Ведёшь рефлексивный диалог \
на русском языке, помогая пользователю глубже понять свои переживания.

Правила:
- Говори тепло и кратко: 1–2 предложения на сообщение.
- Задавай ровно один вопрос — в конце второго сообщения.
- Опирайся на историю разговора из [Контекст].
- Отражай, не интерпретируй и не советуй.
- НЕ используй слова «я понимаю», «конечно», «безусловно».

Оформление:
- Начинай первый абзац с 💬, второй (вопрос) — с 🤔.
- Используй *жирный* для ключевых фраз и _курсив_ для эмоциональных акцентов.
- Ответ — ровно два абзаца, разделённых строкой «---» (без кавычек).
  Первый абзац: что ты слышишь (синтез факта и эмоции).
  Второй абзац: один уточняющий вопрос.\
"""

_CLARIFICATION_SYSTEM_FAST = _CLARIFICATION_SYSTEM + (
    "\n- Режим: краткий (fast) — ответы лаконичны и практичны."
)
_CLARIFICATION_SYSTEM_DEEP = _CLARIFICATION_SYSTEM + (
    "\n- Режим: глубокий (deep) — исследуй нюансы переживания."
)


def _try_openai_clarification(
    latest_user_message: str,
    prior_context: str | None,
    reflective_mode: str,
) -> ClarificationResponse | None:
    from app.conversation._openai import call_chat, parse_two_messages

    system = (
        _CLARIFICATION_SYSTEM_FAST
        if reflective_mode == "fast"
        else _CLARIFICATION_SYSTEM_DEEP
    )
    messages: list[dict] = [{"role": "system", "content": system}]
    if prior_context:
        messages.append(
            {"role": "assistant", "content": f"[Контекст разговора: {prior_context}]"}
        )
    messages.append({"role": "user", "content": latest_user_message})

    raw = call_chat(messages, max_tokens=350)
    if raw is None:
        return None
    parsed = parse_two_messages(raw)
    if parsed is None:
        logger.warning("OpenAI clarification: unexpected format, falling back")
        return None

    # Build updated_context by appending the latest message
    prior = prior_context or ""
    updated = (f"{prior} {latest_user_message}").strip()
    if len(updated) > 2000:
        updated = updated[-2000:]

    return ClarificationResponse(
        messages=parsed,
        action="clarification_turn",
        updated_context=updated,
    )


def compose_clarification_response(
    *,
    latest_user_message: str,
    prior_context: str | None,
    reflective_mode: str,
    prior_memory_context: str | None = None,
) -> ClarificationResponse:
    openai_result = _try_openai_clarification(
        latest_user_message, prior_context, reflective_mode
    )
    if openai_result is not None:
        return openai_result

    normalized = normalize_spaces(latest_user_message)
    combined_context = _build_context(
        prior_context,
        normalized,
        prior_memory_context=prior_memory_context,
    )
    lowered = normalized.lower()
    combined_lowered = combined_context.lower()

    if _is_boundary_request(lowered):
        return ClarificationResponse(
            action="clarification_boundary",
            messages=(
                "💬 Я не хочу уходить в режим общего помощника, если тебе сейчас важнее разобраться в самой ситуации.",
                "🤔 Если хочешь, можем вернуться к тому, что именно в этом для тебя самое напряжённое.",
            ),
            updated_context=combined_context,
        )

    if _is_memory_correction(latest_text=lowered, prior_context=prior_context):
        return ClarificationResponse(
            action="clarification_turn",
            messages=(
                "💬 Понял, беру это как текущую рамку и не хочу цепляться за прошлую версию ситуации.",
                f"🤔 {_build_correction_follow_up(reflective_mode)}",
            ),
            updated_context=normalized[:2000],
        )

    signals = _extract_signals(combined_lowered)
    low_confidence = _is_low_confidence(
        latest_text=lowered,
        _combined_text=combined_lowered,
        signals=signals,
    )
    if low_confidence:
        return ClarificationResponse(
            action="clarification_turn",
            messages=(
                f"💬 {_build_low_confidence_reflection(signals=signals)}",
                f"🤔 {_build_follow_up_question(reflective_mode, low_confidence=True, signals=signals)}",
            ),
            updated_context=combined_context,
        )

    synthesis = (
        f"💬 Если аккуратно разложить это, то факт здесь в том, что {signals.fact}, "
        f"по ощущениям — {signals.emotion}, а в интерпретации сейчас звучит, что {signals.interpretation}."
    )
    return ClarificationResponse(
        action="clarification_turn",
        messages=(
            synthesis,
            f"🤔 {_build_follow_up_question(reflective_mode, low_confidence=False, signals=signals)}",
        ),
        updated_context=combined_context,
    )


def _build_context(
    prior_context: str | None,
    latest_user_message: str,
    *,
    prior_memory_context: str | None = None,
) -> str:
    combined_prior = normalize_spaces(
        " ".join(part for part in (prior_memory_context, prior_context) if part)
    )
    if not combined_prior:
        return latest_user_message[:2000]
    merged = f"{combined_prior} {latest_user_message}"
    if len(merged) <= 2000:
        return merged
    # When combined exceeds the limit, prioritise the latest message and trim
    # the older prior context from the start rather than losing the newest input.
    if len(latest_user_message) <= 2000:
        available = 2000 - len(latest_user_message) - 1
        trimmed_prior = combined_prior[-available:] if available > 0 else ""
        # Advance to the first word boundary so the trimmed prefix does not
        # start mid-word when the character slice falls inside a word.
        if trimmed_prior and " " in trimmed_prior:
            trimmed_prior = trimmed_prior[trimmed_prior.index(" ") + 1:]
        return f"{trimmed_prior} {latest_user_message}".strip()
    return latest_user_message[:2000]


def _is_boundary_request(text: str) -> bool:
    if not any(marker in text for marker in BOUNDARY_REQUEST_MARKERS):
        return False
    return not any(marker in text for marker in CONTEXTUAL_LIFE_MARKERS)


def _extract_signals(text: str) -> ClarificationSignals:
    fact, fact_confident = _extract_fact_phrase(text)
    emotion, emotion_confident = _extract_phrase(
        text,
        EMOTION_MARKERS,
        "тебя это задевает эмоционально",
    )
    interpretation, interpretation_confident = _extract_phrase(
        text,
        INTERPRETATION_MARKERS,
        "ты всё ещё пытаешься понять, как это правильно для себя объяснить",
    )
    return ClarificationSignals(
        fact=fact,
        emotion=emotion,
        interpretation=interpretation,
        fact_confident=fact_confident,
        emotion_confident=emotion_confident,
        interpretation_confident=interpretation_confident,
    )


def _extract_fact_phrase(text: str) -> tuple[str, bool]:
    if "технолог" in text:
        return "технологическая тема стала частью живой ситуации", True
    if "совещ" in text:
        return "это произошло на рабочей встрече", True
    if "работ" in text or "началь" in text:
        return "это происходит на работе", True
    if "проект" in text:
        return "проект стал частью текущего напряжения", True
    if "бизнес" in text:
        return "бизнесовый контекст стал частью конфликта", True
    return _extract_phrase(
        text,
        FACT_MARKERS,
        "в этой ситуации уже есть конкретный напряжённый эпизод",
    )


def _is_low_confidence(
    *,
    latest_text: str,
    _combined_text: str,
    signals: ClarificationSignals,
) -> bool:
    if len(latest_text.split()) < 6:
        return True
    if any(marker in latest_text for marker in LOW_CONFIDENCE_MARKERS):
        return True
    if any(marker in latest_text for marker in CONTRADICTION_MARKERS) and (
        not signals.fact_confident
        or not signals.emotion_confident
        or not signals.interpretation_confident
    ):
        return True
    # When no signal was detected at all, always use tentative wording regardless
    # of message length — the word count does not indicate detection confidence.
    return not any(
        (
            signals.fact_confident,
            signals.emotion_confident,
            signals.interpretation_confident,
        )
    )


def _extract_phrase(
    text: str,
    markers: tuple[tuple[str, str], ...],
    fallback: str,
) -> tuple[str, bool]:
    for marker, phrase in markers:
        if marker in text:
            return phrase, True
    return fallback, False


def _build_low_confidence_reflection(*, signals: ClarificationSignals) -> str:
    anchors: list[str] = []
    if signals.fact_confident:
        anchors.append(f"какой-то опорный факт уже виден: {signals.fact}")
    if signals.emotion_confident:
        anchors.append(f"по ощущениям сейчас ясно, что {signals.emotion}")
    if not anchors:
        return (
            "Пока картина звучит немного рвано, и я не хочу делать слишком уверенные выводы "
            "там, где у тебя внутри ещё всё перемешано."
        )
    return (
        "Пока картина ещё не до конца сложилась, но уже можно опереться на то, что "
        + "; ".join(anchors)
        + "."
    )


def _build_follow_up_question(
    reflective_mode: str,
    *,
    low_confidence: bool,
    signals: ClarificationSignals,
) -> str:
    if low_confidence:
        if reflective_mode == "fast":
            return (
                "Если выбрать один главный узел прямо сейчас, что важнее прояснить: "
                "сам факт произошедшего или то, как это в тебе отзывается?"
            )
        if not signals.fact_confident:
            return "Если пойти на слой глубже через один эпизод, что именно там произошло без догадок о смысле?"
        if not signals.emotion_confident:
            return "Если пойти на слой глубже, что ощущается сильнее всего внутри, когда ты это вспоминаешь?"
        return "Если пойти на слой глубже, какой смысл ты сейчас больше всего невольно достраиваешь поверх самого факта?"

    if reflective_mode == "fast":
        if not signals.fact_confident:
            return "Если выбрать один главный узел, какой конкретный момент здесь задел тебя сильнее всего?"
        if not signals.interpretation_confident:
            return "Если выбрать один главный узел, тебя сильнее ранит сам поступок или то, что он для тебя значит?"
        return "Если выбрать один главный узел, что здесь больнее всего: сам поступок человека или то, что он для тебя значит?"

    if not signals.interpretation_confident:
        return "Если пойти на слой глубже, какой смысл ты сейчас начинаешь придавать этому эпизоду?"
    if not signals.emotion_confident:
        return "Если пойти на слой глубже, что в тебе отзывается сильнее всего, когда ты это вспоминаешь?"
    return "Если пойти на слой глубже, тебя больше ранит сам факт случившегося или смысл, который он для тебя несёт?"


def _build_correction_follow_up(reflective_mode: str) -> str:
    if reflective_mode == "fast":
        return "Тогда что в этом эпизоде задевает тебя сильнее всего прямо сейчас?"
    return (
        "Тогда если опираться только на то, как это выглядит сейчас, "
        "что в этом эпизоде задело тебя сильнее всего?"
    )


def _is_memory_correction(*, latest_text: str, prior_context: str | None) -> bool:
    if not prior_context:
        return False
    # Only trigger correction when the session was seeded with prior memory
    # (indicated by the [recall] sentinel set by _merge_context_for_session).
    # Without this guard, user-authored words like "знакомое" or "повторяется"
    # would falsely trigger correction even when the bot never surfaced recall.
    if not prior_context.startswith("[recall]"):
        return False
    lowered_prior = prior_context.lower()
    if not any(marker in lowered_prior for marker in MEMORY_RECALL_MARKERS):
        return False
    return any(marker in latest_text for marker in MEMORY_CORRECTION_MARKERS)

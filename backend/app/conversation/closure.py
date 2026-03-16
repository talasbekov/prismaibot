from __future__ import annotations

import logging
from dataclasses import dataclass

from app.conversation._text_utils import normalize_spaces

logger = logging.getLogger(__name__)

LOW_CONFIDENCE_MARKERS = (
    "не знаю",
    "не увер",
    "не до конца",
    "не понимаю",
    "как будто",
    "наверное",
)

TAKEAWAY_PATTERNS: tuple[tuple[str, str], ...] = (
    ("не слыш", "тебя сильнее всего задевает не только сам конфликт, но и ощущение, что тебя не услышали"),
    ("повтор", "похоже, больнее всего то, что этот напряженный сценарий повторяется"),
    ("обид", "сейчас в центре ситуации стоит обида и желание, чтобы твою сторону наконец заметили"),
    ("трев", "внутри этой ситуации смешались тревога и попытка понять, насколько безопасно продолжать разговор"),
    ("злит", "под слоем разговора уже накопилось раздражение, которое трудно просто отложить"),
)


@dataclass(frozen=True)
class ClosureResponse:
    messages: tuple[str, ...]
    next_steps: tuple[str, ...]
    takeaway: str
    action: str = "session_closure"


_CLOSURE_SYSTEM = """\
Ты — эмпатичный собеседник-бот «Prism AI». Завершаешь разговор, помогая \
пользователю зафиксировать ключевой инсайт и сформулировать следующие шаги.

Правила:
- Говори тепло и кратко.
- НЕ используй слова «я понимаю», «конечно», «безусловно».

Оформление:
- Начинай takeaway с 🪞, блок шагов — с ✅.
- Используй *жирный* для ключевых фраз.
- Ответ — ровно два абзаца, разделённых строкой «---» (без кавычек).
  Первый абзац (1–2 предложения): главное наблюдение из разговора (takeaway).
  Второй абзац: 2–3 конкретных шага или вопроса для самостоятельной рефлексии.\
"""


def _try_openai_closure(
    latest_user_message: str,
    prior_context: str | None,
    reflective_mode: str,
) -> ClosureResponse | None:
    from app.conversation._openai import call_chat, parse_two_messages

    context_text = " ".join(part for part in (prior_context, latest_user_message) if part)
    if reflective_mode == "fast":
        extra = "\n- Режим: краткий (fast) — шаги лаконичны, 1–2 пункта."
    else:
        extra = "\n- Режим: глубокий (deep) — шаги детальны, 3 пункта."

    raw = call_chat(
        [
            {"role": "system", "content": _CLOSURE_SYSTEM + extra},
            {"role": "user", "content": context_text},
        ],
        max_tokens=400,
    )
    if raw is None:
        return None
    parsed = parse_two_messages(raw)
    if parsed is None:
        logger.warning("OpenAI closure: unexpected format, falling back")
        return None

    takeaway, steps_text = parsed
    return ClosureResponse(
        takeaway=takeaway,
        next_steps=(),
        messages=(takeaway, steps_text),
    )


def compose_session_closure(
    *,
    latest_user_message: str,
    prior_context: str | None,
    reflective_mode: str,
) -> ClosureResponse:
    openai_result = _try_openai_closure(latest_user_message, prior_context, reflective_mode)
    if openai_result is not None:
        return openai_result

    normalized_message = normalize_spaces(latest_user_message)
    combined_context = normalize_spaces(
        " ".join(part for part in (prior_context, normalized_message) if part)
    )
    low_confidence = _is_low_confidence(combined_context)
    takeaway = _build_takeaway(combined_context, low_confidence=low_confidence)
    next_steps, intro = _build_next_steps(
        combined_context,
        reflective_mode=reflective_mode,
        low_confidence=low_confidence,
    )
    return ClosureResponse(
        takeaway=takeaway,
        next_steps=next_steps,
        messages=(
            takeaway,
            "\n".join((intro, *next_steps)),
        ),
    )


def _is_low_confidence(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in LOW_CONFIDENCE_MARKERS)


def _build_takeaway(text: str, *, low_confidence: bool) -> str:
    if low_confidence:
        return (
            "🪞 Если подвести это к ясной точке, пока не до конца ясно, "
            "что здесь было главным источником боли, но видно, что ситуация до сих пор держит тебя внутри. "
            "Это само по себе уже честная точка остановки."
        )

    lowered = text.lower()
    for marker, takeaway in TAKEAWAY_PATTERNS:
        if marker in lowered:
            return f"🪞 Если подвести это к ясной точке, {takeaway}."
    return (
        "🪞 Если подвести это к ясной точке, в этой ситуации уже видно напряжение "
        "между тем, что произошло, и тем, как тебе теперь с этим быть дальше."
    )


def _build_next_steps(
    text: str,
    *,
    reflective_mode: str,
    low_confidence: bool,
) -> tuple[tuple[str, ...], str]:
    if low_confidence:
        steps = (
            "1. Сначала не делать резких выводов, пока картина внутри не стала устойчивее.",
            "2. Если вернешься к разговору, попробуй назвать один факт и одно чувство без длинных объяснений.",
        )
        if reflective_mode == "deep":
            return steps, "✅ Что можно взять с собой сейчас:"
        return steps[:1], "✅ Что можно взять с собой сейчас:"

    lowered = text.lower()
    if "не слыш" in lowered or "перебил" in lowered:
        deep_steps = (
            "1. Отделить для себя сам поступок человека от того смысла, который он у тебя вызвал.",
            "2. Если будешь продолжать разговор, назвать спокойно, в каком именно месте ты почувствовала обесценивание.",
            "3. Если сил на разговор сейчас нет, дать себе короткую паузу и вернуться к теме позже без самодавления.",
        )
        fast_steps = (
            "1. Спокойно назвать, что именно тебя задело в его реакции.",
            "2. Если сейчас слишком остро, взять паузу вместо нового витка ссоры.",
        )
        return (
            fast_steps if reflective_mode == "fast" else deep_steps,
            "✅ Что можно сделать дальше:",
        )

    if "повтор" in lowered:
        deep_steps = (
            "1. Заметь, что именно в этом повторяющемся моменте болит сильнее всего: тон, игнор или ощущение бессилия.",
            "2. Реши, нужен ли тебе сейчас разговор по сути или сначала небольшая пауза, чтобы не войти в тот же круг.",
            "3. Если захочешь продолжить тему позже, опирайся на один конкретный повторяющийся эпизод, а не на весь накопленный архив.",
        )
        fast_steps = (
            "1. Выбрать один повторяющийся узел и держаться его, а не всей истории целиком.",
            "2. Если внутри слишком много напряжения, не раскручивать разговор прямо сейчас.",
        )
        return (
            fast_steps if reflective_mode == "fast" else deep_steps,
            "✅ Что можно сделать дальше:",
        )

    deep_steps = (
        "1. Сформулировать для себя, что в этой ситуации является фактом, а что ты пока только достраиваешь внутри.",
        "2. Решить, нужен ли тебе сейчас разговор, пауза или просто более ясная формулировка того, что тебя задело.",
        "3. Держаться одного следующего шага, а не пытаться закрыть всю ситуацию за раз.",
    )
    fast_steps = (
        "1. Назвать себе одну самую болезненную точку в этой ситуации.",
        "2. Выбрать один небольшой следующий шаг без попытки решить все сразу.",
    )
    return (
        fast_steps if reflective_mode == "fast" else deep_steps,
        "Что можно сделать дальше:",
    )

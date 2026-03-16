from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from app.conversation._text_utils import normalize_spaces

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Low-confidence detection
# ---------------------------------------------------------------------------

WEAK_LOW_CONFIDENCE_MARKERS = (
    "не знаю",
    "все сложно",
    "никак",
    "запут",
    "тяжело объяснить",
)

STRONG_LOW_CONFIDENCE_MARKERS = (
    "как-то",
    "что-то",
)

# ---------------------------------------------------------------------------
# Emotion extraction
#
# Each entry: (substring_marker, full_grammatically_correct_phrase).
# The phrase is inserted into: "Похоже, {situation}, и {emotion}."
# Markers are checked in order; the first non-negated match wins.
# ---------------------------------------------------------------------------

EMOTION_PHRASES: tuple[tuple[str, str], ...] = (
    ("обид", "тебе правда обидно"),
    ("злит", "это тебя злит"),
    ("злю", "это тебя злит"),
    ("бесит", "это тебя бесит"),
    ("страш", "тебе страшно"),
    ("трев", "тебе тревожно"),
    ("стыд", "тебе стыдно"),
    ("вина", "есть чувство вины"),
    ("виноват", "есть чувство вины"),
    ("больно", "тебе больно"),
    ("тяжел", "тебе правда тяжело"),
    ("устал", "это выматывает"),
    ("один", "тебе одиноко"),
    # Composite marker — includes its own negation; kept last to avoid
    # being shadowed by the negation-detection logic for simple markers.
    ("не слыш", "тебя не слышат"),
)

# ---------------------------------------------------------------------------
# Situation extraction
# ---------------------------------------------------------------------------

_NEGATION_WORDS = ("не", "ни")
_RECALL_UNCERTAINTY_MARKERS = (
    "не до конца",
    "неяс",
    "условн",
    "частич",
    "может",
    "не уверен",
    "не увер",
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FirstTrustResponse:
    messages: tuple[str, ...]
    action: str = "first_trust_response"


def compose_first_trust_response(user_text: str) -> FirstTrustResponse:
    return compose_first_trust_response_with_memory(user_text)


def compose_first_trust_response_with_memory(
    user_text: str,
    *,
    prior_memory_context: str | None = None,
) -> FirstTrustResponse:
    """Return the first trust-making reply for the user's opening message.

    Tries OpenAI first; falls back to keyword matching if unavailable.
    """
    openai_result = _try_openai_first_response(user_text, prior_memory_context)
    if openai_result is not None:
        return openai_result
    normalized = normalize_spaces(user_text)
    recall_mode = _classify_memory_recall(prior_memory_context)
    if _is_low_confidence(normalized):
        return FirstTrustResponse(
            messages=(
                "💬 Похоже, тебе сейчас непросто, и я не хочу делать вид, будто уже точно понял всю картину.",
                "🤔 Что в этой ситуации задевает тебя сильнее всего?",
            )
        )

    situation = _extract_situation(normalized)
    emotion = _extract_emotion(normalized)
    opening = f"💬 Похоже, {situation}, и {emotion}."
    if recall_mode == "explicit":
        opening += (
            " Могу ошибаться, но похоже, что здесь снова задевается "
            "уже знакомый для тебя узел."
        )
    # Keep the situational follow-up question regardless of recall_mode:
    # the opening already carries the explicit recall hint when needed.
    return FirstTrustResponse(
        messages=(
            opening,
            "🤔 Сейчас здесь одновременно есть сама ситуация и твоё сомнение, как на неё смотреть. "
            "Расскажи, что в этом для тебя болезненнее всего?",
        )
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_low_confidence(text: str) -> bool:
    """Return True when the message is too short or contains explicit vagueness markers.

    Deliberately does NOT penalise messages that lack a recognised situation
    keyword — a user can describe a clear emotional state without mentioning
    any relationship or work context.
    """
    lowered = text.lower()
    word_count = len(lowered.split())
    has_weak_marker = any(marker in lowered for marker in WEAK_LOW_CONFIDENCE_MARKERS)
    has_strong_marker = any(
        marker in lowered for marker in STRONG_LOW_CONFIDENCE_MARKERS
    )
    # Strong markers ("как-то", "что-то") are common filler words in Russian;
    # only treat them as low-confidence signals for short-to-medium messages so
    # that long, rich messages containing those words are not wrongly suppressed.
    return word_count < 8 or (has_strong_marker and word_count < 15) or (has_weak_marker and word_count < 10)


def _is_negated(text: str, marker_pos: int) -> bool:
    """Return True if a negation word immediately precedes the marker position."""
    words_before = text[:marker_pos].split()
    # Check only the last three words to stay close to the marker.
    recent = words_before[-3:] if len(words_before) >= 3 else words_before
    return any(word in _NEGATION_WORDS for word in recent)


def _extract_situation(text: str) -> str:
    lowered = text.lower()
    if "муж" in lowered:
        return "ситуация с мужем заметно тебя задела"
    if "коллег" in lowered or "совещ" in lowered or "началь" in lowered:
        return "ситуация на работе заметно тебя задела"
    if "партнер" in lowered or "парень" in lowered or "девуш" in lowered:
        return "ситуация с близким человеком заметно тебя задела"
    if "ссор" in lowered or "поруг" in lowered or "конфликт" in lowered:
        return "этот конфликт до сих пор держит тебя внутри"
    return "эта ситуация заметно тебя задела"


def _extract_emotion(text: str) -> str:
    lowered = text.lower()
    for marker, phrase in EMOTION_PHRASES:
        pos = lowered.find(marker)
        if pos != -1 and not _is_negated(lowered, pos):
            return phrase
    return "это тебя задело"


_FIRST_RESPONSE_SYSTEM = """\
Ты — эмпатичный собеседник-бот «Prism AI». Помогаешь пользователю разобраться \
в своих переживаниях через рефлексивный диалог на русском языке.

Правила:
- Говори тепло и кратко: 1–2 предложения на сообщение.
- Задавай ровно один вопрос — в конце второго сообщения.
- Отражай, не интерпретируй и не советуй.
- НЕ используй слова «я понимаю», «конечно», «безусловно».

Оформление:
- Начинай первый абзац с 💬, второй (вопрос) — с 🤔.
- Используй *жирный* для ключевых фраз и _курсив_ для эмоциональных акцентов.
- Ответ — ровно два абзаца, разделённых строкой «---» (без кавычек).
  Первый абзац: эмпатичное отражение того, что услышал.
  Второй абзац: один уточняющий вопрос.\
"""


def _try_openai_first_response(
    user_text: str,
    prior_memory_context: str | None,
) -> FirstTrustResponse | None:
    from app.conversation._openai import call_chat, parse_two_messages

    user_prompt = user_text
    if prior_memory_context:
        user_prompt = f"[Из прошлого разговора: {prior_memory_context}]\n\n{user_text}"

    raw = call_chat(
        [
            {"role": "system", "content": _FIRST_RESPONSE_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=300,
    )
    if raw is None:
        return None
    parsed = parse_two_messages(raw)
    if parsed is None:
        logger.warning("OpenAI first_response: unexpected format, falling back")
        return None
    return FirstTrustResponse(messages=parsed)


def _classify_memory_recall(
    prior_memory_context: str | None,
) -> Literal["none", "internal", "explicit"]:
    if not prior_memory_context:
        return "none"
    lowered = prior_memory_context.lower()
    recurring = any(marker in lowered for marker in ("повтор", "снова", "паттерн", "знаком"))
    if not recurring:
        # Memory exists but no explicit recurring-pattern signal: use it only
        # internally for relevance shaping without surfacing a recall cue (AC4, AC6).
        return "internal"
    if any(marker in lowered for marker in _RECALL_UNCERTAINTY_MARKERS):
        return "internal"
    return "explicit"

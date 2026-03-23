from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import BackgroundTasks
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.billing.prompts import (
    CANCEL_ERROR_MESSAGE,
    PAYMENT_INITIATION_ERROR_MESSAGE,
    PAYMENT_SUCCESS_MESSAGE,
    STATUS_ERROR_MESSAGE,
)
from app.billing.service import (
    build_paywall_response,
    build_status_response,
    get_user_access_state,
    has_premium_access,
    initiate_kaspi_payment,
    is_free_eligible,
    process_cancellation_request,
    record_eligible_session_completion,
)
from app.conversation.clarification import compose_clarification_response
from app.conversation.closure import ClosureResponse, compose_session_closure
from app.conversation.first_response import (
    FirstTrustResponse,
    compose_first_trust_response_with_memory,
)
from app.core.config import settings
from app.memory import (
    SessionSummaryPayload,
    derive_allowed_profile_facts,
    get_session_recall_context,
    record_memory_failure,
    schedule_session_summary_generation,
)
from app.models import ProcessedTelegramUpdate, TelegramSession
from app.ops.alerts import create_and_deliver_operator_alert
from app.ops.deletion import DeletionRequestIntakeError, request_user_data_deletion
from app.ops.signals import record_retryable_signal
from app.safety import (
    CrisisRoutingResponse,
    compose_crisis_routing_response,
    compose_crisis_step_down_response,
    evaluate_incoming_message_safety,
    should_step_down_from_crisis,
)

logger = logging.getLogger(__name__)

# Valid values for TelegramSession.crisis_state. Kept here rather than on the
# SQLModel field because SQLModel 0.0.21 cannot infer a column type from Literal.
CrisisState = Literal["normal", "crisis_active", "step_down_pending"]

# Matches TelegramSession.last_user_message max_length in models.py
MAX_USER_MESSAGE_LENGTH = 2000
_BRAINSTORM_CONTEXT_MARKER = "\n[Brainstorm: "

OPENING_PROMPT = (
    "🌀 Prism AI\n\n"
    "Иногда мысли в голове превращаются в хаос 🧠💭\n\n"
    "Здесь можно:\n"
    "• 🔎 разобраться в ситуации\n"
    "• 🧩 разложить мысли по полочкам\n"
    "• 💡 найти решение\n\n"
    "Я не даю готовых советов.\n"
    "Я задаю вопросы, которые помогают посмотреть на ситуацию с разных сторон и найти выход.\n\n"
    "Чаще всего люди приходят сюда, когда:\n\n"
    "• 🤔 не знают, какое решение принять\n"
    "• 🌪 запутались в мыслях\n"
    "• 💬 хотят спокойно проговорить проблему\n\n"
    "_Если тебе сейчас очень плохо — просто напиши об этом, я не начну с вопросов._"
)
RETURNING_USER_OPENING_PROMPT = (
    "👋 *Рад, что вернулся!*\n\n"
    "Продолжаем с прошлого раза или разберём что-то новое?"
)
CLARIFYING_PROMPT = "🤔 Можешь написать чуть подробнее — что именно сейчас происходит?"
SESSION_BOOTSTRAP_ERROR_PROMPT = "⚠️ Что-то пошло не так. Попробуй написать снова."
SAFETY_CHECK_ERROR_PROMPT = (
    "Я не хочу делать вид, что все в порядке, если проверка на риск сейчас не сработала. "
    "Попробуй написать еще раз через минуту."
)
SAFETY_ROUTING_ERROR_PROMPT = (
    "Я не хочу продолжать обычный разбор, если безопасное переключение сейчас не сработало. "
    "Сейчас лучше считать эту ситуацию чувствительной и не идти дальше как ни в чем не бывало."
)
SAFETY_STEP_DOWN_ERROR_PROMPT = (
    "Я не хочу делать вид, что уже аккуратно вернул разговор в обычный режим, если этот переход сейчас не собрался надежно. "
    "Пока лучше сохранить осторожный режим и не идти дальше слишком резко."
)

DELETE_REQUEST_CONFIRMED_PROMPT = (
    "Понял. Твой запрос на удаление данных принят.\n\n"
    "Сохранённые записи о наших разговорах будут удалены в ближайшее время. "
    "Если что-то пойдёт не так, мы тебя об этом не уведомим — "
    "но запрос не потеряется."
)
DELETE_ALREADY_PENDING_PROMPT = (
    "Ты уже отправил запрос на удаление данных. "
    "Он зарегистрирован и будет выполнен."
)
DELETE_REQUEST_ERROR_PROMPT = (
    "Что-то пошло не так при регистрации запроса на удаление. "
    "Попробуй написать /delete ещё раз."
)

_VALID_MODES = frozenset({"fast", "deep"})


class TelegramMessageOut(BaseModel):
    text: str


class InlineButton(BaseModel):
    text: str
    callback_data: str | None = None
    url: str | None = None

    @model_validator(mode="after")
    def validate_single_action(self) -> InlineButton:
        has_callback = self.callback_data is not None
        has_url = self.url is not None
        if has_callback == has_url:
            raise ValueError("InlineButton must define exactly one action field.")
        return self


class ReplyButton(BaseModel):
    text: str
    request_contact: bool = False


class ReplyKeyboardMarkup(BaseModel):
    keyboard: list[list[ReplyButton]]
    resize_keyboard: bool = True
    one_time_keyboard: bool = True


HELP_MESSAGE = (
    "🧠 *Как проходит разбор в Prism AI:*\n\n"
    "1. 🧩 *Ситуация* — ты описываешь, что у тебя происходит\n"
    "2. 🎯 *Фокус* — вместе понимаем, в чем главный вопрос или проблема\n"
    "3. ⚖️ *Контекст* — учитываем ограничения, страхи и реальность\n"
    "4. 💭 *Размышление* — я задаю вопросы, чтобы ты посмотрел на ситуацию глубже\n"
    "5. 🔎 *Структура* — мысли постепенно выстраиваются в понятную картину\n"
    "6. 💡 *Осознание* — появляются возможные решения и направления\n"
    "7. 🚶 *Действие* — ты сам приходишь к шагам, которые готов сделать\n\n"
    "⚠️ *Важно:* это не психолог, не терапия и не медицинская помощь.\n"
    "Это инструмент для самостоятельного разбора ситуации, который помогает лучше понять свои мысли и найти возможные решения.\n"
    "Если речь идет о серьезных эмоциональных или психологических состояниях, лучше обратиться к специалисту."
)

_HELP_BUTTON_TEXT = "❓ Помощь"
_RESET_BUTTON_TEXT = "🔄 Начать заново"

_PERSISTENT_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[ReplyButton(text=_HELP_BUTTON_TEXT), ReplyButton(text=_RESET_BUTTON_TEXT)]],
    resize_keyboard=True,
    one_time_keyboard=False,
)


class TelegramWebhookResponse(BaseModel):
    status: str
    action: str
    handled: bool = True
    session_id: str | None = None
    signals: list[str] = Field(default_factory=list)
    messages: list[TelegramMessageOut] = Field(default_factory=list)
    inline_keyboard: list[list[InlineButton]] = Field(default_factory=list)
    reply_markup: ReplyKeyboardMarkup | None = None


@dataclass(frozen=True)
class TelegramContact:
    phone_number: str
    first_name: str
    last_name: str | None = None
    user_id: int | None = None


@dataclass
class IncomingMessage:
    telegram_user_id: int
    chat_id: int
    text: str
    contact: TelegramContact | None = None


def _is_update_already_processed(session: Session, update_id: int) -> bool:
    return session.get(ProcessedTelegramUpdate, update_id) is not None


def _record_processed_update(session: Session, update_id: int) -> None:
    session.add(ProcessedTelegramUpdate(update_id=update_id))


async def handle_session_entry(
    session: Session,
    update: dict[str, Any],
    *,
    background_tasks: BackgroundTasks | None = None,
) -> TelegramWebhookResponse:
    # --- DEDUPLICATION GUARD ---
    update_id: int | None = update.get("update_id")
    if update_id is not None:
        try:
            if _is_update_already_processed(session, update_id):
                logger.info("Duplicate Telegram update_id=%d skipped", update_id)
                return TelegramWebhookResponse(
                    status="ok", action="duplicate_skipped", handled=False
                )
            _record_processed_update(session, update_id)
            session.flush()  # Записать в текущую транзакцию (commit вместе с основной операцией)
        except IntegrityError:
            session.rollback()
            logger.info("Duplicate Telegram update_id=%d skipped (race condition)", update_id)
            return TelegramWebhookResponse(
                status="ok", action="duplicate_skipped", handled=False
            )
        except Exception:
            logger.exception(
                "Idempotency check failed for update_id=%s, proceeding",
                update_id,
            )
    # --- END DEDUPLICATION GUARD ---

    if "callback_query" in update:
        cbq = update["callback_query"]
        if isinstance(cbq, dict):
            callback_data = cbq.get("data", "")
            if callback_data == "pay:kaspi":
                return _handle_kaspi_payment_initiation(session, cbq)
            if callback_data.startswith("admin:"):
                return await _handle_admin_callback(session, cbq)
            if callback_data.startswith("brainstorm:mode:"):
                return await _handle_brainstorm_mode_callback(session, cbq)

        mode_callback = _parse_mode_callback(update)
        if mode_callback is not None:
            return await _handle_mode_selection_callback(session, *mode_callback)

    # Standard message parsing and handling
    message = _parse_message(update)
    if message is None:
        return TelegramWebhookResponse(
            status="ignored",
            action="ignored",
            handled=False,
        )

    if message.text.strip() == "/start":
        return _start_brainstorming_session(
            session=session,
            telegram_user_id=message.telegram_user_id,
            chat_id=message.chat_id,
        )

    if message.text.strip() == _HELP_BUTTON_TEXT:
        return TelegramWebhookResponse(
            status="ok",
            action="help_shown",
            handled=True,
            messages=[TelegramMessageOut(text=HELP_MESSAGE)],
        )

    if message.text.strip() == _RESET_BUTTON_TEXT:
        return _start_brainstorming_session(
            session=session,
            telegram_user_id=message.telegram_user_id,
            chat_id=message.chat_id,
            action="brainstorm_reset",
        )

    if message.text.strip() == "/status":
        return _handle_status_command(
            session, message.telegram_user_id, message.chat_id
        )

    if message.text.strip() == "/cancel":
        return await _handle_cancel_command(
            session, message.telegram_user_id, message.chat_id
        )

    if message.text.strip() == "/admin":
        return _handle_admin_command(
            session, message.telegram_user_id, message.chat_id
        )

    if message.text.strip() == "/delete":
        return _handle_delete_command(
            session, message.telegram_user_id
        )

    # --- ADMIN TEXT LOOKUP (Story 7.8) ---
    from app.bot.utils import is_admin
    stripped_text = message.text.strip()
    if is_admin(message.telegram_user_id) and stripped_text.isdigit() and len(stripped_text) >= 5:
        # If admin sends a long number, treat it as a lookup request
        cbq_mock = {"from": {"id": message.telegram_user_id}, "data": f"admin:lookup_user_id:{stripped_text}"}
        return await _handle_admin_callback(session, cbq_mock)
    # --- END ADMIN TEXT LOOKUP ---

    try:
        return await _handle_message(session, message, background_tasks=background_tasks)
    except Exception:
        logger.exception(
            "Unhandled error in session entry for telegram_user_id=%s",
            message.telegram_user_id,
        )
        return TelegramWebhookResponse(
            status="error",
            action="session_bootstrap_error",
            handled=False,
            messages=[TelegramMessageOut(text=SESSION_BOOTSTRAP_ERROR_PROMPT)],
        )


def _handle_kaspi_payment_initiation(
    session: Session, callback_query: dict[str, Any]
) -> TelegramWebhookResponse:
    from_field = callback_query.get("from")
    message_field = callback_query.get("message")
    if not isinstance(from_field, dict) or not isinstance(message_field, dict):
        return TelegramWebhookResponse(status="error", action="payment_invoice_error", handled=False)

    chat_field = message_field.get("chat")
    if not isinstance(chat_field, dict):
        return TelegramWebhookResponse(status="error", action="payment_invoice_error", handled=False)

    telegram_user_id = from_field.get("id")
    chat_id = chat_field.get("id")

    if not isinstance(telegram_user_id, int) or not isinstance(chat_id, int):
        return TelegramWebhookResponse(status="error", action="payment_invoice_error", handled=False)

    from app.billing.prompts import KASPI_PHONE_REQUEST_MESSAGE
    
    return TelegramWebhookResponse(
        status="ok",
        action="request_contact",
        handled=True,
        messages=[TelegramMessageOut(text=KASPI_PHONE_REQUEST_MESSAGE)],
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [ReplyButton(text="📱 Отправить номер для Kaspi", request_contact=True)]
            ]
        )
    )


def _handle_status_command(
    session: Session, telegram_user_id: int, chat_id: int
) -> TelegramWebhookResponse:
    try:
        text, inline_keyboard = build_status_response(session, telegram_user_id)

        return TelegramWebhookResponse(
            status="ok",
            action="status_shown",
            handled=True,
            messages=[TelegramMessageOut(text=text)],
            inline_keyboard=inline_keyboard,
        )
    except Exception:
        logger.exception(
            "Status check failed for telegram_user_id=%s", telegram_user_id
        )
        session.rollback()
        try:
            active_session = _get_or_create_active_session(
                session, telegram_user_id, chat_id
            )
            session.flush()
            record_retryable_signal(
                session,
                session_id=active_session.id,
                telegram_user_id=telegram_user_id,
                signal_type="billing_status_check_failed",
                error_type="BillingStatusCheckError",
                error_message="Access status retrieval failed.",
                suggested_action="review_billing_status_check_failure",
                failure_stage="billing",
            )
            session.commit()
        except Exception:
            logger.exception(
                "Failed to record billing_status_check_failed signal for telegram_user_id=%s",
                telegram_user_id,
            )

        return TelegramWebhookResponse(
            status="error",
            action="status_error",
            handled=True,
            messages=[TelegramMessageOut(text=STATUS_ERROR_MESSAGE)],
        )


def _handle_admin_command(
    session: Session, telegram_user_id: int, chat_id: int
) -> TelegramWebhookResponse:
    from app.bot.utils import is_admin
    
    if not is_admin(telegram_user_id):
        return TelegramWebhookResponse(status="ignored", action="ignored", handled=False)
        
    return TelegramWebhookResponse(
        status="ok",
        action="admin_menu",
        handled=True,
        messages=[TelegramMessageOut(text="*Admin Dashboard*\nВыберите действие:")],
        inline_keyboard=[
            [InlineButton(text="📊 Статистика", callback_data="admin:stats")],
            [InlineButton(text="👤 Пользователь", callback_data="admin:user_lookup")],
            [InlineButton(text="⚠️ Алерты", callback_data="admin:alerts")],
        ]
    )


async def _handle_admin_callback(
    session: Session, callback_query: dict[str, Any]
) -> TelegramWebhookResponse:
    import uuid
    from app.bot.utils import is_admin, send_telegram_message
    from app.ops.billing_review import get_system_stats, get_user_billing_context
    
    telegram_user_id = callback_query.get("from", {}).get("id")
    if not telegram_user_id or not is_admin(telegram_user_id):
        return TelegramWebhookResponse(status="ignored", action="ignored", handled=False)
        
    data = callback_query.get("data", "")
    
    if data == "admin:stats":
        stats = get_system_stats(session)
        text = (
            "*Системная статистика*\n\n"
            f"👥 Всего пользователей: {stats['total_users']}\n"
            f"💬 Всего сессий: {stats['total_sessions']}\n"
            f"💎 Активных подписок: {stats['active_subscriptions']}\n"
            f"⏳ В льготном периоде: {stats['past_due_subscriptions']}\n\n"
            "*За последние 24 часа:*\n"
            f"🕒 Сессий: {stats['recent_sessions_24h']}\n"
            f"✅ Оплат: {stats['completed_intents_24h']}"
        )
        return TelegramWebhookResponse(
            status="ok",
            action="admin_stats",
            handled=True,
            messages=[TelegramMessageOut(text=text)],
        )
        
    if data == "admin:user_lookup":
        return TelegramWebhookResponse(
            status="ok",
            action="admin_user_lookup_prompt",
            handled=True,
            messages=[TelegramMessageOut(text="Введите Telegram ID пользователя для поиска:")],
        )

    if data.startswith("admin:lookup_user_id:"):
        target_user_id = int(data.split(":")[-1])
        context = get_user_billing_context(session, target_user_id)
        if not context:
            return TelegramWebhookResponse(
                status="ok",
                action="admin_user_not_found",
                handled=True,
                messages=[TelegramMessageOut(text=f"Пользователь {target_user_id} не найден.")],
            )
            
        sub_text = "Нет подписки"
        if context.subscription:
            sub_text = (
                f"Статус: {context.subscription['status']}\n"
                f"Провайдер: {context.subscription['provider_type']}\n"
                f"Истекает: {context.subscription['current_period_end']}\n"
                f"Автопродление: {'Выкл' if context.subscription['cancel_at_period_end'] else 'Вкл'}"
            )
            
        text = (
            f"*Информация о пользователе {target_user_id}*\n\n"
            f"Тариф: {context.access_tier}\n"
            f"Бесплатных сессий: {context.free_sessions_used}\n"
            f"Первая сессия завершена: {'Да' if context.first_session_completed else 'Нет'}\n\n"
            f"*Подписка:*\n{sub_text}\n\n"
            f"*Последние оплаты:* {len(context.purchase_intents)}"
        )
        
        buttons = []
        if context.access_tier != "premium":
            buttons.append([InlineButton(text="🚀 Выдать Premium (30д)", callback_data=f"admin:grant_premium:{target_user_id}")])
            
        return TelegramWebhookResponse(
            status="ok",
            action="admin_user_details",
            handled=True,
            messages=[TelegramMessageOut(text=text)],
            inline_keyboard=buttons,
        )
        
    if data.startswith("admin:grant_premium:"):
        target_user_id = int(data.split(":")[-1])
        from app.billing.repository import create_or_update_subscription, upgrade_access_tier, get_or_create_user_access_state
        from app.bot.utils import send_telegram_message
        from datetime import timedelta
        state = get_or_create_user_access_state(session, target_user_id)
        upgrade_access_tier(session, state, "premium")
        
        create_or_update_subscription(
            session,
            telegram_user_id=target_user_id,
            status="active",
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
            provider_type="manual_admin",
        )
        session.commit()
        
        await send_telegram_message(target_user_id, "Вам выдан Premium доступ на 30 дней администратором.")
        
        return TelegramWebhookResponse(
            status="ok",
            action="admin_premium_granted",
            handled=True,
            messages=[TelegramMessageOut(text=f"Premium доступ выдан пользователю {target_user_id}.")],
        )

    if data == "admin:alerts":
        from app.ops.alerts import list_operator_alerts
        alerts = list_operator_alerts(session)
        if not alerts:
            return TelegramWebhookResponse(
                status="ok",
                action="admin_alerts_empty",
                handled=True,
                messages=[TelegramMessageOut(text="Активных алертов нет.")],
            )
            
        text = "*Последние 10 алертов безопасности:*\n\n"
        buttons = []
        for alert in alerts[:10]:
            text += f"• {alert.created_at.strftime('%H:%M')} | {alert.trigger_category} | {alert.classification}\n"
            # Extract last 8 chars of ID for short button
            short_id = str(alert.id)[-8:]
            buttons.append([InlineButton(text=f"🔍 Расследовать {short_id}", callback_data=f"admin:investigate:{alert.id}")])
            
        return TelegramWebhookResponse(
            status="ok",
            action="admin_alerts_list",
            handled=True,
            messages=[TelegramMessageOut(text=text)],
            inline_keyboard=buttons,
        )

    if data.startswith("admin:investigate:"):
        alert_id = uuid.UUID(data.split(":")[-1])
        from app.ops.investigations import request_and_open_operator_investigation
        try:
            inv = request_and_open_operator_investigation(
                session,
                operator_alert_id=alert_id,
                reason_code="critical_safety_review",
                requested_by=f"admin:{telegram_user_id}",
                approved_by=f"admin:{telegram_user_id}",
                audit_notes="Investigated via Telegram Admin Dashboard",
            )
            
            ctx = inv.context_payload
            text = (
                f"*Расследование алерта {str(alert_id)[-8:]}*\n\n"
                f"Пользователь: `{ctx['alert']['telegram_user_id'] if 'telegram_user_id' in ctx['alert'] else 'N/A'}`\n"
                f"Категория: {ctx['alert']['trigger_category']}\n"
                f"Уверенность: {ctx['alert']['confidence']}\n\n"
                f"*Последнее сообщение:* {ctx['current_turn']['last_user_message']}\n\n"
                f"Статус сессии: {ctx['session']['crisis_state']}"
            )
            
            # Since some fields might be missing in payload depending on _build_investigation_context_payload implementation
            # let's be safer or just rely on what's definitely there
            
            return TelegramWebhookResponse(
                status="ok",
                action="admin_investigation_details",
                handled=True,
                messages=[TelegramMessageOut(text=text)],
            )
        except Exception as e:
            logger.exception("Investigation failed")
            return TelegramWebhookResponse(
                status="ok",
                action="admin_investigation_error",
                handled=True,
                messages=[TelegramMessageOut(text=f"Ошибка при открытии расследования: {str(e)}")],
            )

    return TelegramWebhookResponse(status="ignored", action="ignored", handled=False)


async def _handle_cancel_command(
    session: Session, telegram_user_id: int, chat_id: int
) -> TelegramWebhookResponse:
    try:
        result = await process_cancellation_request(session, telegram_user_id=telegram_user_id)
        session.commit()
    except Exception:
        logger.exception(
            "Cancellation request failed for telegram_user_id=%s", telegram_user_id
        )
        session.rollback()
        try:
            active_session = _get_or_create_active_session(
                session, telegram_user_id, chat_id
            )
            session.flush()
            record_retryable_signal(
                session,
                session_id=active_session.id,
                telegram_user_id=telegram_user_id,
                signal_type="billing_cancellation_failed",
                error_type="BillingCancellationError",
                error_message="Cancellation processing failed.",
                suggested_action="review_billing_cancellation_failure",
                failure_stage="billing",
            )
            session.commit()
        except Exception:
            logger.exception(
                "Failed to record billing_cancellation_failed signal for telegram_user_id=%s",
                telegram_user_id,
            )

        return TelegramWebhookResponse(
            status="error",
            action="cancellation_error",
            handled=True,
            messages=[TelegramMessageOut(text=CANCEL_ERROR_MESSAGE)],
        )

    if result.was_premium:
        try:
            active_session = _get_or_create_active_session(
                session, telegram_user_id, chat_id
            )
            session.flush()
            record_retryable_signal(
                session,
                session_id=active_session.id,
                telegram_user_id=telegram_user_id,
                signal_type="billing_cancellation_request_received",
                error_type="BillingCancellationSuccess",
                error_message="Premium cancellation processed successfully.",
                suggested_action="review_billing_cancellation",
                failure_stage="billing",
            )
            session.commit()
        except Exception:
            logger.exception(
                "Failed to record billing_cancellation_request_received signal for telegram_user_id=%s",
                telegram_user_id,
            )

    return TelegramWebhookResponse(
        status="ok",
        action=result.action,
        handled=True,
        messages=[TelegramMessageOut(text=result.message)],
    )


def _handle_delete_command(
    session: Session, telegram_user_id: int
) -> TelegramWebhookResponse:
    try:
        _, created = request_user_data_deletion(session, telegram_user_id=telegram_user_id)
    except DeletionRequestIntakeError:
        logger.exception(
            "Deletion request intake failed for telegram_user_id=%s", telegram_user_id
        )
        session.rollback()
        return TelegramWebhookResponse(
            status="error",
            action="deletion_request_error",
            handled=True,
            messages=[TelegramMessageOut(text=DELETE_REQUEST_ERROR_PROMPT)],
        )
    except Exception:
        logger.exception(
            "Unexpected error in deletion request for telegram_user_id=%s", telegram_user_id
        )
        session.rollback()
        return TelegramWebhookResponse(
            status="error",
            action="deletion_request_error",
            handled=True,
            messages=[TelegramMessageOut(text=DELETE_REQUEST_ERROR_PROMPT)],
        )

    prompt = DELETE_REQUEST_CONFIRMED_PROMPT if created else DELETE_ALREADY_PENDING_PROMPT
    action = "deletion_confirmed" if created else "deletion_already_pending"

    return TelegramWebhookResponse(
        status="ok",
        action=action,
        handled=True,
        messages=[TelegramMessageOut(text=prompt)],
    )


def _parse_message(update: dict[str, Any]) -> IncomingMessage | None:
    payload = update.get("message")
    if not isinstance(payload, dict):
        return None

    chat = payload.get("chat")
    sender = payload.get("from")
    text = payload.get("text") or ""
    contact_data = payload.get("contact")

    if not isinstance(chat, dict) or not isinstance(sender, dict):
        return None

    chat_id = chat.get("id")
    telegram_user_id = sender.get("id")
    if not isinstance(chat_id, int) or not isinstance(telegram_user_id, int):
        return None

    contact = None
    if isinstance(contact_data, dict):
        contact = TelegramContact(
            phone_number=contact_data.get("phone_number", ""),
            first_name=contact_data.get("first_name", ""),
            last_name=contact_data.get("last_name"),
            user_id=contact_data.get("user_id"),
        )

    if not text and not contact:
        return None

    return IncomingMessage(
        telegram_user_id=telegram_user_id,
        chat_id=chat_id,
        text=text,
        contact=contact,
    )


async def _handle_message(
    session: Session,
    incoming: IncomingMessage,
    *,
    background_tasks: BackgroundTasks | None = None,
) -> TelegramWebhookResponse:

    active_session = _get_or_create_active_session(
        session=session,
        telegram_user_id=incoming.telegram_user_id,
        chat_id=incoming.chat_id,
    )

    stripped_text = incoming.text.strip()
    # Guard against oversized input before touching the DB.
    if len(stripped_text) > MAX_USER_MESSAGE_LENGTH:
        stripped_text = stripped_text[:MAX_USER_MESSAGE_LENGTH]

    active_session.last_user_message = stripped_text

    # --- CONTACT HANDLER (Story 7.2 & 7.3) ---
    if incoming.contact:
        message_text = await initiate_kaspi_payment(
            session,
            telegram_user_id=incoming.telegram_user_id,
            phone_number=incoming.contact.phone_number,
        )
        return _build_response(
            action="contact_received",
            session_record=active_session,
            message_texts=[message_text],
            extra_signals=("typing", "contact_processed", "kaspi_invoice_initiated"),
        )
    # --- END CONTACT HANDLER ---

    # Billing gate: skip for crisis sessions, check eligibility for normal flow
    if active_session.crisis_state not in ("crisis_active", "step_down_pending"):
        try:
            premium_access = has_premium_access(session, active_session.telegram_user_id)
            if not premium_access:
                _user_access_state = get_user_access_state(session, active_session.telegram_user_id)
                if not is_free_eligible(_user_access_state):
                    paywall_text, inline_keyboard = build_paywall_response(_user_access_state)
                    _save_session(session, active_session)
                    return _build_response(
                        action="paywall_gate",
                        session_record=active_session,
                        message_texts=[paywall_text],
                        extra_signals=("typing", "paywall_shown"),
                        inline_keyboard=inline_keyboard,
                    )
        except Exception:
            logger.exception(
                "Billing access check failed for telegram_user_id=%s",
                active_session.telegram_user_id,
            )
            record_retryable_signal(
                session,
                session_id=active_session.id,
                telegram_user_id=active_session.telegram_user_id,
                signal_type="billing_access_check_failed",
                error_type="BillingAccessCheckError",
                error_message="Billing eligibility check failed; falling through to normal flow.",
                suggested_action="review_billing_access_check_failure",
                retry_payload={},
                failure_stage="billing",
            )
            # Fail-open: prefer granting access on uncertainty over incorrectly blocking the user

    is_first_turn = active_session.turn_count == 0
    response_messages: Sequence[str]
    summary_payload: SessionSummaryPayload | None = None
    extra_signals: Sequence[str] = ("typing",)
    resumed_after_step_down = False

    try:
        safety_assessment = evaluate_incoming_message_safety(
            session,
            session_record=active_session,
            message_text=stripped_text,
            turn_index=active_session.turn_count + 1,
        )
    except Exception:
        logger.exception(
            "Safety evaluation failed for telegram_user_id=%s",
            active_session.telegram_user_id,
        )
        active_session.last_bot_prompt = SAFETY_CHECK_ERROR_PROMPT
        active_session.last_user_message = stripped_text
        record_retryable_signal(
            session,
            session_id=active_session.id,
            telegram_user_id=active_session.telegram_user_id,
            signal_type="safety_evaluation_failed",
            error_type="SafetyEvaluationError",
            error_message="Incoming message safety evaluation failed before routing.",
            suggested_action="review_safety_evaluation_failure",
            retry_payload={"message_preview": stripped_text[:120]},
            failure_stage="request_path",
        )
        _save_session(session, active_session)
        return _build_response(
            action="safety_check_error",
            session_record=active_session,
            message_texts=[SAFETY_CHECK_ERROR_PROMPT],
            extra_signals=("typing", "safety_check_failed"),
        )

    if safety_assessment.classification == "borderline":
        extra_signals = ("typing", "safety_borderline_detected")

    should_enter_step_down = (
        active_session.crisis_state == "crisis_active"
        and should_step_down_from_crisis(
            message_text=stripped_text,
            assessment=safety_assessment,
        )
    )
    if should_enter_step_down:
        try:
            step_down_response = compose_crisis_step_down_response()
        except Exception:
            logger.exception(
                "Crisis step-down failed for telegram_user_id=%s",
                active_session.telegram_user_id,
            )
            active_session.last_bot_prompt = SAFETY_STEP_DOWN_ERROR_PROMPT
            active_session.turn_count += 1
            record_retryable_signal(
                session,
                session_id=active_session.id,
                telegram_user_id=active_session.telegram_user_id,
                signal_type="safety_step_down_failed",
                error_type="SafetyStepDownError",
                error_message="False-positive recovery failed after a crisis-active session.",
                suggested_action="review_safety_step_down_failure",
                retry_payload={"message_preview": stripped_text[:120]},
                failure_stage="routing",
            )
            _save_session(session, active_session)
            return _build_response(
                action="safety_step_down_error",
                session_record=active_session,
                message_texts=[SAFETY_STEP_DOWN_ERROR_PROMPT],
                extra_signals=("typing", "safety_step_down_failed", "crisis_mode_active"),
            )

        active_session.crisis_state = "step_down_pending"
        active_session.crisis_step_down_at = datetime.now(timezone.utc)
        active_session.last_bot_prompt = "\n\n".join(step_down_response.messages)
        active_session.turn_count += 1
        _save_session(session, active_session)
        return _build_response(
            action=step_down_response.action,
            session_record=active_session,
            message_texts=step_down_response.messages,
            extra_signals=("typing", "safety_recovery_step_down"),
        )

    if (
        active_session.crisis_state == "step_down_pending"
        and safety_assessment.classification == "safe"
        and not safety_assessment.blocks_normal_flow
    ):
        resumed_after_step_down = True
        active_session.crisis_state = "normal"

    should_route_to_crisis = (
        active_session.crisis_state in ("crisis_active", "step_down_pending")
        or safety_assessment.blocks_normal_flow
    )
    if should_route_to_crisis:
        newly_activated = active_session.crisis_state not in ("crisis_active", "step_down_pending")
        try:
            crisis_response = _compose_crisis_routing_response(
                newly_activated=newly_activated,
                safety_classification=safety_assessment.classification,
                safety_confidence=safety_assessment.confidence,
            )
        except Exception:
            logger.exception(
                "Crisis routing failed for telegram_user_id=%s",
                active_session.telegram_user_id,
            )
            # Mark as crisis_active even on routing failure: the session carries
            # known risk regardless of whether the routing response could be composed.
            # Trade-off: if this is a first activation, the retry will see
            # newly_activated=False and deliver the shorter continuation copy rather
            # than the full mode-switch explanation. Accepted as safer than leaving
            # the session in normal state.
            active_session.crisis_state = "crisis_active"
            active_session.brainstorm_phase = None
            active_session.brainstorm_data = None
            if active_session.crisis_activated_at is None:
                active_session.crisis_activated_at = datetime.now(timezone.utc)
            active_session.crisis_last_routed_at = datetime.now(timezone.utc)
            active_session.last_bot_prompt = SAFETY_ROUTING_ERROR_PROMPT
            active_session.turn_count += 1
            record_retryable_signal(
                session,
                session_id=active_session.id,
                telegram_user_id=active_session.telegram_user_id,
                signal_type="safety_routing_failed",
                error_type="SafetyRoutingError",
                error_message="Crisis-aware routing failed after a crisis classification.",
                suggested_action="review_crisis_routing_failure",
                retry_payload={"message_preview": stripped_text[:120]},
                failure_stage="routing",
            )
            _save_session(session, active_session)
            return _build_response(
                action="safety_routing_error",
                session_record=active_session,
                message_texts=[SAFETY_ROUTING_ERROR_PROMPT],
                extra_signals=("typing", "safety_routing_failed", "crisis_mode_active"),
            )

        active_session.crisis_state = "crisis_active"
        active_session.brainstorm_phase = None
        active_session.brainstorm_data = None
        if active_session.crisis_activated_at is None:
            active_session.crisis_activated_at = datetime.now(timezone.utc)
        active_session.crisis_last_routed_at = datetime.now(timezone.utc)
        active_session.last_bot_prompt = "\n\n".join(crisis_response.messages)
        active_session.turn_count += 1
        _save_session(session, active_session)
        try:
            create_and_deliver_operator_alert(
                session,
                session_record=active_session,
                assessment=safety_assessment,
                newly_activated=newly_activated,
            )
        except Exception:
            logger.exception(
                "Operator alert creation failed for telegram_user_id=%s",
                active_session.telegram_user_id,
            )
            record_retryable_signal(
                session,
                session_id=active_session.id,
                telegram_user_id=active_session.telegram_user_id,
                signal_type="operator_alert_creation_failed",
                error_type="OperatorAlertCreationError",
                error_message="Operator alert creation failed after crisis routing.",
                suggested_action="review_operator_alert_creation_failure",
                retry_payload={
                    "classification": safety_assessment.classification,
                    "trigger_category": safety_assessment.trigger_category,
                    "confidence": safety_assessment.confidence,
                },
                failure_stage="ops_delivery",
            )
            session.commit()
        crisis_signals = ["typing", "crisis_mode_active"]
        if safety_assessment.blocks_normal_flow:
            crisis_signals.insert(1, "safety_crisis_detected")
        return _build_response(
            action=crisis_response.action,
            session_record=active_session,
            message_texts=crisis_response.messages,
            extra_signals=tuple(crisis_signals),
            inline_keyboard=[
                [
                    InlineButton(text=label, url=url)
                    for label, url in crisis_response.inline_buttons
                ]
            ],
        )

    # Core loop routing (Reflection or Brainstorming)
    if active_session.brainstorm_phase is not None and active_session.brainstorm_phase != "detect_mode":
        is_reflection = (
            active_session.brainstorm_phase == "reflect"
            or active_session.brainstorm_phase.startswith("reflect_")
        )
        if is_reflection:
            from app.conversation.reflection import route as reflection_route
            result = await reflection_route(active_session, stripped_text)
            action_prefix = "reflect"
        else:
            from app.conversation.brainstorming import route as brainstorm_route
            result = await brainstorm_route(active_session, stripped_text)
            action_prefix = "brainstorm"

        response_messages = result.messages
        action = result.action
        active_session.brainstorm_phase = result.next_phase
        active_session.brainstorm_data = result.updated_data

        if not is_reflection:
            active_session.working_context = _update_brainstorm_context(
                active_session.working_context, result.updated_data
            )
        else:
            # F3 fix: update working_context for reflection
            active_session.working_context = (
                result.updated_data.get("analysis") 
                or result.updated_data.get("topic") 
                or active_session.working_context
            )
        
        if result.summary_payload is not None:
            summary_payload = result.summary_payload
            active_session.status = "completed"
            try:
                record_eligible_session_completion(
                    session,
                    telegram_user_id=active_session.telegram_user_id,
                    session_id=active_session.id,
                )
            except Exception:
                logger.exception(
                    "Billing free-usage recording failed for telegram_user_id=%s",
                    active_session.telegram_user_id,
                )
        active_session.last_bot_prompt = "\n\n".join(response_messages)
        active_session.turn_count += 1
        _save_session(session, active_session)
        if summary_payload is not None:
            if background_tasks is not None:
                schedule_session_summary_generation(background_tasks, summary_payload)
            else:
                logger.error(
                    "BackgroundTasks unavailable for %s session_id=%s; skipping summary",
                    action_prefix,
                    active_session.id,
                )
        return _build_response(
            action=action,
            session_record=active_session,
            message_texts=list(response_messages),
            extra_signals=tuple(extra_signals),
            inline_keyboard=result.inline_keyboard,
        )

    if len(stripped_text) < settings.CONVERSATION_MIN_CLEAR_MESSAGE_LENGTH:
        response_messages = [CLARIFYING_PROMPT]
        action = "clarify_input"
    elif is_first_turn:
        prior_memory_context = _safe_load_prior_memory_context(
            session,
            telegram_user_id=active_session.telegram_user_id,
        )
        first_response = _compose_first_trust_response(
            stripped_text,
            prior_memory_context=prior_memory_context,
        )
        response_messages = first_response.messages
        action = first_response.action
        active_session.working_context = _merge_context_for_session(
            stripped_text,
            prior_memory_context=prior_memory_context,
        )
    elif _should_close_session(active_session) and not resumed_after_step_down:
        closure = _compose_session_closure(
            latest_user_message=stripped_text,
            prior_context=active_session.working_context,
            reflective_mode=active_session.reflective_mode,
        )
        response_messages = closure.messages
        action = closure.action
        summary_payload = SessionSummaryPayload(
            session_id=active_session.id,
            telegram_user_id=active_session.telegram_user_id,
            reflective_mode=active_session.reflective_mode,
            source_turn_count=active_session.turn_count + 1,
            prior_context=active_session.working_context,
            latest_user_message=stripped_text,
            takeaway=closure.takeaway,
            next_steps=list(closure.next_steps),
            allowed_profile_facts=derive_allowed_profile_facts(
                prior_context=active_session.working_context,
                latest_user_message=stripped_text,
                takeaway=closure.takeaway,
            ),
        )
        active_session.working_context = closure.takeaway
        active_session.status = "completed"
        try:
            record_eligible_session_completion(
                session,
                telegram_user_id=active_session.telegram_user_id,
                session_id=active_session.id,
            )
        except Exception:
            logger.exception(
                "Billing free-usage recording failed for telegram_user_id=%s",
                active_session.telegram_user_id,
            )
            record_retryable_signal(
                session,
                session_id=active_session.id,
                telegram_user_id=active_session.telegram_user_id,
                signal_type="billing_free_usage_record_failed",
                error_type="BillingFreeUsageError",
                error_message="Free-usage session event recording failed at session closure.",
                suggested_action="retry_billing_free_usage_recording",
                failure_stage="billing",
            )
    else:
        # prior_memory_context is intentionally not passed here: it was merged
        # into working_context on the first turn and is already part of prior_context.
        # Story 2.4 will layer tentative phrasing on top via working_context rather
        # than re-injecting the recall payload on every turn.
        clarification = compose_clarification_response(
            latest_user_message=stripped_text,
            prior_context=active_session.working_context,
            reflective_mode=active_session.reflective_mode,
        )
        response_messages = clarification.messages
        action = clarification.action
        active_session.working_context = clarification.updated_context

    active_session.last_bot_prompt = "\n\n".join(response_messages)
    active_session.turn_count += 1
    _save_session(session, active_session)
    if summary_payload is not None:
        if background_tasks is not None:
            schedule_session_summary_generation(background_tasks, summary_payload)
        else:
            logger.error(
                "BackgroundTasks unavailable for session_id=%s; recording summary failure signal",
                summary_payload.session_id,
            )
            record_memory_failure(
                summary_payload,
                error_type="BackgroundTasksUnavailable",
                error_message="handle_session_entry called without BackgroundTasks; summary generation skipped",
                failure_stage="handoff",
            )
    return _build_response(
        action=action,
        session_record=active_session,
        message_texts=response_messages,
        extra_signals=extra_signals,
    )


def _compose_first_trust_response(
    user_text: str,
    *,
    prior_memory_context: str | None = None,
) -> FirstTrustResponse:
    return compose_first_trust_response_with_memory(
        user_text,
        prior_memory_context=prior_memory_context,
    )


def _compose_session_closure(
    *,
    latest_user_message: str,
    prior_context: str | None,
    reflective_mode: str,
) -> ClosureResponse:
    return compose_session_closure(
        latest_user_message=latest_user_message,
        prior_context=prior_context,
        reflective_mode=reflective_mode,
    )


def _update_brainstorm_context(working_context: str | None, data: dict | None) -> str:
    if not data:
        return working_context or ""
    parts = []
    if data.get("topic"):
        parts.append(f"Тема: {data['topic']}")
    if data.get("goal"):
        parts.append(f"Цель: {data['goal']}")
    if data.get("approach"):
        parts.append(f"Подход: {data['approach']}")
    if data.get("ideas"):
        parts.append(f"Идей собрано: {len(data['ideas'])}")
    if not parts:
        return working_context or ""
    brainstorm_summary = "; ".join(parts)
    base = _strip_brainstorm_context_marker(working_context)
    result = f"{base}\n[Brainstorm: {brainstorm_summary}]".strip()
    return _trim_text(result) or result


def _compose_crisis_routing_response(
    *,
    newly_activated: bool,
    safety_classification: Literal["safe", "borderline", "crisis"],
    safety_confidence: Literal["low", "medium", "high"],
) -> CrisisRoutingResponse:
    return compose_crisis_routing_response(
        newly_activated=newly_activated,
        safety_classification=safety_classification,
        safety_confidence=safety_confidence,
    )


def _should_close_session(session_record: TelegramSession) -> bool:
    return session_record.turn_count >= settings.CONVERSATION_CLOSURE_MIN_TURN_COUNT


def _get_or_create_active_session(
    session: Session, telegram_user_id: int, chat_id: int
) -> TelegramSession:
    statement = (
        select(TelegramSession)
        .where(TelegramSession.telegram_user_id == telegram_user_id)
        .where(TelegramSession.chat_id == chat_id)
        .where(TelegramSession.status == "active")
    )
    existing_session = session.exec(statement).first()
    if existing_session is not None:
        return existing_session

    new_session = TelegramSession(
        telegram_user_id=telegram_user_id,
        chat_id=chat_id,
        reflective_mode=settings.CONVERSATION_DEFAULT_REFLECTIVE_MODE,
    )
    # Track in the current transaction without committing yet.
    # The single commit happens at the end of _handle_message after all
    # processing (including OpenAI API calls) completes.
    # This avoids a half-initialised session window in the DB during slow ops.
    session.add(new_session)
    return new_session


def _save_session(session: Session, session_record: TelegramSession) -> None:
    _normalize_session_lengths(session_record)
    session_record.updated_at = datetime.now(timezone.utc)
    session.add(session_record)
    session.commit()
    session.refresh(session_record)


def _strip_brainstorm_context_marker(working_context: str | None) -> str:
    if not working_context:
        return ""
    marker_index = working_context.find(_BRAINSTORM_CONTEXT_MARKER)
    if marker_index == -1:
        return working_context
    return working_context[:marker_index].rstrip()


def _trim_text(value: str | None, limit: int = MAX_USER_MESSAGE_LENGTH) -> str | None:
    if value is None or len(value) <= limit:
        return value
    if limit <= 1:
        return value[:limit]
    return f"{value[: limit - 1]}…"


def _normalize_session_lengths(session_record: TelegramSession) -> None:
    session_record.last_user_message = _trim_text(session_record.last_user_message)
    session_record.last_bot_prompt = _trim_text(session_record.last_bot_prompt)
    session_record.working_context = _trim_text(session_record.working_context)


def _safe_load_prior_memory_context(
    session: Session,
    *,
    telegram_user_id: int,
) -> str | None:
    try:
        recall = get_session_recall_context(session, telegram_user_id=telegram_user_id)
    except Exception:
        logger.exception(
            "Failed to load prior memory context for telegram_user_id=%s",
            telegram_user_id,
        )
        return None
    return None if recall is None else recall.continuity_context


_RECALL_SENTINEL = "[recall] "


def _merge_context_for_session(
    latest_user_message: str,
    *,
    prior_memory_context: str | None,
) -> str:
    if not prior_memory_context:
        return latest_user_message
    # The [recall] sentinel marks this context as memory-backed so that
    # correction detection in clarification.py can distinguish memory-informed
    # sessions from sessions where the user happens to use recall-like words.
    merged = f"{_RECALL_SENTINEL}{prior_memory_context} {latest_user_message}"
    if len(merged) <= MAX_USER_MESSAGE_LENGTH:
        return merged
    available = MAX_USER_MESSAGE_LENGTH - len(latest_user_message) - 1 - len(_RECALL_SENTINEL)
    # Trim from the END of prior context (profile facts) to preserve the takeaway
    # at the beginning, which is the most important continuity signal.
    trimmed_prior = prior_memory_context[:available] if available > 0 else ""
    return f"{_RECALL_SENTINEL}{trimmed_prior} {latest_user_message}".strip()


def _parse_mode_callback(
    update: dict[str, Any],
) -> tuple[int, int, str, str] | None:
    """Return (telegram_user_id, chat_id, mode_data, prefix) when callback carries a mode selection prefix."""
    cbq = update.get("callback_query")
    if not isinstance(cbq, dict):
        return None
    data = cbq.get("data")
    if not isinstance(data, str):
        return None
    # Support both legacy "mode:" and new "brainstorm:mode:" prefixes
    if data.startswith("mode:"):
        prefix = "mode:"
    elif data.startswith("brainstorm:mode:"):
        prefix = "brainstorm:mode:"
    else:
        return None

    from_field = cbq.get("from")
    message_field = cbq.get("message")
    if not isinstance(from_field, dict) or not isinstance(message_field, dict):
        return None
    chat_field = message_field.get("chat")
    if not isinstance(chat_field, dict):
        return None
    user_id = from_field.get("id")
    chat_id = chat_field.get("id")
    if not isinstance(user_id, int) or not isinstance(chat_id, int):
        return None
    return user_id, chat_id, data, prefix


async def _handle_mode_selection_callback(
    session: Session, telegram_user_id: int, chat_id: int, mode_data: str, prefix: str
) -> TelegramWebhookResponse:
    mode = mode_data[len(prefix):]
    if mode in _VALID_MODES:
        source = "explicit"
    else:
        logger.warning(
            "Unrecognised mode callback data=%r for user=%s, applying default",
            mode_data,
            telegram_user_id,
        )
        mode = settings.CONVERSATION_DEFAULT_REFLECTIVE_MODE
        source = "fallback"

    session_id: str | None = None
    try:
        active_session = _get_or_create_active_session(session, telegram_user_id, chat_id)
        active_session.reflective_mode = mode
        active_session.mode_source = source
        _save_session(session, active_session)
        session_id = str(active_session.id)
    except Exception:
        logger.exception(
            "Failed to persist mode selection for telegram_user_id=%s", telegram_user_id
        )

    return TelegramWebhookResponse(
        status="ok",
        action="mode_selected",
        session_id=session_id,
        signals=[],
    )


async def _handle_brainstorm_mode_callback(
    session: Session, callback_query: dict[str, Any]
) -> TelegramWebhookResponse:
    from_field = callback_query.get("from")
    message_field = callback_query.get("message")
    if not isinstance(from_field, dict) or not isinstance(message_field, dict):
        return TelegramWebhookResponse(status="error", action="brainstorm_mode_error", handled=False)
    chat_field = message_field.get("chat")
    if not isinstance(chat_field, dict):
        return TelegramWebhookResponse(status="error", action="brainstorm_mode_error", handled=False)
    telegram_user_id = from_field.get("id")
    chat_id = chat_field.get("id")
    if not isinstance(telegram_user_id, int) or not isinstance(chat_id, int):
        return TelegramWebhookResponse(status="error", action="brainstorm_mode_error", handled=False)

    mode = callback_query.get("data", "").split(":")[-1]
    if mode == "reflect":
        active_session = _get_or_create_active_session(session, telegram_user_id, chat_id)
        from app.conversation.reflection import FALLBACKS
        active_session.brainstorm_phase = "reflect_listen"
        active_session.reflective_mode = "deep"  # F6 fix
        message_texts = [FALLBACKS["reflect_listen"]]
        action = "brainstorm_mode_reflect"
    else:  # "brainstorm"
        return _start_brainstorming_session(
            session=session,
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            action="brainstorm_mode_brainstorm",
        )

    _save_session(session, active_session)
    return _build_response(
        action=action,
        session_record=active_session,
        message_texts=message_texts,
        extra_signals=("typing",),
    )



def _start_brainstorming_session(
    *,
    session: Session,
    telegram_user_id: int,
    chat_id: int,
    action: str = "brainstorm_autostart",
) -> TelegramWebhookResponse:
    from app.conversation.brainstorming import FALLBACKS

    active_session = _get_or_create_active_session(session, telegram_user_id, chat_id)
    active_session.brainstorm_phase = "collect_topic"
    active_session.brainstorm_data = {
        "topic": "",
        "goal": "",
        "constraints": "",
        "approach": "",
        "ideas": [],
        "facilitation_turns": 0,
    }
    _save_session(session, active_session)
    response = _build_response(
        action=action,
        session_record=active_session,
        message_texts=[OPENING_PROMPT, FALLBACKS["collect_topic"]],
        extra_signals=("typing",),
    )
    response.reply_markup = _PERSISTENT_KEYBOARD
    return response


def _build_response(
    *,
    action: str,
    session_record: TelegramSession,
    message_texts: Sequence[str],
    extra_signals: Sequence[str] = ("typing",),
    inline_keyboard: list[list[InlineButton]] | None = None,
) -> TelegramWebhookResponse:
    return TelegramWebhookResponse(
        status="ok",
        action=action,
        session_id=str(session_record.id),
        signals=list(extra_signals),
        messages=[
            TelegramMessageOut(text=message_text)
            for message_text in message_texts
        ],
        inline_keyboard=inline_keyboard or [],
    )

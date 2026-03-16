from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.db import engine
from app.memory.schemas import ContinuityOverview
from app.memory.service import get_continuity_overview
from app.models import PeriodicInsight, SessionSummary

logger = logging.getLogger(__name__)


def generate_insights_for_all_users() -> None:
    """Entry point for the periodic insight generation job."""
    processed = 0
    skipped = 0
    failed = 0

    with Session(engine) as session:
        # Get all unique telegram_user_ids from session_summary
        user_ids = session.exec(select(SessionSummary.telegram_user_id).distinct()).all()

    for user_id in user_ids:
        try:
            result = generate_insight_for_user(user_id)
            if result == "generated":
                processed += 1
            else:
                skipped += 1
        except Exception:
            logger.exception("Failed to generate insight for telegram_user_id=%s", user_id)
            failed += 1

    logger.info(
        "Periodic insight generation complete. Processed: %d, Skipped: %d, Failed: %d",
        processed,
        skipped,
        failed,
    )


def generate_insight_for_user(telegram_user_id: int) -> str:
    """Generate and persist a reflective insight for a single user."""
    with Session(engine) as session:
        overview = get_continuity_overview(session, telegram_user_id=telegram_user_id)

        if not _should_generate_insight(overview):
            return "skipped"

        try:
            insight_text = _build_insight_text(overview)

            insight = PeriodicInsight(
                telegram_user_id=telegram_user_id,
                insight_text=insight_text,
                basis_summary_count=len(overview.summaries),
                status="pending_delivery",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(insight)
            session.commit()

            logger.info(
                "Generated insight for telegram_user_id=%s, basis_summary_count=%d",
                telegram_user_id,
                len(overview.summaries),
            )
            return "generated"
        except Exception as exc:
            session.rollback()
            # Save a record of the failure for observability
            try:
                error_insight = PeriodicInsight(
                    telegram_user_id=telegram_user_id,
                    insight_text="",
                    basis_summary_count=len(overview.summaries),
                    status="failed",  # Fixed: using "failed" instead of "skipped" for actual errors
                    generation_error=str(exc)[:500],
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(error_insight)
                session.commit()
            except Exception:
                logger.error("Could not save failure record for telegram_user_id=%s", telegram_user_id)
            raise


def _should_generate_insight(overview: ContinuityOverview) -> bool:
    """Determine if there's enough context to generate a meaningful insight."""
    # AC3: Minimum 2 summaries required
    if len(overview.summaries) < 2:
        return False

    # AC3: At least some summaries must be durable
    has_durable = any(s.retention_scope == "durable_summary" for s in overview.summaries)
    if not has_durable:
        return False

    return True


def _build_insight_text(overview: ContinuityOverview) -> str:
    """Build a calm, reflective insight text based on gathered context."""
    # 1. Opening
    text_parts = ["За последние сессии в ваших размышлениях проявились некоторые важные темы."]

    # 2. Integrate takeaways from summaries (AC2 compliance)
    # We use summary takeaways to reflect actual session history
    recent_takeaways = [s.takeaway for s in overview.summaries[:3] if s.takeaway]
    if recent_takeaways:
        combined_themes = " ".join(recent_takeaways)
        # Simple extraction logic: if specific keywords appear in takeaways, we highlight them
        if any(word in combined_themes.lower() for word in ("отнош", "партнер", "муж", "жен")):
            text_parts.append("Важной нитью в разговорах был контекст личных отношений.")
        if any(word in combined_themes.lower() for word in ("работ", "проект", "коллег")):
            text_parts.append("Заметная часть ваших раздумий касалась рабочих процессов и профессиональной реализации.")

        # Add a bit of specific context from the most recent takeaway if possible
        # but keep it general enough to remain calm and low-pressure
        text_parts.append(f"В частности, мы касались таких моментов: {recent_takeaways[0].rstrip('.')}.")

    # 3. Recurring facts from profile
    if overview.profile_facts:
        fact_lines = [f.fact_value for f in overview.profile_facts[:2]]
        if fact_lines:
            text_parts.append("Также заметно, что " + " ".join(fact_lines))

    # 4. Reflective observation
    text_parts.append(
        "Наблюдение за историей бесед помогает увидеть ситуацию в динамике, "
        "вне зависимости от остроты текущего момента."
    )

    # 5. Closing
    text_parts.append("Эти наблюдения могут стать хорошей основой для нашей следующей глубокой работы.")

    full_text = " ".join(text_parts)
    return full_text[:1500]

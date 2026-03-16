from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.jobs.insight_delivery import deliver_insights_for_all_users
from app.jobs.weekly_insights import generate_insights_for_all_users

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def start_scheduler() -> None:
    """Start the background scheduler."""
    if not scheduler.running:
        interval_days = settings.INSIGHT_GENERATION_INTERVAL_DAYS

        scheduler.add_job(
            generate_insights_for_all_users,
            IntervalTrigger(days=interval_days),
            id="weekly_insights",
            replace_existing=True,
        )

        scheduler.add_job(
            deliver_insights_for_all_users,
            IntervalTrigger(hours=settings.INSIGHT_DELIVERY_INTERVAL_HOURS),
            id="insight_delivery",
            replace_existing=True,
        )

        scheduler.start()
        logger.info(
            "Background scheduler started. Generation interval: %d days, Delivery interval: %d hours",
            interval_days,
            settings.INSIGHT_DELIVERY_INTERVAL_HOURS
        )


def stop_scheduler() -> None:
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")

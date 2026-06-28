"""Daily brief automation.

Runs once a day at 07:00 Australia/Sydney, generating and emailing a portfolio
brief for every user who has holdings. Active only in production (APP_ENV).
"""
import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.pipeline import generate_brief_for_user
from app.services.portfolio import PortfolioService

logger = logging.getLogger(__name__)

SYDNEY_TZ = ZoneInfo("Australia/Sydney")

# Arbitrary constant key for a session-level Postgres advisory lock. Cloud Run
# may run >1 instance (max-instances=2), each with its own in-process scheduler;
# the lock ensures only one instance actually runs the daily batch, so users are
# not double-briefed / double-emailed.
_DAILY_BRIEF_LOCK_KEY = 0x57415443  # "WATC"

_scheduler: AsyncIOScheduler | None = None


async def run_daily_briefs() -> None:
    """Generate and email a brief for every user with holdings.

    Single-runner: a Postgres advisory lock ensures only one instance runs the
    batch even if several are live. Resilient: each user runs in its own DB
    session and try/except, so one user's failure is logged and the run
    continues to the next user.
    """
    async with AsyncSessionLocal() as lock_db:
        got_lock = (
            await lock_db.execute(
                text("SELECT pg_try_advisory_lock(:k)"),
                {"k": _DAILY_BRIEF_LOCK_KEY},
            )
        ).scalar()
        if not got_lock:
            logger.info("Daily briefs already running on another instance; skipping")
            return

        try:
            async with AsyncSessionLocal() as db:
                user_ids = await PortfolioService(db).get_all_user_ids()

            logger.info("Daily brief run starting for %d user(s)", len(user_ids))
            succeeded = 0
            for user_id in user_ids:
                try:
                    async with AsyncSessionLocal() as db:
                        brief = await generate_brief_for_user(
                            user_id, db, send_email=True
                        )
                    if brief is not None:
                        succeeded += 1
                    else:
                        logger.warning(
                            "Daily brief produced no brief for user %s", user_id
                        )
                except Exception:  # noqa: BLE001 — never let one user abort the batch
                    logger.exception(
                        "Daily brief failed for user %s; continuing", user_id
                    )

            logger.info(
                "Daily brief run complete: %d/%d succeeded", succeeded, len(user_ids)
            )
        finally:
            await lock_db.execute(
                text("SELECT pg_advisory_unlock(:k)"), {"k": _DAILY_BRIEF_LOCK_KEY}
            )


def start_scheduler() -> None:
    """Start the daily-brief scheduler. No-op outside production."""
    global _scheduler

    if not settings.is_production:
        logger.info(
            "Scheduler disabled (APP_ENV=%s); daily briefs not scheduled",
            settings.APP_ENV,
        )
        return

    if _scheduler is not None:
        logger.info("Scheduler already running; skipping start")
        return

    scheduler = AsyncIOScheduler(timezone=SYDNEY_TZ)
    scheduler.add_job(
        run_daily_briefs,
        trigger=CronTrigger(hour=7, minute=0, timezone=SYDNEY_TZ),
        id="daily_briefs",
        name="Daily portfolio briefs (07:00 Australia/Sydney)",
        misfire_grace_time=3600,  # tolerate a late start (cold start / redeploy)
        coalesce=True,            # collapse missed runs into one
        max_instances=1,          # never overlap two daily runs
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("Scheduler started: daily briefs at 07:00 Australia/Sydney")


def shutdown_scheduler() -> None:
    """Stop the scheduler if running (called on app shutdown)."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")

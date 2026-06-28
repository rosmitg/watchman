import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import watchman_graph
from app.core.redis import cache_brief
from app.models.state import Alert, Brief, Holding, WatchmanState
from app.services.alert_detector import AlertDetector
from app.services.alert_service import AlertService
from app.services.brief import BriefService
from app.services.email import send_brief_email_for_user
from app.services.portfolio import PortfolioService

logger = logging.getLogger(__name__)


def _dedupe_alerts(alerts: list[Alert]) -> list[Alert]:
    """Drop duplicate alerts, keeping the first seen per (ticker, type)."""
    seen: set[tuple[str, str]] = set()
    unique: list[Alert] = []
    for alert in alerts:
        key = (alert.ticker, alert.type)
        if key in seen:
            continue
        seen.add(key)
        unique.append(alert)
    return unique


async def run_watchman_pipeline(user_id: str, holdings: list[Holding]) -> Brief | None:
    """Runs the full 5-agent LangGraph pipeline for a user's portfolio.

    Builds the initial ``WatchmanState`` from the user's holdings, invokes the
    compiled ``watchman_graph`` (news -> fundamentals -> sentiment -> sec ->
    synthesis), and returns the synthesized Brief from the final state. Returns
    None if synthesis did not produce a brief.
    """
    tickers = [holding.ticker for holding in holdings]

    initial_state: WatchmanState = {
        "user_id": user_id,
        "portfolio": holdings,
        "tickers": tickers,
        "news_findings": [],
        "fundamental_findings": [],
        "sentiment_scores": {},
        "price_movements": [],
        "sec_findings": {},
        "brief": None,
        "alerts": [],
        "generated_at": datetime.now(timezone.utc),
    }

    final_state = await watchman_graph.ainvoke(initial_state)

    # Combine the synthesis agent's alerts with rule-based detections, dedupe by
    # ticker+type, and publish each to the user's real-time alert channel.
    detected = AlertDetector.detect_alerts(final_state)
    synthesis_alerts = final_state.get("alerts", []) or []
    alerts = _dedupe_alerts(synthesis_alerts + detected)
    if alerts:
        alert_service = AlertService()
        try:
            for alert in alerts:
                await alert_service.publish_alert(user_id, alert)
        finally:
            await alert_service.aclose()

    return final_state.get("brief")


async def generate_brief_for_user(
    user_id: str,
    db: AsyncSession,
    *,
    send_email: bool = True,
) -> Brief | None:
    """Generate, persist, cache, and (optionally) email a user's daily brief.

    Shared by the HTTP ``POST /brief/generate`` endpoint and the daily scheduler.
    Reads the user's holdings, runs the pipeline, upserts the brief, refreshes the
    cache, then sends the brief email. Returns the saved Brief, or None if the
    pipeline produced no brief.

    The email step is fire-and-forget (``send_brief_email_for_user`` never raises),
    so a brief is always saved successfully even if delivery fails.
    """
    holdings = await PortfolioService(db).get_holdings(user_id)
    brief = await run_watchman_pipeline(user_id, holdings)
    if brief is None:
        return None

    saved = await BriefService(db).save_brief(brief)
    await cache_brief(user_id, saved)

    if send_email:
        await send_brief_email_for_user(user_id, saved)

    return saved

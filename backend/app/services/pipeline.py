from datetime import datetime, timezone

from app.agents.graph import watchman_graph
from app.models.state import Alert, Brief, Holding, WatchmanState
from app.services.alert_detector import AlertDetector
from app.services.alert_service import AlertService


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

from datetime import datetime, timezone

from app.agents.graph import watchman_graph
from app.models.state import Brief, Holding, WatchmanState


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
    return final_state.get("brief")

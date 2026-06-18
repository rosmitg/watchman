from app.models.state import WatchmanState


async def news_agent(state: WatchmanState) -> WatchmanState:
    """Fetches latest news headlines per ticker via NewsAPI."""
    # TODO Sprint 2: query NewsAPI per ticker, summarize, populate news_findings.
    state["news_findings"] = []
    return state

from app.models.state import WatchmanState


async def sentiment_agent(state: WatchmanState) -> WatchmanState:
    """Scores sentiment of news findings per ticker."""
    # TODO Sprint 2: run sentiment model over news_findings, populate sentiment_scores.
    state["sentiment_scores"] = {}
    return state

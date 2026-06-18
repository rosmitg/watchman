from app.models.state import WatchmanState


async def sec_agent(state: WatchmanState) -> WatchmanState:
    """Checks recent SEC filings relevant to the portfolio tickers."""
    # TODO Sprint 2: query SEC EDGAR for recent filings and embed for semantic search.
    return state

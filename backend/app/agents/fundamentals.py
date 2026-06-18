from app.models.state import WatchmanState


async def fundamentals_agent(state: WatchmanState) -> WatchmanState:
    """Fetches price/fundamental data per ticker and detects significant price moves."""
    # TODO Sprint 2: pull fundamentals via Alpaca/yfinance, compute price_movements.
    state["fundamental_findings"] = []
    state["price_movements"] = []
    return state

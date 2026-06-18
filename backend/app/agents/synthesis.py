from app.models.state import WatchmanState


async def synthesis_agent(state: WatchmanState) -> WatchmanState:
    """Synthesizes all agent findings into a daily brief and alerts via Claude."""
    # TODO Sprint 2: prompt Claude with aggregated state, build Brief and Alerts.
    state["brief"] = None
    state["alerts"] = []
    return state

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.synthesis import build_synthesis_prompt, synthesis_agent
from app.models.state import Holding, WatchmanState


def _state() -> WatchmanState:
    return WatchmanState(
        user_id="user-1",
        portfolio=[
            Holding(
                ticker="AAPL",
                qty=10,
                avg_entry_price=150.0,
                current_price=170.0,
                market_value=1700.0,
            )
        ],
        tickers=["AAPL"],
        news_findings=[],
        fundamental_findings=[],
        sentiment_scores={"AAPL": 0.5},
        price_movements=[],
        sec_findings={},
        brief=None,
        alerts=[],
        generated_at=None,
    )


def test_build_synthesis_prompt_includes_holdings():
    """The prompt mentions the portfolio tickers and holdings."""
    prompt = build_synthesis_prompt(_state())
    assert "AAPL" in prompt
    assert "Portfolio Holdings" in prompt
    assert "10" in prompt  # share quantity


@pytest.mark.asyncio
async def test_synthesis_agent_populates_brief():
    """synthesis_agent parses the LLM response into a populated Brief."""
    llm_payload = {
        "headline": "Markets up on tech strength",
        "portfolio_health": 82,
        "sections": [
            {"title": "Market Summary", "body": "Solid day.", "tickers": ["AAPL"]},
        ],
        "alerts": [
            {
                "ticker": "AAPL",
                "type": "earnings",
                "title": "Earnings soon",
                "body": "AAPL reports next week.",
            }
        ],
    }
    mock_response = MagicMock()
    mock_response.content = json.dumps(llm_payload)

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("app.agents.synthesis.ChatAnthropic", return_value=mock_llm):
        state = await synthesis_agent(_state())

    brief = state["brief"]
    assert brief is not None
    assert brief.headline == "Markets up on tech strength"
    assert brief.portfolio_health == 82
    assert len(brief.sections) == 1
    assert brief.sections[0].title == "Market Summary"
    assert len(state["alerts"]) == 1
    assert state["alerts"][0].ticker == "AAPL"

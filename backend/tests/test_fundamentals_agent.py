from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.agents.fundamentals import (
    classify_price_move,
    fetch_fundamentals_for_ticker,
    fundamentals_agent,
)
from app.models.state import FundamentalData, WatchmanState


def _empty_state(tickers: list[str]) -> WatchmanState:
    return WatchmanState(
        user_id="user-1",
        portfolio=[],
        tickers=tickers,
        news_findings=[],
        fundamental_findings=[],
        sentiment_scores={},
        price_movements=[],
        sec_findings={},
        brief=None,
        alerts=[],
        generated_at=None,
    )


def _mock_yf_ticker(last_price=105.0, previous_close=100.0):
    fast_info = SimpleNamespace(
        last_price=last_price,
        previous_close=previous_close,
        market_cap=1_000_000_000,
        three_month_average_volume=5_000_000,
    )
    mock = MagicMock()
    mock.fast_info = fast_info
    mock.info = {"trailingPE": 25.5}
    return mock


def test_fetch_fundamentals_maps_fields():
    """fetch_fundamentals_for_ticker builds a correct FundamentalData from yfinance."""
    with patch("app.agents.fundamentals.yf.Ticker", return_value=_mock_yf_ticker()):
        data = fetch_fundamentals_for_ticker("AAPL")

    assert isinstance(data, FundamentalData)
    assert data.ticker == "AAPL"
    assert data.price == 105.0
    assert data.change_pct == pytest.approx(5.0)
    assert data.pe_ratio == 25.5
    assert data.market_cap == 1_000_000_000
    assert data.volume == 5_000_000


def test_classify_price_move_up_significant():
    """A +5% move is classified up and significant."""
    move = classify_price_move("AAPL", 5.0)
    assert move.direction == "up"
    assert move.is_significant is True


def test_classify_price_move_flat_not_significant():
    """A +1% move is not significant."""
    move = classify_price_move("AAPL", 1.0)
    assert move.direction == "up"
    assert move.is_significant is False


@pytest.mark.asyncio
async def test_fundamentals_agent_handles_exception_gracefully():
    """A yfinance failure is logged and skipped, not raised."""
    with patch("app.agents.fundamentals.yf.Ticker", side_effect=Exception("yfinance down")):
        state = await fundamentals_agent(_empty_state(["AAPL"]))

    assert state["fundamental_findings"] == []
    assert state["price_movements"] == []

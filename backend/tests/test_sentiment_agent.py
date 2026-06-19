from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.agents.sentiment import score_ticker_sentiment, sentiment_agent
from app.models.state import NewsItem, WatchmanState


def _news(ticker: str, title: str) -> NewsItem:
    return NewsItem(
        ticker=ticker,
        title=title,
        source="Reuters",
        url="https://example.com",
        published_at=datetime.now(timezone.utc),
        summary="summary",
    )


def _state(tickers: list[str], news: list[NewsItem]) -> WatchmanState:
    return WatchmanState(
        user_id="user-1",
        portfolio=[],
        tickers=tickers,
        news_findings=news,
        fundamental_findings=[],
        sentiment_scores={},
        price_movements=[],
        sec_findings={},
        brief=None,
        alerts=[],
        generated_at=None,
    )


def _mock_hf_response(label: str, score: float):
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = [[{"label": label, "score": score}]]
    return mock


@pytest.mark.asyncio
async def test_positive_label_gives_positive_score():
    """A positive FinBERT label yields a positive sentiment score."""
    news = [_news("AAPL", "Apple beats earnings expectations")]
    with patch(
        "app.agents.sentiment.httpx.post",
        return_value=_mock_hf_response("positive", 0.9),
    ):
        state = await sentiment_agent(_state(["AAPL"], news))

    assert state["sentiment_scores"]["AAPL"] == pytest.approx(0.9)


def test_negative_label_gives_negative_score():
    """A negative FinBERT label yields a negative sentiment score."""
    news = [_news("AAPL", "Apple faces major lawsuit")]
    with patch(
        "app.agents.sentiment.httpx.post",
        return_value=_mock_hf_response("negative", 0.8),
    ):
        score = score_ticker_sentiment("AAPL", news, api_key="test-key")

    assert score == pytest.approx(-0.8)


def test_empty_news_returns_zero():
    """A ticker with no news scores 0.0 without calling the API."""
    score = score_ticker_sentiment("AAPL", [], api_key="test-key")
    assert score == 0.0

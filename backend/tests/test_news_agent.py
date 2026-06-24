from unittest.mock import MagicMock, patch

import pytest

from app.agents.news import fetch_news_for_ticker, news_agent
from app.models.state import NewsItem, WatchmanState


def _sample_response(n: int = 2) -> dict:
    return {
        "status": "ok",
        "totalResults": n,
        "articles": [
            {
                "source": {"id": "reuters", "name": "Reuters"},
                "title": f"Headline {i}",
                "url": f"https://example.com/{i}",
                "publishedAt": "2026-06-18T12:34:56Z",
                "description": f"Summary {i}",
            }
            for i in range(n)
        ],
    }


def _empty_state(tickers: list[str]) -> WatchmanState:
    return WatchmanState(
        user_id="user-1",
        portfolio=[],
        tickers=tickers,
        news_findings=[],
        fundamental_findings=[],
        sentiment_scores={},
        price_movements=[],
        brief=None,
        alerts=[],
        generated_at=None,
    )


@pytest.mark.asyncio
async def test_news_agent_populates_findings():
    """Agent populates news_findings when the API returns articles."""
    with patch("app.agents.news.NewsApiClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get_everything.return_value = _sample_response(2)
        mock_client_cls.return_value = mock_client

        state = await news_agent(_empty_state(["AAPL", "MSFT"]))

    # 2 tickers x 2 articles each
    assert len(state["news_findings"]) == 4
    assert all(isinstance(item, NewsItem) for item in state["news_findings"])
    assert {item.ticker for item in state["news_findings"]} == {"AAPL", "MSFT"}


@pytest.mark.asyncio
async def test_news_agent_handles_api_failure_gracefully():
    """Agent returns an empty list (no raise) when the API call fails."""
    with patch("app.agents.news.NewsApiClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get_everything.side_effect = Exception("NewsAPI is down")
        mock_client_cls.return_value = mock_client

        state = await news_agent(_empty_state(["AAPL"]))

    assert state["news_findings"] == []


def test_newsitem_fields_map_correctly():
    """NewsItem fields are mapped correctly from the API response."""
    with patch("app.agents.news.NewsApiClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get_everything.return_value = _sample_response(1)
        mock_client_cls.return_value = mock_client

        items = fetch_news_for_ticker("AAPL", api_key="test-key")

    assert len(items) == 1
    item = items[0]
    assert item.ticker == "AAPL"
    assert item.title == "Headline 0"
    assert item.url == "https://example.com/0"
    assert item.source == "Reuters"
    assert item.summary == "Summary 0"
    assert item.published_at.year == 2026
    assert item.published_at.month == 6
    assert item.published_at.day == 18

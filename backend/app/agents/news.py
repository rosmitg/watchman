import logging
from datetime import datetime, timedelta, timezone

from newsapi import NewsApiClient

from app.core.config import settings
from app.models.state import NewsItem, WatchmanState

logger = logging.getLogger(__name__)

# How many days back to look for news, and how many articles per ticker.
LOOKBACK_DAYS = 3
PAGE_SIZE = 5


def _parse_published_at(value: str | None) -> datetime:
    """Parses NewsAPI's ISO-8601 ``publishedAt`` string into a datetime.

    Falls back to the current time if the value is missing or unparseable.
    """
    if not value:
        return datetime.now(timezone.utc)
    try:
        # NewsAPI returns e.g. "2026-06-18T12:34:56Z".
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


def fetch_news_for_ticker(ticker: str, api_key: str) -> list[NewsItem]:
    """Fetches the latest news headlines for a single ticker via NewsAPI.

    Queries the ``/everything`` endpoint for English articles published in the
    last ``LOOKBACK_DAYS`` days, sorted by recency. On any failure the error is
    logged and an empty list is returned so one ticker can't crash the agent.
    """
    try:
        client = NewsApiClient(api_key=api_key)
        from_date = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime(
            "%Y-%m-%d"
        )
        response = client.get_everything(
            q=ticker,
            language="en",
            sort_by="publishedAt",
            page_size=PAGE_SIZE,
            from_param=from_date,
        )
    except Exception:
        logger.exception("Failed to fetch news for ticker %s", ticker)
        return []

    articles = response.get("articles", []) if isinstance(response, dict) else []
    items: list[NewsItem] = []
    for article in articles:
        try:
            source = article.get("source") or {}
            items.append(
                NewsItem(
                    ticker=ticker,
                    title=article.get("title") or "",
                    source=source.get("name") or "",
                    url=article.get("url") or "",
                    published_at=_parse_published_at(article.get("publishedAt")),
                    summary=article.get("description") or "",
                )
            )
        except Exception:
            logger.exception("Failed to map article for ticker %s", ticker)

    return items


async def news_agent(state: WatchmanState) -> WatchmanState:
    """Fetches latest news headlines per ticker via NewsAPI.

    Iterates over every ticker in the portfolio, fetches its recent news, and
    combines the results into a single flat list on ``news_findings``.
    """
    api_key = settings.NEWS_API_KEY
    findings: list[NewsItem] = []
    for ticker in state.get("tickers", []):
        findings.extend(fetch_news_for_ticker(ticker, api_key))

    state["news_findings"] = findings
    return state

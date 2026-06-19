import logging

import httpx

from app.core.config import settings
from app.models.state import NewsItem, WatchmanState

logger = logging.getLogger(__name__)

FINBERT_URL = "https://api-inference.huggingface.co/models/ProsusAI/finbert"


def _extract_label_score(payload) -> tuple[str, float]:
    """Pulls the top (label, score) from a HuggingFace text-classification response.

    The Inference API returns either a list of label dicts or a list wrapping
    that list (``[[{"label": ..., "score": ...}, ...]]``). Returns the
    highest-scoring label, defaulting to neutral if nothing usable is found.
    """
    scores = payload
    if isinstance(scores, list) and scores and isinstance(scores[0], list):
        scores = scores[0]

    if not isinstance(scores, list) or not scores:
        return "neutral", 0.0

    top = max(scores, key=lambda item: item.get("score", 0.0))
    return top.get("label", "neutral").lower(), float(top.get("score", 0.0))


def score_headline(headline: str, api_key: str) -> float:
    """Scores a single headline's sentiment via FinBERT on the HuggingFace API.

    Returns a signed score: +score for positive, -score for negative, 0.0 for
    neutral. On any API failure returns 0.0 so one headline can't crash the agent.
    """
    try:
        response = httpx.post(
            FINBERT_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"inputs": headline},
            timeout=30.0,
        )
        response.raise_for_status()
        label, score = _extract_label_score(response.json())
    except Exception:
        logger.exception("Failed to score headline sentiment")
        return 0.0

    if label == "positive":
        return score
    if label == "negative":
        return -score
    return 0.0


def score_ticker_sentiment(ticker: str, news_items: list[NewsItem], api_key: str) -> float:
    """Averages the sentiment of every headline for a given ticker.

    Returns 0.0 when the ticker has no associated news.
    """
    headlines = [item.title for item in news_items if item.ticker == ticker]
    if not headlines:
        return 0.0

    total = sum(score_headline(headline, api_key) for headline in headlines)
    return total / len(headlines)


async def sentiment_agent(state: WatchmanState) -> WatchmanState:
    """Scores sentiment of news findings per ticker via FinBERT.

    Populates ``sentiment_scores`` with a ``{ticker: float}`` mapping.
    """
    api_key = settings.HUGGINGFACE_API_KEY
    news_items = state.get("news_findings", [])
    scores: dict[str, float] = {}
    for ticker in state.get("tickers", []):
        scores[ticker] = score_ticker_sentiment(ticker, news_items, api_key)

    state["sentiment_scores"] = scores
    return state

import json
import logging
import re
from datetime import datetime, timezone

from langchain_anthropic import ChatAnthropic

from app.core.config import settings
from app.models.state import Alert, Brief, BriefSection, WatchmanState

logger = logging.getLogger(__name__)

SYNTHESIS_MODEL = "claude-sonnet-4-6"
MAX_NEWS_PER_TICKER = 3


def build_synthesis_prompt(state: WatchmanState) -> str:
    """Builds the synthesis prompt from all findings gathered by the upstream agents.

    Assembles portfolio holdings, price movements, sentiment scores, recent news,
    upcoming earnings, and SEC filings into a single instruction that asks Claude
    to return a daily portfolio brief as JSON.
    """
    portfolio = state.get("portfolio", [])
    price_movements = state.get("price_movements", [])
    sentiment_scores = state.get("sentiment_scores", {})
    news_findings = state.get("news_findings", [])
    sec_findings = state.get("sec_findings", {})

    lines: list[str] = []

    lines.append("# Portfolio Holdings")
    if portfolio:
        for h in portfolio:
            lines.append(
                f"- {h.ticker}: {h.qty} shares, market value ${h.market_value:,.2f}"
            )
    else:
        lines.append("- (no holdings)")

    lines.append("\n# Price Movements")
    if price_movements:
        for m in price_movements:
            flag = " (SIGNIFICANT)" if m.is_significant else ""
            lines.append(f"- {m.ticker}: {m.change_pct:+.2f}% {m.direction}{flag}")
    else:
        lines.append("- (none)")

    lines.append("\n# Sentiment Scores (-1 negative … +1 positive)")
    if sentiment_scores:
        for ticker, score in sentiment_scores.items():
            lines.append(f"- {ticker}: {score:+.2f}")
    else:
        lines.append("- (none)")

    lines.append("\n# Recent News (top headlines per ticker)")
    if news_findings:
        per_ticker: dict[str, int] = {}
        for item in news_findings:
            count = per_ticker.get(item.ticker, 0)
            if count >= MAX_NEWS_PER_TICKER:
                continue
            per_ticker[item.ticker] = count + 1
            lines.append(f"- {item.ticker}: {item.title} ({item.source})")
    else:
        lines.append("- (none)")

    lines.append("\n# Upcoming Earnings & SEC Filings")
    if sec_findings:
        for ticker, data in sec_findings.items():
            earnings = data.get("earnings_date") or "unknown"
            lines.append(f"- {ticker}: next earnings {earnings}")
            for filing in data.get("filings", [])[:MAX_NEWS_PER_TICKER]:
                lines.append(
                    f"    - {filing.get('form')} on {filing.get('filing_date')}"
                )
    else:
        lines.append("- (none)")

    findings_block = "\n".join(lines)

    return f"""You are Watchman, a proactive portfolio intelligence analyst. Using the \
findings below, write a professional but conversational daily portfolio brief.

{findings_block}

Respond with ONLY valid JSON (no markdown fences) matching this schema:
{{
  "headline": "one-line summary of the day",
  "portfolio_health": <integer 0-100 based on overall sentiment and price movements>,
  "sections": [
    {{"title": "Market Summary", "body": "...", "tickers": ["AAPL"]}},
    {{"title": "Key Movers", "body": "...", "tickers": []}},
    {{"title": "News & Sentiment", "body": "...", "tickers": []}},
    {{"title": "Watch List", "body": "...", "tickers": []}}
  ],
  "alerts": [
    {{"ticker": "AAPL", "type": "earnings|price_move|concentration_risk", \
"title": "...", "body": "..."}}
  ]
}}

Include 3-4 sections (Market Summary, Key Movers, News & Sentiment, Watch List) and \
flag any alerts worth surfacing (upcoming earnings, significant price moves, \
concentration risk)."""


def _parse_brief_json(raw: str) -> dict:
    """Extracts a JSON object from the model response, tolerating markdown fences."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    return json.loads(text)


async def synthesis_agent(state: WatchmanState) -> WatchmanState:
    """Synthesizes all agent findings into a daily brief and alerts via Claude.

    On any failure (API error, malformed response) the brief is set to None and
    alerts to an empty list so the pipeline doesn't crash.
    """
    try:
        prompt = build_synthesis_prompt(state)
        llm = ChatAnthropic(
            model=SYNTHESIS_MODEL,
            api_key=settings.ANTHROPIC_API_KEY,
            max_tokens=4096,
        )
        response = await llm.ainvoke(prompt)
        content = response.content if isinstance(response.content, str) else str(response.content)
        data = _parse_brief_json(content)

        now = datetime.now(timezone.utc)
        sections = [BriefSection(**section) for section in data.get("sections", [])]
        alerts = [
            Alert(
                ticker=alert.get("ticker", ""),
                type=alert.get("type", ""),
                title=alert.get("title", ""),
                body=alert.get("body", ""),
                triggered_at=now,
            )
            for alert in data.get("alerts", [])
        ]

        brief = Brief(
            user_id=state["user_id"],
            date=now,
            headline=data.get("headline", ""),
            portfolio_health=int(data.get("portfolio_health", 0)),
            sections=sections,
            alerts=alerts,
        )

        state["brief"] = brief
        state["alerts"] = alerts
        state["generated_at"] = now
    except Exception:
        logger.exception("Failed to synthesize brief")
        state["brief"] = None
        state["alerts"] = []

    return state

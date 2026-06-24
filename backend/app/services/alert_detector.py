import logging
from datetime import date, datetime, timezone

from app.models.state import Alert, WatchmanState

logger = logging.getLogger(__name__)

# A single holding above this fraction of the portfolio is flagged as a
# concentration risk.
CONCENTRATION_THRESHOLD = 0.25
# Sentiment at or below this score is surfaced as a negative-news alert.
NEGATIVE_SENTIMENT_THRESHOLD = -0.3
# Earnings within this many days are flagged as upcoming.
EARNINGS_WINDOW_DAYS = 7


def _parse_earnings_date(value: object) -> date | None:
    """Parse an SEC earnings_date (ISO date or datetime string) into a date."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None


class AlertDetector:
    """Derives rule-based alerts from a completed pipeline ``WatchmanState``.

    Complements the alerts the synthesis agent surfaces with deterministic
    checks over the raw findings (price moves, earnings, concentration, news
    sentiment).
    """

    @staticmethod
    def detect_alerts(state: WatchmanState) -> list[Alert]:
        now = datetime.now(timezone.utc)
        alerts: list[Alert] = []

        # Significant price moves flagged by the fundamentals agent.
        for move in state.get("price_movements", []):
            if move.is_significant:
                alerts.append(
                    Alert(
                        ticker=move.ticker,
                        type="price_move",
                        title=f"{move.ticker} moved {move.change_pct:+.1f}%",
                        body=f"{move.ticker} is {move.direction} {abs(move.change_pct):.1f}% today.",
                        triggered_at=now,
                    )
                )

        # Earnings within the upcoming window, from SEC findings.
        for ticker, data in state.get("sec_findings", {}).items():
            earnings_date = _parse_earnings_date(data.get("earnings_date"))
            if earnings_date is None:
                continue
            days_away = (earnings_date - now.date()).days
            if 0 <= days_away <= EARNINGS_WINDOW_DAYS:
                alerts.append(
                    Alert(
                        ticker=ticker,
                        type="earnings",
                        title=f"{ticker} earnings in {days_away} day(s)",
                        body=f"{ticker} reports earnings on {earnings_date.isoformat()}.",
                        triggered_at=now,
                    )
                )

        # Concentration risk: any single holding above the threshold.
        portfolio = state.get("portfolio", [])
        total_value = sum(holding.market_value for holding in portfolio)
        if total_value > 0:
            for holding in portfolio:
                weight = holding.market_value / total_value
                if weight > CONCENTRATION_THRESHOLD:
                    alerts.append(
                        Alert(
                            ticker=holding.ticker,
                            type="concentration",
                            title=f"{holding.ticker} is {weight:.0%} of your portfolio",
                            body=(
                                f"{holding.ticker} makes up {weight:.0%} of total value, "
                                "above the 25% concentration threshold."
                            ),
                            triggered_at=now,
                        )
                    )

        # Negative news sentiment.
        for ticker, score in state.get("sentiment_scores", {}).items():
            if score < NEGATIVE_SENTIMENT_THRESHOLD:
                alerts.append(
                    Alert(
                        ticker=ticker,
                        type="news",
                        title=f"Negative sentiment on {ticker}",
                        body=f"Recent news sentiment for {ticker} is {score:+.2f}.",
                        triggered_at=now,
                    )
                )

        return alerts

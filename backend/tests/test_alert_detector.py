from datetime import date, timedelta

from app.models.state import Holding, PriceMove, WatchmanState
from app.services.alert_detector import AlertDetector


def _state(**overrides) -> WatchmanState:
    base: WatchmanState = WatchmanState(
        user_id="user-1",
        portfolio=[],
        tickers=[],
        news_findings=[],
        fundamental_findings=[],
        sentiment_scores={},
        price_movements=[],
        sec_findings={},
        brief=None,
        alerts=[],
        generated_at=None,
    )
    base.update(overrides)
    return base


def test_detects_price_move_alert_for_significant_mover():
    state = _state(
        price_movements=[
            PriceMove(ticker="AAPL", change_pct=-8.5, direction="down", is_significant=True),
            PriceMove(ticker="MSFT", change_pct=0.4, direction="up", is_significant=False),
        ]
    )
    alerts = AlertDetector.detect_alerts(state)
    price_alerts = [a for a in alerts if a.type == "price_move"]
    assert len(price_alerts) == 1
    assert price_alerts[0].ticker == "AAPL"


def test_detects_concentration_alert_when_holding_over_25_percent():
    state = _state(
        portfolio=[
            Holding(ticker="AAPL", qty=10, avg_entry_price=100, current_price=300, market_value=3000),
            Holding(ticker="MSFT", qty=10, avg_entry_price=100, current_price=100, market_value=1000),
        ]
    )
    alerts = AlertDetector.detect_alerts(state)
    concentration = [a for a in alerts if a.type == "concentration"]
    # AAPL is 75% (>25%); MSFT is 25% (not strictly above the threshold).
    assert len(concentration) == 1
    assert concentration[0].ticker == "AAPL"


def test_detects_earnings_alert_for_upcoming_date_within_7_days():
    upcoming = (date.today() + timedelta(days=3)).isoformat()
    state = _state(
        sec_findings={
            "AAPL": {"filings": [], "earnings_date": upcoming},
            "MSFT": {"filings": [], "earnings_date": (date.today() + timedelta(days=30)).isoformat()},
        }
    )
    alerts = AlertDetector.detect_alerts(state)
    earnings = [a for a in alerts if a.type == "earnings"]
    assert len(earnings) == 1
    assert earnings[0].ticker == "AAPL"


def test_returns_empty_list_when_no_alerts_triggered():
    state = _state(
        price_movements=[
            PriceMove(ticker="AAPL", change_pct=0.5, direction="up", is_significant=False)
        ],
        sentiment_scores={"AAPL": 0.2},
        sec_findings={"AAPL": {"filings": [], "earnings_date": None}},
    )
    assert AlertDetector.detect_alerts(state) == []

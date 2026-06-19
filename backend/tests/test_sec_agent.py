from datetime import date
from unittest.mock import MagicMock, patch

from app.agents.sec import fetch_cik_for_ticker, fetch_earnings_date


def _mock_atom_response(cik: str | None):
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    if cik is None:
        mock.text = "<feed></feed>"
    else:
        mock.text = f"<feed><company-info><cik>{cik}</cik></company-info></feed>"
    return mock


def test_fetch_cik_parses_response():
    """fetch_cik_for_ticker extracts the CIK from the EDGAR atom response."""
    with patch("app.agents.sec.httpx.get", return_value=_mock_atom_response("0000320193")):
        cik = fetch_cik_for_ticker("AAPL")

    assert cik == "0000320193"


def test_fetch_cik_handles_http_error_gracefully():
    """An HTTP failure returns None instead of raising."""
    with patch("app.agents.sec.httpx.get", side_effect=Exception("EDGAR down")):
        cik = fetch_cik_for_ticker("AAPL")

    assert cik is None


def test_fetch_earnings_date_from_calendar():
    """fetch_earnings_date pulls the next earnings date from the yfinance calendar."""
    mock_ticker = MagicMock()
    mock_ticker.calendar = {"Earnings Date": [date(2026, 7, 30)]}
    with patch("app.agents.sec.yf.Ticker", return_value=mock_ticker):
        earnings = fetch_earnings_date("AAPL")

    assert earnings == "2026-07-30"

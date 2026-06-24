import logging
import re

import httpx
import yfinance as yf

from app.models.state import WatchmanState

logger = logging.getLogger(__name__)

# EDGAR requires a descriptive User-Agent on every request.
EDGAR_HEADERS = {"User-Agent": "Watchman/1.0 contact@watchman.dev"}
EDGAR_BROWSE_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
RECENT_FILINGS_LIMIT = 5


def fetch_cik_for_ticker(ticker: str) -> str | None:
    """Looks up the SEC CIK number for a ticker via the EDGAR browse endpoint.

    Returns the (unpadded) CIK string, or None if it can't be resolved.
    """
    try:
        response = httpx.get(
            EDGAR_BROWSE_URL,
            params={
                "action": "getcompany",
                "ticker": ticker,
                "type": "",
                "dateb": "",
                "owner": "include",
                "count": "10",
                "search_text": "",
                "output": "atom",
            },
            headers=EDGAR_HEADERS,
            timeout=30.0,
        )
        response.raise_for_status()
    except Exception:
        logger.exception("Failed to fetch CIK for ticker %s", ticker)
        return None

    match = re.search(r"<cik>(\d+)</cik>", response.text, re.IGNORECASE)
    if not match:
        return None
    return match.group(1)


def fetch_recent_filings(cik: str) -> list[dict]:
    """Fetches the most recent filings for a company by CIK.

    Returns up to ``RECENT_FILINGS_LIMIT`` filings, each a dict with form type,
    filing date, and description. Returns an empty list on failure.
    """
    padded_cik = cik.zfill(10)
    try:
        response = httpx.get(
            EDGAR_SUBMISSIONS_URL.format(cik=padded_cik),
            headers=EDGAR_HEADERS,
            timeout=30.0,
        )
        response.raise_for_status()
        recent = response.json().get("filings", {}).get("recent", {})
    except Exception:
        logger.exception("Failed to fetch filings for CIK %s", cik)
        return []

    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    descriptions = recent.get("primaryDocDescription", [])

    filings: list[dict] = []
    for i in range(min(RECENT_FILINGS_LIMIT, len(forms))):
        filings.append(
            {
                "form": forms[i],
                "filing_date": dates[i] if i < len(dates) else None,
                "description": descriptions[i] if i < len(descriptions) else None,
            }
        )
    return filings


def fetch_earnings_date(ticker: str) -> str | None:
    """Fetches the next earnings date for a ticker via yfinance.

    Returns an ISO-format date string, or None if unavailable.
    """
    try:
        calendar = yf.Ticker(ticker).calendar
    except Exception:
        logger.exception("Failed to fetch earnings calendar for ticker %s", ticker)
        return None

    if not calendar:
        return None

    # calendar may be a dict ({"Earnings Date": [date, ...]}) or a DataFrame.
    earnings = None
    if isinstance(calendar, dict):
        earnings = calendar.get("Earnings Date")
    else:
        try:
            earnings = calendar.loc["Earnings Date"]
        except Exception:
            earnings = None

    if earnings is None:
        return None

    # Normalize a list/Series down to its first entry.
    if isinstance(earnings, (list, tuple)):
        earnings = earnings[0] if earnings else None
    elif hasattr(earnings, "iloc"):
        earnings = earnings.iloc[0] if len(earnings) else None

    if earnings is None:
        return None

    return earnings.isoformat() if hasattr(earnings, "isoformat") else str(earnings)


async def sec_agent(state: WatchmanState) -> WatchmanState:
    """Fetches recent SEC filings and upcoming earnings dates per ticker.

    Populates ``sec_findings`` with ``{ticker: {filings, earnings_date}}``.
    Failures on a single ticker are logged and skipped.
    """
    findings: dict[str, dict] = {}
    for ticker in state.get("tickers", []):
        try:
            cik = fetch_cik_for_ticker(ticker)
            filings = fetch_recent_filings(cik) if cik else []
            earnings_date = fetch_earnings_date(ticker)
        except Exception:
            logger.exception("Failed to gather SEC findings for ticker %s", ticker)
            continue
        findings[ticker] = {"filings": filings, "earnings_date": earnings_date}

    state["sec_findings"] = findings
    return state

import logging

import yfinance as yf

from app.models.state import FundamentalData, PriceMove, WatchmanState

logger = logging.getLogger(__name__)

# A daily move larger than this (in percent, absolute) is considered significant.
SIGNIFICANT_MOVE_PCT = 3.0


def fetch_fundamentals_for_ticker(ticker: str) -> FundamentalData:
    """Fetches current price and fundamental data for a single ticker via yfinance."""
    yf_ticker = yf.Ticker(ticker)
    fast_info = yf_ticker.fast_info

    current_price = fast_info.last_price
    previous_close = fast_info.previous_close
    change_pct = ((current_price - previous_close) / previous_close) * 100 if previous_close else 0.0

    # info is a heavier call; only trailingPE is pulled from it.
    pe_ratio = None
    try:
        pe_ratio = yf_ticker.info.get("trailingPE")
    except Exception:
        logger.exception("Failed to fetch info (PE ratio) for ticker %s", ticker)

    return FundamentalData(
        ticker=ticker,
        price=current_price,
        change_pct=change_pct,
        pe_ratio=pe_ratio,
        market_cap=fast_info.market_cap,
        volume=fast_info.three_month_average_volume,
    )


def classify_price_move(ticker: str, change_pct: float) -> PriceMove:
    """Classifies a daily percentage change into a direction and significance flag."""
    if change_pct > 0:
        direction = "up"
    elif change_pct < 0:
        direction = "down"
    else:
        direction = "flat"

    return PriceMove(
        ticker=ticker,
        change_pct=change_pct,
        direction=direction,
        is_significant=abs(change_pct) > SIGNIFICANT_MOVE_PCT,
    )


async def fundamentals_agent(state: WatchmanState) -> WatchmanState:
    """Fetches price/fundamental data per ticker and detects significant price moves.

    Iterates over every ticker, populating ``fundamental_findings`` and
    ``price_movements``. A failure on one ticker is logged and skipped so it
    can't crash the whole agent.
    """
    findings: list[FundamentalData] = []
    movements: list[PriceMove] = []
    for ticker in state.get("tickers", []):
        try:
            data = fetch_fundamentals_for_ticker(ticker)
        except Exception:
            logger.exception("Failed to fetch fundamentals for ticker %s", ticker)
            continue
        findings.append(data)
        movements.append(classify_price_move(ticker, data.change_pct))

    state["fundamental_findings"] = findings
    state["price_movements"] = movements
    return state

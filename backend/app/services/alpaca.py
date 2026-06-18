from fastapi import HTTPException, status

from alpaca.common.exceptions import APIError
from alpaca.trading.client import TradingClient

from app.core.config import settings


def _to_float(value) -> float | None:
    if value is None:
        return None
    return float(value)


class AlpacaService:
    """Thin wrapper around the Alpaca trading API for reading positions."""

    def __init__(self, api_key: str, secret_key: str) -> None:
        # alpaca-py selects the environment via the ``paper`` flag rather than a
        # base_url; derive it from the configured endpoint.
        paper = "paper" in settings.ALPACA_BASE_URL.lower()
        self.client = TradingClient(api_key, secret_key, paper=paper)

    def get_positions(self) -> list[dict]:
        """Return current Alpaca positions as plain dicts.

        Raises HTTPException 502 if the upstream Alpaca API errors.
        """
        try:
            positions = self.client.get_all_positions()
        except APIError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Alpaca API error: {exc}",
            ) from exc

        return [
            {
                "ticker": p.symbol,
                "qty": _to_float(p.qty),
                "avg_entry_price": _to_float(p.avg_entry_price),
                "current_price": _to_float(p.current_price),
                "market_value": _to_float(p.market_value),
            }
            for p in positions
        ]

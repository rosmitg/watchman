from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.alpaca import AlpacaService


@pytest.mark.asyncio
async def test_holdings_without_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/portfolio/holdings")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_sync_without_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/portfolio/sync")
    assert response.status_code == 403


def test_alpaca_get_positions_maps_fields():
    """AlpacaService maps Alpaca positions to plain dicts (Alpaca client mocked)."""
    fake_position = MagicMock(
        symbol="AAPL",
        qty="10",
        avg_entry_price="150.0",
        current_price="175.5",
        market_value="1755.0",
    )

    with patch("app.services.alpaca.TradingClient") as mock_client_cls:
        mock_client_cls.return_value.get_all_positions.return_value = [fake_position]
        service = AlpacaService("key", "secret")
        positions = service.get_positions()

    assert positions == [
        {
            "ticker": "AAPL",
            "qty": 10.0,
            "avg_entry_price": 150.0,
            "current_price": 175.5,
            "market_value": 1755.0,
        }
    ]

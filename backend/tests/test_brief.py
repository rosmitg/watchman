from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.dependencies import get_current_user_id
from app.main import app
from app.models.state import Brief, BriefSection


@pytest.mark.asyncio
async def test_today_without_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/brief/today")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_today_with_invalid_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/brief/today",
            headers={"Authorization": "Bearer not-a-real-token"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_generate_without_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/brief/generate")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_generate_runs_pipeline_and_returns_brief():
    """POST /brief/generate runs the pipeline and returns the saved Brief."""
    generated = Brief(
        user_id="user-123",
        date=datetime(2026, 6, 19),
        headline="Markets up on tech strength",
        portfolio_health=82,
        sections=[BriefSection(title="Market Summary", body="Solid day.", tickers=["AAPL"])],
        alerts=[],
    )

    # Auth + DB are dependency-injected; override rather than hit real services.
    app.dependency_overrides[get_current_user_id] = lambda: "user-123"
    app.dependency_overrides[get_db] = lambda: MagicMock()

    mock_portfolio = MagicMock()
    mock_portfolio.get_holdings = AsyncMock(return_value=[])
    mock_brief_service = MagicMock()
    mock_brief_service.save_brief = AsyncMock(return_value=generated)

    try:
        with (
            patch("app.api.routes.brief.PortfolioService", return_value=mock_portfolio),
            patch("app.api.routes.brief.BriefService", return_value=mock_brief_service),
            patch(
                "app.api.routes.brief.run_watchman_pipeline",
                new=AsyncMock(return_value=generated),
            ),
            patch("app.api.routes.brief.cache_brief", new=AsyncMock()) as mock_cache,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/brief/generate",
                    headers={"Authorization": "Bearer fake"},
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["headline"] == "Markets up on tech strength"
    assert body["portfolio_health"] == 82
    assert body["sections"][0]["title"] == "Market Summary"
    mock_cache.assert_awaited_once()

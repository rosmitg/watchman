import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


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

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.models.state import Alert


def test_websocket_rejected_with_invalid_token():
    """A malformed token is rejected with the 4001 close code before accept."""
    with TestClient(app) as client:
        try:
            with client.websocket_connect("/ws/user-1?token=not-a-real-token"):
                pass
        except WebSocketDisconnect as exc:
            assert exc.code == 4001
        else:
            raise AssertionError("expected the connection to be rejected")


def test_websocket_accepted_with_valid_token():
    """A valid token is accepted and queued alerts are flushed on connect."""

    async def _blocking_listen(*_args, **_kwargs):
        # Mimics a live channel with no new messages until disconnect.
        while True:
            await asyncio.sleep(3600)
        yield  # pragma: no cover - keeps this an async generator

    queued_alert = Alert(
        ticker="AAPL",
        type="price_move",
        title="AAPL moved -8.0%",
        body="AAPL is down 8.0% today.",
        triggered_at=datetime.now(timezone.utc),
    )

    mock_pubsub = MagicMock()
    mock_pubsub.listen = _blocking_listen

    mock_service = MagicMock()
    mock_service.get_queued_alerts = AsyncMock(return_value=[queued_alert])
    mock_service.clear_queued_alerts = AsyncMock()
    mock_service.subscribe = AsyncMock(return_value=mock_pubsub)
    mock_service.unsubscribe = AsyncMock()
    mock_service.aclose = AsyncMock()

    with TestClient(app) as client:
        with (
            patch(
                "app.api.routes.websocket.verify_supabase_jwt",
                return_value={"sub": "user-1"},
            ),
            patch(
                "app.api.routes.websocket.AlertService",
                return_value=mock_service,
            ),
        ):
            with client.websocket_connect("/ws/user-1?token=valid-token") as ws:
                data = ws.receive_json()

    assert data["ticker"] == "AAPL"
    assert data["type"] == "price_move"

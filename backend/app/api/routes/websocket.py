import asyncio
import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from app.core.security import verify_supabase_jwt
from app.services.alert_service import AlertService

logger = logging.getLogger(__name__)

router = APIRouter()

# Close code returned to clients that present a missing or invalid token.
INVALID_TOKEN_CLOSE_CODE = 4001


def _token_valid(token: str) -> bool:
    """Return True if the token is a valid Supabase JWT."""
    try:
        verify_supabase_jwt(token)
        return True
    except HTTPException:
        return False


async def _flush_queued_alerts(
    websocket: WebSocket, alert_service: AlertService, user_id: str
) -> None:
    """Send any alerts queued while the user was offline, then clear them."""
    queued = await alert_service.get_queued_alerts(user_id)
    for alert in queued:
        await websocket.send_text(alert.model_dump_json())
    if queued:
        await alert_service.clear_queued_alerts(user_id)


async def _forward_pubsub(websocket: WebSocket, pubsub) -> None:
    """Forward each published alert message to the WebSocket as JSON."""
    async for message in pubsub.listen():
        if message.get("type") == "message":
            await websocket.send_text(message["data"])


async def _watch_disconnect(websocket: WebSocket) -> None:
    """Block until the client disconnects (incoming frames are ignored)."""
    while True:
        await websocket.receive_text()


async def _stream_alerts(
    websocket: WebSocket, alert_service: AlertService, user_id: str
) -> None:
    """Stream live alerts until either the channel ends or the client leaves."""
    pubsub = await alert_service.subscribe(user_id)
    forward = asyncio.create_task(_forward_pubsub(websocket, pubsub))
    watch = asyncio.create_task(_watch_disconnect(websocket))
    try:
        done, _ = await asyncio.wait(
            {forward, watch}, return_when=asyncio.FIRST_COMPLETED
        )
    finally:
        for task in (forward, watch):
            task.cancel()
        await asyncio.gather(forward, watch, return_exceptions=True)
        await alert_service.unsubscribe(pubsub, user_id)

    # A completed watch task means the client went away — propagate it so the
    # endpoint runs its disconnect cleanup.
    if watch in done:
        raise WebSocketDisconnect()


@router.websocket("/ws/{user_id}")
async def alerts_websocket(websocket: WebSocket, user_id: str) -> None:
    """Real-time alert stream for a single user.

    Validates the ``?token=`` query param against Supabase before accepting,
    flushes any alerts queued while the user was offline, then streams live
    alerts published to the user's Redis channel until they disconnect.
    """
    token = websocket.query_params.get("token")
    if not token or not _token_valid(token):
        await websocket.close(code=INVALID_TOKEN_CLOSE_CODE)
        return

    await websocket.accept()
    connections: dict[str, WebSocket] = websocket.app.state.connections
    connections[user_id] = websocket

    alert_service = AlertService()
    try:
        await _flush_queued_alerts(websocket, alert_service, user_id)
        await _stream_alerts(websocket, alert_service, user_id)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Alert WebSocket failed for user %s", user_id)
    finally:
        # Only drop our own entry — a reconnect may have replaced it.
        if connections.get(user_id) is websocket:
            connections.pop(user_id, None)
        await alert_service.aclose()

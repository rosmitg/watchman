import redis.asyncio as aioredis

from app.core.redis import get_redis_client
from app.models.state import Alert

# Queued alerts live for 24h so a user who is offline still receives them on
# their next reconnect.
ALERT_TTL_SECONDS = 24 * 60 * 60


def alert_channel(user_id: str) -> str:
    """Redis pub/sub channel a user's live connection subscribes to."""
    return f"alerts:{user_id}"


def alert_key(user_id: str, ticker: str, timestamp: int) -> str:
    """Key under which a single queued alert is stored."""
    return f"alerts:{user_id}:{ticker}:{timestamp}"


def alert_key_pattern(user_id: str) -> str:
    """Glob pattern matching every queued alert for a user."""
    return f"alerts:{user_id}:*"


class AlertService:
    """Publishes alerts to live connections and queues them for offline users.

    Each alert is both published to the user's pub/sub channel (for any connected
    WebSocket) and stored under a per-alert key with a 24h TTL so offline users
    receive a backlog when they reconnect.
    """

    def __init__(self, client: aioredis.Redis | None = None):
        self._client = client or get_redis_client()

    async def publish_alert(self, user_id: str, alert: Alert) -> None:
        """Publish an alert live and queue it for later delivery."""
        payload = alert.model_dump_json()
        await self._client.publish(alert_channel(user_id), payload)
        timestamp = int(alert.triggered_at.timestamp())
        await self._client.set(
            alert_key(user_id, alert.ticker, timestamp),
            payload,
            ex=ALERT_TTL_SECONDS,
        )

    async def get_queued_alerts(self, user_id: str) -> list[Alert]:
        """Return all queued alerts for a user (e.g. on WebSocket connect)."""
        alerts: list[Alert] = []
        async for key in self._client.scan_iter(match=alert_key_pattern(user_id)):
            raw = await self._client.get(key)
            if raw is not None:
                alerts.append(Alert.model_validate_json(raw))
        return alerts

    async def clear_queued_alerts(self, user_id: str) -> None:
        """Delete every queued alert for a user once they've been flushed."""
        keys = [key async for key in self._client.scan_iter(match=alert_key_pattern(user_id))]
        if keys:
            await self._client.delete(*keys)

    async def subscribe(self, user_id: str) -> aioredis.client.PubSub:
        """Subscribe to a user's alert channel and return the PubSub handle."""
        pubsub = self._client.pubsub()
        await pubsub.subscribe(alert_channel(user_id))
        return pubsub

    async def unsubscribe(self, pubsub: aioredis.client.PubSub, user_id: str) -> None:
        """Unsubscribe and release a PubSub handle, ignoring teardown errors."""
        try:
            await pubsub.unsubscribe(alert_channel(user_id))
            await pubsub.aclose()
        except Exception:
            pass

    async def aclose(self) -> None:
        """Close the underlying Redis client."""
        await self._client.aclose()

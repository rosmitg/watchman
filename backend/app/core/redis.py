from datetime import date

import redis.asyncio as aioredis

from app.core.config import settings
from app.models.state import Brief

# Briefs are cached for 12 hours.
BRIEF_TTL_SECONDS = 12 * 60 * 60


def get_redis_client() -> aioredis.Redis:
    """Returns an async Redis client built from the configured REDIS_URL."""
    return aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )


def brief_cache_key(user_id: str) -> str:
    """Builds the cache key for a user's brief for the current day."""
    return f"brief:{user_id}:{date.today().isoformat()}"


async def cache_brief(user_id: str, brief: Brief) -> None:
    """Serialises a Brief to JSON and stores it in Redis with a 12-hour TTL."""
    client = get_redis_client()
    try:
        await client.set(
            brief_cache_key(user_id),
            brief.model_dump_json(),
            ex=BRIEF_TTL_SECONDS,
        )
    finally:
        await client.aclose()


async def get_cached_brief(user_id: str) -> Brief | None:
    """Retrieves and deserialises a cached Brief, or None if not present."""
    client = get_redis_client()
    try:
        raw = await client.get(brief_cache_key(user_id))
    finally:
        await client.aclose()

    if raw is None:
        return None
    return Brief.model_validate_json(raw)

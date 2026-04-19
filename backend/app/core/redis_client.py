"""Shared async Redis connection for rate limits, OTP storage, and Celery-adjacent features."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from app.core.config import settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    import redis.asyncio as redis_async

logger = get_logger(__name__)

_redis: Optional["redis_async.Redis"] = None


async def get_async_redis():
    """Return a singleton ``redis.asyncio.Redis`` client (decode_responses=True)."""
    global _redis
    if _redis is not None:
        return _redis

    try:
        import redis.asyncio as redis_async
    except ImportError as exc:  # pragma: no cover
        logger.error("redis_package_missing", error=str(exc))
        raise RuntimeError(
            "The 'redis' package is required for this feature. "
            "Install dependencies: pip install redis>=5.0.0"
        ) from exc

    _redis = redis_async.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )
    logger.info("redis_async_client_initialized")
    return _redis

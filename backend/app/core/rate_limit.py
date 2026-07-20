"""HTTP-layer rate limiting helpers."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_client import get_async_redis

logger = get_logger(__name__)

_memory_windows: Dict[str, Deque[float]] = defaultdict(deque)


@dataclass(frozen=True)
class RateLimit:
    """Fixed-window rate limit policy."""

    name: str
    limit: int
    window_seconds: int


def _client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


async def enforce_rate_limit(request: Request, policy: RateLimit, *, subject: str | None = None) -> None:
    """Enforce a rate limit using Redis, with dev-only in-memory fallback."""
    if not settings.RATE_LIMIT_ENABLED:
        return

    identity = subject or _client_identifier(request)
    key = f"rate-limit:{policy.name}:{identity}"

    try:
        redis = await get_async_redis()
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, policy.window_seconds)
        if current > policy.limit:
            ttl = await redis.ttl(key)
            retry_after = max(int(ttl), 1)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )
        return
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "rate_limit_backend_unavailable",
            policy=policy.name,
            error=str(exc),
        )
        if settings.is_production and settings.RATE_LIMIT_FAIL_CLOSED:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limit service unavailable.",
            )

    now = time.monotonic()
    window = _memory_windows[key]
    cutoff = now - policy.window_seconds
    while window and window[0] <= cutoff:
        window.popleft()
    if len(window) >= policy.limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(policy.window_seconds)},
        )
    window.append(now)


SCRAPING_RATE_LIMIT = RateLimit("scraping", settings.SCRAPING_RATE_LIMIT_PER_MINUTE, 60)
EXTERNAL_URL_PARSE_RATE_LIMIT = RateLimit("external-url-parse", 5, 60)
EXTERNAL_TEXT_PARSE_RATE_LIMIT = RateLimit("external-text-parse", 10, 60)
RECOMMENDATION_REGENERATE_RATE_LIMIT = RateLimit("recommendation-regenerate", 2, 3600)
CRON_RATE_LIMIT = RateLimit("cron", 10, 60)
PUBLIC_JOB_SEARCH_RATE_LIMIT = RateLimit("public-job-search", 60, 60)
PUBLIC_JOB_DETAIL_RATE_LIMIT = RateLimit("public-job-detail", 120, 60)
PUBLIC_JOB_SITEMAP_RATE_LIMIT = RateLimit("public-job-sitemap", 10, 60)
HANDOFF_VERIFY_RATE_LIMIT = RateLimit("handoff-verify", 20, 60)
ANALYTICS_INGEST_RATE_LIMIT = RateLimit("analytics-ingest", 300, 60)

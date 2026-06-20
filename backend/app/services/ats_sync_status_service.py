"""Operational status tracking for the ATS job mirror."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_client import get_async_redis

logger = get_logger(__name__)

ATS_SYNC_STATUS_KEY = "ats-sync:status"

_memory_status: Dict[str, Any] = {
    "status": "never_run",
    "last_run_at": None,
    "last_success_at": None,
    "last_error": None,
    "last_trigger": None,
    "counts": {
        "fetched": 0,
        "created": 0,
        "updated": 0,
        "archived": 0,
        "skipped": 0,
    },
    "updated_at": None,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utc_now().isoformat()


def _normalise_counts(stats: Dict[str, Any] | None) -> Dict[str, int]:
    stats = stats or {}
    return {
        "fetched": int(stats.get("fetched", 0) or 0),
        "created": int(stats.get("created", 0) or 0),
        "updated": int(stats.get("updated", 0) or 0),
        "archived": int(stats.get("archived", 0) or 0),
        "skipped": int(stats.get("skipped", 0) or 0),
    }


def _decode_status(raw: str | None) -> Dict[str, Any]:
    if not raw:
        return dict(_memory_status)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("ats_sync_status.invalid_json")
        return dict(_memory_status)
    return {**_memory_status, **parsed}


def _save_memory_status(status: Dict[str, Any]) -> None:
    _memory_status.clear()
    _memory_status.update(status)


def _write_status_sync(status: Dict[str, Any]) -> None:
    _save_memory_status(status)
    try:
        import redis

        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.set(ATS_SYNC_STATUS_KEY, json.dumps(status))
        client.close()
    except Exception as exc:  # pragma: no cover - environment-specific fallback
        logger.error("ats_sync_status.redis_write_failed", error=str(exc))


def _read_status_sync() -> Dict[str, Any]:
    try:
        import redis

        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            return _decode_status(client.get(ATS_SYNC_STATUS_KEY))
        finally:
            client.close()
    except Exception as exc:  # pragma: no cover - environment-specific fallback
        logger.error("ats_sync_status.redis_read_failed", error=str(exc))
        return dict(_memory_status)


async def _read_status_async() -> Dict[str, Any]:
    try:
        redis = await get_async_redis()
        return _decode_status(await redis.get(ATS_SYNC_STATUS_KEY))
    except Exception as exc:  # pragma: no cover - environment-specific fallback
        logger.error("ats_sync_status.redis_read_failed", error=str(exc))
        return dict(_memory_status)


def record_sync_started_sync(trigger: str) -> None:
    current = _read_status_sync()
    status = {
        **current,
        "status": "running",
        "last_run_at": _iso_now(),
        "last_error": None,
        "last_trigger": trigger,
        "updated_at": _iso_now(),
    }
    _write_status_sync(status)


def record_sync_success_sync(stats: Dict[str, Any], trigger: str) -> None:
    now = _iso_now()
    current = _read_status_sync()
    status = {
        **current,
        "status": "success",
        "last_run_at": now,
        "last_success_at": now,
        "last_error": None,
        "last_trigger": trigger,
        "counts": _normalise_counts(stats),
        "updated_at": now,
    }
    _write_status_sync(status)


def record_sync_failure_sync(error: str, trigger: str) -> None:
    now = _iso_now()
    current = _read_status_sync()
    status = {
        **current,
        "status": "failed",
        "last_run_at": now,
        "last_error": error,
        "last_trigger": trigger,
        "updated_at": now,
    }
    _write_status_sync(status)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def with_staleness(status: Dict[str, Any], *, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or _utc_now()
    last_success_at = _parse_datetime(status.get("last_success_at"))
    stale_after_minutes = settings.ATS_SYNC_STALE_AFTER_MINUTES
    age_seconds = None
    stale = True

    if last_success_at is not None:
        age_seconds = max(0, int((now - last_success_at).total_seconds()))
        stale = age_seconds > stale_after_minutes * 60

    return {
        **status,
        "stale": stale,
        "stale_after_minutes": stale_after_minutes,
        "age_seconds": age_seconds,
    }


async def get_sync_status_async() -> Dict[str, Any]:
    return with_staleness(await _read_status_async())

"""Redis-backed OTP storage + send rate limits for WhatsApp opt-in."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.core.config import settings

if TYPE_CHECKING:
    pass


def otp_hash(user_id: str, code: str) -> str:
    """HMAC-SHA256 hex digest — never store raw OTPs."""
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        f"{user_id}:{code}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def generate_otp_code() -> str:
    """Six-digit numeric OTP (leading zeros allowed)."""
    return f"{secrets.randbelow(1_000_000):06d}"


async def assert_otp_rate_limits(redis, user_id: str) -> None:
    """Raise 429 if hourly or daily OTP send caps are exceeded."""
    now = datetime.now(timezone.utc)
    hour_key = f"wa_otp_rl:h:{user_id}:{now.strftime('%Y%m%d%H')}"
    day_key = f"wa_otp_rl:d:{user_id}:{now.strftime('%Y%m%d')}"

    hour_count = await redis.incr(hour_key)
    if hour_count == 1:
        await redis.expire(hour_key, 3660)
    day_count = await redis.incr(day_key)
    if day_count == 1:
        await redis.expire(day_key, 90000)

    if hour_count > settings.WHATSAPP_OTP_MAX_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification code requests this hour. Try again later.",
        )
    if day_count > settings.WHATSAPP_OTP_MAX_PER_DAY:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification code requests today. Try again tomorrow.",
        )


async def store_otp(redis, user_id: str, code: str) -> None:
    await redis.setex(
        f"wa_otp:{user_id}",
        settings.WHATSAPP_OTP_TTL_SECONDS,
        otp_hash(user_id, code),
    )


async def verify_and_consume_otp(redis, user_id: str, code: str) -> bool:
    key = f"wa_otp:{user_id}"
    stored = await redis.get(key)
    if not stored:
        return False
    if not hmac.compare_digest(stored, otp_hash(user_id, code.strip())):
        return False
    await redis.delete(key)
    return True

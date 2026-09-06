"""Purpose-bound SMS password recovery. Redis is mandatory and fails closed.

No reset code or grant establishes an application session. Only a consumed grant
can authorize a password-only update to the previously verified Auth identity.
"""

import asyncio
import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_client import get_async_redis
from app.integrations.arkesel import arkesel_sms
from app.integrations.moolre import moolre_sms

logger = get_logger(__name__)
PREFIX = "auth:{password-reset}:"
CODE_TTL = 300
GRANT_TTL = 300
MAX_ATTEMPTS = 5
GENERIC_MESSAGE = "If this number belongs to an account with a verified phone, a reset code will arrive by SMS."
INVALID_CODE = "The code is invalid or expired. Request a new code if needed."
INVALID_GRANT = "This reset has expired or was already used. Request a new code."

LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[2]) end
if count > tonumber(ARGV[1]) then return math.max(redis.call('TTL', KEYS[1]), 1) end
return 0
"""
ARM_SCRIPT = """
if redis.call('GET', KEYS[2]) ~= ARGV[1] or redis.call('EXISTS', KEYS[1]) == 0 then return 0 end
local ttl = redis.call('TTL', KEYS[1])
if ttl <= 0 then return 0 end
local existing = cjson.decode(redis.call('GET', KEYS[1]))
local armed = cjson.decode(ARGV[2])
armed.attempts = existing.attempts
redis.call('SET', KEYS[1], cjson.encode(armed), 'EX', ttl)
return 1
"""
VERIFY_SCRIPT = """
local raw = redis.call('GET', KEYS[1])
if not raw then return 0 end
local data = cjson.decode(raw)
if redis.call('GET', data.index_key) ~= data.generation then redis.call('DEL', KEYS[1]); return 0 end
data.attempts = data.attempts + 1
if data.attempts > tonumber(ARGV[2]) then redis.call('DEL', KEYS[1]); return 0 end
if data.user_id ~= '' and data.code_hash == ARGV[1] then
  local grant = cjson.encode({user_id=data.user_id, binding=data.binding, index_key=data.index_key, generation=data.generation})
  redis.call('SET', KEYS[2], grant, 'EX', ARGV[3])
  redis.call('DEL', KEYS[1])
  return 1
end
if data.attempts >= tonumber(ARGV[2]) then
  redis.call('DEL', KEYS[1])
else
  redis.call('SET', KEYS[1], cjson.encode(data), 'KEEPTTL')
end
return 0
"""
CONSUME_SCRIPT = """
local raw = redis.call('GET', KEYS[1])
if not raw then return nil end
redis.call('DEL', KEYS[1])
local data = cjson.decode(raw)
if redis.call('GET', data.index_key) ~= data.generation then return nil end
redis.call('DEL', data.index_key)
return raw
"""


def digest(purpose: str, value: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"password-reset:{purpose}:{value}".encode(), hashlib.sha256).hexdigest()


def normalize_phone(value: str) -> str:
    phone = re.sub(r"[\s()-]", "", value.strip())
    if re.fullmatch(r"0[0-9]{9}", phone):
        phone = "+233" + phone[1:]
    elif re.fullmatch(r"233[0-9]{9}", phone):
        phone = "+" + phone
    elif re.fullmatch(r"[0-9]{9}", phone):
        phone = "+233" + phone
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", phone):
        raise ValueError("Enter a valid phone number, for example 024 123 4567.")
    return phone


def identity_binding(user: dict) -> str:
    # Any contact/password/profile update after the request invalidates recovery.
    fields = [user.get(key) for key in ("id", "email", "phone", "phone_confirmed_at", "updated_at")]
    return digest("identity", json.dumps(fields, separators=(",", ":")))


def verified_identity(user: dict, user_id: str, phone: str | None = None) -> bool:
    if str(user.get("id")) != user_id or not user.get("email") or not user.get("phone_confirmed_at") or not user.get("phone"):
        return False
    if user.get("deleted_at") or user.get("is_anonymous"):
        return False
    if user.get("banned_until"):
        try:
            if datetime.fromisoformat(user["banned_until"].replace("Z", "+00:00")) > datetime.now(timezone.utc):
                return False
        except (TypeError, ValueError):
            return False
    if phone is not None and "+" + user["phone"].lstrip("+") != phone:
        return False
    return True


def require_configuration() -> None:
    if not settings.auth_supabase_service_key.strip():
        logger.error('password_reset_configuration_missing', setting='auth_service_key')
        raise HTTPException(503, "Password reset is temporarily unavailable.")
    if not any(provider for _, provider in sms_providers()):
        logger.error('password_reset_configuration_missing', setting='sms_provider')
        raise HTTPException(503, "Password reset is temporarily unavailable.")


def sms_providers():
    available = {
        "arkesel": arkesel_sms if settings.ARKESEL_SMS_ENABLED and settings.ARKESEL_API_KEY.strip() and settings.ARKESEL_SENDER_ID.strip() else None,
        "moolre": moolre_sms if settings.MOOLRE_SMS_ENABLED and settings.MOOLRE_VAS_KEY.strip() and settings.MOOLRE_SENDER_ID.strip() else None,
    }
    for name in dict.fromkeys(item.strip().lower() for item in settings.SMS_PROVIDERS.split(',')):
        if available.get(name):
            yield name, available[name]


async def redis_call(method: str, *args, **kwargs):
    try:
        async with asyncio.timeout(3):
            redis = await get_async_redis()
            return await getattr(redis, method)(*args, **kwargs)
    except Exception as exc:
        logger.error("password_reset_state_unavailable", error_type=type(exc).__name__)
        raise HTTPException(503, "Password reset is temporarily unavailable.") from None


async def limit(scope: str, subject: str, count: int, seconds: int):
    retry = await redis_call('eval', LIMIT_SCRIPT, 1, PREFIX + 'limit:' + scope + ':' + digest('limit', subject), count, seconds)
    if retry:
        raise HTTPException(429, "Too many reset attempts. Please try again later.", headers={"Retry-After": str(retry)})


async def auth_user(user_id: str) -> dict | None:
    key = settings.auth_supabase_service_key
    if not key:
        raise HTTPException(503, "Password reset is temporarily unavailable.")
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(
                f"{settings.auth_supabase_url.rstrip('/')}/auth/v1/admin/users/{user_id}",
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
            )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        return data.get('user', data)
    except Exception as exc:
        logger.error("password_reset_auth_lookup_failed", error_type=type(exc).__name__)
        raise HTTPException(503, "Password reset is temporarily unavailable.") from None


async def create_challenge(phone: str, ip: str) -> str:
    require_configuration()
    for scope, subject, count, seconds in [
        ('request-ip', ip, 10, 900),
        ('request-phone', phone, 3, 3600), ('request-phone-day', phone, 10, 86400),
        ('request-cooldown', phone, 1, 60),
    ]:
        await limit(scope, subject, count, seconds)
    challenge = secrets.token_urlsafe(32)
    index_key = PREFIX + 'current:' + digest('subject', phone)
    data = dict(user_id='', binding='', code_hash='', attempts=0, index_key=index_key, generation=challenge)
    # A new generation invalidates earlier codes AND verified reset grants.
    await redis_call('set', index_key, challenge, ex=CODE_TTL + GRANT_TTL)
    await redis_call('set', PREFIX + 'code:' + challenge, json.dumps(data), ex=CODE_TTL)
    return challenge


async def deliver_challenge(challenge: str, user_id: str | None, phone: str) -> None:
    """Run after the generic response so lookup/provider timing cannot enumerate users.

    Delivery is best effort; worker shutdown leaves an unusable challenge, and
    users can request another. Never mark verification successful on delivery.
    """
    try:
        if not user_id:
            return
        user = await auth_user(user_id)
        if not user or not verified_identity(user, user_id, phone=phone):
            return
        code = f"{secrets.randbelow(1_000_000):06d}"
        index_key = PREFIX + 'current:' + digest('subject', phone)
        data = dict(user_id=user_id, binding=identity_binding(user), code_hash=digest('code', challenge + ':' + code), attempts=0, index_key=index_key, generation=challenge)
        armed = await redis_call('eval', ARM_SCRIPT, 2, PREFIX + 'code:' + challenge, index_key, challenge, json.dumps(data))
        if not armed:
            return
        for name, provider in sms_providers():
            try:
                await provider.send_auth_code(phone_e164=phone, otp=code, purpose='password_reset')
                logger.info('password_reset_sms_accepted', provider=name)
                return
            except Exception as exc:
                logger.warning('password_reset_sms_failed', provider=name, error_type=type(exc).__name__)
        await redis_call('delete', PREFIX + 'code:' + challenge)
    except Exception as exc:
        logger.error('password_reset_delivery_unavailable', error_type=type(exc).__name__)


async def verify_challenge(challenge: str, code: str, ip: str) -> str:
    await limit('verify-ip', ip, 30, 900)
    grant = secrets.token_urlsafe(32)
    valid = await redis_call('eval', VERIFY_SCRIPT, 2,
        PREFIX + 'code:' + challenge, PREFIX + 'grant:' + digest('grant', grant),
        digest('code', challenge + ':' + code), MAX_ATTEMPTS, GRANT_TTL)
    if not valid:
        raise HTTPException(400, INVALID_CODE)
    return grant


async def consume_grant(grant: str, ip: str) -> dict:
    await limit('complete-ip', ip, 20, 900)
    raw = await redis_call('eval', CONSUME_SCRIPT, 1, PREFIX + 'grant:' + digest('grant', grant))
    if not raw:
        raise HTTPException(400, INVALID_GRANT)
    return json.loads(raw)


async def change_password(user_id: str, password: str) -> None:
    key = settings.auth_supabase_service_key
    if not key:
        raise HTTPException(503, "Password reset is temporarily unavailable.")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.put(
                f"{settings.auth_supabase_url.rstrip('/')}/auth/v1/admin/users/{user_id}",
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
                json={"password": password},
            )
        if response.status_code in (400, 422):
            raise HTTPException(400, "Choose a stronger password and request a new reset code.")
        response.raise_for_status()
        # Supabase admin UpdatePassword(nil) removes all refresh sessions.
        logger.info('password_reset_completed', account_ref=digest('audit', user_id)[:16])
    except HTTPException:
        raise
    except Exception as exc:
        logger.error('password_reset_update_failed', error_type=type(exc).__name__)
        # The grant stays consumed on an ambiguous network failure.
        raise HTTPException(503, "Could not confirm the reset. Try signing in with your new password, or request a new code.") from None

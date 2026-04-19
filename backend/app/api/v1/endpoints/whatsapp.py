"""
WhatsApp opt-in / verification / webhook endpoints.

See ``docs/RECOMMENDATIONS_V2_PLAN.md`` §6. Authenticated routes live under
``/api/v1/notifications/whatsapp``. Meta's webhook lives at
``/api/v1/webhooks/whatsapp`` (GET challenge + POST events).
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.redis_client import get_async_redis
from app.integrations.whatsapp import (
    get_whatsapp_client,
    verify_webhook_signature,
)
from app.models.notification import (
    NotificationPreferences,
    WhatsappIncomingEvent,
    WhatsappMessage,
)
from app.services.whatsapp_otp import (
    assert_otp_rate_limits,
    generate_otp_code,
    store_otp,
    verify_and_consume_otp,
)

logger = get_logger(__name__)

router_notifications = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
router_webhooks = APIRouter(tags=["whatsapp-webhooks"])

_E164 = re.compile(r"^\+[1-9]\d{7,14}$")
_DIGEST_TIME = re.compile(r"^([01][0-9]|2[0-3]):[0-5][0-9]$")

STOP_KEYWORDS = frozenset(
    {
        "STOP",
        "STOPALL",
        "UNSUBSCRIBE",
        "OPTOUT",
        "END",
        "CANCEL",
    }
)


def _normalize_wa_phone(phone: str) -> str:
    digits = "".join(c for c in phone if c.isdigit())
    if not digits:
        return ""
    return f"+{digits}"


def _mask_phone(e164: Optional[str]) -> Optional[str]:
    if not e164 or len(e164) < 6:
        return None
    return f"{e164[:3]}…{e164[-2:]}"


def _validate_e164(phone: str) -> str:
    p = phone.strip().replace(" ", "")
    if not _E164.match(p):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Phone must be in international E.164 format (e.g. +233241234567).",
        )
    return p


def _get_or_create_prefs(db: Session, user_id: uuid.UUID) -> NotificationPreferences:
    row = (
        db.query(NotificationPreferences)
        .filter(NotificationPreferences.user_id == user_id)
        .first()
    )
    if row:
        return row
    row = NotificationPreferences(user_id=user_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


async def _redis_required():
    try:
        return await get_async_redis()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is required for WhatsApp verification. "
            "Install redis and set REDIS_URL.",
        ) from exc


class OptInRequest(BaseModel):
    phone: str = Field(..., description="E.164 phone, e.g. +233241234567")


class VerifyRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=10)


class PreferencesRequest(BaseModel):
    digest_time_local: Optional[str] = Field(None, description="HH:mm in 24h local time")
    timezone: Optional[str] = Field(None, description="IANA zone, e.g. Africa/Accra")


class WhatsappStatusResponse(BaseModel):
    whatsapp_opted_in: bool
    whatsapp_phone_verified: bool
    phone_masked: Optional[str] = None
    digest_time_local: str = "08:00"
    timezone: str = "UTC"


def _whatsapp_send_allowed() -> bool:
    """Dry-run works without WHATSAPP_ENABLED; live/sandbox requires the master switch."""
    if settings.WHATSAPP_SEND_MODE == "dry_run":
        return True
    return bool(settings.WHATSAPP_ENABLED)


@router_notifications.post("/opt-in", status_code=status.HTTP_202_ACCEPTED)
async def whatsapp_opt_in(
    body: OptInRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    redis=Depends(_redis_required),
):
    if not _whatsapp_send_allowed():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp is not enabled. Set WHATSAPP_ENABLED=true "
            "(or use WHATSAPP_SEND_MODE=dry_run for local testing without Meta).",
        )

    phone = _validate_e164(body.phone)
    uid = uuid.UUID(str(current_user["id"]))
    await assert_otp_rate_limits(redis, str(uid))

    code = generate_otp_code()
    prefs = _get_or_create_prefs(db, uid)
    prefs.whatsapp_phone_e164 = phone
    prefs.whatsapp_opted_in = False
    prefs.whatsapp_phone_verified_at = None
    prefs.whatsapp_opted_in_at = None
    prefs.whatsapp_opt_in_source = "profile_page"
    db.commit()

    client = get_whatsapp_client()
    try:
        await client.send_template(
            to_e164=phone,
            template_name=settings.WHATSAPP_TEMPLATE_OTP,
            language_code="en",
            body_parameters=[code],
        )
    except httpx.HTTPStatusError as exc:
        logger.warning("whatsapp_opt_in_send_failed", status=exc.response.status_code)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not send verification message via WhatsApp. Try again later.",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("whatsapp_opt_in_send_error")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="WhatsApp send failed.",
        ) from exc

    await store_otp(redis, str(uid), code)
    if settings.WHATSAPP_DEBUG_LOG_OTP:
        logger.warning(
            "whatsapp_otp_debug_enabled",
            user_id=str(uid),
            otp=code,
        )
    return {"detail": "Verification code sent.", "expires_in_seconds": settings.WHATSAPP_OTP_TTL_SECONDS}


@router_notifications.post("/verify", status_code=status.HTTP_200_OK)
async def whatsapp_verify(
    body: VerifyRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    redis=Depends(_redis_required),
):
    uid = uuid.UUID(str(current_user["id"]))
    code = body.code.strip()
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Enter the 6-digit code from WhatsApp.",
        )

    ok = await verify_and_consume_otp(redis, str(uid), code)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code.",
        )

    prefs = _get_or_create_prefs(db, uid)
    if not prefs.whatsapp_phone_e164:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No phone pending verification. Request a new code.",
        )
    prefs.whatsapp_phone_verified_at = datetime.now(timezone.utc)
    prefs.whatsapp_opted_in = True
    prefs.whatsapp_opted_in_at = datetime.now(timezone.utc)
    if not prefs.whatsapp_opt_in_source:
        prefs.whatsapp_opt_in_source = "profile_page"
    prefs.whatsapp_opted_out_at = None
    db.commit()
    return {"detail": "Phone verified. WhatsApp job alerts are on."}


@router_notifications.post("/opt-out", status_code=status.HTTP_200_OK)
async def whatsapp_opt_out(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = uuid.UUID(str(current_user["id"]))
    prefs = _get_or_create_prefs(db, uid)
    prefs.whatsapp_opted_in = False
    prefs.whatsapp_opted_out_at = datetime.now(timezone.utc)
    db.commit()
    return {"detail": "WhatsApp alerts turned off."}


@router_notifications.get("/status", response_model=WhatsappStatusResponse)
async def whatsapp_status(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = uuid.UUID(str(current_user["id"]))
    row = (
        db.query(NotificationPreferences)
        .filter(NotificationPreferences.user_id == uid)
        .first()
    )
    if not row:
        return WhatsappStatusResponse(
            whatsapp_opted_in=False,
            whatsapp_phone_verified=False,
            digest_time_local="08:00",
            timezone="UTC",
        )
    verified = row.whatsapp_phone_verified_at is not None
    return WhatsappStatusResponse(
        whatsapp_opted_in=bool(row.whatsapp_opted_in and verified),
        whatsapp_phone_verified=verified,
        phone_masked=_mask_phone(row.whatsapp_phone_e164),
        digest_time_local=row.whatsapp_digest_time_local or "08:00",
        timezone=row.whatsapp_timezone or "UTC",
    )


@router_notifications.post("/preferences", status_code=status.HTTP_200_OK)
async def whatsapp_preferences(
    body: PreferencesRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = uuid.UUID(str(current_user["id"]))
    prefs = _get_or_create_prefs(db, uid)

    if body.digest_time_local is not None:
        t = body.digest_time_local.strip()
        if not _DIGEST_TIME.match(t):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="digest_time_local must be HH:mm (24-hour).",
            )
        prefs.whatsapp_digest_time_local = t

    if body.timezone is not None:
        tz = body.timezone.strip()
        try:
            ZoneInfo(tz)
        except ZoneInfoNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown IANA timezone: {tz}",
            ) from exc
        prefs.whatsapp_timezone = tz

    db.commit()
    return {"detail": "Preferences saved."}


@router_webhooks.get("/whatsapp", response_class=PlainTextResponse)
async def whatsapp_webhook_verify(request: Request):
    """Meta subscription handshake (``hub.challenge`` echo)."""
    params = request.query_params
    if params.get("hub.mode") != "subscribe":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid mode")
    secret = (settings.WHATSAPP_VERIFY_TOKEN or "").strip()
    if not secret or params.get("hub.verify_token") != secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid verify token")
    challenge = params.get("hub.challenge") or ""
    return PlainTextResponse(challenge)


def _map_meta_status(s: str) -> str:
    s = (s or "").lower()
    if s in ("pending", "accepted"):
        return "queued"
    allowed = {
        "queued",
        "sent",
        "delivered",
        "read",
        "failed",
        "rate_limited",
        "opt_out_blocked",
    }
    if s in allowed:
        return s
    if s in ("deleted", "warning"):
        return "failed"
    return "failed"


@router_webhooks.post("/whatsapp", status_code=status.HTTP_200_OK)
async def whatsapp_webhook_events(
    request: Request,
    db: Session = Depends(get_db),
):
    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256")
    app_secret = (settings.WHATSAPP_APP_SECRET or "").strip()
    if app_secret:
        if not verify_webhook_signature(body, sig, app_secret=app_secret):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bad signature")
    else:
        logger.warning("whatsapp_webhook_no_app_secret_hmac_skipped")

    try:
        payload: Dict[str, Any] = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value") or {}
            await _process_whatsapp_value(db, value)

    db.commit()
    return {"detail": "ok"}


async def _process_whatsapp_value(db: Session, value: Dict[str, Any]) -> None:
    for st in value.get("statuses", []):
        wamid = st.get("id")
        meta_status = _map_meta_status(str(st.get("status", "")))
        ts_raw = st.get("timestamp")
        ts_dt: Optional[datetime] = None
        if ts_raw is not None:
            try:
                ts_dt = datetime.fromtimestamp(int(ts_raw), tz=timezone.utc)
            except (TypeError, ValueError, OSError):
                ts_dt = None

        row = (
            db.query(WhatsappMessage)
            .filter(WhatsappMessage.provider_message_id == wamid)
            .first()
        )
        if row:
            row.status = meta_status
            if meta_status == "sent" and ts_dt:
                row.sent_at = ts_dt
            if meta_status == "delivered" and ts_dt:
                row.delivered_at = ts_dt
            if meta_status == "read" and ts_dt:
                row.read_at = ts_dt

        phone_digits = "".join(
            c for c in str(st.get("recipient_id", "") or "") if c.isdigit()
        )
        phone = _normalize_wa_phone(phone_digits) if phone_digits else "+0"
        ev = WhatsappIncomingEvent(
            phone_e164=phone,
            user_id=None,
            event_type="status_update",
            body=json.dumps(st)[:2000],
            raw=st,
        )
        db.add(ev)

    for msg in value.get("messages", []):
        from_raw = str(msg.get("from", ""))
        phone = _normalize_wa_phone(from_raw)
        text_body = (msg.get("text") or {}).get("body") or ""
        body_upper = text_body.strip().upper()

        user_row = (
            db.query(NotificationPreferences)
            .filter(NotificationPreferences.whatsapp_phone_e164 == phone)
            .first()
        )
        uid = user_row.user_id if user_row else None

        if body_upper in STOP_KEYWORDS and user_row:
            user_row.whatsapp_opted_in = False
            user_row.whatsapp_opted_out_at = datetime.now(timezone.utc)
            logger.info("whatsapp_stop_keyword", user_id=str(uid), phone=_mask_phone(phone))

        ev = WhatsappIncomingEvent(
            phone_e164=phone or "+0",
            user_id=uid,
            event_type="text",
            body=text_body[:4000] if text_body else None,
            raw=msg,
        )
        db.add(ev)

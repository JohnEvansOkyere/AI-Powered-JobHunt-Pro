"""Email digest opt-in / preferences / unsubscribe / webhook endpoints.

See ``docs/features/EMAIL_JOB_DIGEST.md``. Authenticated routes live under
``/api/v1/notifications/email``. Two routes are deliberately unauthenticated:

* ``GET|POST /api/v1/notifications/email/unsubscribe`` — the footer and
  ``List-Unsubscribe`` link. It is authorised by a per-user random token, not
  a session, because a recipient must be able to unsubscribe from their mail
  client without logging in (RFC 8058 / CAN-SPAM).
* ``POST /api/v1/webhooks/email`` — Resend delivery events, authorised by the
  Svix HMAC signature.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.integrations.email import verify_webhook_signature
from app.models.notification import EmailMessage, NotificationPreferences
from app.models.user import User
from app.services.email_copy import LOCALE_PACKS, SUPPORTED_LOCALES
from app.services.email_digest import (
    EmailDigestDispatcher,
    EmailDigestSendError,
    new_unsubscribe_token,
)

logger = get_logger(__name__)

router_notifications = APIRouter(prefix="/email", tags=["email-notifications"])
router_webhooks = APIRouter(tags=["email-webhooks"])

_DIGEST_TIME_RE = r"^([01][0-9]|2[0-3]):[0-5][0-9]$"

# Resend event name -> (email_messages.status, timestamp column, suppression reason)
WEBHOOK_EVENT_MAP: Dict[str, str] = {
    "email.sent": "sent",
    "email.delivered": "delivered",
    "email.opened": "opened",
    "email.clicked": "clicked",
    "email.bounced": "bounced",
    "email.complained": "complained",
    "email.delivery_delayed": "queued",
}


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


def _validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Timezone must be a valid IANA name, e.g. Africa/Accra.",
        ) from exc
    return value


def _mask_email(address: Optional[str]) -> Optional[str]:
    if not address or "@" not in address:
        return None
    local, _, domain = address.partition("@")
    head = local[:2] if len(local) > 2 else local[:1]
    return f"{head}***@{domain}"


class EmailOptInRequest(BaseModel):
    email: Optional[EmailStr] = Field(
        None,
        description="Delivery address. Omit to use the account's signup email.",
    )
    locale: str = Field(
        default="en",
        description="Language pack: en | twi.",
    )
    digest_time_local: str = Field(default="07:00", pattern=_DIGEST_TIME_RE)
    timezone: str = Field(default="UTC")
    frequency: str = Field(default="daily")
    weekday: int = Field(default=1, ge=0, le=6)

    @field_validator("locale")
    @classmethod
    def _check_locale(cls, v: str) -> str:
        if v not in SUPPORTED_LOCALES:
            raise ValueError(f"locale must be one of {', '.join(SUPPORTED_LOCALES)}")
        return v

    @field_validator("frequency")
    @classmethod
    def _check_frequency(cls, v: str) -> str:
        if v not in ("daily", "weekly"):
            raise ValueError("frequency must be 'daily' or 'weekly'")
        return v


class EmailPreferencesRequest(BaseModel):
    locale: Optional[str] = None
    digest_time_local: Optional[str] = Field(None, pattern=_DIGEST_TIME_RE)
    timezone: Optional[str] = None
    frequency: Optional[str] = None
    weekday: Optional[int] = Field(None, ge=0, le=6)
    pause_until: Optional[datetime] = None

    @field_validator("locale")
    @classmethod
    def _check_locale(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in SUPPORTED_LOCALES:
            raise ValueError(f"locale must be one of {', '.join(SUPPORTED_LOCALES)}")
        return v

    @field_validator("frequency")
    @classmethod
    def _check_frequency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("daily", "weekly"):
            raise ValueError("frequency must be 'daily' or 'weekly'")
        return v


class EmailStatusResponse(BaseModel):
    email_opted_in: bool
    email_masked: Optional[str] = None
    suppressed: bool = False
    locale: str = "en"
    digest_time_local: str = "07:00"
    timezone: str = "UTC"
    frequency: str = "daily"
    weekday: int = 1
    paused_until: Optional[datetime] = None
    last_sent_at: Optional[datetime] = None
    available_locales: List[Dict[str, str]] = []


def _status_payload(
    db: Session,
    prefs: NotificationPreferences,
    address: Optional[str],
) -> EmailStatusResponse:
    last = (
        db.query(EmailMessage)
        .filter(
            EmailMessage.user_id == prefs.user_id,
            EmailMessage.sent_at.isnot(None),
        )
        .order_by(EmailMessage.sent_at.desc())
        .first()
    )
    return EmailStatusResponse(
        email_opted_in=bool(prefs.email_opted_in and not prefs.email_opted_out_at),
        email_masked=_mask_email(address),
        suppressed=EmailDigestDispatcher(db).is_suppressed(address or ""),
        locale=prefs.email_locale or "en",
        digest_time_local=prefs.email_digest_time_local or "07:00",
        timezone=prefs.email_timezone or "UTC",
        frequency=prefs.email_digest_frequency or "daily",
        weekday=int(prefs.email_digest_weekday or 1),
        paused_until=prefs.email_paused_until,
        last_sent_at=last.sent_at if last else None,
        available_locales=[
            {"code": pack.code, "label": pack.label} for pack in LOCALE_PACKS.values()
        ],
    )


def _account_email(db: Session, user_id: uuid.UUID) -> Optional[str]:
    user = db.get(User, user_id)
    return (user.email or "").strip() if user and user.email else None


@router_notifications.post("/opt-in", status_code=status.HTTP_200_OK)
async def email_opt_in(
    body: EmailOptInRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Record explicit consent for job digest emails."""
    user_id = uuid.UUID(str(current_user["id"]))
    _validate_timezone(body.timezone)

    address = (str(body.email) if body.email else None) or _account_email(db, user_id)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No email address on file. Provide one in the request body.",
        )

    dispatcher = EmailDigestDispatcher(db)
    if dispatcher.is_suppressed(address):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This address previously bounced or reported spam and cannot be "
            "re-subscribed. Use a different address or contact support.",
        )

    now = datetime.now(timezone.utc)
    prefs = _get_or_create_prefs(db, user_id)
    prefs.email_opted_in = True
    prefs.email_opted_in_at = now
    prefs.email_opt_in_source = "profile_page"
    prefs.email_address = address
    prefs.email_locale = body.locale
    prefs.email_digest_time_local = body.digest_time_local
    prefs.email_timezone = body.timezone
    prefs.email_digest_frequency = body.frequency
    prefs.email_digest_weekday = body.weekday
    prefs.email_opted_out_at = None
    prefs.email_paused_until = None
    # Rotate on re-opt-in so any previously leaked unsubscribe link is dead.
    prefs.email_unsubscribe_token = new_unsubscribe_token()

    user = db.get(User, user_id)
    if user and user.email_verified and (user.email or "").strip().lower() == address.lower():
        prefs.email_verified_at = now

    db.commit()
    db.refresh(prefs)
    logger.info("email_opt_in", user_id=str(user_id), locale=body.locale)
    return {"status": "subscribed", **_status_payload(db, prefs, address).model_dump()}


@router_notifications.post("/opt-out", status_code=status.HTTP_200_OK)
async def email_opt_out(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Withdraw consent. Preferences are kept so re-opting in is one click."""
    user_id = uuid.UUID(str(current_user["id"]))
    prefs = _get_or_create_prefs(db, user_id)
    prefs.email_opted_in = False
    prefs.email_opted_out_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("email_opt_out", user_id=str(user_id))
    return {"status": "unsubscribed"}


@router_notifications.get("/status", response_model=EmailStatusResponse)
async def email_status(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> EmailStatusResponse:
    """Current email digest subscription state for the signed-in user."""
    user_id = uuid.UUID(str(current_user["id"]))
    prefs = _get_or_create_prefs(db, user_id)
    address = (prefs.email_address or "").strip() or _account_email(db, user_id)
    return _status_payload(db, prefs, address)


@router_notifications.post("/preferences", status_code=status.HTTP_200_OK)
async def update_email_preferences(
    body: EmailPreferencesRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update dialect, send time, cadence or pause window."""
    user_id = uuid.UUID(str(current_user["id"]))
    prefs = _get_or_create_prefs(db, user_id)

    if body.locale is not None:
        prefs.email_locale = body.locale
    if body.digest_time_local is not None:
        prefs.email_digest_time_local = body.digest_time_local
    if body.timezone is not None:
        prefs.email_timezone = _validate_timezone(body.timezone)
    if body.frequency is not None:
        prefs.email_digest_frequency = body.frequency
    if body.weekday is not None:
        prefs.email_digest_weekday = body.weekday
    if body.pause_until is not None:
        prefs.email_paused_until = body.pause_until

    db.commit()
    db.refresh(prefs)
    address = (prefs.email_address or "").strip() or _account_email(db, user_id)
    return {"status": "updated", **_status_payload(db, prefs, address).model_dump()}


@router_notifications.post("/test-send", status_code=status.HTTP_200_OK)
async def send_test_digest(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Send the signed-in user their own digest now, bypassing the schedule.

    Useful for previewing a dialect. Still honours opt-in, suppression and the
    daily per-user cap, so it cannot be used to spam an address.
    """
    user_id = str(current_user["id"])
    dispatcher = EmailDigestDispatcher(db)
    try:
        return await dispatcher.send_digest_for_user(user_id)
    except EmailDigestSendError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Email provider rejected the send: {exc}",
        ) from exc


def _unsubscribe_page(message: str) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Email preferences</title></head>
<body style="margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:#f4f5f7;">
<div style="max-width:460px;margin:12vh auto;background:#fff;border:1px solid #e5e7eb;border-radius:16px;padding:32px;text-align:center;">
<p style="margin:0 0 10px;font-size:17px;font-weight:800;color:#4f46e5;">VeloxaHire</p>
<p style="margin:0 0 20px;font-size:15px;line-height:1.6;color:#374151;">{message}</p>
<a href="{(settings.APP_PUBLIC_URL or '').rstrip('/')}/dashboard/settings"
   style="display:inline-block;padding:11px 20px;background:#4f46e5;color:#fff;border-radius:10px;
          font-size:14px;font-weight:600;text-decoration:none;">Manage email settings</a>
</div></body></html>""",
        status_code=200,
    )


def _apply_unsubscribe(db: Session, token: str) -> bool:
    cleaned = (token or "").strip()
    if not cleaned:
        return False
    prefs = (
        db.query(NotificationPreferences)
        .filter(NotificationPreferences.email_unsubscribe_token == cleaned)
        .first()
    )
    if not prefs:
        return False
    if prefs.email_opted_in or not prefs.email_opted_out_at:
        prefs.email_opted_in = False
        prefs.email_opted_out_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("email_unsubscribe_via_token", user_id=str(prefs.user_id))
    return True


@router_notifications.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe_via_link(
    token: str = "",
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """One-click unsubscribe from the email footer. Intentionally unauthenticated."""
    if _apply_unsubscribe(db, token):
        return _unsubscribe_page(
            "You're unsubscribed from job match emails. "
            "You can turn them back on any time from your settings."
        )
    # Never reveal whether a token exists — always answer the same way.
    return _unsubscribe_page(
        "That unsubscribe link is no longer valid. "
        "You can manage job match emails from your settings."
    )


@router_notifications.post("/unsubscribe", status_code=status.HTTP_200_OK)
async def unsubscribe_one_click(
    token: str = "",
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """RFC 8058 ``List-Unsubscribe-Post`` target used by Gmail/Yahoo."""
    _apply_unsubscribe(db, token)
    return {"status": "unsubscribed"}


@router_webhooks.post("/email", status_code=status.HTTP_200_OK)
async def resend_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Ingest Resend delivery events and maintain the suppression list."""
    raw = await request.body()
    if not verify_webhook_signature(
        raw,
        svix_id=request.headers.get("svix-id"),
        svix_timestamp=request.headers.get("svix-timestamp"),
        svix_signature=request.headers.get("svix-signature"),
        secret=settings.RESEND_WEBHOOK_SECRET,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature.",
        )

    try:
        event = await request.json()
    except Exception:  # noqa: BLE001 - malformed body from provider
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed webhook payload.",
        )

    event_type = str(event.get("type") or "")
    data = event.get("data") or {}
    provider_id = data.get("email_id") or data.get("id")
    recipients = data.get("to") or []
    address = recipients[0] if isinstance(recipients, list) and recipients else None

    new_status = WEBHOOK_EVENT_MAP.get(event_type)
    if not new_status:
        return {"status": "ignored", "type": event_type}

    now = datetime.now(timezone.utc)
    message = None
    if provider_id:
        message = (
            db.query(EmailMessage)
            .filter(EmailMessage.provider_message_id == str(provider_id))
            .first()
        )

    if message:
        message.status = new_status
        if new_status == "delivered" and not message.delivered_at:
            message.delivered_at = now
        elif new_status == "opened" and not message.opened_at:
            message.opened_at = now
        elif new_status == "clicked" and not message.clicked_at:
            message.clicked_at = now
        elif new_status in ("bounced", "complained"):
            message.error_code = event_type
            message.error_message = str(data.get("reason") or "")[:1000]
        db.commit()
        address = address or message.email_address

    # A hard bounce or spam complaint must stop all future mail to that
    # address, regardless of what the user's preferences still say.
    if address and new_status in ("bounced", "complained"):
        bounce_type = str(data.get("bounce_type") or data.get("type") or "").lower()
        is_soft = "soft" in bounce_type or "transient" in bounce_type
        if new_status == "complained" or not is_soft:
            EmailDigestDispatcher(db).suppress(
                address,
                reason="complaint" if new_status == "complained" else "hard_bounce",
                detail=str(data.get("reason") or event_type)[:500],
            )
            logger.warning(
                "email_address_suppressed",
                event=event_type,
                address=_mask_email(address),
            )

    return {"status": "processed", "type": event_type}

"""WhatsApp Tier-1 recommendation digest dispatcher.

The dispatcher is deliberately small and conservative:

* only verified, opted-in users are eligible;
* local digest time is evaluated with the user's IANA timezone;
* a per-user local-date idempotency key prevents duplicate daily sends;
* every attempt is recorded in ``whatsapp_messages`` before the Meta call.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.whatsapp import get_whatsapp_client
from app.models.job_recommendation import JobRecommendation
from app.models.notification import NotificationPreferences, WhatsappMessage
from app.models.user import User

logger = get_logger(__name__)

ACTIVE_SEND_STATUSES = ("queued", "sent", "delivered", "read")
FAILED_RETRYABLE_STATUSES = ("failed", "rate_limited")
TEMPLATE_LANGUAGE = "en"


class WhatsappDigestSendError(RuntimeError):
    """Raised when a digest send should be retried by Celery."""


@dataclass(frozen=True)
class DueDigest:
    user_id: str
    local_date: str
    phone_e164: str


def utc_day_bounds(now: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """Return UTC [start, end) bounds for the day containing ``now``."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    start = datetime.combine(current.date(), time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def digest_idempotency_key(user_id: str, local_date: str) -> str:
    return f"whatsapp:digest:{user_id}:{local_date}"


def payload_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def digest_cta_url() -> str:
    base = (settings.APP_PUBLIC_URL or "http://localhost:3000").strip().rstrip("/")
    return f"{base}/dashboard/recommendations"


def _parse_digest_time(value: Optional[str]) -> time:
    raw = (value or "08:00").strip()
    try:
        hour_s, minute_s = raw.split(":", 1)
        return time(hour=int(hour_s), minute=int(minute_s[:2]))
    except (TypeError, ValueError):
        return time(hour=8, minute=0)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def digest_due_for_preferences(
    prefs: NotificationPreferences,
    now_utc: Optional[datetime] = None,
) -> Tuple[bool, Optional[str]]:
    """Return whether this preference row is due and its local date.

    The Beat task runs hourly, while users can store HH:mm. A digest is due
    once the scheduled local time is in the previous 60 minutes.
    """
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if not prefs.whatsapp_opted_in or not prefs.whatsapp_phone_verified_at:
        return False, None
    if prefs.whatsapp_opted_out_at or not prefs.whatsapp_phone_e164:
        return False, None
    if prefs.whatsapp_paused_until and _aware_utc(prefs.whatsapp_paused_until) > now:
        return False, None

    try:
        tz = ZoneInfo(prefs.whatsapp_timezone or "UTC")
    except ZoneInfoNotFoundError:
        logger.warning(
            "whatsapp_digest_invalid_timezone",
            user_id=str(prefs.user_id),
            timezone=prefs.whatsapp_timezone,
        )
        return False, None

    local_now = now.astimezone(tz)
    scheduled_time = _parse_digest_time(prefs.whatsapp_digest_time_local)
    scheduled_local = datetime.combine(local_now.date(), scheduled_time, tzinfo=tz)
    delta_seconds = (local_now - scheduled_local).total_seconds()
    if 0 <= delta_seconds < 3600:
        return True, local_now.date().isoformat()
    return False, local_now.date().isoformat()


def format_digest_job_list(recommendations: Sequence[JobRecommendation]) -> str:
    """Build the compact template parameter for recommended jobs."""
    lines: List[str] = []
    for idx, rec in enumerate(recommendations, start=1):
        job = rec.job
        if not job:
            continue
        title = " ".join((job.title or "Role").split())[:80]
        company = " ".join((job.company or "Company").split())[:60]
        location = " ".join((job.location or "").split())[:60]
        suffix = f" - {location}" if location else ""
        lines.append(f"{idx}. {title} at {company}{suffix}")
    return "\n".join(lines)


class WhatsappDigestDispatcher:
    """Find due users and send their Tier-1 recommendation digest."""

    def __init__(self, db: Session):
        self.db = db

    def due_users(self, now_utc: Optional[datetime] = None) -> List[DueDigest]:
        now = now_utc or datetime.now(timezone.utc)
        rows = (
            self.db.query(NotificationPreferences)
            .filter(
                NotificationPreferences.whatsapp_opted_in.is_(True),
                NotificationPreferences.whatsapp_phone_verified_at.isnot(None),
                NotificationPreferences.whatsapp_phone_e164.isnot(None),
                NotificationPreferences.whatsapp_opted_out_at.is_(None),
            )
            .all()
        )
        due: List[DueDigest] = []
        for prefs in rows:
            ok, local_date = digest_due_for_preferences(prefs, now)
            if ok and local_date:
                due.append(
                    DueDigest(
                        user_id=str(prefs.user_id),
                        local_date=local_date,
                        phone_e164=str(prefs.whatsapp_phone_e164),
                    )
                )
        return due

    async def send_digest_for_user(
        self,
        user_id: str,
        *,
        local_date: Optional[str] = None,
        now_utc: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        now = now_utc or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        uid = uuid.UUID(str(user_id))
        prefs = (
            self.db.query(NotificationPreferences)
            .filter(NotificationPreferences.user_id == uid)
            .first()
        )
        if not prefs or not self._can_send_to_preferences(prefs, now):
            return {"status": "skipped", "reason": "not_opted_in", "user_id": str(uid)}

        effective_local_date = local_date or self._local_date_for_prefs(prefs, now)
        idempotency_key = digest_idempotency_key(str(uid), effective_local_date)
        existing = (
            self.db.query(WhatsappMessage)
            .filter(WhatsappMessage.idempotency_key == idempotency_key)
            .first()
        )
        if existing and (
            existing.status in ACTIVE_SEND_STATUSES or existing.provider_message_id
        ):
            return {
                "status": "duplicate",
                "message_id": str(existing.id),
                "user_id": str(uid),
            }

        if self._global_send_budget_exhausted(now):
            return {"status": "skipped", "reason": "global_cap", "user_id": str(uid)}
        if self._user_send_budget_exhausted(uid, now):
            return {"status": "skipped", "reason": "user_cap", "user_id": str(uid)}

        recs = self._tier1_recommendations(uid, now)
        if not recs:
            return {"status": "skipped", "reason": "no_tier1", "user_id": str(uid)}

        job_list = format_digest_job_list(recs)
        if not job_list:
            return {"status": "skipped", "reason": "no_job_details", "user_id": str(uid)}

        user = self.db.get(User, uid)
        first_name = self._first_name(user)
        params = [first_name, job_list, digest_cta_url()]
        payload = {
            "to": prefs.whatsapp_phone_e164,
            "template": settings.WHATSAPP_TEMPLATE_DIGEST,
            "language": TEMPLATE_LANGUAGE,
            "body_parameters": params,
        }
        audit = existing or WhatsappMessage(
            user_id=uid,
            template_name=settings.WHATSAPP_TEMPLATE_DIGEST,
            template_language=TEMPLATE_LANGUAGE,
            phone_e164=prefs.whatsapp_phone_e164,
            payload_hash=payload_hash(payload),
            idempotency_key=idempotency_key,
            status="queued",
        )
        if existing:
            audit.status = "queued"
            audit.error_code = None
            audit.error_message = None
            audit.payload_hash = payload_hash(payload)
        else:
            self.db.add(audit)
        self.db.commit()

        try:
            response = await get_whatsapp_client().send_template(
                to_e164=str(prefs.whatsapp_phone_e164),
                template_name=settings.WHATSAPP_TEMPLATE_DIGEST,
                language_code=TEMPLATE_LANGUAGE,
                body_parameters=params,
            )
        except Exception as exc:  # noqa: BLE001 - Celery decides retry envelope
            audit.status = "failed"
            audit.error_code = exc.__class__.__name__
            audit.error_message = str(exc)[:1000]
            self.db.commit()
            logger.warning(
                "whatsapp_digest_send_failed",
                user_id=str(uid),
                error=str(exc),
            )
            raise WhatsappDigestSendError(str(exc)) from exc

        message = (response.get("messages") or [{}])[0]
        audit.provider_message_id = message.get("id")
        audit.status = "sent"
        audit.sent_at = now
        self.db.commit()
        return {
            "status": "sent",
            "message_id": str(audit.id),
            "provider_message_id": audit.provider_message_id,
            "jobs": len(recs),
            "user_id": str(uid),
        }

    def _can_send_to_preferences(
        self,
        prefs: NotificationPreferences,
        now: datetime,
    ) -> bool:
        if not prefs.whatsapp_opted_in or not prefs.whatsapp_phone_verified_at:
            return False
        if prefs.whatsapp_opted_out_at or not prefs.whatsapp_phone_e164:
            return False
        if prefs.whatsapp_paused_until and _aware_utc(prefs.whatsapp_paused_until) > now:
            return False
        return True

    def _local_date_for_prefs(self, prefs: NotificationPreferences, now: datetime) -> str:
        try:
            tz = ZoneInfo(prefs.whatsapp_timezone or "UTC")
        except ZoneInfoNotFoundError:
            tz = ZoneInfo("UTC")
        return now.astimezone(tz).date().isoformat()

    def _global_send_budget_exhausted(self, now: datetime) -> bool:
        start, end = utc_day_bounds(now)
        count = (
            self.db.query(WhatsappMessage)
            .filter(
                WhatsappMessage.template_name == settings.WHATSAPP_TEMPLATE_DIGEST,
                WhatsappMessage.created_at >= start,
                WhatsappMessage.created_at < end,
                WhatsappMessage.status.in_(ACTIVE_SEND_STATUSES),
            )
            .count()
        )
        return int(count or 0) >= int(settings.WHATSAPP_MAX_SENDS_PER_DAY)

    def _user_send_budget_exhausted(self, user_id: uuid.UUID, now: datetime) -> bool:
        start, end = utc_day_bounds(now)
        count = (
            self.db.query(WhatsappMessage)
            .filter(
                WhatsappMessage.user_id == user_id,
                WhatsappMessage.template_name == settings.WHATSAPP_TEMPLATE_DIGEST,
                WhatsappMessage.created_at >= start,
                WhatsappMessage.created_at < end,
                WhatsappMessage.status.in_(ACTIVE_SEND_STATUSES),
            )
            .count()
        )
        return int(count or 0) >= int(settings.WHATSAPP_MAX_SENDS_PER_USER_PER_DAY)

    def _tier1_recommendations(
        self,
        user_id: uuid.UUID,
        now: datetime,
    ) -> List[JobRecommendation]:
        return (
            self.db.query(JobRecommendation)
            .options(joinedload(JobRecommendation.job))
            .filter(
                and_(
                    JobRecommendation.user_id == user_id,
                    JobRecommendation.tier == "tier1",
                    JobRecommendation.expires_at > now,
                )
            )
            .order_by(JobRecommendation.match_score.desc())
            .limit(max(1, int(settings.WHATSAPP_DIGEST_MAX_JOBS)))
            .all()
        )

    def _first_name(self, user: Optional[User]) -> str:
        if not user or not user.full_name:
            return "there"
        first = user.full_name.strip().split()[0]
        return first[:40] if first else "there"

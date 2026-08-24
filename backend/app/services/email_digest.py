"""Email recommendation digest dispatcher.

Companion to :mod:`app.services.whatsapp_digest`, with the same conservative
rules:

* only opted-in, non-suppressed users are eligible;
* local digest time is evaluated with the user's IANA timezone;
* a per-user local-date idempotency key prevents duplicate sends;
* every attempt is recorded in ``email_messages`` before the provider call.

Email adds three things WhatsApp does not need: a hard suppression list fed by
bounce/complaint webhooks, a weekly cadence option, and one-click unsubscribe
tokens so the footer link works without a logged-in session.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.email import get_email_client
from app.models.job_recommendation import JobRecommendation
from app.models.notification import (
    EmailMessage,
    EmailSuppression,
    NotificationPreferences,
)
from app.models.user import User
from app.services.email_copy import DigestJob, render_digest

logger = get_logger(__name__)

ACTIVE_SEND_STATUSES = ("queued", "sent", "delivered", "opened", "clicked")
TEMPLATE_NAME = "job_recommendation_digest"


class EmailDigestSendError(RuntimeError):
    """Raised when a digest send should be retried by Celery."""


@dataclass(frozen=True)
class DueEmailDigest:
    user_id: str
    local_date: str
    email_address: str


def utc_day_bounds(now: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """Return UTC [start, end) bounds for the day containing ``now``."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    start = datetime.combine(current.date(), time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def digest_idempotency_key(user_id: str, local_date: str) -> str:
    return f"email:digest:{user_id}:{local_date}"


def payload_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _base_app_url() -> str:
    return (settings.APP_PUBLIC_URL or "http://localhost:3000").strip().rstrip("/")


def _base_api_url() -> str:
    return (settings.API_PUBLIC_URL or "http://localhost:8000").strip().rstrip("/")


def digest_cta_url() -> str:
    return f"{_base_app_url()}/dashboard/recommendations"


def settings_url() -> str:
    return f"{_base_app_url()}/dashboard/settings"


def unsubscribe_url(token: str) -> str:
    return f"{_base_api_url()}/api/v1/notifications/email/unsubscribe?token={token}"


def job_url(job: Any) -> str:
    """Prefer our own job page so clicks are attributable; fall back to source."""
    job_id = getattr(job, "id", None)
    if job_id:
        return f"{_base_app_url()}/jobs/{job_id}"
    return (getattr(job, "source_url", None) or getattr(job, "job_link", None) or "").strip()


def new_unsubscribe_token() -> str:
    return secrets.token_urlsafe(32)


def _parse_digest_time(value: Optional[str]) -> time:
    raw = (value or "07:00").strip()
    try:
        hour_s, minute_s = raw.split(":", 1)
        return time(hour=int(hour_s), minute=int(minute_s[:2]))
    except (TypeError, ValueError):
        return time(hour=7, minute=0)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def digest_due_for_preferences(
    prefs: NotificationPreferences,
    now_utc: Optional[datetime] = None,
) -> Tuple[bool, Optional[str]]:
    """Return whether this preference row is due and its local date.

    Beat runs hourly while users store HH:mm, so a digest is due once the
    scheduled local time falls in the previous 60 minutes. Weekly subscribers
    additionally have to match ``email_digest_weekday`` (0=Monday).
    """
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if not prefs.email_opted_in or prefs.email_opted_out_at:
        return False, None
    if prefs.email_paused_until and _aware_utc(prefs.email_paused_until) > now:
        return False, None

    try:
        tz = ZoneInfo(prefs.email_timezone or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        logger.warning(
            "email_digest_invalid_timezone",
            user_id=str(prefs.user_id),
            timezone=prefs.email_timezone,
        )
        return False, None

    local_now = now.astimezone(tz)
    local_date = local_now.date().isoformat()

    if (prefs.email_digest_frequency or "daily") == "weekly":
        if local_now.weekday() != int(prefs.email_digest_weekday or 0):
            return False, local_date

    scheduled_time = _parse_digest_time(prefs.email_digest_time_local)
    scheduled_local = datetime.combine(local_now.date(), scheduled_time, tzinfo=tz)
    delta_seconds = (local_now - scheduled_local).total_seconds()
    if 0 <= delta_seconds < 3600:
        return True, local_date
    return False, local_date


def to_digest_jobs(recommendations: Sequence[JobRecommendation]) -> List[DigestJob]:
    """Flatten recommendation rows into the renderer's view model."""
    rows: List[DigestJob] = []
    for rec in recommendations:
        job = rec.job
        if not job or not job.title:
            continue
        rows.append(
            DigestJob(
                title=job.title,
                company=job.company or "",
                location=job.location or "",
                url=job_url(job),
                match_score=rec.match_score,
                match_reason=rec.match_reason,
                salary=job.salary_range,
                job_type=job.job_type,
            )
        )
    return rows


class EmailDigestDispatcher:
    """Find due users and send their recommendation digest."""

    def __init__(self, db: Session):
        self.db = db

    # -- discovery ---------------------------------------------------------

    def due_users(self, now_utc: Optional[datetime] = None) -> List[DueEmailDigest]:
        now = now_utc or datetime.now(timezone.utc)
        rows = (
            self.db.query(NotificationPreferences)
            .filter(
                NotificationPreferences.email_opted_in.is_(True),
                NotificationPreferences.email_opted_out_at.is_(None),
            )
            .all()
        )
        due: List[DueEmailDigest] = []
        for prefs in rows:
            ok, local_date = digest_due_for_preferences(prefs, now)
            if not ok or not local_date:
                continue
            address = self._resolve_address(prefs)
            if not address:
                continue
            due.append(
                DueEmailDigest(
                    user_id=str(prefs.user_id),
                    local_date=local_date,
                    email_address=address,
                )
            )
        return due

    # -- sending -----------------------------------------------------------

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

        address = self._resolve_address(prefs)
        if not address:
            return {"status": "skipped", "reason": "no_address", "user_id": str(uid)}
        if self.is_suppressed(address):
            return {"status": "skipped", "reason": "suppressed", "user_id": str(uid)}

        effective_local_date = local_date or self._local_date_for_prefs(prefs, now)
        idempotency_key = digest_idempotency_key(str(uid), effective_local_date)
        existing = (
            self.db.query(EmailMessage)
            .filter(EmailMessage.idempotency_key == idempotency_key)
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

        recs = self._recommendations(uid, now)
        jobs = to_digest_jobs(recs)
        if len(jobs) < max(1, int(settings.EMAIL_DIGEST_MIN_JOBS)):
            return {
                "status": "skipped",
                "reason": "not_enough_matches",
                "matches": len(jobs),
                "user_id": str(uid),
            }

        user = self.db.get(User, uid)
        token = self._ensure_unsubscribe_token(prefs)
        rendered = render_digest(
            locale=prefs.email_locale or settings.EMAIL_DEFAULT_LOCALE,
            first_name=self._first_name(user),
            jobs=jobs,
            user_id=str(uid),
            on_date=date.fromisoformat(effective_local_date),
            cta_url=digest_cta_url(),
            unsubscribe_url=unsubscribe_url(token),
            settings_url=settings_url(),
        )

        content_hash = payload_hash(
            {
                "subject": rendered["subject"],
                "jobs": [f"{j.title}|{j.company}|{j.url}" for j in jobs],
            }
        )
        if self._identical_to_last_send(uid, content_hash):
            return {
                "status": "skipped",
                "reason": "unchanged_since_last_send",
                "user_id": str(uid),
            }

        audit = existing or EmailMessage(
            user_id=uid,
            email_address=address,
            template_name=TEMPLATE_NAME,
            locale=rendered["locale"],
            subject=rendered["subject"],
            payload_hash=content_hash,
            idempotency_key=idempotency_key,
            status="queued",
            job_count=len(jobs),
        )
        if existing:
            audit.status = "queued"
            audit.error_code = None
            audit.error_message = None
            audit.email_address = address
            audit.locale = rendered["locale"]
            audit.subject = rendered["subject"]
            audit.payload_hash = content_hash
            audit.job_count = len(jobs)
        else:
            self.db.add(audit)
        self.db.commit()

        # RFC 8058 one-click unsubscribe. Gmail and Yahoo require these headers
        # for bulk senders; without them the digest is far likelier to be
        # filtered as spam.
        headers = {
            "List-Unsubscribe": f"<{unsubscribe_url(token)}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }

        try:
            response = await get_email_client().send_email(
                to=address,
                subject=rendered["subject"],
                html=rendered["html"],
                text=rendered["text"],
                headers=headers,
                tags=[
                    {"name": "template", "value": TEMPLATE_NAME},
                    {"name": "locale", "value": rendered["locale"]},
                ],
            )
        except Exception as exc:  # noqa: BLE001 - Celery decides the retry envelope
            audit.status = "failed"
            audit.error_code = exc.__class__.__name__
            audit.error_message = str(exc)[:1000]
            self.db.commit()
            logger.warning(
                "email_digest_send_failed",
                user_id=str(uid),
                error=str(exc),
            )
            raise EmailDigestSendError(str(exc)) from exc

        audit.provider_message_id = response.get("id")
        audit.status = "sent"
        audit.sent_at = now
        self.db.commit()
        logger.info(
            "email_digest_sent",
            user_id=str(uid),
            locale=rendered["locale"],
            jobs=len(jobs),
        )
        return {
            "status": "sent",
            "message_id": str(audit.id),
            "provider_message_id": audit.provider_message_id,
            "locale": rendered["locale"],
            "jobs": len(jobs),
            "user_id": str(uid),
        }

    # -- suppression -------------------------------------------------------

    def is_suppressed(self, address: str) -> bool:
        normalized = (address or "").strip().lower()
        if not normalized:
            return True
        return (
            self.db.query(EmailSuppression)
            .filter(func.lower(EmailSuppression.email_address) == normalized)
            .first()
            is not None
        )

    def suppress(self, address: str, *, reason: str, detail: Optional[str] = None) -> None:
        """Add an address to the permanent blocklist (idempotent)."""
        normalized = (address or "").strip().lower()
        if not normalized:
            return
        if self.is_suppressed(normalized):
            return
        self.db.add(
            EmailSuppression(
                email_address=normalized,
                reason=reason,
                detail=(detail or None),
            )
        )
        self.db.commit()

    # -- internals ---------------------------------------------------------

    def _can_send_to_preferences(
        self,
        prefs: NotificationPreferences,
        now: datetime,
    ) -> bool:
        if not prefs.email_opted_in or prefs.email_opted_out_at:
            return False
        if prefs.email_paused_until and _aware_utc(prefs.email_paused_until) > now:
            return False
        return True

    def _resolve_address(self, prefs: NotificationPreferences) -> Optional[str]:
        explicit = (prefs.email_address or "").strip()
        if explicit:
            return explicit
        user = self.db.get(User, prefs.user_id)
        if not user or not user.is_active:
            return None
        return (user.email or "").strip() or None

    def _ensure_unsubscribe_token(self, prefs: NotificationPreferences) -> str:
        if prefs.email_unsubscribe_token:
            return str(prefs.email_unsubscribe_token)
        token = new_unsubscribe_token()
        prefs.email_unsubscribe_token = token
        self.db.commit()
        return token

    def _local_date_for_prefs(self, prefs: NotificationPreferences, now: datetime) -> str:
        try:
            tz = ZoneInfo(prefs.email_timezone or "UTC")
        except (ZoneInfoNotFoundError, ValueError):
            tz = ZoneInfo("UTC")
        return now.astimezone(tz).date().isoformat()

    def _global_send_budget_exhausted(self, now: datetime) -> bool:
        start, end = utc_day_bounds(now)
        count = (
            self.db.query(EmailMessage)
            .filter(
                EmailMessage.template_name == TEMPLATE_NAME,
                EmailMessage.created_at >= start,
                EmailMessage.created_at < end,
                EmailMessage.status.in_(ACTIVE_SEND_STATUSES),
            )
            .count()
        )
        return int(count or 0) >= int(settings.EMAIL_MAX_SENDS_PER_DAY)

    def _user_send_budget_exhausted(self, user_id: uuid.UUID, now: datetime) -> bool:
        start, end = utc_day_bounds(now)
        count = (
            self.db.query(EmailMessage)
            .filter(
                EmailMessage.user_id == user_id,
                EmailMessage.template_name == TEMPLATE_NAME,
                EmailMessage.created_at >= start,
                EmailMessage.created_at < end,
                EmailMessage.status.in_(ACTIVE_SEND_STATUSES),
            )
            .count()
        )
        return int(count or 0) >= int(settings.EMAIL_MAX_SENDS_PER_USER_PER_DAY)

    def _identical_to_last_send(self, user_id: uuid.UUID, content_hash: str) -> bool:
        """Skip a digest whose job list is byte-identical to the last one sent.

        Recommendations only refresh every 12h, so without this a user on a
        daily cadence can receive the same six jobs twice.
        """
        last = (
            self.db.query(EmailMessage)
            .filter(
                EmailMessage.user_id == user_id,
                EmailMessage.template_name == TEMPLATE_NAME,
                EmailMessage.status.in_(ACTIVE_SEND_STATUSES),
            )
            .order_by(EmailMessage.created_at.desc())
            .first()
        )
        return bool(last and last.payload_hash == content_hash)

    def _recommendations(
        self,
        user_id: uuid.UUID,
        now: datetime,
    ) -> List[JobRecommendation]:
        """Tier-1 first, topped up with Tier-2 so the digest is never thin."""
        limit = max(1, int(settings.EMAIL_DIGEST_MAX_JOBS))
        base = (
            self.db.query(JobRecommendation)
            .options(joinedload(JobRecommendation.job))
            .filter(
                and_(
                    JobRecommendation.user_id == user_id,
                    JobRecommendation.expires_at > now,
                )
            )
        )
        tier1 = (
            base.filter(JobRecommendation.tier == "tier1")
            .order_by(JobRecommendation.match_score.desc())
            .limit(limit)
            .all()
        )
        if len(tier1) >= limit:
            return tier1

        top_up = (
            base.filter(JobRecommendation.tier == "tier2")
            .order_by(JobRecommendation.match_score.desc())
            .limit(limit - len(tier1))
            .all()
        )
        return tier1 + top_up

    def _first_name(self, user: Optional[User]) -> str:
        if not user or not user.full_name:
            return "there"
        first = user.full_name.strip().split()
        if not first:
            return "there"
        return first[0][:40]

"""Notification preference + WhatsApp audit models.

Mirrors ``migrations/009_add_whatsapp.sql`` (WhatsApp) and
``migrations/018_add_email_digests.sql`` (email). See
``docs/RECOMMENDATIONS_V2_PLAN.md`` §6.3 and
``docs/features/EMAIL_JOB_DIGEST.md``. :class:`NotificationPreferences` is
channel-scoped by column prefix so a third channel needs no schema rewrite.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.core.database import Base


class NotificationPreferences(Base):
    """Per-user channel consent + delivery preferences.

    Primary key is ``user_id`` (one row per user). Consent columns are
    prefixed per channel (``whatsapp_*``, ``email_*``); each channel's
    dispatcher reads only its own prefix.
    """

    __tablename__ = "notification_preferences"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # WhatsApp consent state. `whatsapp_opted_in` is the single source of
    # truth for "may we send this user a marketing template"; the dispatcher
    # MUST read it and MUST NOT rely on just `phone_verified_at`.
    whatsapp_opted_in = Column(Boolean, nullable=False, default=False)
    whatsapp_opted_in_at = Column(TIMESTAMP(timezone=True), nullable=True)
    whatsapp_opt_in_source = Column(Text, nullable=True)
    whatsapp_phone_e164 = Column(Text, nullable=True)
    whatsapp_phone_verified_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Delivery windowing.
    whatsapp_digest_time_local = Column(Text, nullable=False, default="08:00")
    whatsapp_timezone = Column(Text, nullable=False, default="UTC")

    # Opt-out / pause state.
    whatsapp_opted_out_at = Column(TIMESTAMP(timezone=True), nullable=True)
    whatsapp_paused_until = Column(TIMESTAMP(timezone=True), nullable=True)

    # Email consent state. `email_opted_in` is the single source of truth for
    # "may we send this user a digest"; a verified Supabase address alone is
    # NOT consent. `email_address` is optional — NULL falls back to users.email.
    email_opted_in = Column(Boolean, nullable=False, default=False)
    email_opted_in_at = Column(TIMESTAMP(timezone=True), nullable=True)
    email_opt_in_source = Column(Text, nullable=True)
    email_address = Column(Text, nullable=True)
    email_verified_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Email delivery windowing + dialect.
    email_digest_time_local = Column(Text, nullable=False, default="07:00")
    email_timezone = Column(Text, nullable=False, default="UTC")
    email_locale = Column(Text, nullable=False, default="en")
    email_digest_frequency = Column(Text, nullable=False, default="daily")
    email_digest_weekday = Column(SmallInteger, nullable=False, default=1)

    # Email opt-out / pause state.
    email_opted_out_at = Column(TIMESTAMP(timezone=True), nullable=True)
    email_paused_until = Column(TIMESTAMP(timezone=True), nullable=True)

    # Random secret backing one-click unsubscribe links (no auth session).
    email_unsubscribe_token = Column(Text, nullable=True, unique=True)

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "whatsapp_opt_in_source IS NULL "
            "OR whatsapp_opt_in_source IN ('signup', 'profile_page', 'admin')",
            name="notification_preferences_opt_in_source_check",
        ),
        CheckConstraint(
            r"whatsapp_digest_time_local ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$'",
            name="notification_preferences_digest_time_format",
        ),
        CheckConstraint(
            "email_opt_in_source IS NULL "
            "OR email_opt_in_source IN ('signup', 'profile_page', 'admin')",
            name="notification_preferences_email_opt_in_source_check",
        ),
        CheckConstraint(
            r"email_digest_time_local ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$'",
            name="notification_preferences_email_digest_time_format",
        ),
        CheckConstraint(
            "email_locale IN ('en', 'twi')",
            name="notification_preferences_email_locale_check",
        ),
        CheckConstraint(
            "email_digest_frequency IN ('daily', 'weekly')",
            name="notification_preferences_email_frequency_check",
        ),
        CheckConstraint(
            "email_digest_weekday BETWEEN 0 AND 6",
            name="notification_preferences_email_weekday_check",
        ),
    )


class WhatsappMessage(Base):
    """Append-only audit record for every outbound WhatsApp send attempt.

    `status` is a CHECK-constrained string rather than a SQL enum because
    Meta occasionally introduces new states; evolving a CHECK is less
    disruptive than ALTER TYPE.
    """

    __tablename__ = "whatsapp_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    template_name = Column(Text, nullable=False)
    template_language = Column(Text, nullable=False, default="en")
    phone_e164 = Column(Text, nullable=False)
    payload_hash = Column(Text, nullable=False)
    idempotency_key = Column(Text, nullable=True, unique=True)
    provider_message_id = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="queued")
    error_code = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    delivered_at = Column(TIMESTAMP(timezone=True), nullable=True)
    read_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'queued', 'sent', 'delivered', 'read', "
            "'failed', 'rate_limited', 'opt_out_blocked'"
            ")",
            name="whatsapp_messages_status_check",
        ),
        Index("idx_whatsapp_messages_user_id", "user_id"),
        Index("idx_whatsapp_messages_status", "status"),
        Index("idx_whatsapp_messages_phone_created", "phone_e164", "created_at"),
    )


class WhatsappIncomingEvent(Base):
    """Inbound webhook events — status callbacks + user-initiated messages.

    We store the full raw payload so consent/unsubscribe evidence is
    preserved verbatim, which matters for compliance audits.
    """

    __tablename__ = "whatsapp_incoming_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_e164 = Column(Text, nullable=False)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type = Column(Text, nullable=False)
    body = Column(Text, nullable=True)
    raw = Column(JSONB, nullable=False)
    received_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('text', 'status_update', 'button', 'interactive', 'other')",
            name="whatsapp_incoming_events_type_check",
        ),
        Index("idx_whatsapp_incoming_events_phone", "phone_e164"),
        Index("idx_whatsapp_incoming_events_user", "user_id"),
        Index("idx_whatsapp_incoming_events_received_at", "received_at"),
    )


class EmailMessage(Base):
    """Append-only audit record for every outbound digest email attempt.

    Mirrors :class:`WhatsappMessage`. `status` is CHECK-constrained rather
    than a SQL enum so new provider event types (Resend adds them over time)
    only need a constraint change, not an ALTER TYPE.
    """

    __tablename__ = "email_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    email_address = Column(Text, nullable=False)
    template_name = Column(Text, nullable=False)
    locale = Column(Text, nullable=False, default="en")
    subject = Column(Text, nullable=False)
    payload_hash = Column(Text, nullable=False)
    idempotency_key = Column(Text, nullable=True, unique=True)
    provider_message_id = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="queued")
    job_count = Column(Integer, nullable=False, default=0)
    error_code = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    delivered_at = Column(TIMESTAMP(timezone=True), nullable=True)
    opened_at = Column(TIMESTAMP(timezone=True), nullable=True)
    clicked_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'queued', 'sent', 'delivered', 'opened', 'clicked', "
            "'bounced', 'complained', 'failed', 'rate_limited', 'opt_out_blocked'"
            ")",
            name="email_messages_status_check",
        ),
        Index("idx_email_messages_user_id", "user_id"),
        Index("idx_email_messages_status", "status"),
        Index("idx_email_messages_created_at", "created_at"),
    )


class EmailSuppression(Base):
    """Addresses we must never mail again.

    Fed by provider bounce/complaint webhooks and by manual blocks. Checked
    before every send — an opted-in user whose address hard-bounced still
    gets no mail, because continuing to send wrecks domain reputation.
    """

    __tablename__ = "email_suppressions"

    email_address = Column(Text, primary_key=True)
    reason = Column(Text, nullable=False)
    detail = Column(Text, nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "reason IN ('hard_bounce', 'complaint', 'manual', 'invalid')",
            name="email_suppressions_reason_check",
        ),
    )

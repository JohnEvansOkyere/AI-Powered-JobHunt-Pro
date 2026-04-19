"""Notification preference + WhatsApp audit models.

Mirrors ``migrations/009_add_whatsapp.sql`` (see
``docs/RECOMMENDATIONS_V2_PLAN.md`` §6.3). WhatsApp is the first channel;
the shape of :class:`NotificationPreferences` is intentionally
channel-aware so email/SMS can be added without a schema rewrite.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.core.database import Base


class NotificationPreferences(Base):
    """Per-user channel consent + delivery preferences.

    Primary key is ``user_id`` (one row per user). Consent columns are
    scoped to WhatsApp for now; a future migration will add analogous
    columns (or a JSON map) for email and SMS.
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

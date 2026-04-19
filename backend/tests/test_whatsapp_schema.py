"""
Smoke tests for the WhatsApp schema migration (Phase 4a).

These don't exercise any Meta API logic — they just ensure the new SQLAlchemy
models declare the columns the migration creates and that the dispatcher
settings parse with safe defaults. Catches accidental drift between
``migrations/009_add_whatsapp.sql`` and ``app/models/notification.py``.
"""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.models import (
    NotificationPreferences,
    WhatsappIncomingEvent,
    WhatsappMessage,
)


REQUIRED_PREFERENCES_COLUMNS = {
    "user_id",
    "whatsapp_opted_in",
    "whatsapp_opted_in_at",
    "whatsapp_opt_in_source",
    "whatsapp_phone_e164",
    "whatsapp_phone_verified_at",
    "whatsapp_digest_time_local",
    "whatsapp_timezone",
    "whatsapp_opted_out_at",
    "whatsapp_paused_until",
    "created_at",
    "updated_at",
}

REQUIRED_MESSAGE_COLUMNS = {
    "id",
    "user_id",
    "template_name",
    "template_language",
    "phone_e164",
    "payload_hash",
    "idempotency_key",
    "provider_message_id",
    "status",
    "error_code",
    "error_message",
    "sent_at",
    "delivered_at",
    "read_at",
    "created_at",
}

REQUIRED_INCOMING_COLUMNS = {
    "id",
    "phone_e164",
    "user_id",
    "event_type",
    "body",
    "raw",
    "received_at",
}


def _columns(model) -> set[str]:
    return {col.name for col in model.__table__.columns}


def test_notification_preferences_columns():
    missing = REQUIRED_PREFERENCES_COLUMNS - _columns(NotificationPreferences)
    assert not missing, f"NotificationPreferences missing columns: {missing}"


def test_whatsapp_message_columns():
    missing = REQUIRED_MESSAGE_COLUMNS - _columns(WhatsappMessage)
    assert not missing, f"WhatsappMessage missing columns: {missing}"


def test_whatsapp_incoming_event_columns():
    missing = REQUIRED_INCOMING_COLUMNS - _columns(WhatsappIncomingEvent)
    assert not missing, f"WhatsappIncomingEvent missing columns: {missing}"


def test_message_status_check_constraint():
    """The status CHECK must be present — this is what enforces the state machine."""
    table = WhatsappMessage.__table__
    check_names = {
        c.name for c in table.constraints if c.name
    }
    assert "whatsapp_messages_status_check" in check_names


def test_whatsapp_settings_have_safe_defaults():
    # Master switch must default OFF so an unconfigured env can never accidentally send.
    assert settings.WHATSAPP_ENABLED is False
    # Send mode must default to dry_run.
    assert settings.WHATSAPP_SEND_MODE == "dry_run"
    # Per-user-per-day cap protects candidates from digest re-run spam.
    assert settings.WHATSAPP_MAX_SENDS_PER_USER_PER_DAY >= 1


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("live", "live"),
        ("DRY_RUN", "dry_run"),
        ("sandbox", "sandbox"),
        ("garbage", "dry_run"),   # unknown values fall back to the safest mode
        ("", "dry_run"),
    ],
)
def test_send_mode_validator_clamps_unknown_values(raw, expected, monkeypatch):
    from app.core.config import Settings

    s = Settings(WHATSAPP_SEND_MODE=raw)
    assert s.WHATSAPP_SEND_MODE == expected

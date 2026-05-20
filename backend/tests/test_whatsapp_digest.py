"""WhatsApp digest dispatcher helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.core.config import settings
from app.models.notification import NotificationPreferences
from app.services.whatsapp_digest import (
    digest_cta_url,
    digest_due_for_preferences,
    digest_idempotency_key,
    format_digest_job_list,
    payload_hash,
)


def _prefs(**overrides) -> NotificationPreferences:
    data = {
        "user_id": uuid.uuid4(),
        "whatsapp_opted_in": True,
        "whatsapp_phone_e164": "+15551234567",
        "whatsapp_phone_verified_at": datetime(2026, 5, 20, 7, 0, tzinfo=timezone.utc),
        "whatsapp_digest_time_local": "08:30",
        "whatsapp_timezone": "UTC",
        "whatsapp_opted_out_at": None,
        "whatsapp_paused_until": None,
    }
    data.update(overrides)
    return NotificationPreferences(**data)


def test_digest_due_when_scheduled_time_is_in_previous_hour():
    prefs = _prefs()
    due, local_date = digest_due_for_preferences(
        prefs,
        datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc),
    )
    assert due is True
    assert local_date == "2026-05-20"


def test_digest_not_due_before_scheduled_time_or_when_paused():
    before, _ = digest_due_for_preferences(
        _prefs(),
        datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc),
    )
    paused, _ = digest_due_for_preferences(
        _prefs(whatsapp_paused_until=datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc)),
        datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc),
    )
    assert before is False
    assert paused is False


def test_digest_due_respects_user_timezone():
    prefs = _prefs(whatsapp_digest_time_local="08:00", whatsapp_timezone="Africa/Accra")
    due, local_date = digest_due_for_preferences(
        prefs,
        datetime(2026, 5, 20, 8, 45, tzinfo=timezone.utc),
    )
    assert due is True
    assert local_date == "2026-05-20"


def test_digest_idempotency_key_is_per_user_local_date():
    uid = str(uuid.uuid4())
    assert digest_idempotency_key(uid, "2026-05-20") == f"whatsapp:digest:{uid}:2026-05-20"


def test_payload_hash_is_stable_for_key_order():
    left = payload_hash({"b": 2, "a": [1, 2]})
    right = payload_hash({"a": [1, 2], "b": 2})
    assert left == right


def test_digest_cta_url_uses_public_app_url(monkeypatch):
    monkeypatch.setattr(settings, "APP_PUBLIC_URL", "https://app.example.com/")
    assert digest_cta_url() == "https://app.example.com/dashboard/recommendations"


def test_format_digest_job_list_is_compact():
    recs = [
        SimpleNamespace(
            job=SimpleNamespace(
                title="Senior Backend Engineer",
                company="Acme",
                location="Remote",
            )
        ),
        SimpleNamespace(
            job=SimpleNamespace(
                title="AI Engineer",
                company="Data Co",
                location=None,
            )
        ),
    ]
    assert format_digest_job_list(recs) == (
        "1. Senior Backend Engineer at Acme - Remote\n"
        "2. AI Engineer at Data Co"
    )

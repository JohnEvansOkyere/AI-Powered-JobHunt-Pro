"""Email digest scheduling, dialect rendering and webhook signature tests."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.integrations.email import verify_webhook_signature
from app.models.notification import NotificationPreferences
from app.services.email_copy import (
    DEFAULT_LOCALE,
    LOCALE_PACKS,
    SUPPORTED_LOCALES,
    DigestJob,
    get_pack,
    render_digest,
    variant_index,
)
from app.services.email_digest import (
    digest_cta_url,
    digest_due_for_preferences,
    digest_idempotency_key,
    payload_hash,
    to_digest_jobs,
    unsubscribe_url,
)


def _prefs(**overrides) -> NotificationPreferences:
    data = {
        "user_id": uuid.uuid4(),
        "email_opted_in": True,
        "email_address": "candidate@example.com",
        "email_digest_time_local": "07:30",
        "email_timezone": "UTC",
        "email_locale": "en",
        "email_digest_frequency": "daily",
        "email_digest_weekday": 1,
        "email_opted_out_at": None,
        "email_paused_until": None,
    }
    data.update(overrides)
    return NotificationPreferences(**data)


def _jobs(count: int = 3):
    return [
        DigestJob(
            title=f"Data Analyst {i}",
            company="MTN Ghana",
            location="Accra, Ghana",
            url=f"https://app.example.com/jobs/{i}",
            match_score=0.9 - (i / 100),
            match_reason="Your SQL experience matches the requirement.",
            salary="GHS 6,000",
            job_type="Full-time",
        )
        for i in range(count)
    ]


# --- scheduling -------------------------------------------------------------


def test_digest_due_when_scheduled_time_is_in_previous_hour():
    due, local_date = digest_due_for_preferences(
        _prefs(),
        datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc),
    )
    assert due is True
    assert local_date == "2026-05-20"


def test_digest_not_due_before_scheduled_time():
    due, _ = digest_due_for_preferences(
        _prefs(),
        datetime(2026, 5, 20, 7, 0, tzinfo=timezone.utc),
    )
    assert due is False


def test_digest_not_due_when_opted_out_or_paused():
    opted_out, _ = digest_due_for_preferences(
        _prefs(email_opted_out_at=datetime(2026, 5, 1, tzinfo=timezone.utc)),
        datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc),
    )
    paused, _ = digest_due_for_preferences(
        _prefs(email_paused_until=datetime(2026, 5, 25, tzinfo=timezone.utc)),
        datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc),
    )
    not_opted_in, _ = digest_due_for_preferences(
        _prefs(email_opted_in=False),
        datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc),
    )
    assert opted_out is False
    assert paused is False
    assert not_opted_in is False


def test_digest_due_respects_user_timezone():
    # 07:30 Africa/Accra == 07:30 UTC (Accra is UTC+0), so 08:00 UTC is in window.
    due, _ = digest_due_for_preferences(
        _prefs(email_timezone="Africa/Accra"),
        datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc),
    )
    # In UTC-5 the same instant is 03:00 local — well before the 07:30 slot.
    not_due, _ = digest_due_for_preferences(
        _prefs(email_timezone="America/New_York"),
        datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc),
    )
    assert due is True
    assert not_due is False


def test_weekly_digest_only_fires_on_configured_weekday():
    # 2026-05-20 is a Wednesday (weekday 2).
    wrong_day, _ = digest_due_for_preferences(
        _prefs(email_digest_frequency="weekly", email_digest_weekday=0),
        datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc),
    )
    right_day, _ = digest_due_for_preferences(
        _prefs(email_digest_frequency="weekly", email_digest_weekday=2),
        datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc),
    )
    assert wrong_day is False
    assert right_day is True


def test_invalid_timezone_is_skipped_not_crashed():
    due, _ = digest_due_for_preferences(
        _prefs(email_timezone="Mars/Olympus"),
        datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc),
    )
    assert due is False


def test_idempotency_key_is_per_user_local_date():
    uid = str(uuid.uuid4())
    assert digest_idempotency_key(uid, "2026-05-20") == f"email:digest:{uid}:2026-05-20"


def test_payload_hash_is_stable_for_key_order():
    assert payload_hash({"b": 2, "a": [1, 2]}) == payload_hash({"a": [1, 2], "b": 2})


def test_urls_use_configured_public_hosts(monkeypatch):
    monkeypatch.setattr(settings, "APP_PUBLIC_URL", "https://app.example.com/")
    monkeypatch.setattr(settings, "API_PUBLIC_URL", "https://api.example.com/")
    assert digest_cta_url() == "https://app.example.com/dashboard/recommendations"
    assert unsubscribe_url("tok") == (
        "https://api.example.com/api/v1/notifications/email/unsubscribe?token=tok"
    )


# --- dialect rendering ------------------------------------------------------


@pytest.mark.parametrize("locale", SUPPORTED_LOCALES)
def test_every_locale_renders_subject_html_and_text(locale):
    rendered = render_digest(
        locale=locale,
        first_name="Kwame",
        jobs=_jobs(3),
        user_id="user-1",
        on_date=date(2026, 5, 20),
        cta_url="https://app.example.com/dashboard/recommendations",
        unsubscribe_url="https://api.example.com/u?token=t",
        settings_url="https://app.example.com/dashboard/settings",
    )
    assert rendered["locale"] == locale
    assert "Kwame" in rendered["subject"]
    assert rendered["html"].startswith("<!doctype html>")
    # Both alternatives must carry the jobs and the unsubscribe link.
    for body in (rendered["html"], rendered["text"]):
        assert "Data Analyst 0" in body
        assert "MTN Ghana" in body
        assert "token=t" in body


def test_unknown_locale_falls_back_to_english():
    assert get_pack("xx-YY").code == DEFAULT_LOCALE
    assert get_pack(None).code == DEFAULT_LOCALE


def test_language_packs_are_actually_distinct():
    subjects = {
        code: pack.subjects[0] for code, pack in LOCALE_PACKS.items()
    }
    assert len(set(subjects.values())) == len(subjects)
    assert "Adwuma" in LOCALE_PACKS["twi"].jobs_heading


def test_english_pack_carries_no_pidgin_markers():
    """The English pack must read as Ghanaian professional English.

    West African pidgins are country-specific; Nigerian-Pidgin phrasing reads
    as foreign to a Ghanaian candidate and lands worse than plain English.
    """
    pack = LOCALE_PACKS["en"]
    corpus = " ".join(
        [
            *pack.subjects,
            *pack.preheaders,
            *pack.greetings,
            *pack.intros,
            *pack.signoffs,
            pack.jobs_heading,
            pack.cta_button,
            pack.footer_reason,
            pack.single_job_note,
        ]
    ).lower()
    for marker in (
        "chaley",
        "how body",
        "wey ",
        "sabi",
        "dey ",
        "we don ",
        "abeg",
        "no dull",
        "make you",
        " am.",
    ):
        assert marker not in corpus, f"pidgin marker {marker!r} in English pack"


def test_untrusted_job_fields_are_html_escaped():
    hostile = [
        DigestJob(
            title='<script>alert(1)</script>',
            company='Acme" onmouseover="x',
            location="Accra",
            url="https://app.example.com/jobs/1",
            match_score=0.8,
            match_reason="<img src=x onerror=alert(2)>",
        )
    ]
    rendered = render_digest(
        locale="en",
        first_name='<b>Kwame</b>',
        jobs=hostile,
        user_id="user-1",
        on_date=date(2026, 5, 20),
        cta_url="https://app.example.com/x",
        unsubscribe_url="https://api.example.com/u?token=t",
        settings_url="https://app.example.com/s",
    )
    html_body = rendered["html"]
    # The payloads must survive only as inert text: no live tag may be formed
    # and no attribute may be broken out of.
    assert "<script" not in html_body
    assert "<img" not in html_body
    assert 'onmouseover="x' not in html_body
    assert "<b>Kwame</b>" not in html_body
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_body
    assert "&lt;img src=x onerror=alert(2)&gt;" in html_body


def test_variant_rotation_changes_across_days_and_users():
    days = {variant_index("user-1", date(2026, 5, 20 + d), 3) for d in range(3)}
    users = {variant_index(f"user-{i}", date(2026, 5, 20), 3) for i in range(6)}
    assert len(days) > 1
    assert len(users) > 1
    assert variant_index("user-1", date(2026, 5, 20), 0) == 0


def test_single_match_note_is_included_for_one_job():
    rendered = render_digest(
        locale="en",
        first_name="Kwame",
        jobs=_jobs(1),
        user_id="user-1",
        on_date=date(2026, 5, 20),
        cta_url="https://app.example.com/x",
        unsubscribe_url="https://api.example.com/u?token=t",
        settings_url="https://app.example.com/s",
    )
    assert LOCALE_PACKS["en"].single_job_note in rendered["text"]


def test_to_digest_jobs_skips_rows_without_a_job(monkeypatch):
    monkeypatch.setattr(settings, "APP_PUBLIC_URL", "https://app.example.com")
    recs = [
        SimpleNamespace(job=None, match_score=0.9, match_reason=None),
        SimpleNamespace(
            job=SimpleNamespace(
                id="job-1",
                title="Data Analyst",
                company="MTN",
                location="Accra",
                salary_range=None,
                job_type="Full-time",
                source_url=None,
                job_link=None,
            ),
            match_score=0.9,
            match_reason="Good fit",
        ),
    ]
    rows = to_digest_jobs(recs)
    assert len(rows) == 1
    assert rows[0].url == "https://app.example.com/jobs/job-1"


# --- webhook signature ------------------------------------------------------


def _sign(secret_b64: str, msg_id: str, timestamp: str, body: bytes) -> str:
    key = base64.b64decode(secret_b64)
    signed = f"{msg_id}.{timestamp}.".encode() + body
    return "v1," + base64.b64encode(
        hmac.new(key, signed, hashlib.sha256).digest()
    ).decode()


def test_webhook_signature_accepts_valid_svix_payload():
    secret_b64 = base64.b64encode(b"super-secret-key").decode()
    body = json.dumps({"type": "email.delivered"}).encode()
    ts = str(int(time.time()))
    signature = _sign(secret_b64, "msg_1", ts, body)

    assert verify_webhook_signature(
        body,
        svix_id="msg_1",
        svix_timestamp=ts,
        svix_signature=signature,
        secret=f"whsec_{secret_b64}",
    )


def test_webhook_signature_rejects_tampering_replay_and_missing_headers():
    secret_b64 = base64.b64encode(b"super-secret-key").decode()
    body = json.dumps({"type": "email.delivered"}).encode()
    ts = str(int(time.time()))
    signature = _sign(secret_b64, "msg_1", ts, body)
    secret = f"whsec_{secret_b64}"

    # Body tampered after signing.
    assert not verify_webhook_signature(
        body + b" ",
        svix_id="msg_1",
        svix_timestamp=ts,
        svix_signature=signature,
        secret=secret,
    )
    # Timestamp outside the replay window.
    old_ts = str(int(time.time()) - 3600)
    assert not verify_webhook_signature(
        body,
        svix_id="msg_1",
        svix_timestamp=old_ts,
        svix_signature=_sign(secret_b64, "msg_1", old_ts, body),
        secret=secret,
    )
    # No secret configured, or headers absent.
    assert not verify_webhook_signature(
        body, svix_id="msg_1", svix_timestamp=ts, svix_signature=signature, secret=""
    )
    assert not verify_webhook_signature(
        body, svix_id=None, svix_timestamp=ts, svix_signature=signature, secret=secret
    )

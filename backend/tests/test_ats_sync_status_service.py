from datetime import datetime, timedelta, timezone

from app.services.ats_sync_status_service import with_staleness


def test_sync_status_is_stale_when_never_successful():
    status = {"status": "never_run", "last_success_at": None}

    result = with_staleness(status, now=datetime(2026, 6, 20, tzinfo=timezone.utc))

    assert result["stale"] is True
    assert result["age_seconds"] is None


def test_sync_status_is_not_stale_inside_threshold():
    now = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)
    status = {
        "status": "success",
        "last_success_at": (now - timedelta(minutes=5)).isoformat(),
    }

    result = with_staleness(status, now=now)

    assert result["stale"] is False
    assert result["age_seconds"] == 300


def test_sync_status_is_stale_outside_threshold():
    now = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)
    status = {
        "status": "success",
        "last_success_at": (now - timedelta(minutes=30)).isoformat(),
    }

    result = with_staleness(status, now=now)

    assert result["stale"] is True
    assert result["age_seconds"] == 1800

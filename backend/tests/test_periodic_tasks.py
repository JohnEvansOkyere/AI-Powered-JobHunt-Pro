"""
Smoke tests for the Celery Beat migration (Phase 2).

These don't actually run the tasks; they just verify that the Beat schedule
and task registrations exist, so a refactor that accidentally deletes a cron
entry is caught at CI time.
"""

from __future__ import annotations

import pytest

from app.tasks import celery_app as celery_module
from app.tasks.celery_app import celery_app

EXPECTED_BEAT_ENTRIES = {
    "scrape-recent-jobs-every-3-days": "scheduler.scrape_recent_jobs",
    "generate-recommendations-every-2-days": "scheduler.generate_recommendations_for_all",
    "backfill-empty-users-hourly": "scheduler.generate_recommendations_for_empty_users",
    "cleanup-expired-saved-jobs-daily": "scheduler.cleanup_expired_saved_jobs",
    "cleanup-expired-recommendations-daily": "scheduler.cleanup_expired_recommendations",
    "cleanup-old-jobs-daily": "scheduler.cleanup_old_jobs",
}


def test_beat_schedule_has_all_expected_entries():
    schedule = celery_app.conf.beat_schedule
    missing = [key for key in EXPECTED_BEAT_ENTRIES if key not in schedule]
    assert not missing, f"Missing beat entries: {missing}"


@pytest.mark.parametrize(
    "entry_name,task_name",
    sorted(EXPECTED_BEAT_ENTRIES.items()),
)
def test_beat_entry_points_at_registered_task(entry_name: str, task_name: str):
    entry = celery_app.conf.beat_schedule[entry_name]
    assert entry["task"] == task_name, (
        f"{entry_name} should point at {task_name}, got {entry['task']}"
    )


def test_all_scheduled_tasks_are_registered():
    # Importing the module registers the tasks via @celery_app.task decorators.
    from app.tasks import periodic_tasks  # noqa: F401

    registered = set(celery_app.tasks.keys())
    for task_name in EXPECTED_BEAT_ENTRIES.values():
        assert task_name in registered, f"{task_name} not registered with Celery"


def test_apscheduler_package_is_gone():
    """Ensure the old app.scheduler package was removed."""
    with pytest.raises(ModuleNotFoundError):
        __import__("app.scheduler")


def test_celery_include_covers_periodic_tasks():
    include = celery_module.celery_app.conf.include or []
    assert "app.tasks.periodic_tasks" in include

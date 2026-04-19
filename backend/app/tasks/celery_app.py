"""
Celery Application Configuration.

Celery Beat owns all periodic jobs after the Phase 2 scheduler migration
(see docs/RECOMMENDATIONS_V2_PLAN.md §7). APScheduler is no longer started
from the FastAPI lifespan.
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "ai_job_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.job_scraping",
        "app.tasks.ai_processing",
        "app.tasks.periodic_tasks",
        "app.tasks.embeddings",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Beat schedule — mirrors what APScheduler used to own.
# Entries are keyed by a human-readable name; each points at a registered
# Celery task name. Keep the keys stable: tests assert on them.
celery_app.conf.beat_schedule = {
    # Scrape fresh jobs every 3 days at 06:00 UTC
    "scrape-recent-jobs-every-3-days": {
        "task": "scheduler.scrape_recent_jobs",
        "schedule": crontab(minute=0, hour=6, day_of_month="*/3"),
    },
    # Generate recommendations for all eligible users every 2 days at 07:00 UTC
    "generate-recommendations-every-2-days": {
        "task": "scheduler.generate_recommendations_for_all",
        "schedule": crontab(minute=0, hour=7, day_of_month="*/2"),
    },
    # Hourly backfill for users with zero recommendations (catches new signups
    # without waiting for the 2-day generation pass)
    "backfill-empty-users-hourly": {
        "task": "scheduler.generate_recommendations_for_empty_users",
        "schedule": crontab(minute=15),
    },
    # Daily cleanups — staggered so they don't all hit SessionLocal at once
    "cleanup-expired-saved-jobs-daily": {
        "task": "scheduler.cleanup_expired_saved_jobs",
        "schedule": crontab(minute=0, hour=0),
    },
    "cleanup-expired-recommendations-daily": {
        "task": "scheduler.cleanup_expired_recommendations",
        "schedule": crontab(minute=5, hour=0),
    },
    "cleanup-old-jobs-daily": {
        "task": "scheduler.cleanup_old_jobs",
        "schedule": crontab(minute=10, hour=0),
    },
}

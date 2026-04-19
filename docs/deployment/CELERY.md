# Celery Worker + Beat

All periodic work (scraping, recommendation generation, cleanup) runs through
Celery Beat after the Phase 2 scheduler migration (see
`docs/RECOMMENDATIONS_V2_PLAN.md` §7). The FastAPI process no longer runs
APScheduler.

## Required processes

You need **three** long-running processes in production:

| Process | Command | Purpose |
|---|---|---|
| FastAPI | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | HTTP API only |
| Celery worker | `celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2` | Executes queued + scheduled tasks |
| Celery Beat | `celery -A app.tasks.celery_app beat --loglevel=info` | Emits periodic jobs onto the broker |

Run the worker and beat from `backend/` with the same virtualenv that serves
the API.

## Environment variables

- `CELERY_BROKER_URL` — Redis URL (default `redis://localhost:6379/0`).
- `CELERY_RESULT_BACKEND` — same default; results are small so a shared Redis
  is fine.
- `REDIS_URL` — fallback / convenience.
- `SCHEDULER_MODE` — `celery` (default) or `disabled`. Setting `disabled`
  does **not** stop Celery Beat; it only silences the startup log. Ops can
  disable periodic work by stopping the Beat process.

## Beat schedule

Defined in `backend/app/tasks/celery_app.py` as `celery_app.conf.beat_schedule`:

| Name | Task | Cron (UTC) |
|---|---|---|
| `scrape-recent-jobs-every-3-days` | `scheduler.scrape_recent_jobs` | Every 3rd day at 06:00 |
| `generate-recommendations-every-2-days` | `scheduler.generate_recommendations_for_all` | Every 2nd day at 07:00 |
| `backfill-empty-users-hourly` | `scheduler.generate_recommendations_for_empty_users` | Every hour at :15 |
| `cleanup-expired-saved-jobs-daily` | `scheduler.cleanup_expired_saved_jobs` | 00:00 |
| `cleanup-expired-recommendations-daily` | `scheduler.cleanup_expired_recommendations` | 00:05 |
| `cleanup-old-jobs-daily` | `scheduler.cleanup_old_jobs` | 00:10 |

The smoke test in `backend/tests/test_periodic_tasks.py` asserts these entries
exist so they cannot be silently removed.

## Manual triggers

- `POST /api/v1/jobs/cleanup-old` (requires `X-Cron-Secret` when
  `CRON_SECRET` is set) runs `cleanup_old_jobs` inline; useful for external
  cron services that cannot speak to Redis.
- `POST /api/v1/jobs/recommendations/generate-all` triggers the all-user
  recommendation pass via the API.

## Local development

If you don't want to run Redis locally, you can:

1. Skip Celery entirely — periodic tasks simply won't fire. The API and UI
   still work for on-demand flows.
2. Or run Redis with Docker:

   ```
   docker run --rm -p 6379:6379 redis:7-alpine
   ```

Then launch the worker + beat in two separate terminals using the commands
above.

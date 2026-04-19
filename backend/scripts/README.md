# `backend/scripts/`

Operational, scraping, maintenance, diagnostics, and seed scripts. Nothing in
here is imported by the FastAPI app or the Celery workers — these are all
command-line entry points for humans.

All Python scripts are safe to run with:

```bash
cd backend
venv/bin/python scripts/<subfolder>/<script>.py [args]
```

Each script adds `backend/` to `sys.path` itself (`Path(__file__).resolve().parents[2]`),
so you don't need `PYTHONPATH` gymnastics.

## Layout

| Folder | Purpose |
|---|---|
| `ops/` | Long-running / process-start scripts used in dev + prod (Celery worker, Celery beat, connection helpers). |
| `scrape/` | Manual scraping entry points. The scheduled job is owned by Celery Beat (`scheduler.scrape_recent_jobs`); these scripts exist for ad-hoc runs. |
| `maintenance/` | Periodic cleanups and one-off data tasks. The scheduled cleanups are owned by Celery Beat; these scripts mirror them for ad-hoc use. |
| `diagnostics/` | Read-only health checks (DB reachable, `.env` complete, job counts). |
| `seeds/` | Populate a local DB with realistic data for development. |
| `legacy/` | One-shot codemods that have already been run. Kept for history; safe to delete. |

## ops/

| Script | What it does |
|---|---|
| `start_celery_worker.sh` | Starts a Celery worker. See `docs/deployment/CELERY.md`. |
| `start_celery_beat.sh` | Starts Celery Beat (periodic scheduler). |
| `fix_connection.sh` | Dev-only helper for common Supabase connectivity errors. |

## scrape/

| Script | What it does |
|---|---|
| `scrape_jobs_now.py` | Run the standard scraping flow once, now. |
| `scrape_jobs_5days.py` | Scrape jobs posted in the last 5 days (wider window than the default). |
| `scrape_jobs_ghana.py` | Ghana-focused keyword pass. |
| `scrape_jobs_test.py` | No-date-filter smoke test; useful when RemoteOK returns nothing for the current window. |
| `daily_job_scraper.py` | Standalone daily scraper (pre-Celery). Still runnable via cron if someone opts out of Celery Beat. |
| `run_scrape_and_recommend.py` | Scrape then immediately generate recommendations (end-to-end smoke test). |

Equivalent scheduled task: `scheduler.scrape_recent_jobs` (every 3 days,
06:00 UTC).

## maintenance/

| Script | What it does |
|---|---|
| `cleanup_old_jobs.py` | Application-aware cleanup. Deletes jobs older than 7 days that have **no applications attached**; keeps everything else so users never lose their history. |
| `generate_recommendations.py` | Run the recommendation generator for all eligible users, now. |
| `delete_tailored_cvs.py` | One-time wipe of the orphaned `tailored-cvs/` Supabase Storage prefix. Run after applying migration `007_remove_cv_tailoring.sql`. |
| `backfill_embeddings.py` | One-time backfill of the `job_embeddings` / `user_embeddings` cache after applying migration `008_recommendations_v2.sql`. Supports `--dry-run`, `--force`, `--jobs-only`, `--users-only`, `--limit`. Idempotent — the pipeline short-circuits on unchanged `source_hash`. |

Equivalent scheduled tasks: `scheduler.cleanup_old_jobs`,
`scheduler.generate_recommendations_for_all`.

## diagnostics/

| Script | What it does |
|---|---|
| `check_database.py` | Connects to the DB and reports table counts + a sample of recent jobs. |
| `check_env.py` | Verifies every required variable is present in `.env`. |
| `test_db_connection.py` | Minimal DB reachability test; prints `SELECT 1` roundtrip. |

## seeds/

| Script | What it does |
|---|---|
| `seed_jobs.py` | Baseline synthetic jobs for local dev. |
| `seed_jobs_improved.py` | Same, with richer metadata + skills. |
| `seed_jobs_remoteok.py` | Seeds from a cached RemoteOK sample (no external call). |
| `seed_jobs_simple.py` | Minimal seed set for unit-test-adjacent use. |

## legacy/

| Script | Status |
|---|---|
| `fix_tests.py` | One-shot codemod that added a fixture to existing tests. Already run against the repo; kept for reference. Safe to delete. |

## Adding a new script

- Pick the right subfolder (or add a new one + update this README).
- Start from this preamble so imports work from any CWD:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.database import SessionLocal  # etc.
```

- Print a clear usage line on success and a non-zero exit on failure.
- If the script mirrors a Celery Beat task, link to the task name in this
  README so humans know they're running the same thing the scheduler runs.

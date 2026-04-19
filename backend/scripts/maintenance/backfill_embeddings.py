"""One-shot backfill for the Recommendations V2 embedding cache.

Context
-------
Migration ``008_recommendations_v2.sql`` creates empty ``job_embeddings``
and ``user_embeddings`` tables. Until those tables are populated,
``job_recommendations.semantic_fit`` is always NULL and the three-tier
UI shows nothing in Tier 1 / Tier 2. The live Celery tasks
``embeddings.embed_job`` and ``embeddings.embed_user`` cover the
steady-state (they fire on new-job ingestion and profile/CV updates),
so this script only has to handle the initial population.

It intentionally mirrors what the Celery tasks do — calling
``upsert_job_embedding`` / ``upsert_user_embedding`` from
``app.services.embedding_pipeline`` — so there is no second code path to
keep in sync. The pipeline already short-circuits on unchanged
``source_hash``, which means re-running this script is idempotent and
cheap.

Usage
-----
    cd backend
    venv/bin/python scripts/maintenance/backfill_embeddings.py --dry-run
    venv/bin/python scripts/maintenance/backfill_embeddings.py
    venv/bin/python scripts/maintenance/backfill_embeddings.py --jobs-only --limit 200
    venv/bin/python scripts/maintenance/backfill_embeddings.py --force   # re-embed everything

Provider wiring
---------------
Respects ``AI_EMBEDDING_PROVIDER`` / ``AI_EMBEDDING_MODEL`` from
``.env``. The defaults are Gemini + ``text-embedding-004`` (768 dim).
If you flip providers later you MUST re-run with ``--force`` because the
existing rows will have a different ``model`` tag and be ignored at read
time. See ``docs/RECOMMENDATIONS_V2_PLAN.md`` §3.1.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.logging import get_logger  # noqa: E402
from app.models.embeddings import JobEmbedding, UserEmbedding  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.user_profile import UserProfile  # noqa: E402
from app.services.embedding_pipeline import (  # noqa: E402
    upsert_job_embedding,
    upsert_user_embedding,
)

logger = get_logger(__name__)


@dataclass
class Tally:
    """Rolling counters for end-of-run reporting."""

    updated: int = 0
    skipped: int = 0
    empty: int = 0
    failed: int = 0

    def add(self, *, updated: bool, empty: bool) -> None:
        if empty:
            self.empty += 1
        elif updated:
            self.updated += 1
        else:
            self.skipped += 1

    def fail(self) -> None:
        self.failed += 1

    def total(self) -> int:
        return self.updated + self.skipped + self.empty + self.failed


def _print_header() -> None:
    print("=" * 72)
    print("Recommendations V2 — embedding backfill")
    print("=" * 72)
    print(f"  Provider : {settings.AI_EMBEDDING_PROVIDER}")
    print(f"  Model    : {settings.AI_EMBEDDING_MODEL}")
    print()


def _job_ids_needing_embedding(
    db: Session,
    *,
    force: bool,
    limit: Optional[int],
) -> List[str]:
    """Jobs that don't have a matching cached embedding yet.

    When ``force`` is True we return every job, because the caller wants to
    re-embed unconditionally (e.g. provider migration). Otherwise we LEFT
    JOIN against ``job_embeddings`` filtered by the currently configured
    model and return only the unmatched rows.
    """
    if force:
        stmt = select(Job.id)
    else:
        model = settings.AI_EMBEDDING_MODEL
        stmt = (
            select(Job.id)
            .outerjoin(
                JobEmbedding,
                (JobEmbedding.job_id == Job.id)
                & (JobEmbedding.model == model),
            )
            .where(JobEmbedding.job_id.is_(None))
        )

    if limit is not None:
        stmt = stmt.limit(limit)

    return [row[0] for row in db.execute(stmt).all()]


def _user_ids_needing_embedding(
    db: Session,
    *,
    force: bool,
    limit: Optional[int],
) -> List[str]:
    """Users with a profile row but no cached embedding for the current model."""
    if force:
        stmt = select(UserProfile.user_id)
    else:
        model = settings.AI_EMBEDDING_MODEL
        stmt = (
            select(UserProfile.user_id)
            .outerjoin(
                UserEmbedding,
                (UserEmbedding.user_id == UserProfile.user_id)
                & (UserEmbedding.model == model),
            )
            .where(UserEmbedding.user_id.is_(None))
        )

    if limit is not None:
        stmt = stmt.limit(limit)

    return [row[0] for row in db.execute(stmt).all()]


async def _backfill_jobs(
    db: Session,
    job_ids: List[str],
    *,
    force: bool,
    dry_run: bool,
) -> Tally:
    tally = Tally()
    total = len(job_ids)
    for i, job_id in enumerate(job_ids, start=1):
        job = db.get(Job, job_id)
        if job is None:
            logger.warning("Job %s disappeared between query and embed; skipping.", job_id)
            continue

        if dry_run:
            print(f"  [{i:>5}/{total}] (dry-run) would embed job {job_id}")
            tally.add(updated=True, empty=False)
            continue

        try:
            result = await upsert_job_embedding(db, job, force=force)
        except Exception as exc:  # noqa: BLE001 - log and continue; a single bad row shouldn't kill the run
            logger.exception("Failed to embed job %s: %s", job_id, exc)
            tally.fail()
            continue

        empty = result.dims == 0 and result.skipped and not result.provider
        tally.add(updated=not result.skipped, empty=empty)
        if i % 50 == 0 or i == total:
            print(
                f"  [{i:>5}/{total}] jobs: "
                f"updated={tally.updated} skipped={tally.skipped} "
                f"empty={tally.empty} failed={tally.failed}"
            )

    return tally


async def _backfill_users(
    db: Session,
    user_ids: List[str],
    *,
    force: bool,
    dry_run: bool,
) -> Tally:
    tally = Tally()
    total = len(user_ids)
    for i, user_id in enumerate(user_ids, start=1):
        if dry_run:
            print(f"  [{i:>5}/{total}] (dry-run) would embed user {user_id}")
            tally.add(updated=True, empty=False)
            continue

        try:
            result = await upsert_user_embedding(db, str(user_id), force=force)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to embed user %s: %s", user_id, exc)
            tally.fail()
            continue

        empty = result.dims == 0 and result.skipped and not result.provider
        tally.add(updated=not result.skipped, empty=empty)
        if i % 50 == 0 or i == total:
            print(
                f"  [{i:>5}/{total}] users: "
                f"updated={tally.updated} skipped={tally.skipped} "
                f"empty={tally.empty} failed={tally.failed}"
            )

    return tally


async def _run(args: argparse.Namespace) -> int:
    _print_header()
    db = SessionLocal()
    started = time.monotonic()
    exit_code = 0

    try:
        if not args.users_only:
            print("> Scanning jobs...")
            job_ids = _job_ids_needing_embedding(
                db, force=args.force, limit=args.limit
            )
            print(f"  {len(job_ids)} job(s) need embedding.")
            if job_ids:
                jobs_tally = await _backfill_jobs(
                    db, job_ids, force=args.force, dry_run=args.dry_run
                )
                print()
                print(
                    "  jobs: "
                    f"updated={jobs_tally.updated} "
                    f"skipped={jobs_tally.skipped} "
                    f"empty={jobs_tally.empty} "
                    f"failed={jobs_tally.failed}"
                )
                if jobs_tally.failed:
                    exit_code = 2
            print()

        if not args.jobs_only:
            print("> Scanning users...")
            user_ids = _user_ids_needing_embedding(
                db, force=args.force, limit=args.limit
            )
            print(f"  {len(user_ids)} user(s) need embedding.")
            if user_ids:
                users_tally = await _backfill_users(
                    db, user_ids, force=args.force, dry_run=args.dry_run
                )
                print()
                print(
                    "  users: "
                    f"updated={users_tally.updated} "
                    f"skipped={users_tally.skipped} "
                    f"empty={users_tally.empty} "
                    f"failed={users_tally.failed}"
                )
                if users_tally.failed:
                    exit_code = 2
    finally:
        db.close()

    print()
    print(f"Done in {time.monotonic() - started:.1f}s.")
    if args.dry_run:
        print("(dry-run — no rows were written)")

    return exit_code


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill job and user embeddings for Recommendations V2.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List rows that would be embedded without calling the provider.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-embed rows even if a cached vector already exists for the current model.",
    )
    parser.add_argument(
        "--jobs-only",
        action="store_true",
        help="Only backfill jobs (skip users).",
    )
    parser.add_argument(
        "--users-only",
        action="store_true",
        help="Only backfill users (skip jobs).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap the number of rows processed per section (useful for smoke tests).",
    )
    args = parser.parse_args(argv)

    if args.jobs_only and args.users_only:
        parser.error("--jobs-only and --users-only are mutually exclusive")
    return args


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())

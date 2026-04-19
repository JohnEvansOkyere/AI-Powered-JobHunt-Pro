"""Celery tasks that keep the embedding cache fresh.

Two entry points, per ``docs/RECOMMENDATIONS_V2_PLAN.md`` §5.6:

*  :func:`embed_job_task` — enqueue on every "new job ingested" event
   (scraper finish, recruiter post approval).
*  :func:`embed_user_task` — enqueue on every profile/CV update.

Both tasks are idempotent by design (the embedding pipeline short-circuits
when the ``source_hash`` hasn't changed), so retrying a failed task never
costs an extra API call for unchanged content.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from celery.utils.log import get_task_logger

from app.ai.embeddings import EmbeddingUnavailableError
from app.core.database import SessionLocal
from app.models.job import Job
from app.services.embedding_pipeline import (
    upsert_job_embedding,
    upsert_user_embedding,
)
from app.tasks.celery_app import celery_app

logger = get_task_logger(__name__)


# Retry envelope:
#   - up to 3 tries, exponential back-off capped at 60s
#   - retry on transient embedding errors (provider 5xx, timeout)
#   - do NOT retry on "no text to embed" (caller should ignore)
_RETRYABLE = (EmbeddingUnavailableError,)


def _run_async(coro):
    """Celery workers don't run an event loop — give each task its own."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="embeddings.embed_job",
    bind=True,
    autoretry_for=_RETRYABLE,
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
)
def embed_job_task(self, job_id: str, *, force: bool = False) -> dict:
    """Refresh the cached embedding for a single job.

    Args:
        job_id: UUID string of the job. Non-existent jobs are logged and skipped.
        force: Bypass the ``source_hash`` short-circuit. Use during
            provider migrations.

    Returns:
        A small diagnostic dict. Intentionally not returning the vector
        itself — it's already persisted.
    """
    db = SessionLocal()
    try:
        job: Optional[Job] = db.get(Job, job_id)
        if job is None:
            logger.warning("embed_job: job_id=%s not found", job_id)
            return {"status": "missing", "job_id": job_id}
        result = _run_async(upsert_job_embedding(db, job, force=force))
        return {
            "status": "skipped" if result.skipped else "updated",
            "job_id": job_id,
            "model": result.model,
            "dims": result.dims,
            "provider": result.provider,
        }
    finally:
        db.close()


@celery_app.task(
    name="embeddings.embed_user",
    bind=True,
    autoretry_for=_RETRYABLE,
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
)
def embed_user_task(self, user_id: str, *, force: bool = False) -> dict:
    """Refresh the cached embedding for a single user."""
    db = SessionLocal()
    try:
        result = _run_async(upsert_user_embedding(db, user_id, force=force))
        return {
            "status": "skipped" if result.skipped else "updated",
            "user_id": user_id,
            "model": result.model,
            "dims": result.dims,
            "provider": result.provider,
        }
    finally:
        db.close()

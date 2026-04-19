"""Embedding pipeline — compute, cache, and invalidate vectors for jobs and users.

This module is intentionally thin:
  * It describes **what text** each entity embeds (the free-text "recipe").
  * It hashes that text to avoid re-calling the embedding API for
    unchanged content.
  * It calls :mod:`app.ai.embeddings` to get the vector.
  * It writes the result into ``job_embeddings`` / ``user_embeddings``
    tagged with the producing model.

Business logic lives elsewhere; this file never ranks jobs. That keeps
the contract clean enough to test and easy to swap providers. The recipes
here are conservative — they favor terms the embedding model has been
trained on (titles, skills, descriptions), which empirically beats
throwing the full JSON profile at the API.

See ``docs/RECOMMENDATIONS_V2_PLAN.md`` §3.1 and §5.6.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, List, Optional

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingResult, embed_one, source_hash
from app.core.logging import get_logger
from app.models.cv import CV
from app.models.embeddings import JobEmbedding, UserEmbedding
from app.models.job import Job
from app.models.user_profile import UserProfile

logger = get_logger(__name__)


# Char budgets per input. Gemini free tier is generous but we keep texts
# bounded so one pathological description can't break a whole batch.
JOB_TEXT_CHAR_BUDGET = 4_000
USER_TEXT_CHAR_BUDGET = 6_000


# --- Text recipes ---------------------------------------------------------


def job_embedding_text(job: Job) -> str:
    """Build the text we embed for a job.

    Order matters: we front-load the highest-signal fields so a
    description-heavy truncation still captures title + company + skills.
    """
    parts: List[str] = []
    parts.append(f"Title: {job.title}")
    if job.company:
        parts.append(f"Company: {job.company}")
    if job.normalized_title and job.normalized_title != job.title:
        parts.append(f"Normalized title: {job.normalized_title}")
    if job.location:
        parts.append(f"Location: {job.location}")
    if job.remote_type:
        parts.append(f"Remote: {job.remote_type}")
    if job.experience_level:
        parts.append(f"Level: {job.experience_level}")
    if job.skills:
        parts.append(f"Skills: {_maybe_json_list(job.skills)}")
    if job.requirements:
        parts.append(f"Requirements: {_maybe_json_list(job.requirements)}")
    if job.description:
        parts.append(f"Description: {job.description}")

    text = "\n".join(p for p in parts if p and p.strip())
    return text[:JOB_TEXT_CHAR_BUDGET]


def user_embedding_text(profile: Optional[UserProfile], cv: Optional[CV]) -> str:
    """Build the text we embed for a user.

    Blends profile signals (intent — what jobs the user WANTS) with CV
    signals (evidence — what they've done). Profile comes first because
    it's the stronger match signal for recommendations.
    """
    parts: List[str] = []
    if profile:
        if profile.primary_job_title:
            parts.append(f"Target role: {profile.primary_job_title}")
        if profile.secondary_job_titles:
            parts.append(
                f"Also considering: {', '.join(t for t in profile.secondary_job_titles if t)}"
            )
        if profile.seniority_level:
            parts.append(f"Seniority: {profile.seniority_level}")
        if profile.desired_industries:
            parts.append(
                f"Industries: {', '.join(i for i in profile.desired_industries if i)}"
            )
        if profile.work_preference:
            parts.append(f"Work preference: {profile.work_preference}")
        tech = _format_skills(profile.technical_skills)
        if tech:
            parts.append(f"Technical skills: {tech}")
        if profile.soft_skills:
            parts.append(f"Soft skills: {', '.join(profile.soft_skills)}")
        if profile.tools_technologies:
            parts.append(f"Tools: {', '.join(profile.tools_technologies)}")
        if profile.personal_branding_summary:
            parts.append(f"About: {profile.personal_branding_summary}")

    if cv:
        # The CV model varies between projects; pull fields defensively.
        # We only want parsed text snippets, not file blobs.
        cv_summary = getattr(cv, "summary", None) or getattr(cv, "extracted_text", None)
        if cv_summary:
            parts.append(f"CV summary: {cv_summary}")

    text = "\n".join(p for p in parts if p and p.strip())
    return text[:USER_TEXT_CHAR_BUDGET]


def _maybe_json_list(raw: str) -> str:
    """Jobs store ``skills``/``requirements`` as JSON-text. Flatten them for the prompt."""
    if not raw:
        return ""
    stripped = raw.strip()
    if stripped.startswith("["):
        try:
            items = json.loads(stripped)
            if isinstance(items, list):
                return ", ".join(str(x) for x in items if x)
        except (ValueError, TypeError):
            pass
    return stripped


def _format_skills(raw: object) -> str:
    """Render technical_skills JSONB as a short comma-separated list."""
    if not raw:
        return ""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return raw
    if isinstance(raw, list):
        names: List[str] = []
        for item in raw:
            if isinstance(item, dict) and item.get("skill"):
                names.append(str(item["skill"]))
            elif isinstance(item, str):
                names.append(item)
        return ", ".join(names)
    return str(raw)


# --- Upserters ------------------------------------------------------------


@dataclass(frozen=True)
class EmbeddingUpsertResult:
    """Tiny value object so callers can tell whether we did real work."""

    skipped: bool  # True if hash matched and we short-circuited
    model: str
    dims: int
    provider: Optional[str]  # None when skipped


async def upsert_job_embedding(
    db: Session,
    job: Job,
    *,
    force: bool = False,
) -> EmbeddingUpsertResult:
    """Compute + cache the embedding for a single job.

    Returns an :class:`EmbeddingUpsertResult` describing what happened. If
    the source text hasn't changed since last run we skip the API call —
    this is the main knob that keeps the free-tier budget safe.

    ``force=True`` bypasses the hash check (use for provider migrations).
    """
    text = job_embedding_text(job)
    if not text:
        logger.warning("Job %s produced empty embedding text; skipping.", job.id)
        return EmbeddingUpsertResult(skipped=True, model="", dims=0, provider=None)

    new_hash = source_hash(text)
    existing: Optional[JobEmbedding] = db.get(JobEmbedding, job.id)
    if existing and not force and existing.source_hash == new_hash:
        return EmbeddingUpsertResult(
            skipped=True,
            model=existing.model,
            dims=len(existing.embedding) if existing.embedding is not None else 0,
            provider=None,
        )

    result = await embed_one(text)
    _upsert_job_row(db, job.id, result, new_hash)
    db.commit()
    return EmbeddingUpsertResult(
        skipped=False,
        model=result.model,
        dims=result.dims,
        provider=result.provider,
    )


async def upsert_user_embedding(
    db: Session,
    user_id: str,
    *,
    force: bool = False,
) -> EmbeddingUpsertResult:
    """Compute + cache the user embedding for one user."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    cv = (
        db.query(CV)
        .filter(CV.user_id == user_id)
        .order_by(CV.created_at.desc())
        .first()
    )
    text = user_embedding_text(profile, cv)
    if not text:
        logger.info("User %s has no profile/CV signal yet; no embedding produced.", user_id)
        return EmbeddingUpsertResult(skipped=True, model="", dims=0, provider=None)

    new_hash = source_hash(text)
    existing: Optional[UserEmbedding] = db.get(UserEmbedding, user_id)
    if existing and not force and existing.source_hash == new_hash:
        return EmbeddingUpsertResult(
            skipped=True,
            model=existing.model,
            dims=len(existing.embedding) if existing.embedding is not None else 0,
            provider=None,
        )

    result = await embed_one(text)
    _upsert_user_row(db, user_id, result, new_hash)
    db.commit()
    return EmbeddingUpsertResult(
        skipped=False,
        model=result.model,
        dims=result.dims,
        provider=result.provider,
    )


def iter_jobs_missing_embeddings(db: Session, *, model: str) -> Iterable[Job]:
    """Yield jobs that don't have a current-model embedding yet.

    Used by the backfill / provider-switch tooling. Results are streamed
    to keep memory flat for large tables.
    """
    # LEFT JOIN on matching-model rows; anything with NULL is missing.
    q = (
        db.query(Job)
        .outerjoin(
            JobEmbedding,
            (JobEmbedding.job_id == Job.id) & (JobEmbedding.model == model),
        )
        .filter(JobEmbedding.job_id.is_(None))
    )
    for row in q.yield_per(200):
        yield row


# --- Private helpers ------------------------------------------------------


def _upsert_job_row(
    db: Session,
    job_id,
    result: EmbeddingResult,
    hash_value: str,
) -> None:
    stmt = (
        pg_insert(JobEmbedding)
        .values(
            job_id=job_id,
            embedding=result.vector,
            model=result.model,
            source_hash=hash_value,
        )
        .on_conflict_do_update(
            index_elements=[JobEmbedding.job_id],
            set_={
                "embedding": result.vector,
                "model": result.model,
                "source_hash": hash_value,
                "embedded_at": func.now(),
            },
        )
    )
    db.execute(stmt)


def _upsert_user_row(
    db: Session,
    user_id,
    result: EmbeddingResult,
    hash_value: str,
) -> None:
    stmt = (
        pg_insert(UserEmbedding)
        .values(
            user_id=user_id,
            embedding=result.vector,
            model=result.model,
            source_hash=hash_value,
        )
        .on_conflict_do_update(
            index_elements=[UserEmbedding.user_id],
            set_={
                "embedding": result.vector,
                "model": result.model,
                "source_hash": hash_value,
                "embedded_at": func.now(),
            },
        )
    )
    db.execute(stmt)

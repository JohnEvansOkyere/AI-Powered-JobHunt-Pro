"""Recommendations V2 API endpoints.

GET  /api/v1/recommendations         — paginated, tier-filtered
POST /api/v1/recommendations/regenerate — per-user on-demand trigger (rate-limited)
POST /api/v1/recommendations/generate-all — cron trigger (X-Cron-Secret)

The legacy endpoint ``/jobs/recommendations`` issues a 307 to Tier-2 here
so existing clients keep working without breaking (see jobs.py 307 redirect).

See docs/RECOMMENDATIONS_V2_PLAN.md §5.7.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db, SessionLocal
from app.core.logging import get_logger
from app.models.job_recommendation import JobRecommendation
from app.models.job import Job

logger = get_logger(__name__)

router = APIRouter()

VALID_TIERS = {"tier1", "tier2", "tier3"}
REGENERATE_COOLDOWN_SECONDS = 3600  # 1 hour per user


# ---- Response models ---------------------------------------------------


class JobSnippet(BaseModel):
    """Minimal job info for the recommendation list."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    company: str
    location: Optional[str] = None
    remote_type: Optional[str] = None
    job_type: Optional[str] = None
    source: Optional[str] = None
    job_link: Optional[str] = None
    source_url: Optional[str] = None
    posted_date: Optional[datetime] = None
    scraped_at: Optional[datetime] = None


class RecommendationItem(BaseModel):
    """One recommendation row exposed to the frontend."""

    id: str
    job_id: str
    tier: str
    match_score: float
    match_reason: Optional[str] = None
    semantic_fit: Optional[float] = None
    title_alignment: Optional[float] = None
    skill_overlap: Optional[float] = None
    freshness: Optional[float] = None
    llm_rerank_score: Optional[float] = None
    expires_at: datetime
    job: Optional[JobSnippet] = None


class RecommendationsResponse(BaseModel):
    items: List[RecommendationItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    tier: Optional[str] = None


# ---- Endpoints ---------------------------------------------------------


@router.get("", response_model=RecommendationsResponse)
async def get_recommendations(
    tier: Optional[str] = Query(
        None,
        description="Filter by tier: 'tier1', 'tier2', or 'tier3'. Omit for all tiers.",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Return pre-computed tiered recommendations for the authenticated user."""
    if tier and tier not in VALID_TIERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier '{tier}'. Must be one of: {', '.join(sorted(VALID_TIERS))}",
        )

    user_id = current_user["id"]
    now = datetime.now(timezone.utc)

    q = db.query(JobRecommendation).filter(
        JobRecommendation.user_id == user_id,
        JobRecommendation.expires_at > now,
    )
    if tier:
        q = q.filter(JobRecommendation.tier == tier)
    q = q.order_by(JobRecommendation.match_score.desc())

    total = q.count()

    # Empty? Kick off background generation so the user sees results soon.
    if total == 0:
        background_tasks.add_task(_bg_run, user_id)

    offset = (page - 1) * page_size
    recs = q.offset(offset).limit(page_size).all()

    # Fetch jobs for the page.
    job_ids = [r.job_id for r in recs]
    jobs = db.query(Job).filter(Job.id.in_(job_ids)).all()
    job_map = {str(j.id): j for j in jobs}

    items: List[RecommendationItem] = []
    for rec in recs:
        job = job_map.get(str(rec.job_id))
        snippet: Optional[JobSnippet] = None
        if job:
            snippet = JobSnippet(
                id=str(job.id),
                title=job.title,
                company=job.company,
                location=job.location,
                remote_type=job.remote_type,
                job_type=job.job_type,
                source=job.source,
                job_link=job.job_link,
                source_url=job.source_url,
                posted_date=job.posted_date,
                scraped_at=job.scraped_at,
            )
        items.append(
            RecommendationItem(
                id=str(rec.id),
                job_id=str(rec.job_id),
                tier=rec.tier,
                match_score=rec.match_score,
                match_reason=rec.match_reason,
                semantic_fit=rec.semantic_fit,
                title_alignment=rec.title_alignment,
                skill_overlap=rec.skill_overlap,
                freshness=rec.freshness,
                llm_rerank_score=rec.llm_rerank_score,
                expires_at=rec.expires_at,
                job=snippet,
            )
        )

    total_pages = max(1, (total + page_size - 1) // page_size)
    return RecommendationsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        tier=tier,
    )


@router.post("/regenerate", status_code=status.HTTP_202_ACCEPTED)
async def regenerate_recommendations(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Trigger an on-demand recommendation run for the current user.

    Rate-limited to once per hour. Returns 202 immediately; the run
    happens asynchronously so the UI should poll ``GET /recommendations``
    shortly after.
    """
    user_id = current_user["id"]
    # Check if we have fresh enough results to skip early.
    # "Fresh" = at least one non-expired recommendation from the last hour.
    from datetime import timedelta

    recent_cutoff = datetime.now(timezone.utc) - timedelta(seconds=REGENERATE_COOLDOWN_SECONDS)
    exists = (
        db.query(JobRecommendation)
        .filter(
            JobRecommendation.user_id == user_id,
            JobRecommendation.expires_at > datetime.now(timezone.utc),
            JobRecommendation.created_at > recent_cutoff,
        )
        .first()
    )
    if exists:
        return {"status": "already_fresh", "message": "Your recommendations were updated recently."}

    background_tasks.add_task(_bg_run, user_id)
    return {
        "status": "queued",
        "message": "Recommendation run started. Check back in a minute.",
    }


@router.post("/generate-all", status_code=status.HTTP_200_OK)
async def generate_all(
    x_cron_secret: Optional[str] = Header(None, alias="X-Cron-Secret"),
    db: Session = Depends(get_db),
):
    """Run recommendations for ALL eligible users. Requires X-Cron-Secret header."""
    if settings.CRON_SECRET:
        if not x_cron_secret or x_cron_secret != settings.CRON_SECRET:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or missing X-Cron-Secret header",
            )
    try:
        from app.services.recommendation_engine_v2 import RecommendationEngineV2

        engine = RecommendationEngineV2(db)
        stats = await engine.run_for_all_eligible_users()
        return {"status": "success", **stats}
    except Exception as exc:
        logger.error("generate-all failed: %r", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ---- Background helper -------------------------------------------------


async def _bg_run(user_id: str) -> None:
    """Run V2 engine in a fresh DB session for background tasks."""
    db = SessionLocal()
    try:
        from app.services.recommendation_engine_v2 import RecommendationEngineV2

        engine = RecommendationEngineV2(db)
        stats = await engine.run_for_user(user_id)
        logger.info(
            "Background recs V2 user=%s: t1=%d t2=%d t3=%d error=%s",
            user_id,
            stats.tier1,
            stats.tier2,
            stats.tier3,
            stats.error,
        )
    except Exception as exc:
        logger.error("Background recs V2 exception for user=%s: %r", user_id, exc)
    finally:
        db.close()

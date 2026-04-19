"""
Periodic Celery tasks.

These tasks replace the in-process APScheduler (see
`docs/RECOMMENDATIONS_V2_PLAN.md` §7, Phase 2). They are registered on the
Celery Beat schedule in `app/tasks/celery_app.py`.

All async work is executed via a throwaway event loop so the tasks stay
synchronous from Celery's perspective.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.constants import TECH_JOB_KEYWORDS
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


def _run_async(coro) -> Any:
    """Execute an async coroutine in a fresh event loop from a sync context."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


# ---------------------------------------------------------------------------
# Task: scrape recent jobs
# ---------------------------------------------------------------------------


@celery_app.task(name="scheduler.scrape_recent_jobs", ignore_result=False)
def scrape_recent_jobs() -> Dict[str, Any]:
    """
    Scrape jobs posted within the last 3 days from all FREE sources, plus any
    configured API-key sources. Runs on the Celery Beat schedule.
    """
    from app.core.config import settings
    from app.services.job_scraper_service import JobScraperService

    logger.info("scheduled.scrape_recent_jobs.start")

    db: Session = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=3)

        sources = ["remotive", "remoteok", "joinrise", "arbeitnow"]
        if getattr(settings, "JOOBLE_API_KEY", None):
            sources.append("jooble")
        if getattr(settings, "FINDWORK_API_KEY", None):
            sources.append("findwork")
        if getattr(settings, "SERPAPI_API_KEY", None):
            sources.append("serpapi")
        if getattr(settings, "ADZUNA_APP_ID", None) and getattr(
            settings, "ADZUNA_APP_KEY", None
        ):
            sources.append("adzuna")

        logger.info(
            "scheduled.scrape_recent_jobs.sources",
            sources=sources,
            keyword_count=len(TECH_JOB_KEYWORDS),
            cutoff=cutoff_date.isoformat(),
        )

        scraper = JobScraperService()
        result = _run_async(
            scraper.scrape_jobs(
                sources=sources,
                keywords=TECH_JOB_KEYWORDS,
                location="Worldwide",
                max_results_per_source=100,
                db=db,
                min_posted_date=cutoff_date,
            )
        )

        logger.info(
            "scheduled.scrape_recent_jobs.done",
            total_found=result.get("total_found", 0),
            stored=result.get("stored", 0),
            duplicates=result.get("duplicates", 0),
            failed=result.get("failed", 0),
        )

        # Piggy-back: ensure old jobs are cleaned even if midnight cleanup missed
        try:
            deleted = cleanup_old_jobs.run()  # synchronous call within worker
            logger.info("scheduled.scrape_recent_jobs.post_cleanup", deleted=deleted)
        except Exception as cleanup_err:  # pragma: no cover - defensive
            logger.warning(
                "scheduled.scrape_recent_jobs.post_cleanup_failed",
                error=str(cleanup_err),
            )

        return result

    except Exception as exc:
        logger.error(
            "scheduled.scrape_recent_jobs.failed", error=str(exc), exc_info=True
        )
        return {"status": "failed", "error": str(exc)}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Task: generate recommendations for all eligible users
# ---------------------------------------------------------------------------


@celery_app.task(
    name="scheduler.generate_recommendations_for_all", ignore_result=False
)
def generate_recommendations_for_all() -> Dict[str, Any]:
    """Generate recommendations for every eligible user."""
    from app.services.recommendation_generator import RecommendationGenerator

    logger.info("scheduled.generate_recommendations_for_all.start")

    db: Session = SessionLocal()
    try:
        generator = RecommendationGenerator(db)
        stats = _run_async(generator.generate_recommendations_for_all_users())
        logger.info(
            "scheduled.generate_recommendations_for_all.done", **(stats or {})
        )
        return stats or {}
    except Exception as exc:
        logger.error(
            "scheduled.generate_recommendations_for_all.failed",
            error=str(exc),
            exc_info=True,
        )
        db.rollback()
        return {"status": "failed", "error": str(exc)}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Task: backfill recommendations for users with zero recs
# ---------------------------------------------------------------------------


@celery_app.task(
    name="scheduler.generate_recommendations_for_empty_users", ignore_result=False
)
def generate_recommendations_for_empty_users() -> Dict[str, Any]:
    """
    Backfill recommendations for eligible users who currently have zero.

    Runs on a tight cadence so new signups see matches without waiting for
    the full generation pass.
    """
    from app.services.recommendation_generator import RecommendationGenerator

    logger.info("scheduled.backfill_empty_users.start")

    db: Session = SessionLocal()
    try:
        generator = RecommendationGenerator(db)
        user_ids = generator.get_eligible_user_ids_with_zero_recommendations()
        if not user_ids:
            logger.info("scheduled.backfill_empty_users.none")
            return {"status": "success", "users_processed": 0, "total_generated": 0}

        generated = 0
        errors = 0
        for user_id in user_ids:
            try:
                count = _run_async(
                    generator.generate_recommendations_for_user(user_id)
                )
                generated += count or 0
            except Exception as per_user_exc:
                errors += 1
                logger.error(
                    "scheduled.backfill_empty_users.user_failed",
                    user_id=user_id,
                    error=str(per_user_exc),
                )

        logger.info(
            "scheduled.backfill_empty_users.done",
            users_processed=len(user_ids),
            total_generated=generated,
            errors=errors,
        )
        return {
            "status": "success",
            "users_processed": len(user_ids),
            "total_generated": generated,
            "errors": errors,
        }
    except Exception as exc:
        logger.error(
            "scheduled.backfill_empty_users.failed", error=str(exc), exc_info=True
        )
        db.rollback()
        return {"status": "failed", "error": str(exc)}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Task: cleanup expired saved jobs
# ---------------------------------------------------------------------------


@celery_app.task(name="scheduler.cleanup_expired_saved_jobs", ignore_result=False)
def cleanup_expired_saved_jobs() -> int:
    """Delete saved applications past their `expires_at` timestamp."""
    from app.models.application import Application

    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        expired = (
            db.query(Application)
            .filter(
                Application.status == "saved",
                Application.expires_at < now,
            )
            .all()
        )
        if not expired:
            logger.info("scheduled.cleanup_expired_saved_jobs.none")
            return 0

        for application in expired:
            db.delete(application)
        db.commit()

        logger.info(
            "scheduled.cleanup_expired_saved_jobs.done",
            deleted=len(expired),
        )
        return len(expired)
    except Exception as exc:
        logger.error(
            "scheduled.cleanup_expired_saved_jobs.failed",
            error=str(exc),
            exc_info=True,
        )
        db.rollback()
        return 0
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Task: cleanup expired recommendations
# ---------------------------------------------------------------------------


@celery_app.task(name="scheduler.cleanup_expired_recommendations", ignore_result=False)
def cleanup_expired_recommendations() -> int:
    """Delete recommendations past their retention window."""
    from app.services.recommendation_generator import RecommendationGenerator

    db: Session = SessionLocal()
    try:
        generator = RecommendationGenerator(db)
        deleted = generator.cleanup_expired_recommendations()
        logger.info(
            "scheduled.cleanup_expired_recommendations.done", deleted=deleted
        )
        return deleted
    except Exception as exc:
        logger.error(
            "scheduled.cleanup_expired_recommendations.failed",
            error=str(exc),
            exc_info=True,
        )
        db.rollback()
        return 0
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Task: cleanup scraped jobs older than 7 days (skip jobs with applications)
# ---------------------------------------------------------------------------


@celery_app.task(name="scheduler.cleanup_old_jobs", ignore_result=False)
def cleanup_old_jobs() -> int:
    """Delete scraped jobs older than 7 days, preserving those with applications."""
    from app.models.application import Application
    from app.models.job import Job

    db: Session = SessionLocal()
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
        old_jobs = (
            db.query(Job)
            .filter(
                Job.scraped_at < cutoff_date,
                Job.source != "external",
            )
            .all()
        )
        if not old_jobs:
            logger.info("scheduled.cleanup_old_jobs.none")
            return 0

        jobs_to_delete = []
        jobs_skipped = 0
        for job in old_jobs:
            has_applications = (
                db.query(Application).filter(Application.job_id == job.id).count()
                > 0
            )
            if has_applications:
                jobs_skipped += 1
            else:
                jobs_to_delete.append(job)

        if not jobs_to_delete:
            logger.info(
                "scheduled.cleanup_old_jobs.all_retained",
                candidates=len(old_jobs),
                skipped=jobs_skipped,
            )
            return 0

        for job in jobs_to_delete:
            db.delete(job)
        db.commit()

        logger.info(
            "scheduled.cleanup_old_jobs.done",
            deleted=len(jobs_to_delete),
            skipped=jobs_skipped,
        )
        return len(jobs_to_delete)
    except Exception as exc:
        logger.error(
            "scheduled.cleanup_old_jobs.failed", error=str(exc), exc_info=True
        )
        db.rollback()
        return 0
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Helper: public manual trigger used by the cron-secret cleanup endpoint
# ---------------------------------------------------------------------------


def trigger_cleanup_old_jobs_sync() -> int:
    """
    Run the cleanup task inline (synchronously) from an HTTP handler.

    Callers like the `/jobs/cleanup-old` cron endpoint prefer inline execution
    so the response can report the deletion count directly.
    """
    return cleanup_old_jobs.run()

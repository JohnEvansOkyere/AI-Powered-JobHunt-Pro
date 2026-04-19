"""Backward-compatible wrapper around Recommendation Engine V2.

The previous implementation used a separate matching stack with hard
exclusion gates. Recommendations V2 moved generation to cached embeddings,
LLM rerank, and tiered persistence in
:mod:`app.services.recommendation_engine_v2`.

This class keeps the historical public methods used by legacy endpoints,
scripts, and Celery tasks, but delegates generation to V2 so there is only
one production recommendation pipeline.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.application import Application
from app.models.cv import CV
from app.models.job_recommendation import JobRecommendation
from app.models.user_profile import UserProfile
from app.services.recommendation_engine_v2 import RecommendationEngineV2

logger = get_logger(__name__)


class RecommendationGenerator:
    """Compatibility facade for V2 recommendation generation."""

    def __init__(self, db: Session):
        self.db = db
        self.engine = RecommendationEngineV2(db)

    def user_eligible_for_recommendations(self, user_id: str) -> bool:
        """User has enough signal for V2: profile, CV, or saved/applied jobs."""
        cv_exists = (
            self.db.query(CV.id)
            .filter(CV.user_id == user_id)
            .order_by(CV.created_at.desc())
            .first()
            is not None
        )
        profile = (
            self.db.query(UserProfile)
            .filter(UserProfile.user_id == user_id)
            .first()
        )
        has_profile_signal = bool(
            profile
            and (
                profile.primary_job_title
                or profile.secondary_job_titles
                or profile.technical_skills
            )
        )
        has_interest_signal = (
            self.db.query(Application.id)
            .filter(
                and_(
                    Application.user_id == user_id,
                    Application.status.in_(("saved", "applied", "interviewing", "offer")),
                )
            )
            .first()
            is not None
        )
        return cv_exists or has_profile_signal or has_interest_signal

    async def generate_recommendations_for_user(self, user_id: str) -> int:
        """Generate V2 recommendations for a single user and return row count."""
        stats = await self.engine.run_for_user(str(user_id))
        if stats.error:
            logger.warning(
                "recommendation_generator_v2_user_failed",
                user_id=str(user_id),
                error=stats.error,
            )
        return stats.total

    async def generate_recommendations_for_all_users(self) -> Dict[str, Any]:
        """Generate V2 recommendations for every eligible user.

        Returns both the V2 tier totals and the legacy ``total_recommendations``
        key so old scripts and endpoints continue to display useful summaries.
        """
        stats = await self.engine.run_for_all_eligible_users()
        total = (
            int(stats.get("tier1_total", 0))
            + int(stats.get("tier2_total", 0))
            + int(stats.get("tier3_total", 0))
        )
        return {
            **stats,
            "total_recommendations": total,
        }

    def get_eligible_user_ids_with_zero_recommendations(self) -> List[str]:
        """Eligible users who currently have no active recommendation rows."""
        now = datetime.now(timezone.utc)
        users_with_cvs = {str(r[0]) for r in self.db.query(CV.user_id).distinct().all()}
        users_with_profiles = {
            str(r[0])
            for r in (
                self.db.query(UserProfile.user_id)
                .filter(
                    or_(
                        UserProfile.primary_job_title.isnot(None),
                        UserProfile.technical_skills.isnot(None),
                    )
                )
                .distinct()
                .all()
            )
        }
        eligible = users_with_cvs | users_with_profiles
        if not eligible:
            return []

        users_with_recs = {
            str(r[0])
            for r in (
                self.db.query(JobRecommendation.user_id)
                .filter(JobRecommendation.expires_at > now)
                .distinct()
                .all()
            )
        }
        return sorted(eligible - users_with_recs)

    def cleanup_expired_recommendations(self) -> int:
        """Delete expired recommendation rows."""
        now = datetime.now(timezone.utc)
        deleted = (
            self.db.query(JobRecommendation)
            .filter(JobRecommendation.expires_at < now)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        logger.info("recommendation_generator_cleanup_expired", deleted=deleted)
        return int(deleted or 0)

    def get_recommendations_for_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        tier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Read precomputed V2 recommendations for a user."""
        return self.engine.get_for_user(
            str(user_id),
            tier=tier,
            page=page,
            page_size=page_size,
        )

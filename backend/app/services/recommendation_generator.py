"""
Recommendation Generator Service

Generates pre-computed job recommendations for users using AI matching.
Runs as a scheduled background job to avoid real-time delays.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, delete

from app.models.job import Job
from app.models.cv import CV
from app.models.job_recommendation import JobRecommendation
from app.services.ai_job_matcher import AIJobMatcher

logger = logging.getLogger(__name__)


class RecommendationGenerator:
    """Generates and manages pre-computed job recommendations."""

    def __init__(self, db: Session):
        self.db = db
        self.matcher = AIJobMatcher()
        self.recommendations_per_user = 50  # Store top 50 matches per user
        self.expiry_days = 3  # Recommendations expire after 3 days

    async def generate_recommendations_for_user(self, user_id: str) -> int:
        """
        Generate recommendations for a single user.

        Args:
            user_id: User UUID

        Returns:
            Number of recommendations created
        """
        logger.info(f"Generating recommendations for user: {user_id}")

        # Get user's latest CV
        cv = self.db.query(CV).filter(
            CV.user_id == user_id
        ).order_by(CV.created_at.desc()).first()

        if not cv:
            logger.warning(f"No CV found for user {user_id}, skipping recommendations")
            return 0

        # Get jobs from last 7 days (wider window to ensure enough matches)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
        recent_jobs = self.db.query(Job).filter(
            Job.scraped_at >= cutoff_date
        ).all()

        if not recent_jobs:
            logger.warning("No recent jobs found")
            return 0

        logger.info(f"Found {len(recent_jobs)} recent jobs to match against")

        # Generate matches using AI
        try:
            matches = await self.matcher.match_jobs_to_cv(
                cv=cv,
                jobs=recent_jobs,
                user_id=user_id,
                db=self.db
            )
        except Exception as e:
            logger.error(f"Error matching jobs for user {user_id}: {e}")
            return 0

        # Sort by match score and take top N
        matches.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        top_matches = matches[:self.recommendations_per_user]

        logger.info(f"Generated {len(top_matches)} recommendations for user {user_id}")

        # Delete existing recommendations for this user (rolling replacement)
        self.db.query(JobRecommendation).filter(
            JobRecommendation.user_id == user_id
        ).delete()

        # Save new recommendations
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.expiry_days)
        recommendations_created = 0

        for match in top_matches:
            try:
                recommendation = JobRecommendation(
                    user_id=user_id,
                    job_id=match['job_id'],
                    match_score=match.get('match_score', 0.0),
                    match_reason=match.get('match_reason', 'AI-based profile matching'),
                    expires_at=expires_at
                )
                self.db.add(recommendation)
                recommendations_created += 1
            except Exception as e:
                logger.error(f"Error saving recommendation: {e}")
                continue

        self.db.commit()

        logger.info(f"✅ Created {recommendations_created} recommendations for user {user_id}")
        return recommendations_created

    async def generate_recommendations_for_all_users(self) -> Dict[str, Any]:
        """
        Generate recommendations for all users who have CVs.

        Returns:
            Summary statistics
        """
        logger.info("=" * 80)
        logger.info("🎯 RECOMMENDATION GENERATION: Starting for all users")
        logger.info(f"⏰ Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info("=" * 80)

        # Get all users who have CVs
        users_with_cvs = self.db.query(CV.user_id).distinct().all()
        user_ids = [str(user[0]) for user in users_with_cvs]

        if not user_ids:
            logger.warning("No users with CVs found")
            return {
                'total_users': 0,
                'successful': 0,
                'failed': 0,
                'total_recommendations': 0
            }

        logger.info(f"Found {len(user_ids)} users with CVs")

        stats = {
            'total_users': len(user_ids),
            'successful': 0,
            'failed': 0,
            'total_recommendations': 0
        }

        # Generate recommendations for each user
        for user_id in user_ids:
            try:
                count = await self.generate_recommendations_for_user(user_id)
                stats['total_recommendations'] += count
                stats['successful'] += 1
            except Exception as e:
                logger.error(f"Failed to generate recommendations for user {user_id}: {e}")
                stats['failed'] += 1
                continue

        logger.info("=" * 80)
        logger.info(f"✅ RECOMMENDATION GENERATION COMPLETED")
        logger.info(f"   Users processed: {stats['successful']}/{stats['total_users']}")
        logger.info(f"   Total recommendations: {stats['total_recommendations']}")
        logger.info(f"   Failed: {stats['failed']}")
        logger.info("=" * 80)

        return stats

    def cleanup_expired_recommendations(self) -> int:
        """
        Delete expired recommendations.

        Returns:
            Number of recommendations deleted
        """
        logger.info("🧹 Cleaning up expired recommendations")

        now = datetime.now(timezone.utc)
        result = self.db.query(JobRecommendation).filter(
            JobRecommendation.expires_at < now
        ).delete()

        self.db.commit()

        logger.info(f"✅ Deleted {result} expired recommendations")
        return result

    def get_recommendations_for_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Get active recommendations for a user (paginated).

        Args:
            user_id: User UUID
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Paginated recommendations with job details
        """
        now = datetime.now(timezone.utc)

        # Query active recommendations
        query = self.db.query(JobRecommendation).filter(
            and_(
                JobRecommendation.user_id == user_id,
                JobRecommendation.expires_at > now
            )
        ).order_by(JobRecommendation.match_score.desc())

        # Get total count
        total = query.count()

        # Paginate
        offset = (page - 1) * page_size
        recommendations = query.offset(offset).limit(page_size).all()

        return {
            'recommendations': recommendations,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }

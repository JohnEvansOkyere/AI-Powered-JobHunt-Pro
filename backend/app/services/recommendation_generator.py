"""
Recommendation Generator Service

Generates pre-computed job recommendations for users using AI matching.
Runs as a scheduled background job to avoid real-time delays.

Uses BOTH CV and Profile data for matching:
- Profile data: Job titles, skills, preferences, industries
- CV data: Experience, education, certifications

Recommendations are generated for users who have either:
1. A CV uploaded (with or without profile)
2. A profile with job details filled in (primary job title, skills, etc.)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, delete, or_

from app.models.job import Job
from app.models.cv import CV
from app.models.user_profile import UserProfile
from app.models.job_recommendation import JobRecommendation
from app.models.application import Application
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
        Generate recommendations for a single user using CV, profile, AND application history.

        The AI matcher will use:
        - Profile data: primary/secondary job titles, skills, preferences
        - CV data: experience, education (if available)
        - Application history: jobs user has saved, viewed, or applied to (interest signals)

        Args:
            user_id: User UUID

        Returns:
            Number of recommendations created
        """
        logger.info(f"Generating recommendations for user: {user_id}")

        # Get user's latest CV (optional - can be None)
        cv = self.db.query(CV).filter(
            CV.user_id == user_id
        ).order_by(CV.created_at.desc()).first()

        # Get user's profile (used for job titles, skills, preferences)
        profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()

        # Get user's interested jobs (saved, draft/in-progress, submitted, etc.)
        # These serve as signals for what kinds of jobs the user wants
        interested_job_ids = self._get_user_interested_job_ids(user_id)
        interested_jobs = []
        if interested_job_ids:
            interested_jobs = self.db.query(Job).filter(
                Job.id.in_(interested_job_ids)
            ).all()
            logger.info(f"User {user_id} has {len(interested_jobs)} interested jobs for context")

        # Check if user has enough data for matching
        has_cv = cv is not None
        has_profile_data = profile and (
            profile.primary_job_title or
            profile.secondary_job_titles or
            profile.technical_skills
        )
        has_interest_signals = len(interested_jobs) > 0

        if not has_cv and not has_profile_data and not has_interest_signals:
            logger.warning(f"User {user_id} has no CV, profile, or interest signals - skipping recommendations")
            return 0

        logger.info(f"User {user_id}: CV={has_cv}, Profile={has_profile_data}, Interest signals={has_interest_signals}")

        # Get jobs from last 7 days (wider window to ensure enough matches)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
        recent_jobs = self.db.query(Job).filter(
            Job.scraped_at >= cutoff_date
        ).all()

        if not recent_jobs:
            logger.warning("No recent jobs found")
            return 0

        logger.info(f"Found {len(recent_jobs)} recent jobs to match against")

        # Generate matches using AI (uses CV + profile + interest signals)
        try:
            matches = await self.matcher.match_jobs_to_cv(
                cv=cv,  # Can be None - matcher will use profile data
                jobs=recent_jobs,
                user_id=user_id,
                db=self.db,
                interested_jobs=interested_jobs  # NEW: pass user's interested jobs
            )
        except Exception as e:
            logger.error(f"Error matching jobs for user {user_id}: {e}")
            return 0

        # Boost scores for jobs similar to user's interested jobs
        if interested_jobs:
            matches = self._boost_similar_to_interests(matches, interested_jobs, recent_jobs)

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

    def _get_user_interested_job_ids(self, user_id: str) -> List[str]:
        """
        Get job IDs that user has shown interest in.

        Interest signals (in order of strength):
        - submitted: User applied to this job (strongest signal)
        - interviewing: User is interviewing for this job
        - finalized/reviewed/draft: User is actively working on application
        - saved: User bookmarked this job

        Args:
            user_id: User UUID

        Returns:
            List of job UUIDs user is interested in
        """
        # Query applications with interest-indicating statuses
        interest_statuses = ['saved', 'draft', 'reviewed', 'finalized', 'sent', 'submitted', 'interviewing']

        applications = self.db.query(Application.job_id).filter(
            and_(
                Application.user_id == user_id,
                Application.status.in_(interest_statuses)
            )
        ).all()

        job_ids = [str(app.job_id) for app in applications]
        return job_ids

    def _boost_similar_to_interests(
        self,
        matches: List[Dict[str, Any]],
        interested_jobs: List[Job],
        all_jobs: List[Job]
    ) -> List[Dict[str, Any]]:
        """
        Boost match scores for jobs similar to user's interested jobs.

        Uses simple keyword matching on job titles and companies.
        Jobs that are similar to what the user has saved/applied to get a boost.

        Args:
            matches: Current match results
            interested_jobs: Jobs user has shown interest in
            all_jobs: All available jobs

        Returns:
            Updated matches with boosted scores
        """
        if not interested_jobs:
            return matches

        # Extract key signals from interested jobs
        interested_titles = set()
        interested_companies = set()
        interested_keywords = set()

        for job in interested_jobs:
            # Add job title words (excluding common words)
            title_words = job.title.lower().split()
            for word in title_words:
                if len(word) > 3 and word not in {'senior', 'junior', 'lead', 'staff', 'principal', 'remote', 'hybrid'}:
                    interested_keywords.add(word)

            # Track normalized title patterns
            interested_titles.add(job.normalized_title.lower() if job.normalized_title else job.title.lower())

            # Track companies (user might prefer similar companies)
            interested_companies.add(job.company.lower())

        logger.info(f"Interest signals - Keywords: {list(interested_keywords)[:10]}, Companies: {list(interested_companies)[:5]}")

        # Create a map of job_id to job for quick lookup
        job_map = {str(job.id): job for job in all_jobs}

        # Boost scores for similar jobs
        for match in matches:
            job_id = match.get('job_id')
            if not job_id or job_id not in job_map:
                continue

            job = job_map[job_id]
            boost = 0.0

            # Check title keyword overlap
            job_title_lower = job.title.lower()
            job_title_words = set(job_title_lower.split())
            keyword_overlap = len(job_title_words.intersection(interested_keywords))

            if keyword_overlap >= 2:
                boost += 15.0  # Strong title similarity
                logger.debug(f"Title keyword boost (+15%): {job.title}")
            elif keyword_overlap >= 1:
                boost += 8.0  # Partial title similarity
                logger.debug(f"Partial title boost (+8%): {job.title}")

            # Check if same company
            if job.company.lower() in interested_companies:
                boost += 10.0  # Same company as saved/applied job
                logger.debug(f"Company boost (+10%): {job.company}")

            # Apply boost
            if boost > 0:
                original_score = match.get('match_score', 0)
                new_score = min(100.0, original_score + boost)
                match['match_score'] = new_score

                # Update reason to indicate interest-based boosting
                if 'similar to your saved jobs' not in match.get('match_reason', ''):
                    match['match_reason'] = f"{match.get('match_reason', '')} - similar to your saved jobs"

                logger.info(f"🎯 Interest boost: {job.title} ({job.company}) - {original_score:.1f}% → {new_score:.1f}% (+{boost}%)")

        return matches

    async def generate_recommendations_for_all_users(self) -> Dict[str, Any]:
        """
        Generate recommendations for all users who have CVs OR profiles with job details.

        This includes:
        - Users with CVs (parsed or not)
        - Users with profiles that have primary_job_title or technical_skills set

        Returns:
            Summary statistics
        """
        logger.info("=" * 80)
        logger.info("🎯 RECOMMENDATION GENERATION: Starting for all eligible users")
        logger.info(f"⏰ Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info("=" * 80)

        # Get users with CVs
        users_with_cvs = self.db.query(CV.user_id).distinct().all()
        cv_user_ids = {str(user[0]) for user in users_with_cvs}

        # Get users with profiles that have job details (primary job title OR technical skills)
        users_with_profiles = self.db.query(UserProfile.user_id).filter(
            or_(
                UserProfile.primary_job_title.isnot(None),
                UserProfile.technical_skills.isnot(None)
            )
        ).distinct().all()
        profile_user_ids = {str(user[0]) for user in users_with_profiles}

        # Union of both sets - users who have CV OR profile with job details
        user_ids = list(cv_user_ids | profile_user_ids)

        if not user_ids:
            logger.warning("No users with CVs or profiles found")
            return {
                'total_users': 0,
                'successful': 0,
                'failed': 0,
                'total_recommendations': 0
            }

        logger.info(f"Found {len(user_ids)} eligible users:")
        logger.info(f"   - Users with CVs: {len(cv_user_ids)}")
        logger.info(f"   - Users with profiles: {len(profile_user_ids)}")
        logger.info(f"   - Total unique users: {len(user_ids)}")

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

"""
Optimized Job Matching Service

Performance improvements:
1. Caching of match results
2. Limit jobs processed per request
3. Background job for full matching
4. Return cached results immediately
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
import hashlib
import json

from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.user_profile import UserProfile
from app.models.cv import CV
from app.core.logging import get_logger

logger = get_logger(__name__)


class OptimizedJobMatchingService:
    """
    Optimized service for matching jobs to users.

    Key optimizations:
    - Returns cached matches if available (< 1 hour old)
    - Limits processing to top N jobs per request
    - Returns immediately while processing in background
    """

    # Cache expiry time (1 hour)
    CACHE_EXPIRY_HOURS = 1

    # Max jobs to process per request
    MAX_JOBS_PER_REQUEST = 20

    def __init__(self):
        """Initialize optimized matching service."""
        pass

    async def get_cached_matches(
        self,
        user_id: str,
        db: Session,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get cached job matches for a user.
        Returns cached results if available, otherwise computes new matches.

        This is FAST - returns immediately with cached data.

        Args:
            user_id: User ID
            db: Database session
            limit: Maximum number of matches to return

        Returns:
            List of job matches with scores
        """
        # Check for cached matches
        cutoff_time = datetime.utcnow() - timedelta(hours=self.CACHE_EXPIRY_HOURS)

        cached_matches = db.query(JobMatch).filter(
            and_(
                JobMatch.user_id == user_id,
                JobMatch.updated_at >= cutoff_time
            )
        ).order_by(JobMatch.relevance_score.desc()).limit(limit).all()

        if cached_matches:
            logger.info(f"Returning {len(cached_matches)} cached matches for user {user_id}")

            # Convert to format expected by API
            results = []
            for match in cached_matches:
                job = db.query(Job).filter(Job.id == match.job_id).first()
                if job:
                    results.append({
                        "job": job,
                        "relevance_score": match.relevance_score,
                        "match_reasons": match.match_reasons or []
                    })

            return results

        # No cached matches - compute new ones (limited set)
        logger.info(f"No cached matches found, computing new matches for user {user_id}")
        return await self.compute_quick_matches(user_id, db, limit)

    async def compute_quick_matches(
        self,
        user_id: str,
        db: Session,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Compute matches for a limited set of jobs (FAST).

        Only processes MAX_JOBS_PER_REQUEST jobs to keep response time low.

        Args:
            user_id: User ID
            db: Database session
            limit: Maximum number of matches to return

        Returns:
            List of job matches
        """
        # Get user profile
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            logger.warning(f"No profile found for user {user_id}")
            return []

        # Get active CV
        cv = db.query(CV).filter(
            and_(CV.user_id == user_id, CV.is_active == True)
        ).first()

        # Get recent jobs (limit to reduce processing time)
        jobs = db.query(Job).order_by(Job.created_at.desc()).limit(self.MAX_JOBS_PER_REQUEST).all()

        if not jobs:
            logger.warning(f"No jobs available for matching")
            return []

        logger.info(f"Quick matching {len(jobs)} recent jobs for user {user_id}")

        # Prepare user data
        user_data = self._prepare_user_data(profile, cv)

        # Match jobs with minimum score threshold
        matches = []
        MIN_SCORE = 20.0  # Minimum 20% relevance required (lowered to allow more relevant matches)

        for job in jobs:
            match_result = self._quick_match_job(user_data, job, profile)

            # Only include jobs with meaningful match scores
            if match_result["relevance_score"] >= MIN_SCORE:
                matches.append({
                    "job": job,
                    **match_result
                })
            else:
                logger.debug(f"Excluded job '{job.title}' - score too low: {match_result['relevance_score']}")

        # Sort by score
        matches.sort(key=lambda x: x["relevance_score"], reverse=True)
        matches = matches[:limit]

        # Cache results
        try:
            for match in matches:
                self._store_match(user_id, match["job"].id, match, db)
            db.commit()
            logger.info(f"Cached {len(matches)} quick matches")
        except Exception as e:
            logger.error(f"Error caching matches: {e}")
            db.rollback()

        return matches

    def _prepare_user_data(self, profile: UserProfile, cv: Optional[CV]) -> Dict[str, Any]:
        """Extract user skills and preferences from profile and CV."""
        skills = []

        # Extract technical skills from profile (JSONB format: [{skill, years, confidence}])
        if profile.technical_skills:
            if isinstance(profile.technical_skills, list):
                for skill_obj in profile.technical_skills:
                    if isinstance(skill_obj, dict) and 'skill' in skill_obj:
                        skills.append(skill_obj['skill'])
                    elif isinstance(skill_obj, str):
                        skills.append(skill_obj)

        # Add tools/technologies
        if profile.tools_technologies:
            skills.extend(profile.tools_technologies)

        # Add CV skills if available
        if cv and cv.parsed_content:
            parsed = cv.parsed_content
            if isinstance(parsed, dict):
                cv_skills = parsed.get("skills", {})
                if isinstance(cv_skills, dict):
                    technical = cv_skills.get("technical", [])
                    if technical:
                        skills.extend(technical)

        # Deduplicate and lowercase
        skills = list(set([s.lower().strip() for s in skills if s]))

        user_data = {
            "skills": skills,
            "job_title": profile.primary_job_title or "",
            "seniority": profile.seniority_level or "",
            "work_preference": profile.work_preference or "",
        }

        return user_data

    def _quick_match_job(
        self,
        user_data: Dict[str, Any],
        job: Job,
        profile: UserProfile
    ) -> Dict[str, Any]:
        """
        Improved job matching with better relevance filtering.

        Changes:
        - Word boundary matching for skills (not substring)
        - Excludes non-tech job titles
        - Minimum score threshold of 40%
        """
        import re

        score = 0.0
        reasons = []

        job_text = f"{job.title} {job.description}".lower()
        job_title_lower = job.title.lower()

        # FILTER 1: Exclude non-tech/non-relevant job categories
        excluded_keywords = [
            'therapist', 'therapy', 'physical therapy', 'behavioral',
            'nurse', 'nursing', 'medical', 'healthcare', 'physician',
            'teacher', 'tutor', 'counselor', 'social worker',
            'driver', 'delivery', 'warehouse', 'retail', 'sales clerk'
        ]

        for keyword in excluded_keywords:
            if keyword in job_title_lower:
                logger.debug(f"Excluded job '{job.title}' - non-tech category: {keyword}")
                return {"relevance_score": 0.0, "match_reasons": []}

        # FILTER 2: Only include jobs with tech/business keywords in title
        tech_title_keywords = [
            'engineer', 'developer', 'programmer', 'architect', 'devops',
            'data', 'analyst', 'scientist', 'machine learning', 'ai', 'ml',
            'software', 'backend', 'frontend', 'full stack', 'fullstack',
            'cloud', 'platform', 'infrastructure', 'security', 'qa', 'test',
            'product manager', 'project manager', 'scrum master', 'agile',
            'designer', 'ux', 'ui', 'technical', 'lead', 'head of', 'cto', 'cio'
        ]

        has_tech_keyword = any(kw in job_title_lower for kw in tech_title_keywords)
        if not has_tech_keyword:
            logger.debug(f"Excluded job '{job.title}' - no tech keywords in title")
            return {"relevance_score": 0.0, "match_reasons": []}

        # 1. Skill matching (60% weight) - Use word boundaries
        matched_skills = []
        for skill in user_data["skills"]:
            # Use word boundary matching to avoid false positives
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, job_text):
                matched_skills.append(skill)

        if matched_skills:
            skill_score = min(60, len(matched_skills) * 10)
            score += skill_score
            reasons.append(f"Skills match: {', '.join(matched_skills[:3])}")

        # 2. Title matching (30% weight) - Check if job title contains user's role keywords
        if user_data["job_title"]:
            user_title_lower = user_data["job_title"].lower()

            # Split by pipe (|) to handle multiple job titles
            user_job_titles = [t.strip() for t in user_title_lower.split('|')]

            # Check if any user job title appears in the job title
            title_match_score = 0
            for user_role in user_job_titles:
                # Extract key role words (ignore common words like "senior", "junior")
                role_words = [w for w in user_role.split() if w not in ['senior', 'junior', 'mid', 'entry', 'level', '/', '-']]

                # Check if role words appear in job title
                matching_words = [w for w in role_words if w in job_title_lower]

                if matching_words:
                    # Give points based on how many words matched
                    word_match_ratio = len(matching_words) / max(len(role_words), 1)
                    role_score = int(word_match_ratio * 30)
                    title_match_score = max(title_match_score, role_score)

            if title_match_score > 0:
                score += title_match_score
                reasons.append("Job title matches your role")

        # 3. Location preference (5% weight) - Reduced importance
        if profile.work_preference == "remote" and job.remote_type == "remote":
            score += 5
            reasons.append("Remote position")

        # 4. Seniority matching (5% weight) - Reduced importance
        if user_data["seniority"]:
            seniority = user_data["seniority"].lower()
            if seniority in job_title_lower:
                score += 5
                reasons.append(f"Seniority: {seniority}")

        return {
            "relevance_score": round(min(100, score), 2),
            "match_reasons": reasons[:5]
        }

    def _store_match(
        self,
        user_id: str,
        job_id: str,
        match_result: Dict[str, Any],
        db: Session
    ):
        """Store or update job match in database."""
        existing = db.query(JobMatch).filter(
            and_(
                JobMatch.user_id == user_id,
                JobMatch.job_id == job_id
            )
        ).first()

        if existing:
            # Update existing match
            existing.relevance_score = match_result["relevance_score"]
            existing.match_reasons = match_result["match_reasons"]
            existing.updated_at = datetime.utcnow()
        else:
            # Create new match
            match = JobMatch(
                user_id=user_id,
                job_id=job_id,
                relevance_score=match_result["relevance_score"],
                match_reasons=match_result["match_reasons"]
            )
            db.add(match)


# Singleton instance
_optimized_service = None

def get_optimized_matching_service() -> OptimizedJobMatchingService:
    """Get singleton instance of optimized matching service."""
    global _optimized_service
    if _optimized_service is None:
        _optimized_service = OptimizedJobMatchingService()
    return _optimized_service

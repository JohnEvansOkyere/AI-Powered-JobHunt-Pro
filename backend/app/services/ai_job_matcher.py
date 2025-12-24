"""
AI-Powered Job Matching Service

Uses OpenAI embeddings for semantic similarity matching.
Much more accurate than keyword matching - understands context and meaning.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
import os

from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.user_profile import UserProfile
from app.models.cv import CV
from app.core.logging import get_logger

logger = get_logger(__name__)


class AIJobMatcher:
    """
    AI-powered job matching using OpenAI embeddings.

    How it works:
    1. Creates semantic embeddings of user's profile (skills, experience, goals)
    2. Creates semantic embeddings of each job (title, description)
    3. Calculates cosine similarity (0-100%) between user and job
    4. Only shows jobs with 50%+ similarity (good quality matches worth applying to)
    """

    CACHE_EXPIRY_HOURS = 1
    MAX_JOBS_PER_REQUEST = 20
    MIN_SCORE = 50.0  # Only show good-quality matches (50%+ = worth applying)

    def __init__(self):
        """Initialize OpenAI client."""
        # Load from environment (settings will have loaded .env)
        from app.core.config import settings

        api_key = settings.OPENAI_API_KEY if hasattr(settings, 'OPENAI_API_KEY') else os.getenv("OPENAI_API_KEY")

        if not api_key:
            logger.warning("OPENAI_API_KEY not configured - AI matching will fail")
            raise ValueError("OPENAI_API_KEY not found in environment. Please add it to .env file.")

        self.client = OpenAI(api_key=api_key)
        self.model = "text-embedding-3-small"  # Fast, cheap, accurate
        logger.info("AI Job Matcher initialized with OpenAI embeddings")

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text using OpenAI."""
        try:
            # Clean text
            text = text.replace("\n", " ").strip()
            if not text:
                return []

            response = self.client.embeddings.create(
                input=[text],
                model=self.model
            )

            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return []

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors (0-1)."""
        if not vec1 or not vec2:
            return 0.0

        vec1 = np.array(vec1)
        vec2 = np.array(vec2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(similarity)

    def create_user_profile_text(self, profile: UserProfile, cv: Optional[CV]) -> str:
        """
        Create a rich text representation of user's profile.
        This will be converted to an embedding for matching.
        """
        parts = []

        # Job titles they want
        if profile.primary_job_title:
            parts.append(f"Target roles: {profile.primary_job_title}")

        # Seniority level
        if profile.seniority_level:
            parts.append(f"Seniority: {profile.seniority_level}")

        # Skills
        skills = []
        if profile.technical_skills:
            if isinstance(profile.technical_skills, list):
                for skill_obj in profile.technical_skills:
                    if isinstance(skill_obj, dict) and 'skill' in skill_obj:
                        skills.append(skill_obj['skill'])
                    elif isinstance(skill_obj, str):
                        skills.append(skill_obj)

        if profile.tools_technologies:
            skills.extend(profile.tools_technologies)

        if skills:
            parts.append(f"Technical skills: {', '.join(skills[:20])}")  # Limit to avoid token limits

        # Soft skills
        if profile.soft_skills:
            parts.append(f"Soft skills: {', '.join(profile.soft_skills[:10])}")

        # Work preferences
        if profile.work_preference:
            parts.append(f"Work preference: {profile.work_preference}")

        # Industries
        if profile.desired_industries:
            parts.append(f"Industries: {', '.join(profile.desired_industries[:5])}")

        # Experience from CV
        if cv and cv.parsed_content:
            parsed = cv.parsed_content
            if isinstance(parsed, dict):
                # Add experience summary
                experience = parsed.get('experience', [])
                if experience and isinstance(experience, list):
                    exp_summary = []
                    for exp in experience[:3]:  # Top 3 experiences
                        if isinstance(exp, dict):
                            role = exp.get('role', '')
                            company = exp.get('company', '')
                            if role:
                                exp_summary.append(f"{role} at {company}")

                    if exp_summary:
                        parts.append(f"Experience: {'; '.join(exp_summary)}")

        profile_text = ". ".join(parts)
        logger.debug(f"User profile text: {profile_text[:200]}...")
        return profile_text

    def create_job_text(self, job: Job) -> str:
        """
        Create a rich text representation of the job.
        This will be converted to an embedding for matching.
        """
        parts = []

        # Job title (most important)
        parts.append(f"Job Title: {job.title}")

        # Company
        parts.append(f"Company: {job.company}")

        # Remote type
        if job.remote_type:
            parts.append(f"Work type: {job.remote_type}")

        # Location
        if job.location:
            parts.append(f"Location: {job.location}")

        # Job description (truncate to avoid token limits)
        if job.description:
            # Clean HTML tags
            import re
            clean_desc = re.sub(r'<[^>]+>', '', job.description)
            clean_desc = clean_desc.replace('\n', ' ').strip()

            # Limit to 500 chars to save tokens
            if len(clean_desc) > 500:
                clean_desc = clean_desc[:500] + "..."

            parts.append(f"Description: {clean_desc}")

        job_text = ". ".join(parts)
        return job_text

    async def get_cached_matches(
        self,
        user_id: str,
        db: Session,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get cached job matches or compute new ones using AI.

        Returns only high-quality matches (60%+ similarity).
        """
        # Check cache first
        cutoff_time = datetime.utcnow() - timedelta(hours=self.CACHE_EXPIRY_HOURS)

        cached_matches = db.query(JobMatch).filter(
            and_(
                JobMatch.user_id == user_id,
                JobMatch.updated_at >= cutoff_time,
                JobMatch.relevance_score >= self.MIN_SCORE  # Only high-quality matches
            )
        ).order_by(JobMatch.relevance_score.desc()).limit(limit).all()

        if cached_matches:
            logger.info(f"Returning {len(cached_matches)} cached AI matches (50%+ quality)")
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

        # No cache - compute AI matches
        logger.info(f"Cache miss - computing AI matches for user {user_id}")
        return await self.compute_ai_matches(user_id, db, limit)

    async def compute_ai_matches(
        self,
        user_id: str,
        db: Session,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Compute job matches using OpenAI embeddings.

        This is the core AI matching logic.
        """
        # Get user profile
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            logger.warning(f"No profile found for user {user_id}")
            return []

        # Get CV
        cv = db.query(CV).filter(
            and_(CV.user_id == user_id, CV.is_active == True)
        ).first()

        # Create user profile embedding
        logger.info("Creating user profile embedding...")
        user_text = self.create_user_profile_text(profile, cv)
        user_embedding = self.get_embedding(user_text)

        if not user_embedding:
            logger.error("Failed to create user embedding")
            return []

        # Get recent jobs (limit to save API costs)
        jobs = db.query(Job).order_by(Job.created_at.desc()).limit(self.MAX_JOBS_PER_REQUEST).all()

        if not jobs:
            logger.warning("No jobs available for matching")
            return []

        logger.info(f"Matching user against {len(jobs)} recent jobs using AI...")

        # Filter out non-tech jobs first (save API costs)
        tech_jobs = self._filter_tech_jobs(jobs)
        logger.info(f"Filtered to {len(tech_jobs)} tech jobs")

        # Match each job
        matches = []
        for job in tech_jobs:
            # Create job embedding
            job_text = self.create_job_text(job)
            job_embedding = self.get_embedding(job_text)

            if not job_embedding:
                continue

            # Calculate similarity (0-1)
            similarity = self.cosine_similarity(user_embedding, job_embedding)

            # Convert to percentage (0-100)
            score = round(similarity * 100, 2)

            # Only include high-quality matches
            if score >= self.MIN_SCORE:
                reasons = self._generate_match_reasons(score, profile, job)

                matches.append({
                    "job": job,
                    "relevance_score": score,
                    "match_reasons": reasons
                })

                logger.info(f"✅ Match: {job.title} - {score}%")
            else:
                logger.debug(f"❌ Low score: {job.title} - {score}%")

        # Sort by score
        matches.sort(key=lambda x: x["relevance_score"], reverse=True)
        matches = matches[:limit]

        # Cache results
        try:
            for match in matches:
                self._store_match(user_id, match["job"].id, match, db)
            db.commit()
            logger.info(f"Cached {len(matches)} AI matches")
        except Exception as e:
            logger.error(f"Error caching matches: {e}")
            db.rollback()

        return matches

    def _filter_tech_jobs(self, jobs: List[Job]) -> List[Job]:
        """Filter out non-tech jobs to save API costs."""
        excluded_keywords = [
            'therapist', 'therapy', 'physical therapy', 'behavioral',
            'nurse', 'nursing', 'medical', 'healthcare', 'physician',
            'teacher', 'tutor', 'counselor', 'social worker',
            'driver', 'delivery', 'warehouse', 'retail', 'sales clerk'
        ]

        tech_title_keywords = [
            'engineer', 'developer', 'programmer', 'architect', 'devops',
            'data', 'analyst', 'scientist', 'machine learning', 'ai', 'ml',
            'software', 'backend', 'frontend', 'full stack', 'fullstack',
            'cloud', 'platform', 'infrastructure', 'security', 'qa', 'test',
            'product manager', 'project manager', 'scrum master', 'agile',
            'designer', 'ux', 'ui', 'technical', 'lead', 'head of', 'cto', 'cio'
        ]

        filtered = []
        for job in jobs:
            title_lower = job.title.lower()

            # Exclude non-tech
            if any(kw in title_lower for kw in excluded_keywords):
                continue

            # Require tech keyword
            if any(kw in title_lower for kw in tech_title_keywords):
                filtered.append(job)

        return filtered

    def _generate_match_reasons(self, score: float, profile: UserProfile, job: Job) -> List[str]:
        """Generate human-readable reasons for the match."""
        reasons = []

        if score >= 70:
            reasons.append("Excellent match - highly recommended")
        elif score >= 60:
            reasons.append("Strong match - great opportunity")
        elif score >= 50:
            reasons.append("Good match - worth applying")

        # Check for title alignment
        if profile.primary_job_title:
            user_titles = [t.strip().lower() for t in profile.primary_job_title.split('|')]
            job_title_lower = job.title.lower()

            for user_title in user_titles:
                # Extract key words
                key_words = [w for w in user_title.split() if len(w) > 3]
                if any(word in job_title_lower for word in key_words):
                    reasons.append("Title aligns with your target roles")
                    break

        # Check remote preference
        if profile.work_preference == "remote" and job.remote_type == "remote":
            reasons.append("Remote position matches your preference")

        # Check seniority
        if profile.seniority_level and profile.seniority_level.lower() in job.title.lower():
            reasons.append(f"Matches your {profile.seniority_level} level")

        return reasons[:5]  # Limit to 5 reasons

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
                match_reasons=match_result["match_reasons"],
                status="pending",
                matched_at=datetime.utcnow()
            )
            db.add(match)


# Singleton instance
_ai_matcher_instance = None

def get_ai_job_matcher() -> AIJobMatcher:
    """Get singleton instance of AI job matcher."""
    global _ai_matcher_instance
    if _ai_matcher_instance is None:
        _ai_matcher_instance = AIJobMatcher()
    return _ai_matcher_instance

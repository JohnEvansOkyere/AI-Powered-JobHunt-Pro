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
    4. Shows jobs with 20%+ similarity (reasonable matches worth considering)
    """

    CACHE_EXPIRY_HOURS = 1
    MAX_JOBS_PER_REQUEST = 200  # Check more jobs for better matches
    MIN_SCORE = 20.0  # Show matches with 20%+ similarity (reasonable threshold)

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

    def create_user_profile_text(self, profile: UserProfile, cv: Optional[CV], interested_jobs: Optional[List[Job]] = None) -> str:
        """
        Create a rich text representation of user's profile.
        This will be converted to an embedding for matching.

        Uses ALL available profile fields:
        - primary_job_title, secondary_job_titles
        - technical_skills (JSON string or list of {skill: name} objects)
        - soft_skills, tools_technologies
        - seniority_level, work_preference
        - desired_industries, preferred_keywords
        - experience (from profile AND CV)
        - interested_jobs: Jobs user has saved/applied to (interest signals)
        """
        import json
        parts = []

        # Job titles they want (include both primary and secondary)
        # Note: primary_job_title can contain multiple titles separated by "|"
        target_roles = []
        if profile.primary_job_title:
            # Split by "|" in case multiple titles are combined
            primary_titles = [t.strip() for t in profile.primary_job_title.split("|")]
            target_roles.extend(primary_titles)
        if profile.secondary_job_titles:
            if isinstance(profile.secondary_job_titles, list):
                target_roles.extend(profile.secondary_job_titles)
            elif isinstance(profile.secondary_job_titles, str):
                # Try to parse as JSON if it's a string
                try:
                    parsed = json.loads(profile.secondary_job_titles)
                    if isinstance(parsed, list):
                        target_roles.extend(parsed)
                except (json.JSONDecodeError, TypeError):
                    target_roles.append(profile.secondary_job_titles)

        if target_roles:
            parts.append(f"Target roles: {', '.join(target_roles)}")

        # Seniority level
        if profile.seniority_level:
            parts.append(f"Seniority: {profile.seniority_level}")

        # Technical Skills - handle both JSON string and list formats
        skills = []
        if profile.technical_skills:
            tech_skills = profile.technical_skills

            # If it's a string, try to parse as JSON
            if isinstance(tech_skills, str):
                try:
                    tech_skills = json.loads(tech_skills)
                except (json.JSONDecodeError, TypeError):
                    # If parsing fails, treat as comma-separated string
                    skills.extend([s.strip() for s in tech_skills.split(",")])
                    tech_skills = None

            # If it's a list, extract skill names
            if isinstance(tech_skills, list):
                for skill_obj in tech_skills:
                    if isinstance(skill_obj, dict) and 'skill' in skill_obj:
                        skills.append(skill_obj['skill'])
                    elif isinstance(skill_obj, str):
                        skills.append(skill_obj)

        # Add tools_technologies
        if profile.tools_technologies:
            if isinstance(profile.tools_technologies, list):
                skills.extend(profile.tools_technologies)
            elif isinstance(profile.tools_technologies, str):
                try:
                    parsed = json.loads(profile.tools_technologies)
                    if isinstance(parsed, list):
                        skills.extend(parsed)
                except (json.JSONDecodeError, TypeError):
                    skills.extend([s.strip() for s in profile.tools_technologies.split(",")])

        if skills:
            # Remove duplicates while preserving order
            unique_skills = list(dict.fromkeys(skills))
            parts.append(f"Technical skills: {', '.join(unique_skills[:25])}")

        # Soft skills
        if profile.soft_skills:
            soft_skills = profile.soft_skills
            if isinstance(soft_skills, str):
                try:
                    soft_skills = json.loads(soft_skills)
                except (json.JSONDecodeError, TypeError):
                    soft_skills = [s.strip() for s in soft_skills.split(",")]

            if isinstance(soft_skills, list) and soft_skills:
                parts.append(f"Soft skills: {', '.join(soft_skills[:10])}")

        # Work preferences
        if profile.work_preference:
            parts.append(f"Work preference: {profile.work_preference}")

        # Industries
        if profile.desired_industries:
            industries = profile.desired_industries
            if isinstance(industries, str):
                try:
                    industries = json.loads(industries)
                except (json.JSONDecodeError, TypeError):
                    industries = [s.strip() for s in industries.split(",")]

            if isinstance(industries, list) and industries:
                parts.append(f"Industries: {', '.join(industries[:5])}")

        # Preferred keywords (important for matching!)
        if profile.preferred_keywords:
            keywords = profile.preferred_keywords
            if isinstance(keywords, str):
                try:
                    keywords = json.loads(keywords)
                except (json.JSONDecodeError, TypeError):
                    keywords = [s.strip() for s in keywords.split(",")]

            if isinstance(keywords, list) and keywords:
                parts.append(f"Preferred keywords: {', '.join(keywords[:10])}")

        # Experience from PROFILE (stored in profile.experience field)
        if profile.experience:
            experience_data = profile.experience
            if isinstance(experience_data, str):
                try:
                    experience_data = json.loads(experience_data)
                except (json.JSONDecodeError, TypeError):
                    experience_data = None

            if isinstance(experience_data, list) and experience_data:
                exp_summary = []
                for exp in experience_data[:3]:  # Top 3 experiences
                    if isinstance(exp, dict):
                        role = exp.get('role', '')
                        company = exp.get('company', '')
                        duration = exp.get('duration', '')
                        if role:
                            exp_text = f"{role} at {company}"
                            if duration:
                                exp_text += f" ({duration})"
                            exp_summary.append(exp_text)

                if exp_summary:
                    parts.append(f"Experience: {'; '.join(exp_summary)}")

        # Experience from CV (additional experience data)
        if cv and cv.parsed_content:
            parsed = cv.parsed_content
            if isinstance(parsed, str):
                try:
                    parsed = json.loads(parsed)
                except (json.JSONDecodeError, TypeError):
                    parsed = None

            if isinstance(parsed, dict):
                # Add CV experience (if not already from profile)
                cv_experience = parsed.get('experience', [])
                if cv_experience and isinstance(cv_experience, list):
                    cv_exp_summary = []
                    for exp in cv_experience[:3]:
                        if isinstance(exp, dict):
                            role = exp.get('role', exp.get('title', ''))
                            company = exp.get('company', '')
                            if role:
                                cv_exp_summary.append(f"{role} at {company}")

                    if cv_exp_summary:
                        parts.append(f"CV Experience: {'; '.join(cv_exp_summary)}")

                # Add CV skills (complement profile skills)
                cv_skills = parsed.get('skills', {})
                if isinstance(cv_skills, dict):
                    tech = cv_skills.get('technical', [])
                    if tech and isinstance(tech, list):
                        parts.append(f"CV Skills: {', '.join(tech[:10])}")

        # Add interest signals from saved/applied jobs
        # This helps the AI understand what kinds of jobs the user is interested in
        if interested_jobs:
            interested_titles = []
            interested_companies = []

            for job in interested_jobs[:5]:  # Limit to 5 most recent
                if job.title:
                    interested_titles.append(job.title)
                if job.company:
                    interested_companies.append(job.company)

            if interested_titles:
                parts.append(f"Interested in jobs like: {', '.join(interested_titles[:5])}")

            if interested_companies:
                unique_companies = list(dict.fromkeys(interested_companies))[:3]
                parts.append(f"Companies of interest: {', '.join(unique_companies)}")

        profile_text = ". ".join(parts)
        logger.info(f"User profile text ({len(profile_text)} chars): {profile_text[:300]}...")
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

    def _calculate_title_boost(self, job_title: str, profile: UserProfile) -> float:
        """
        Calculate boost score for jobs that match user's target job titles.

        Returns:
            float: Boost percentage (0-40)
        """
        import json
        job_title_lower = job_title.lower()

        # Get user's target job titles
        target_titles = []

        # Handle primary_job_title (may contain multiple titles separated by "|")
        if profile.primary_job_title:
            primary_titles = [t.strip().lower() for t in profile.primary_job_title.split("|")]
            target_titles.extend(primary_titles)

        # Handle secondary_job_titles (may be list or JSON string)
        if profile.secondary_job_titles:
            secondary = profile.secondary_job_titles
            if isinstance(secondary, str):
                try:
                    secondary = json.loads(secondary)
                except (json.JSONDecodeError, TypeError):
                    secondary = [secondary]

            if isinstance(secondary, list):
                target_titles.extend([t.lower() for t in secondary if isinstance(t, str)])

        if not target_titles:
            return 0.0

        # Check for exact or near-exact matches
        for target_title in target_titles:
            # Exact match (e.g., "AI Engineer" == "AI Engineer")
            if target_title == job_title_lower:
                logger.info(f"💯 EXACT title match: '{job_title}' matches '{target_title}'")
                return 40.0  # +40% boost for exact match

            # Job title contains target title (e.g., "Senior AI Engineer" contains "AI Engineer")
            if target_title in job_title_lower:
                logger.info(f"🎯 Job title contains target: '{job_title}' contains '{target_title}'")
                return 30.0  # +30% boost

            # Target title contains job title (e.g., "Machine Learning Engineer" contains "ML Engineer")
            if job_title_lower in target_title:
                logger.info(f"🎯 Target contains job title: '{target_title}' contains '{job_title}'")
                return 30.0  # +30% boost

            # Fuzzy match - check key words
            # e.g., "Machine Learning Engineer" and "ML Engineer" should match
            job_words = set(job_title_lower.split())
            target_words = set(target_title.split())
            common_words = job_words.intersection(target_words)

            # If they share important keywords (not just "engineer" or "developer")
            important_words = common_words - {'engineer', 'developer', 'senior', 'junior', 'lead', 'staff', 'principal'}
            if len(important_words) >= 2:  # At least 2 important words match
                logger.info(f"🎯 Keyword match: '{job_title}' and '{target_title}' share {important_words}")
                return 20.0  # +20% boost for keyword match

        return 0.0  # No boost

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

            # BOOST SCORE FOR EXACT TITLE MATCHES
            # If job title matches user's target job titles, give significant boost
            title_boost = self._calculate_title_boost(job.title, profile)
            if title_boost > 0:
                original_score = score
                score = min(100, score + title_boost)  # Cap at 100
                logger.info(f"🎯 Title boost: {job.title} - {original_score}% → {score}% (+{title_boost}%)")

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
        import json
        reasons = []

        if score >= 70:
            reasons.append("Excellent match - highly recommended")
        elif score >= 60:
            reasons.append("Strong match - great opportunity")
        elif score >= 50:
            reasons.append("Good match - worth applying")

        # Check for title alignment (check both primary and secondary titles)
        # Handle pipe-separated primary titles and JSON secondary titles
        user_titles = []
        if profile.primary_job_title:
            # Split by "|" for multiple titles
            user_titles.extend([t.strip().lower() for t in profile.primary_job_title.split("|")])

        if profile.secondary_job_titles:
            secondary = profile.secondary_job_titles
            if isinstance(secondary, str):
                try:
                    secondary = json.loads(secondary)
                except (json.JSONDecodeError, TypeError):
                    secondary = [secondary]
            if isinstance(secondary, list):
                user_titles.extend([t.lower() for t in secondary if isinstance(t, str)])

        job_title_lower = job.title.lower()

        for user_title in user_titles:
            # Extract key words (ignore common words)
            key_words = [w for w in user_title.split() if len(w) > 3]
            if any(word in job_title_lower for word in key_words):
                reasons.append("Title aligns with your target roles")
                break

        # Check remote/flexible preference
        if profile.work_preference in ["remote", "flexible"] and job.remote_type == "remote":
            reasons.append("Remote position matches your preference")
        elif profile.work_preference == "flexible" and job.remote_type in ["remote", "hybrid"]:
            reasons.append("Flexible work option matches your preference")

        # Check seniority
        if profile.seniority_level and profile.seniority_level.lower() in job.title.lower():
            reasons.append(f"Matches your {profile.seniority_level} level")

        return reasons[:5]  # Limit to 5 reasons

    async def match_jobs_to_cv(
        self,
        cv: Optional[CV],
        jobs: List[Job],
        user_id: str,
        db: Session,
        interested_jobs: Optional[List[Job]] = None
    ) -> List[Dict[str, Any]]:
        """
        Match jobs to a user using their CV, profile, and interest signals.

        This is the main method used by the recommendation generator.
        It combines:
        - Profile settings (job titles, skills, preferences)
        - CV data (experience, education)
        - Interest signals (jobs user has saved/applied to)

        Args:
            cv: User's CV (optional - can be None if user only has profile)
            jobs: List of jobs to match against
            user_id: User's UUID
            db: Database session
            interested_jobs: Jobs user has shown interest in (saved, applied, etc.)

        Returns:
            List of matches with job_id, match_score, and match_reason
        """
        # Get user profile (required for matching)
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

        if not profile:
            logger.warning(f"No profile found for user {user_id} - cannot generate recommendations")
            return []

        # Check if we have enough data to match
        has_profile_data = bool(
            profile.primary_job_title or
            profile.secondary_job_titles or
            profile.technical_skills
        )
        has_cv_data = bool(cv and cv.parsed_content)
        has_interest_signals = bool(interested_jobs and len(interested_jobs) > 0)

        if not has_profile_data and not has_cv_data and not has_interest_signals:
            logger.warning(f"User {user_id} has no profile, CV, or interest signals - skipping recommendations")
            return []

        # Create user profile embedding (combines profile + CV + interest signals)
        logger.info(f"Creating embedding for user {user_id} (profile: {has_profile_data}, CV: {has_cv_data}, interests: {has_interest_signals})")
        user_text = self.create_user_profile_text(profile, cv, interested_jobs)

        if not user_text.strip():
            logger.warning(f"Empty profile text for user {user_id}")
            return []

        user_embedding = self.get_embedding(user_text)

        if not user_embedding:
            logger.error(f"Failed to create user embedding for {user_id}")
            return []

        # Filter to tech jobs to save API costs
        tech_jobs = self._filter_tech_jobs(jobs)
        logger.info(f"Matching against {len(tech_jobs)} tech jobs (filtered from {len(jobs)})")

        matches = []

        for job in tech_jobs:
            try:
                # Create job embedding
                job_text = self.create_job_text(job)
                job_embedding = self.get_embedding(job_text)

                if not job_embedding:
                    continue

                # Calculate cosine similarity (0-1)
                similarity = self.cosine_similarity(user_embedding, job_embedding)

                # Convert to percentage (0-100)
                score = round(similarity * 100, 2)

                # Apply title boost for matching job titles
                title_boost = self._calculate_title_boost(job.title, profile)
                if title_boost > 0:
                    score = min(100, score + title_boost)

                # Only include matches above minimum threshold
                if score >= self.MIN_SCORE:
                    reasons = self._generate_match_reasons(score, profile, job)
                    reason_text = reasons[0] if reasons else "AI-based profile matching"

                    matches.append({
                        "job_id": str(job.id),
                        "match_score": score,
                        "match_reason": reason_text,
                        "match_reasons": reasons,
                    })

            except Exception as e:
                logger.error(f"Error matching job {job.id}: {e}")
                continue

        logger.info(f"Generated {len(matches)} matches for user {user_id}")
        return matches

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

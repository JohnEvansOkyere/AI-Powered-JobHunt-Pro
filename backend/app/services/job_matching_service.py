"""
Job Matching Service

Matches jobs to users based on CV data, profile information, and preferences.
Uses AI for intelligent matching and scoring.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime

from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.user_profile import UserProfile
from app.models.cv import CV
from app.services.ai_service import get_ai_service
from app.core.logging import get_logger

logger = get_logger(__name__)


class JobMatchingService:
    """
    Service for matching jobs to users based on multiple criteria.
    """
    
    def __init__(self):
        """Initialize job matching service."""
        self.ai_service = get_ai_service()
    
    async def match_jobs_for_user(
        self,
        user_id: str,
        db: Session,
        limit: int = 50,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Match jobs for a user based on their CV and profile.
        
        Args:
            user_id: User ID
            db: Database session
            limit: Maximum number of matches to return
            min_score: Minimum relevance score (0-100)
            
        Returns:
            List of job matches with scores and reasons
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
        
        # Get all jobs (processed or pending - we'll match against all)
        # Query jobs directly without separate count queries to avoid transaction issues
        try:
            # Try processed jobs first
            jobs = db.query(Job).filter(
                Job.processing_status == "processed"
            ).limit(limit * 2).all()
            
            # If no processed jobs, try pending
            if not jobs:
                jobs = db.query(Job).filter(
                    Job.processing_status == "pending"
                ).limit(limit * 2).all()
            
            # If still no jobs, try any non-archived jobs
            if not jobs:
                jobs = db.query(Job).filter(
                    Job.processing_status != "archived"
                ).limit(limit * 2).all()
            
            if not jobs:
                # Log counts for debugging
                all_count = db.query(Job).count()
                processed_count = db.query(Job).filter(Job.processing_status == "processed").count()
                pending_count = db.query(Job).filter(Job.processing_status == "pending").count()
                logger.warning(
                    f"No jobs available for matching. "
                    f"Total jobs: {all_count}, "
                    f"Processed: {processed_count}, "
                    f"Pending: {pending_count}"
                )
                return []
            
            logger.info(f"Found {len(jobs)} jobs to match against (statuses: {set(j.processing_status for j in jobs)})")
        except Exception as e:
            logger.error(f"Error querying jobs: {e}", exc_info=True)
            return []
        
        # Prepare user data for matching
        user_data = self._prepare_user_data(profile, cv)
        
        # Match each job
        matches = []
        for job in jobs:
            match_result = await self._match_single_job(user_data, job, profile)
            
            if match_result["relevance_score"] >= min_score:
                matches.append({
                    "job": job,
                    **match_result
                })
        
        # Sort by relevance score
        matches.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Limit results
        matches = matches[:limit]
        
        # Store matches in database
        try:
            for match in matches:
                self._store_match(user_id, match["job"].id, match, db)
            # Commit all matches at once
            db.commit()
            logger.info(f"Stored {len(matches)} job matches in database")
        except Exception as e:
            logger.error(f"Error storing matches: {e}", exc_info=True)
            db.rollback()
            # Continue even if storing fails - return matches anyway
        
        logger.info(f"Matched {len(matches)} jobs for user {user_id}")
        return matches
    
    def _prepare_user_data(
        self,
        profile: UserProfile,
        cv: Optional[CV]
    ) -> Dict[str, Any]:
        """
        Prepare user data from profile and CV for matching.
        
        Args:
            profile: User profile
            cv: Active CV (optional)
            
        Returns:
            dict: Prepared user data
        """
        user_data = {
            "primary_job_title": profile.primary_job_title,
            "secondary_job_titles": profile.secondary_job_titles or [],
            "seniority_level": profile.seniority_level,
            "work_preference": profile.work_preference,
            "technical_skills": [],
            "soft_skills": profile.soft_skills or [],
            "experience": [],
            "preferred_keywords": profile.preferred_keywords or [],
            "excluded_keywords": profile.excluded_keywords or [],
        }
        
        # Extract skills from profile
        if profile.technical_skills:
            user_data["technical_skills"] = [
                skill.get("skill") if isinstance(skill, dict) else skill
                for skill in profile.technical_skills
            ]
        
        # Extract experience from profile
        if profile.experience:
            user_data["experience"] = profile.experience
        
        # Extract data from CV if available
        if cv and cv.parsed_content:
            parsed = cv.parsed_content
            
            # Add CV skills
            if isinstance(parsed, dict):
                skills = parsed.get("skills", {})
                if isinstance(skills, dict):
                    technical = skills.get("technical", [])
                    if technical:
                        user_data["technical_skills"].extend(technical)
                    
                    # Add certifications
                    certs = skills.get("certifications", [])
                    if certs:
                        user_data["technical_skills"].extend(certs)
                
                # Add CV experience
                cv_experience = parsed.get("experience", [])
                if cv_experience and isinstance(cv_experience, list):
                    user_data["experience"].extend(cv_experience)
        
        # Remove duplicates
        user_data["technical_skills"] = list(set(user_data["technical_skills"]))
        
        return user_data
    
    async def _match_single_job(
        self,
        user_data: Dict[str, Any],
        job: Job,
        profile: UserProfile
    ) -> Dict[str, Any]:
        """
        Match a single job against user data.
        
        Args:
            user_data: Prepared user data
            job: Job to match
            profile: User profile
            
        Returns:
            dict: Match result with scores and reasons
        """
        scores = {
            "skill_match_score": 0.0,
            "experience_match_score": 0.0,
            "preference_match_score": 0.0,
        }
        reasons = []
        
        # 1. Skill Matching
        skill_score, skill_reasons = self._calculate_skill_match(
            user_data["technical_skills"],
            job.description
        )
        scores["skill_match_score"] = skill_score
        if skill_reasons:
            reasons.extend(skill_reasons)
        
        # 2. Experience Matching
        exp_score, exp_reasons = self._calculate_experience_match(
            user_data["experience"],
            user_data["primary_job_title"],
            job.title,
            job.description
        )
        scores["experience_match_score"] = exp_score
        if exp_reasons:
            reasons.extend(exp_reasons)
        
        # 3. Preference Matching
        pref_score, pref_reasons = self._calculate_preference_match(
            profile,
            job
        )
        scores["preference_match_score"] = pref_score
        if pref_reasons:
            reasons.extend(pref_reasons)
        
        # 4. Calculate overall relevance score
        # Weighted average: 40% skills, 30% experience, 30% preferences
        relevance_score = (
            scores["skill_match_score"] * 0.4 +
            scores["experience_match_score"] * 0.3 +
            scores["preference_match_score"] * 0.3
        )
        
        # Boost score if job title matches
        if user_data["primary_job_title"]:
            title_lower = user_data["primary_job_title"].lower()
            job_title_lower = job.title.lower()
            if title_lower in job_title_lower or job_title_lower in title_lower:
                relevance_score = min(100, relevance_score + 10)
                reasons.append("Job title matches your primary role")
        
        return {
            "relevance_score": round(relevance_score, 2),
            **scores,
            "match_reasons": reasons[:5]  # Top 5 reasons
        }
    
    def _calculate_skill_match(
        self,
        user_skills: List[str],
        job_description: str
    ) -> tuple:
        """
        Calculate skill match score.
        
        Args:
            user_skills: List of user skills
            job_description: Job description text
            
        Returns:
            tuple: (score, reasons)
        """
        if not user_skills:
            return 0.0, []
        
        job_desc_lower = job_description.lower()
        matched_skills = []
        
        for skill in user_skills:
            skill_lower = skill.lower()
            # Check if skill appears in job description
            if skill_lower in job_desc_lower:
                matched_skills.append(skill)
        
        if not matched_skills:
            return 0.0, []
        
        score = (len(matched_skills) / len(user_skills)) * 100
        score = min(100, score)  # Cap at 100
        
        reasons = [f"Matched {len(matched_skills)} skills: {', '.join(matched_skills[:3])}"]
        
        return round(score, 2), reasons
    
    def _calculate_experience_match(
        self,
        user_experience: List[Dict[str, Any]],
        user_job_title: Optional[str],
        job_title: str,
        job_description: str
    ) -> tuple:
        """
        Calculate experience match score.
        
        Args:
            user_experience: List of user experience items
            user_job_title: User's primary job title
            job_title: Job title
            job_description: Job description
            
        Returns:
            tuple: (score, reasons)
        """
        score = 50.0  # Base score
        reasons = []
        
        # Check job title similarity
        if user_job_title:
            user_title_lower = user_job_title.lower()
            job_title_lower = job_title.lower()
            
            # Extract key words from titles
            user_words = set(user_title_lower.split())
            job_words = set(job_title_lower.split())
            
            common_words = user_words.intersection(job_words)
            if common_words:
                score += 20
                reasons.append("Job title aligns with your experience")
        
        # Check experience relevance
        if user_experience:
            job_desc_lower = job_description.lower()
            relevant_experience = 0
            
            for exp in user_experience:
                if isinstance(exp, dict):
                    role = exp.get("role", "").lower()
                    company = exp.get("company", "").lower()
                    achievements = exp.get("achievements", [])
                    
                    # Check if role/company mentioned in job description
                    if role and role in job_desc_lower:
                        relevant_experience += 1
                    elif company and company in job_desc_lower:
                        relevant_experience += 1
                    
                    # Check achievements
                    for achievement in achievements:
                        if isinstance(achievement, str) and achievement.lower() in job_desc_lower:
                            relevant_experience += 0.5
            
            if relevant_experience > 0:
                score += min(30, relevant_experience * 10)
                reasons.append("Your experience aligns with job requirements")
        
        return round(min(100, score), 2), reasons
    
    def _calculate_preference_match(
        self,
        profile: UserProfile,
        job: Job
    ) -> tuple:
        """
        Calculate preference match score.
        
        Args:
            profile: User profile
            job: Job listing
            
        Returns:
            tuple: (score, reasons)
        """
        score = 50.0  # Base score
        reasons = []
        
        # Work preference match
        if profile.work_preference and job.remote_type:
            if profile.work_preference.lower() == job.remote_type.lower():
                score += 20
                reasons.append(f"Work type matches: {job.remote_type}")
            elif profile.work_preference == "flexible":
                score += 10
                reasons.append("Work type is flexible")
        
        # Location match (basic - can be enhanced)
        if profile.work_preference == "remote" and job.remote_type == "remote":
            score += 15
            reasons.append("Remote work preference matched")
        
        # Job type match
        if profile.contract_type and job.job_type:
            if job.job_type.lower() in [ct.lower() for ct in profile.contract_type]:
                score += 15
                reasons.append(f"Contract type matches: {job.job_type}")
        
        # Check excluded keywords
        if profile.excluded_keywords:
            job_text = f"{job.title} {job.description}".lower()
            excluded_found = [
                kw for kw in profile.excluded_keywords
                if kw.lower() in job_text
            ]
            if excluded_found:
                score -= 30  # Penalty for excluded keywords
                reasons.append(f"Contains excluded keywords: {', '.join(excluded_found[:2])}")
        
        return round(max(0, min(100, score)), 2), reasons
    
    def _store_match(
        self,
        user_id: str,
        job_id: str,
        match_result: Dict[str, Any],
        db: Session
    ) -> None:
        """
        Store or update job match in database.
        
        Args:
            user_id: User ID
            job_id: Job ID
            match_result: Match result with scores
            db: Database session
        """
        import uuid
        
        try:
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            job_uuid = job_id if isinstance(job_id, uuid.UUID) else uuid.UUID(job_id)
            
            # Check if match already exists
            existing = db.query(JobMatch).filter(
                and_(
                    JobMatch.user_id == user_uuid,
                    JobMatch.job_id == job_uuid
                )
            ).first()
            
            if existing:
                # Update existing match
                existing.relevance_score = match_result["relevance_score"]
                existing.skill_match_score = match_result.get("skill_match_score")
                existing.experience_match_score = match_result.get("experience_match_score")
                existing.preference_match_score = match_result.get("preference_match_score")
                existing.match_reasons = match_result.get("match_reasons", [])
                existing.updated_at = datetime.utcnow()
            else:
                # Create new match
                match = JobMatch(
                    user_id=user_uuid,
                    job_id=job_uuid,
                    relevance_score=match_result["relevance_score"],
                    skill_match_score=match_result.get("skill_match_score"),
                    experience_match_score=match_result.get("experience_match_score"),
                    preference_match_score=match_result.get("preference_match_score"),
                    match_reasons=match_result.get("match_reasons", []),
                    status="new"
                )
                db.add(match)
            
            # Don't commit here - let the caller handle commits
            # This allows batching multiple matches in one commit
        except Exception as e:
            logger.error(f"Error storing match for job {job_id}: {e}", exc_info=True)
            db.rollback()
            raise


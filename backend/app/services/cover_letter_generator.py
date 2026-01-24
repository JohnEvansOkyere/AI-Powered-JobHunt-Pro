"""
Cover Letter Generation Service

Generates tailored cover letters for specific job applications using AI.
"""

import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.services.ai_service import get_ai_service
from app.ai.router import get_model_router
from app.ai.base import TaskType
from app.models.cv import CV
from app.models.job import Job
from app.models.user_profile import UserProfile
from app.models.application import Application
from app.utils.sanitizer import get_sanitizer

logger = get_logger(__name__)


class CoverLetterGenerator:
    """Service for generating tailored cover letters for job applications."""
    
    def __init__(self):
        """Initialize cover letter generator."""
        self.ai_service = get_ai_service()
        self.ai_router = get_model_router()
        self.sanitizer = get_sanitizer()
    
    async def generate_cover_letter_from_custom_description(
        self,
        user_id: str,
        job_title: str,
        company_name: str,
        job_description: str,
        location: Optional[str],
        job_type: Optional[str],
        remote_type: Optional[str],
        db: Session,
        tone: str = "professional",
        length: str = "medium"
    ) -> Dict[str, Any]:
        """
        Generate a cover letter from a custom job description provided by the user.

        Args:
            user_id: User ID
            job_title: Job title provided by user
            company_name: Company name provided by user
            job_description: Job description provided by user
            location: Optional location
            job_type: Optional job type
            remote_type: Optional remote type
            db: Database session
            tone: Writing tone (professional, confident, friendly, enthusiastic)
            length: Length preference (short, medium, long)

        Returns:
            dict: Generation result with cover letter text and metadata
        """
        try:
            # Get user's active CV
            cv = db.query(CV).filter(
                CV.user_id == user_id,
                CV.is_active == True
            ).first()

            if not cv:
                raise ValueError("No active CV found. Please upload a CV first.")

            if not cv.parsed_content:
                raise ValueError("CV has not been parsed yet. Please wait for parsing to complete.")

            # Create a temporary job object
            temp_job_id = str(uuid.uuid4())
            
            # Create temporary job record for tracking purposes
            temp_job = Job(
                id=uuid.UUID(temp_job_id),
                title=job_title,
                company=company_name,
                description=job_description,
                location=location or "Not specified",
                job_type=job_type or "full-time",
                remote_type=remote_type or "unspecified",
                job_link=f"custom-job-{temp_job_id}",
                source="custom",
                salary_range=None,
                requirements=None,
                posted_date=datetime.utcnow(),
                expires_at=None,
                match_score=None
            )
            
            # Add temporary job to session
            db.add(temp_job)
            db.flush()

            # Get user profile for additional context
            profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

            logger.info(f"Generating cover letter for user {user_id} with custom job description")
            logger.info(f"Job: {job_title} at {company_name}")

            # Prepare CV data
            cv_data = cv.parsed_content
            if isinstance(cv_data, str):
                cv_data = json.loads(cv_data)

            # Generate cover letter using AI
            cover_letter_text = await self._generate_cover_letter_content(
                cv_data=cv_data,
                job=temp_job,
                profile=profile,
                tone=tone,
                length=length
            )

            # Create or update Application record with the custom job
            application = db.query(Application).filter(
                Application.user_id == user_id,
                Application.job_id == temp_job.id
            ).first()
            
            if application:
                application.cover_letter = cover_letter_text
                application.status = "draft"
                application.generation_settings = {
                    "tone": tone,
                    "length": length,
                    "custom_job": True,
                    "type": "cover_letter"
                }
                application.updated_at = datetime.utcnow()
            else:
                application = Application(
                    user_id=user_id,
                    job_id=temp_job.id,
                    cv_id=cv.id,
                    cover_letter=cover_letter_text,
                    status="draft",
                    generation_settings={
                        "tone": tone,
                        "length": length,
                        "custom_job": True,
                        "type": "cover_letter"
                    }
                )
                db.add(application)
            
            db.commit()
            db.refresh(application)
            
            logger.info(f"Successfully generated cover letter for user {user_id} with custom job description")
            
            return {
                "application_id": str(application.id),
                "cover_letter": cover_letter_text,
                "status": "completed",
                "created_at": application.created_at.isoformat() if application.created_at else None
            }
            
        except Exception as e:
            logger.error(f"Error generating custom cover letter: {e}", exc_info=True)
            db.rollback()
            raise
    
    async def _generate_cover_letter_content(
        self,
        cv_data: Dict[str, Any],
        job: Job,
        profile: Optional[UserProfile],
        tone: str,
        length: str
    ) -> str:
        """
        Generate cover letter content using AI.

        Args:
            cv_data: Original CV structured data
            job: Job listing
            profile: User profile (optional)
            tone: Writing tone
            length: Length preference (short, medium, long)

        Returns:
            str: Cover letter text
        """
        # SECURITY: Sanitize all inputs before sending to AI
        logger.info("Sanitizing CV data, job data, and profile data before AI processing")

        # Sanitize CV data
        sanitized_cv = self.sanitizer.sanitize_cv_data(cv_data)

        # Sanitize job data
        job_dict = {
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "job_type": job.job_type,
            "remote_type": job.remote_type,
            "description": job.description,
            "requirements": getattr(job, 'requirements', None),
        }
        sanitized_job = self.sanitizer.sanitize_job_data(job_dict)

        # Sanitize profile data
        profile_dict = None
        if profile:
            profile_dict = {
                "primary_job_title": profile.primary_job_title,
                "seniority_level": profile.seniority_level,
                "work_preference": profile.work_preference,
                "technical_skills": profile.technical_skills,
                "soft_skills": profile.soft_skills,
            }
        sanitized_profile = self.sanitizer.sanitize_profile_data(profile_dict)

        # Get personal info from CV
        personal_info = sanitized_cv.get("personal_info", {})
        applicant_name = personal_info.get("name", "")
        
        # Get experience highlights
        experience = sanitized_cv.get("experience", [])
        experience_summary = ""
        if experience and len(experience) > 0:
            recent_exp = experience[0]
            experience_summary = f"Currently/Previously: {recent_exp.get('title', '')} at {recent_exp.get('company', '')}"

        # Determine paragraph count based on length
        paragraph_guidance = {
            "short": "3 paragraphs (opening, 1 highlight paragraph, closing)",
            "medium": "4 paragraphs (opening, 2 highlight paragraphs, closing)",
            "long": "5 paragraphs (opening, 3 detailed highlight paragraphs, closing)"
        }
        paragraph_count = paragraph_guidance.get(length, paragraph_guidance["medium"])

        # Build comprehensive prompt with SANITIZED data
        job_requirements = f"""
Job Title: {sanitized_job.get('title', 'Not specified')}
Company: {sanitized_job.get('company', 'Not specified')}
Location: {sanitized_job.get('location', 'Not specified')}
Job Type: {sanitized_job.get('job_type', 'Not specified')}
Remote Type: {sanitized_job.get('remote_type', 'Not specified')}

Job Description:
{sanitized_job.get('description', 'Not specified')}
"""

        # Add profile context if available
        profile_context = ""
        if sanitized_profile and sanitized_profile.get('primary_job_title'):
            tech_skills = sanitized_profile.get('technical_skills', [])
            profile_context = f"""
Candidate Profile:
- Current Role Focus: {sanitized_profile.get('primary_job_title', 'Not specified')}
- Seniority Level: {sanitized_profile.get('seniority_level', 'Not specified')}
- Key Skills: {', '.join(tech_skills[:8]) if tech_skills else 'Not specified'}
"""

        # Convert sanitized CV to JSON for context
        cv_json = json.dumps(sanitized_cv, indent=2)[:1500]  # Limit size

        tone_instructions = {
            "professional": "Use a formal, professional tone. Be courteous and business-like.",
            "confident": "Use a confident, assertive tone. Show strong conviction in your abilities.",
            "friendly": "Use a warm, approachable tone while maintaining professionalism.",
            "enthusiastic": "Show genuine excitement about the opportunity. Be energetic and positive."
        }

        prompt = f"""You are an expert career advisor and professional cover letter writer. Write a compelling cover letter for this job application.

{job_requirements}

{profile_context}

Candidate Background (from CV):
Name: {applicant_name}
{experience_summary}

Key Experience & Skills (summarized):
{cv_json}

WRITING INSTRUCTIONS:

1. **Structure**: Write {paragraph_count}
   - Opening: Address hiring manager, mention the position
   - Body: Highlight 2-3 most relevant experiences/achievements that match the job
   - Closing: Express enthusiasm, call to action

2. **Tone**: {tone_instructions.get(tone, tone_instructions['professional'])}

3. **Content Guidelines**:
   - Start with a strong opening that captures attention
   - Highlight SPECIFIC achievements and metrics from the CV that match job requirements
   - Explain WHY you're interested in this specific role and company
   - Show you understand the company's needs and how you can address them
   - Use concrete examples, not generic statements
   - Demonstrate cultural fit and enthusiasm

4. **Format**:
   - Use proper business letter format
   - Include date placeholder: [Date]
   - Address to: Hiring Manager, {sanitized_job.get('company', 'Company')}
   - Sign off appropriately based on tone

5. **Critical Rules**:
   - DO NOT fabricate experience or achievements
   - DO NOT make claims not supported by the CV
   - DO be specific about relevant experience
   - DO show genuine interest in the role
   - Keep it concise and impactful

Return the complete cover letter text, properly formatted and ready to use."""

        system_prompt = """You are an expert cover letter writer who creates compelling, personalized cover letters. 
You maintain authenticity while highlighting relevant experience and showing genuine enthusiasm."""
        
        try:
            response = await self.ai_router.generate(
                task_type=TaskType.COVER_LETTER,
                prompt=prompt,
                system_prompt=system_prompt,
                user_id=None,
                max_tokens=1200,
                temperature=0.8
            )
            
            if not response:
                raise ValueError("AI model returned empty response")
            
            # Clean up response
            cover_letter = response.strip()
            
            # Remove markdown formatting if present
            if cover_letter.startswith("```"):
                lines = cover_letter.split("\n")
                cover_letter = "\n".join(lines[1:-1]) if len(lines) > 2 else cover_letter
            
            return cover_letter
            
        except Exception as e:
            logger.error(f"Error generating cover letter content: {e}")
            raise ValueError(f"Failed to generate cover letter: {str(e)}")


# Global service instance
_cover_letter_generator: Optional[CoverLetterGenerator] = None


def get_cover_letter_generator() -> CoverLetterGenerator:
    """Get or create the global cover letter generator instance."""
    global _cover_letter_generator
    if _cover_letter_generator is None:
        _cover_letter_generator = CoverLetterGenerator()
    return _cover_letter_generator

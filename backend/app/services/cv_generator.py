"""
CV Generation Service

Generates tailored CVs for specific job applications using AI.
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.supabase_client import get_supabase_service_client
from app.services.ai_service import get_ai_service
from app.ai.router import get_model_router
from app.ai.base import TaskType
from app.models.cv import CV
from app.models.job import Job
from app.models.user_profile import UserProfile
from app.models.application import Application
from app.core.config import settings

logger = get_logger(__name__)


class CVGenerator:
    """Service for generating tailored CVs for job applications."""
    
    def __init__(self):
        """Initialize CV generator."""
        self.ai_service = get_ai_service()
        self.ai_router = get_model_router()
        self.supabase = get_supabase_service_client()
    
    async def generate_tailored_cv(
        self,
        user_id: str,
        job_id: str,
        db: Session,
        tone: str = "professional",
        highlight_skills: bool = True,
        emphasize_relevant_experience: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a tailored CV for a specific job.
        
        Args:
            user_id: User ID
            job_id: Job ID to tailor CV for
            db: Database session
            tone: Writing tone (professional, confident, friendly)
            highlight_skills: Whether to highlight relevant skills
            emphasize_relevant_experience: Whether to emphasize relevant experience
            
        Returns:
            dict: Generation result with CV path and metadata
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
            
            # Get job details
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            # Get user profile for additional context
            profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            
            logger.info(f"Generating tailored CV for user {user_id}, job {job_id}")
            
            # Prepare CV data
            cv_data = cv.parsed_content
            if isinstance(cv_data, str):
                cv_data = json.loads(cv_data)
            
            # Generate tailored CV content
            tailored_content = await self._generate_cv_content(
                cv_data=cv_data,
                job=job,
                profile=profile,
                tone=tone,
                highlight_skills=highlight_skills,
                emphasize_relevant_experience=emphasize_relevant_experience
            )
            
            # Convert to formatted document (Markdown format for now)
            formatted_cv = self._format_cv_document(tailored_content, cv_data, job)
            
            # Save to Supabase Storage
            file_name = f"tailored_cv_{job_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
            storage_path = f"tailored-cvs/{user_id}/{file_name}"
            
            # Upload to Supabase Storage
            try:
                file_bytes = formatted_cv.encode('utf-8')
                
                storage_response = self.supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
                    path=storage_path,
                    file=file_bytes,
                    file_options={"content-type": "text/markdown", "upsert": "true"}
                )
                
                # Check for errors (Supabase returns UploadResponse object)
                if hasattr(storage_response, 'error') and storage_response.error:
                    raise ValueError(f"Failed to upload tailored CV: {storage_response.error}")
                elif isinstance(storage_response, dict) and storage_response.get("error"):
                    raise ValueError(f"Failed to upload tailored CV: {storage_response['error']}")
                
                logger.info(f"Tailored CV uploaded successfully to: {storage_path}")
                
            except Exception as storage_error:
                logger.error(f"Supabase Storage upload exception: {storage_error}")
                raise ValueError(f"Failed to upload tailored CV to storage: {str(storage_error)}")
            
            # Get public URL
            try:
                public_url_result = self.supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).get_public_url(storage_path)
                public_url = public_url_result if isinstance(public_url_result, str) else public_url_result.get("publicUrl", "")
            except Exception as e:
                logger.warning(f"Could not get public URL: {e}")
                public_url = ""
            
            # Create or update Application record
            application = db.query(Application).filter(
                Application.user_id == user_id,
                Application.job_id == job_id
            ).first()
            
            if application:
                application.tailored_cv_path = storage_path
                application.status = "draft"
                application.generation_settings = {
                    "tone": tone,
                    "highlight_skills": highlight_skills,
                    "emphasize_relevant_experience": emphasize_relevant_experience
                }
                application.updated_at = datetime.utcnow()
            else:
                application = Application(
                    user_id=user_id,
                    job_id=job_id,
                    cv_id=cv.id,
                    tailored_cv_path=storage_path,
                    status="draft",
                    generation_settings={
                        "tone": tone,
                        "highlight_skills": highlight_skills,
                        "emphasize_relevant_experience": emphasize_relevant_experience
                    }
                )
                db.add(application)
            
            db.commit()
            db.refresh(application)
            
            logger.info(f"Successfully generated tailored CV for user {user_id}, job {job_id}")
            
            return {
                "application_id": str(application.id),
                "cv_path": storage_path,
                "public_url": public_url,
                "status": "completed",
                "created_at": application.created_at.isoformat() if application.created_at else None
            }
            
        except Exception as e:
            logger.error(f"Error generating tailored CV: {e}", exc_info=True)
            db.rollback()
            raise
    
    async def _generate_cv_content(
        self,
        cv_data: Dict[str, Any],
        job: Job,
        profile: Optional[UserProfile],
        tone: str,
        highlight_skills: bool,
        emphasize_relevant_experience: bool
    ) -> Dict[str, Any]:
        """
        Generate tailored CV content using AI.
        
        Args:
            cv_data: Original CV structured data
            job: Job listing
            profile: User profile (optional)
            tone: Writing tone
            highlight_skills: Whether to highlight skills
            emphasize_relevant_experience: Whether to emphasize experience
            
        Returns:
            dict: Tailored CV content
        """
        # Build comprehensive prompt
        job_requirements = f"""
Job Title: {job.title}
Company: {job.company}
Location: {job.location or 'Not specified'}
Job Type: {job.job_type or 'Not specified'}
Remote Type: {job.remote_type or 'Not specified'}

Job Description:
{job.description[:3000]}
"""
        
        # Add profile context if available
        profile_context = ""
        if profile:
            profile_context = f"""
User Profile Context:
- Primary Job Title: {profile.primary_job_title or 'Not specified'}
- Seniority Level: {profile.seniority_level or 'Not specified'}
- Work Preference: {profile.work_preference or 'Not specified'}
- Technical Skills: {', '.join([s.get('skill', s) if isinstance(s, dict) else s for s in (profile.technical_skills or [])[:10]])}
- Soft Skills: {', '.join(profile.soft_skills or [])[:10]}
"""
        
        prompt = f"""You are an expert career advisor and CV writer. Tailor this CV for the specific job application.

{job_requirements}

{profile_context}

Original CV Data:
{json.dumps(cv_data, indent=2)[:4000]}

Instructions:
1. Maintain all factual information (names, dates, companies, etc.) - DO NOT fabricate anything
2. Reorder and emphasize experience that is MOST RELEVANT to this job
3. Highlight skills that match the job requirements
4. Adjust the professional summary to align with the job description
5. Use a {tone} tone throughout
6. Keep the CV concise and impactful (2 pages maximum when formatted)
7. Focus on achievements and results that relate to the job requirements

Return a JSON object with the tailored CV structure:
{{
  "summary": "Tailored professional summary (2-3 sentences)",
  "experience": [
    {{
      "title": "Job title",
      "company": "Company name",
      "location": "Location",
      "start_date": "Start date",
      "end_date": "End date",
      "description": "Tailored job description emphasizing relevant aspects",
      "achievements": ["Relevant achievement 1", "Relevant achievement 2"],
      "relevance_note": "Why this experience is relevant to the job"
    }}
  ],
  "skills": {{
    "highlighted": ["Most relevant skills for this job"],
    "technical": ["All technical skills"],
    "languages": ["Languages"],
    "certifications": ["Certifications"]
  }},
  "education": [Education entries - keep as is],
  "projects": [
    {{
      "name": "Project name",
      "description": "Tailored description emphasizing relevance",
      "technologies": ["Technologies"],
      "relevance_note": "Why this project is relevant"
    }}
  ],
  "tailoring_notes": "Brief explanation of key changes made"
}}

Return ONLY valid JSON, no markdown formatting."""
        
        system_prompt = """You are an expert CV writer who tailors resumes for specific job applications. 
You maintain accuracy while emphasizing relevant experience and skills. You never fabricate information."""
        
        try:
            response = await self.ai_router.generate(
                task_type=TaskType.CV_TAILORING,
                prompt=prompt,
                system_prompt=system_prompt,
                user_id=None,  # Will be passed from caller
                max_tokens=4000,
                temperature=0.7
            )
            
            if not response:
                raise ValueError("AI model returned empty response")
            
            # Parse JSON response
            text = response.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            
            tailored_data = json.loads(text)
            return tailored_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Response was: {response[:500]}")
            # Return original CV data if parsing fails
            return cv_data
        except Exception as e:
            logger.error(f"Error generating tailored CV content: {e}")
            # Return original CV data on error
            return cv_data
    
    def _format_cv_document(
        self,
        tailored_content: Dict[str, Any],
        original_cv_data: Dict[str, Any],
        job: Job
    ) -> str:
        """
        Format tailored CV content as a Markdown document.
        
        Args:
            tailored_content: Tailored CV content from AI
            original_cv_data: Original CV data (for personal info)
            job: Job listing
            
        Returns:
            str: Formatted CV document (Markdown)
        """
        lines = []
        
        # Header with personal info
        personal_info = original_cv_data.get("personal_info", {})
        lines.append("# " + personal_info.get("name", "Your Name"))
        lines.append("")
        if personal_info.get("email"):
            lines.append(f"Email: {personal_info['email']}")
        if personal_info.get("phone"):
            lines.append(f"Phone: {personal_info['phone']}")
        if personal_info.get("location"):
            lines.append(f"Location: {personal_info['location']}")
        if personal_info.get("linkedin"):
            lines.append(f"LinkedIn: {personal_info['linkedin']}")
        if personal_info.get("github"):
            lines.append(f"GitHub: {personal_info['github']}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Professional Summary
        if tailored_content.get("summary"):
            lines.append("## Professional Summary")
            lines.append("")
            lines.append(tailored_content["summary"])
            lines.append("")
        
        # Highlighted Skills
        if tailored_content.get("skills", {}).get("highlighted"):
            lines.append("## Key Skills")
            lines.append("")
            skills = tailored_content["skills"]["highlighted"]
            lines.append(", ".join(skills))
            lines.append("")
        
        # Experience
        if tailored_content.get("experience"):
            lines.append("## Professional Experience")
            lines.append("")
            for exp in tailored_content["experience"]:
                lines.append(f"### {exp.get('title', '')} at {exp.get('company', '')}")
                if exp.get("location"):
                    lines.append(f"*{exp.get('location')}*")
                if exp.get("start_date") or exp.get("end_date"):
                    dates = f"{exp.get('start_date', '')} - {exp.get('end_date', 'Present')}"
                    lines.append(f"*{dates}*")
                lines.append("")
                if exp.get("description"):
                    lines.append(exp["description"])
                    lines.append("")
                if exp.get("achievements"):
                    lines.append("**Key Achievements:**")
                    for achievement in exp["achievements"]:
                        lines.append(f"- {achievement}")
                    lines.append("")
                if exp.get("relevance_note"):
                    lines.append(f"*Note: {exp['relevance_note']}*")
                    lines.append("")
        
        # Education
        if tailored_content.get("education"):
            lines.append("## Education")
            lines.append("")
            for edu in tailored_content["education"]:
                lines.append(f"### {edu.get('degree', '')}")
                lines.append(f"{edu.get('institution', '')}")
                if edu.get("location"):
                    lines.append(f"*{edu.get('location')}*")
                if edu.get("graduation_date"):
                    lines.append(f"*Graduated: {edu.get('graduation_date')}*")
                if edu.get("gpa"):
                    lines.append(f"*GPA: {edu.get('gpa')}*")
                lines.append("")
        
        # Skills (Full List)
        skills_data = tailored_content.get("skills", {})
        if skills_data.get("technical"):
            lines.append("## Technical Skills")
            lines.append("")
            lines.append(", ".join(skills_data["technical"]))
            lines.append("")
        
        # Projects
        if tailored_content.get("projects"):
            lines.append("## Projects")
            lines.append("")
            for project in tailored_content["projects"]:
                lines.append(f"### {project.get('name', '')}")
                if project.get("description"):
                    lines.append(project["description"])
                if project.get("technologies"):
                    lines.append(f"**Technologies:** {', '.join(project['technologies'])}")
                if project.get("relevance_note"):
                    lines.append(f"*{project['relevance_note']}*")
                lines.append("")
        
        # Footer note
        lines.append("---")
        lines.append("")
        lines.append(f"*Tailored for: {job.title} at {job.company}*")
        lines.append(f"*Generated on: {datetime.utcnow().strftime('%B %d, %Y')}*")
        
        return "\n".join(lines)


# Global service instance
_cv_generator: Optional[CVGenerator] = None


def get_cv_generator() -> CVGenerator:
    """Get or create the global CV generator instance."""
    global _cv_generator
    if _cv_generator is None:
        _cv_generator = CVGenerator()
    return _cv_generator


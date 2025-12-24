"""
AI Service Layer

High-level service for common AI operations with built-in error handling,
cost optimization, and usage tracking.
"""

import json
from typing import Optional, Dict, Any, List
from app.ai.router import get_model_router
from app.ai.base import TaskType
from app.ai.usage_tracker import get_usage_tracker
from app.core.logging import get_logger

logger = get_logger(__name__)


class AIService:
    """
    High-level AI service for common operations.
    
    Provides:
    - Simplified API for common AI tasks
    - Automatic error handling and retries
    - Cost tracking
    - Provider fallback
    """
    
    def __init__(self):
        """Initialize AI service."""
        self.router = get_model_router()
        self.usage_tracker = get_usage_tracker()
    
    async def parse_cv(
        self,
        cv_text: str,
        user_id: Optional[str] = None,
        preferred_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse CV text and extract structured data.
        
        Args:
            cv_text: Raw CV text
            user_id: User ID for rate limiting
            preferred_provider: Preferred AI provider
            
        Returns:
            dict: Structured CV data
        """
        prompt = f"""Extract structured information from this CV/resume. Return a JSON object with the following structure:

{{
  "personal_info": {{
    "name": "Full name",
    "email": "Email address",
    "phone": "Phone number",
    "location": "City, Country",
    "linkedin": "LinkedIn URL if present",
    "github": "GitHub URL if present",
    "website": "Personal website if present"
  }},
  "summary": "Professional summary or objective",
  "experience": [
    {{
      "title": "Job title",
      "company": "Company name",
      "location": "Location",
      "start_date": "Start date",
      "end_date": "End date or 'Present'",
      "description": "Job description",
      "achievements": ["Achievement 1", "Achievement 2"]
    }}
  ],
  "education": [
    {{
      "degree": "Degree name",
      "institution": "Institution name",
      "location": "Location",
      "graduation_date": "Graduation date",
      "gpa": "GPA if mentioned"
    }}
  ],
  "skills": {{
    "technical": ["Skill 1", "Skill 2"],
    "languages": ["Language 1", "Language 2"],
    "certifications": ["Certification 1", "Certification 2"]
  }},
  "projects": [
    {{
      "name": "Project name",
      "description": "Project description",
      "technologies": ["Tech 1", "Tech 2"],
      "url": "Project URL if present"
    }}
  ]
}}

CV Text:
{cv_text[:4000]}

Return only valid JSON, no markdown formatting."""
        
        try:
            response = await self.router.generate(
                task_type=TaskType.CV_PARSING,
                prompt=prompt,
                user_id=user_id,
                preferred_provider=preferred_provider,
                max_tokens=2000,
                temperature=0.3  # Lower temperature for structured extraction
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
            
            return json.loads(text)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            # Return basic structure
            return self._get_empty_cv_structure()
        except Exception as e:
            logger.error(f"Error parsing CV with AI: {e}")
            return self._get_empty_cv_structure()
    
    def _get_empty_cv_structure(self) -> Dict[str, Any]:
        """Get empty CV structure."""
        return {
            "personal_info": {},
            "summary": "",
            "experience": [],
            "education": [],
            "skills": {"technical": [], "languages": [], "certifications": []},
            "projects": [],
        }
    
    async def tailor_cv(
        self,
        cv_data: Dict[str, Any],
        job_description: str,
        user_id: Optional[str] = None,
        preferred_provider: Optional[str] = None
    ) -> str:
        """
        Tailor CV content for a specific job.
        
        Args:
            cv_data: Structured CV data
            job_description: Job description
            user_id: User ID
            preferred_provider: Preferred provider
            
        Returns:
            str: Tailored CV content
        """
        prompt = f"""Tailor this CV for the following job description. Highlight relevant skills and experience.

Job Description:
{job_description[:2000]}

CV Data:
{str(cv_data)[:3000]}

Provide a tailored version of the CV that emphasizes relevant experience and skills."""
        
        system_prompt = "You are an expert career advisor. Tailor CVs to match job requirements while maintaining accuracy."
        
        response = await self.router.generate(
            task_type=TaskType.CV_TAILORING,
            prompt=prompt,
            system_prompt=system_prompt,
            user_id=user_id,
            preferred_provider=preferred_provider,
            max_tokens=3000,
            temperature=0.7
        )
        
        return response or ""
    
    async def generate_cover_letter(
        self,
        cv_data: Dict[str, Any],
        job_description: str,
        company_name: str,
        user_id: Optional[str] = None,
        preferred_provider: Optional[str] = None
    ) -> str:
        """
        Generate a cover letter for a job application.
        
        Args:
            cv_data: Structured CV data
            job_description: Job description
            company_name: Company name
            user_id: User ID
            preferred_provider: Preferred provider
            
        Returns:
            str: Generated cover letter
        """
        prompt = f"""Write a professional cover letter for the following position:

Company: {company_name}
Job Description:
{job_description[:2000]}

Applicant Information:
{str(cv_data.get('personal_info', {}))[:500]}

Write a compelling cover letter that:
1. Addresses the hiring manager professionally
2. Highlights relevant experience from the CV
3. Explains why the candidate is a good fit
4. Shows enthusiasm for the role
5. Is concise (3-4 paragraphs)"""
        
        system_prompt = "You are an expert career advisor. Write professional, compelling cover letters."
        
        response = await self.router.generate(
            task_type=TaskType.COVER_LETTER,
            prompt=prompt,
            system_prompt=system_prompt,
            user_id=user_id,
            preferred_provider=preferred_provider,
            max_tokens=1000,
            temperature=0.8
        )
        
        return response or ""
    
    async def match_jobs(
        self,
        cv_data: Dict[str, Any],
        job_descriptions: List[Dict[str, Any]],
        user_id: Optional[str] = None,
        preferred_provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Match CV against multiple job descriptions.
        
        Args:
            cv_data: Structured CV data
            job_descriptions: List of job descriptions with IDs
            user_id: User ID
            preferred_provider: Preferred provider
            
        Returns:
            list: Job matches with scores
        """
        # For now, return simple matches
        # TODO: Implement proper matching algorithm
        matches = []
        for job in job_descriptions:
            # Simple keyword matching (placeholder)
            score = 0.5  # Placeholder score
            matches.append({
                "job_id": job.get("id"),
                "score": score,
                "reasons": ["Basic match"]
            })
        
        return matches
    
    def get_usage_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get AI usage statistics.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            dict: Usage statistics
        """
        return self.usage_tracker.get_usage_stats(hours)
    
    def get_provider_stats(self, provider: str, hours: int = 24) -> Dict[str, Any]:
        """
        Get statistics for a specific provider.
        
        Args:
            provider: Provider name
            hours: Number of hours to look back
            
        Returns:
            dict: Provider statistics
        """
        return self.usage_tracker.get_provider_stats(provider, hours)


# Global service instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get or create the global AI service instance."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service


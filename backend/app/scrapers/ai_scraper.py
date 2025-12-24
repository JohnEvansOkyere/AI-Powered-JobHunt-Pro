"""
AI-Assisted Job Scraper

Uses AI to extract job information from web pages or unstructured data.
This can be used as a fallback or enhancement for traditional scrapers.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from app.scrapers.base import BaseScraper, JobListing
from app.ai.router import get_model_router
from app.ai.base import TaskType
from app.core.logging import get_logger

logger = get_logger(__name__)


class AIScraper(BaseScraper):
    """
    AI-assisted scraper that uses LLMs to extract job information.
    
    Useful for:
    - Extracting data from unstructured HTML
    - Parsing job descriptions
    - Normalizing job data
    - Extracting structured information
    """
    
    def __init__(self):
        """Initialize AI scraper."""
        super().__init__("ai")
        self.ai_router = get_model_router()
    
    async def extract_job_from_text(
        self,
        raw_text: str,
        source_url: Optional[str] = None
    ) -> Optional[JobListing]:
        """
        Extract job information from unstructured text using AI.
        
        Args:
            raw_text: Raw text content (HTML, plain text, etc.)
            source_url: Source URL for the job posting
            
        Returns:
            JobListing: Extracted job listing, or None if extraction fails
        """
        prompt = f"""Extract job information from the following text and return it as JSON.

Text:
{raw_text[:3000]}

Return a JSON object with the following structure:
{{
  "title": "Job title",
  "company": "Company name",
  "location": "Location (city, state, country)",
  "description": "Full job description",
  "salary_range": "Salary range if mentioned",
  "job_type": "full-time, contract, part-time, etc.",
  "remote_type": "remote, hybrid, or onsite",
  "posted_date": "Date posted if mentioned (YYYY-MM-DD format)"
}}

Return only valid JSON, no markdown formatting."""
        
        try:
            response = await self.ai_router.generate(
                task_type=TaskType.JOB_ANALYSIS,
                prompt=prompt,
                max_tokens=1000,
                temperature=0.3
            )
            
            if not response:
                return None
            
            # Parse JSON response
            import json
            text = response.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            
            data = json.loads(text)
            
            # Create JobListing
            job = JobListing(
                title=data.get("title", ""),
                company=data.get("company", ""),
                location=data.get("location"),
                description=data.get("description", ""),
                job_link=source_url or "",
                source="ai",
                salary_range=data.get("salary_range"),
                job_type=data.get("job_type"),
                remote_type=data.get("remote_type"),
            )
            
            # Parse posted date if available
            if data.get("posted_date"):
                try:
                    from datetime import datetime
                    job.posted_date = datetime.strptime(data["posted_date"], "%Y-%m-%d")
                except:
                    pass
            
            return self.normalize_job(job)
            
        except Exception as e:
            logger.error(f"AI job extraction failed: {e}")
            return None
    
    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs
    ) -> List[JobListing]:
        """
        Scrape jobs using AI.
        
        Note: This is typically used as a helper, not a primary scraper.
        It requires raw text/HTML to extract from.
        
        Args:
            keywords: Search keywords (not used directly)
            location: Location filter (not used directly)
            max_results: Maximum results
            **kwargs: Should include 'raw_data' or 'urls' to extract from
            
        Returns:
            List[JobListing]: Extracted job listings
        """
        jobs = []
        
        # If raw_data is provided, extract from it
        if "raw_data" in kwargs:
            raw_data = kwargs["raw_data"]
            if isinstance(raw_data, str):
                job = await self.extract_job_from_text(raw_data)
                if job:
                    jobs.append(job)
            elif isinstance(raw_data, list):
                for text in raw_data[:max_results]:
                    job = await self.extract_job_from_text(text)
                    if job:
                        jobs.append(job)
        
        return jobs
    
    def normalize_job(self, job: JobListing) -> JobListing:
        """
        Normalize AI-extracted job data.
        
        Args:
            job: Raw job listing
            
        Returns:
            JobListing: Normalized job listing
        """
        # Normalize title
        if not job.normalized_title:
            job.normalized_title = self.normalize_title(job.title)
        
        # Normalize location
        if job.location and not job.normalized_location:
            job.normalized_location = self.normalize_location(job.location)
        
        return job


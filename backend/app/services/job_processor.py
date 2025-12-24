"""
Job Processing Service

Processes and normalizes jobs after scraping.
Uses AI to extract additional information and improve job data quality.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.job import Job
from app.ai.router import get_model_router
from app.ai.base import TaskType
from app.core.logging import get_logger

logger = get_logger(__name__)


class JobProcessor:
    """
    Service for processing and enriching job data.
    """
    
    def __init__(self):
        """Initialize job processor."""
        self.ai_router = get_model_router()
    
    async def process_job(self, job: Job, db: Session) -> Job:
        """
        Process a single job: normalize, enrich, and extract additional data.
        
        Args:
            job: Job record to process
            db: Database session
            
        Returns:
            Job: Processed job record
        """
        try:
            # Use AI to extract additional structured data
            enriched_data = await self._enrich_with_ai(job)
            
            # Update job with enriched data
            if enriched_data.get("normalized_title") and not job.normalized_title:
                job.normalized_title = enriched_data["normalized_title"]
            
            if enriched_data.get("normalized_location") and not job.normalized_location:
                job.normalized_location = enriched_data["normalized_location"]
            
            if enriched_data.get("salary_range") and not job.salary_range:
                job.salary_range = enriched_data["salary_range"]
            
            if enriched_data.get("job_type") and not job.job_type:
                job.job_type = enriched_data["job_type"]
            
            if enriched_data.get("remote_type") and not job.remote_type:
                job.remote_type = enriched_data["remote_type"]
            
            # Mark as processed
            job.processing_status = "processed"
            job.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(job)
            
            return job
            
        except Exception as e:
            logger.error(f"Error processing job {job.id}: {e}")
            job.processing_status = "processed"  # Mark as processed even if enrichment failed
            db.commit()
            return job
    
    async def _enrich_with_ai(self, job: Job) -> Dict[str, Any]:
        """
        Use AI to extract additional structured data from job description.
        
        Args:
            job: Job record
            
        Returns:
            dict: Enriched data
        """
        prompt = f"""Extract structured information from this job posting:

Title: {job.title}
Company: {job.company}
Location: {job.location}
Description:
{job.description[:2000]}

Extract and return JSON with:
{{
  "normalized_title": "Normalized job title (remove location, remote tags, etc.)",
  "normalized_location": "Normalized location (city, state format)",
  "salary_range": "Salary range if mentioned",
  "job_type": "full-time, contract, part-time, etc.",
  "remote_type": "remote, hybrid, or onsite",
  "required_skills": ["skill1", "skill2"],
  "experience_level": "entry, mid, senior, etc."
}}

Return only valid JSON, no markdown."""
        
        try:
            response = await self.ai_router.generate(
                task_type=TaskType.JOB_ANALYSIS,
                prompt=prompt,
                max_tokens=500,
                temperature=0.3,
                optimize_cost=True  # Use cheaper provider for processing
            )
            
            if not response:
                return {}
            
            import json
            text = response.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            
            return json.loads(text)
            
        except Exception as e:
            logger.error(f"AI enrichment failed for job {job.id}: {e}")
            return {}
    
    async def process_pending_jobs(self, db: Session, limit: int = 50) -> int:
        """
        Process multiple pending jobs in batch.
        
        Args:
            db: Database session
            limit: Maximum number of jobs to process
            
        Returns:
            int: Number of jobs processed
        """
        pending_jobs = db.query(Job).filter(
            Job.processing_status == "pending"
        ).limit(limit).all()
        
        processed_count = 0
        for job in pending_jobs:
            try:
                await self.process_job(job, db)
                processed_count += 1
            except Exception as e:
                logger.error(f"Error processing job {job.id}: {e}")
                continue
        
        return processed_count


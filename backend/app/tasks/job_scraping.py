"""
Job Scraping Background Tasks

Celery tasks for scraping jobs from various job boards.
"""

import asyncio
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

try:
    from app.tasks.celery_app import celery_app
except ImportError:
    # Celery not installed, create a mock for development
    class MockTask:
        def __init__(self, func):
            self.func = func
        def __call__(self, *args, **kwargs):
            return self.func(*args, **kwargs)
        def delay(self, *args, **kwargs):
            # In development without Celery, run synchronously
            return self.func(*args, **kwargs)
    
    class MockCelery:
        def task(self, *args, **kwargs):
            def decorator(func):
                return MockTask(func)
            return decorator
    celery_app = MockCelery()
from app.core.logging import get_logger
from app.core.database import SessionLocal
from app.services.job_scraper_service import JobScraperService
from app.models.scraping_job import ScrapingJob

logger = get_logger(__name__)


@celery_app.task(name="scrape_jobs", bind=True, max_retries=3)
def scrape_jobs_task(
    self,
    scraping_job_id: str,
    sources: List[str],
    keywords: Optional[List[str]] = None,
    location: Optional[str] = None,
    max_results_per_source: int = 50
):
    """
    Background task to scrape jobs from specified sources.
    
    Args:
        scraping_job_id: ID of the scraping_job record
        sources: List of job board sources to scrape
        keywords: Optional keywords to filter jobs
        location: Optional location filter
        max_results_per_source: Maximum results per source
        
    Returns:
        dict: Summary of scraping results
    """
    logger.info(f"Starting job scraping task {scraping_job_id} for sources: {sources}")
    
    # Default to remotive if no sources provided
    if not sources:
        sources = ["remotive"]

    db: Session = SessionLocal()
    scraper_service = JobScraperService()
    
    try:
        # Run async scraping
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            scraper_service.scrape_jobs(
                sources=sources,
                keywords=keywords,
                location=location,
                max_results_per_source=max_results_per_source,
                db=db,
                scraping_job_id=scraping_job_id
            )
        )
        
        loop.close()
        
        logger.info(f"Job scraping task {scraping_job_id} completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Job scraping task {scraping_job_id} failed: {e}", exc_info=True)
        
        # Update scraping job status
        try:
            scraping_job = db.query(ScrapingJob).filter(ScrapingJob.id == scraping_job_id).first()
            if scraping_job:
                scraping_job.status = "failed"
                scraping_job.error_message = str(e)
                from datetime import datetime
                scraping_job.completed_at = datetime.utcnow()
                db.commit()
        except Exception as db_error:
            logger.error(f"Error updating scraping job status: {db_error}")
        
        # Retry if not exceeded max retries
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
        raise
    
    finally:
        db.close()


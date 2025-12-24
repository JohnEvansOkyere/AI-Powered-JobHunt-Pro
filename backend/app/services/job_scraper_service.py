"""
Job Scraping Service

Orchestrates job scraping from multiple sources, handles normalization,
deduplication, and storage.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.scrapers.base import BaseScraper, JobListing
from app.scrapers.linkedin_scraper import LinkedInScraper
from app.scrapers.indeed_scraper import IndeedScraper
from app.scrapers.ai_scraper import AIScraper
from app.scrapers.serpapi_scraper import SerpAPIScraper
from app.models.job import Job
from app.models.scraping_job import ScrapingJob
from app.core.logging import get_logger
from app.core.config import settings
# Database session will be passed as parameter

logger = get_logger(__name__)


class JobScraperService:
    """
    Service for scraping and managing jobs from multiple sources.
    """
    
    def __init__(self):
        """Initialize job scraper service."""
        self.scrapers: Dict[str, BaseScraper] = {
            "linkedin": LinkedInScraper(),
            "indeed": IndeedScraper(),
            "ai": AIScraper(),
            "remotive": None,  # Lazy init below
            "serpapi": None,   # Lazy init below
        }
        # Lazy-load Remotive to avoid import issues if requests missing
        try:
            from app.scrapers.remotive_scraper import RemotiveScraper
            self.scrapers["remotive"] = RemotiveScraper()
        except Exception as e:
            logger.warning(f"Remotive scraper unavailable: {e}")

        # SerpAPI scraper (Google Jobs)
        try:
            serpapi_key = settings.SERPAPI_API_KEY
            if serpapi_key:
                self.scrapers["serpapi"] = SerpAPIScraper(api_key=serpapi_key)
                logger.info("SerpAPI scraper initialized.")
            else:
                logger.warning("SERPAPI_API_KEY not set; SerpAPI scraper disabled.")
        except Exception as e:
            logger.warning(f"SerpAPI scraper unavailable: {e}")
    
    def get_scraper(self, source: str) -> Optional[BaseScraper]:
        """
        Get scraper for a source.
        
        Args:
            source: Source name (linkedin, indeed, ai, etc.)
            
        Returns:
            BaseScraper: Scraper instance, or None if not found
        """
        return self.scrapers.get(source.lower())
    
    async def scrape_jobs(
        self,
        sources: List[str],
        keywords: Optional[List[str]] = None,
        location: Optional[str] = None,
        max_results_per_source: int = 50,
        db: Optional[Session] = None,
        scraping_job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scrape jobs from multiple sources.
        
        Args:
            sources: List of source names to scrape
            keywords: Search keywords
            location: Location filter
            max_results_per_source: Maximum results per source
            db: Database session
            scraping_job_id: ID of the scraping job record (for progress tracking)
            
        Returns:
            dict: Summary of scraping results
        """
        keywords = keywords or []
        all_jobs: List[JobListing] = []
        
        # Update scraping job status if provided
        scraping_job = None
        if scraping_job_id and db:
            scraping_job = db.query(ScrapingJob).filter(ScrapingJob.id == scraping_job_id).first()
            if scraping_job:
                scraping_job.status = "running"
                scraping_job.started_at = datetime.utcnow()
                db.commit()
        
        total_sources = len(sources)
        for idx, source in enumerate(sources):
            try:
                scraper = self.get_scraper(source)
                if not scraper:
                    logger.warning(f"Scraper not found for source: {source}")
                    continue
                
                logger.info(f"Scraping {source}... ({idx + 1}/{total_sources})")
                
                # Scrape jobs
                jobs = await scraper.scrape(
                    keywords=keywords,
                    location=location,
                    max_results=max_results_per_source
                )
                
                # Normalize jobs
                normalized_jobs = [scraper.normalize_job(job) for job in jobs]
                all_jobs.extend(normalized_jobs)
                
                logger.info(f"Scraped {len(jobs)} jobs from {source}")
                
                # Update progress
                if scraping_job:
                    progress = int(((idx + 1) / total_sources) * 90)  # 90% for scraping, 10% for processing
                    scraping_job.progress = progress
                    scraping_job.jobs_found = len(all_jobs)
                    db.commit()
                
            except Exception as e:
                logger.error(f"Error scraping {source}: {e}", exc_info=True)
                continue
        
        # Deduplicate and store jobs
        if db:
            stored_count = await self._store_jobs(all_jobs, db, scraping_job)
        else:
            stored_count = 0
        
        # Update scraping job completion
        if scraping_job and db:
            scraping_job.status = "completed"
            scraping_job.progress = 100
            scraping_job.jobs_processed = stored_count
            scraping_job.completed_at = datetime.utcnow()
            scraping_job.result_summary = {
                "total_found": len(all_jobs),
                "stored": stored_count,
                "duplicates": len(all_jobs) - stored_count,
                "sources": sources
            }
            db.commit()
        
        return {
            "total_found": len(all_jobs),
            "stored": stored_count,
            "duplicates": len(all_jobs) - stored_count,
            "sources": sources
        }
    
    def _is_duplicate(self, job: JobListing, db: Session) -> bool:
        """
        Check if a job is a duplicate.
        
        Args:
            job: Job listing to check
            db: Database session
            
        Returns:
            bool: True if duplicate exists
        """
        # Check by job_link (most reliable)
        existing = db.query(Job).filter(Job.job_link == job.job_link).first()
        if existing:
            return True
        
        # Check by title + company + location (fuzzy match)
        # Within last 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        existing = db.query(Job).filter(
            and_(
                Job.title.ilike(f"%{job.title[:50]}%"),
                Job.company.ilike(f"%{job.company}%"),
                Job.posted_date >= cutoff_date
            )
        ).first()
        
        return existing is not None
    
    async def _store_jobs(
        self,
        jobs: List[JobListing],
        db: Session,
        scraping_job: Optional[ScrapingJob] = None
    ) -> int:
        """
        Store jobs in database, skipping duplicates.
        
        Args:
            jobs: List of job listings
            db: Database session
            scraping_job: Scraping job record (for progress tracking)
            
        Returns:
            int: Number of jobs stored
        """
        stored_count = 0
        
        for idx, job_listing in enumerate(jobs):
            try:
                # Check for duplicates
                if self._is_duplicate(job_listing, db):
                    continue
                
                # Create Job record
                job = Job(
                    title=job_listing.title,
                    company=job_listing.company,
                    location=job_listing.location,
                    description=job_listing.description,
                    job_link=job_listing.job_link,
                    source=job_listing.source,
                    source_id=job_listing.source_id,
                    posted_date=job_listing.posted_date,
                    normalized_title=job_listing.normalized_title or job_listing.title,
                    normalized_location=job_listing.normalized_location or job_listing.location,
                    salary_range=job_listing.salary_range,
                    job_type=job_listing.job_type,
                    remote_type=job_listing.remote_type,
                    processing_status="pending"
                )
                
                db.add(job)
                stored_count += 1
                
                # Commit in batches for performance
                if stored_count % 10 == 0:
                    db.commit()
                    if scraping_job:
                        scraping_job.jobs_processed = stored_count
                        db.commit()
                
            except Exception as e:
                logger.error(f"Error storing job: {e}", exc_info=True)
                db.rollback()
                continue
        
        # Final commit
        db.commit()
        
        return stored_count
    
    def get_available_sources(self) -> List[str]:
        """
        Get list of available scraping sources.
        
        Returns:
            List[str]: List of source names
        """
        return list(self.scrapers.keys())


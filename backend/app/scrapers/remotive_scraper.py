"""
Remotive Job Scraper

Scrapes public remote jobs from the Remotive API (no API key required).
Docs: https://remotive.io/api/remote-jobs
"""

from typing import List, Optional
from datetime import datetime
import requests

from app.scrapers.base import BaseScraper, JobListing
from app.core.logging import get_logger

logger = get_logger(__name__)


class RemotiveScraper(BaseScraper):
    """Remotive job scraper using their public API."""

    BASE_URL = "https://remotive.io/api/remote-jobs"

    def __init__(self):
        """Initialize Remotive scraper."""
        super().__init__("remotive")

    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs
    ) -> List[JobListing]:
        """
        Scrape jobs from Remotive public API.

        Args:
            keywords: Search keywords
            location: Location filter (ignored; Remotive is remote-first)
            max_results: Maximum number of results

        Returns:
            List[JobListing]: Scraped job listings
        """
        query = " ".join(keywords) if keywords else ""
        params = {"search": query} if query else {}

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            jobs = data.get("jobs", [])[:max_results]

            listings: List[JobListing] = []
            for job in jobs:
                listing = JobListing(
                    title=job.get("title") or "Untitled",
                    company=job.get("company_name") or "Unknown",
                    location=job.get("candidate_required_location") or "Remote",
                    description=job.get("description") or "",
                    job_link=job.get("url") or job.get("slug") or "",
                    source="remotive",
                    source_id=str(job.get("id")),
                    posted_date=self._parse_date(job.get("publication_date")),
                    salary_range=job.get("salary") or None,
                    job_type=job.get("job_type") or None,
                    remote_type="remote",
                )
                listings.append(self.normalize_job(listing))

            logger.info(f"Remotive: fetched {len(listings)} jobs for query='{query}'")
            return listings
        except Exception as e:
            logger.error(f"Remotive scraping failed: {e}", exc_info=True)
            return []

    def _parse_date(self, dt_str: Optional[str]) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except Exception:
            return None

    def normalize_job(self, job: JobListing) -> JobListing:
        """Normalize Remotive job data."""
        if not job.normalized_title:
            job.normalized_title = self.normalize_title(job.title)

        if job.location and not job.normalized_location:
            job.normalized_location = self.normalize_location(job.location)

        if job.description:
            if not job.salary_range:
                job.salary_range = self.extract_salary(job.description) or job.salary_range
            if not job.job_type:
                job.job_type = self.extract_job_type(job.description)
            if not job.remote_type:
                job.remote_type = self.extract_remote_type(job.description) or "remote"

        return job


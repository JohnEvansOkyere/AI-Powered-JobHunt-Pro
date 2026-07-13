"""
Working Nomads Job Scraper

Scrapes remote jobs from the Working Nomads public API (free, no API key needed).
Returns the latest ~30 published jobs across tech and non-tech categories.
API: https://www.workingnomads.com/api/exposed_jobs/
"""

from typing import List, Optional
from datetime import datetime, timezone
import httpx

from app.scrapers.base import BaseScraper, JobListing
from app.core.logging import get_logger

logger = get_logger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


class WorkingNomadsScraper(BaseScraper):
    """Working Nomads scraper using their public JSON API."""

    BASE_URL = "https://www.workingnomads.com/api/exposed_jobs/"

    def __init__(self):
        super().__init__("workingnomads")

    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs
    ) -> List[JobListing]:
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=HEADERS, follow_redirects=True) as client:
                resp = await client.get(self.BASE_URL)
                resp.raise_for_status()
                jobs = resp.json()

            if keywords:
                keywords_lower = [kw.lower() for kw in keywords]
                filtered = []
                for job in jobs:
                    text = f"{job.get('title', '')} {job.get('category_name', '')} {job.get('tags', '')}".lower()
                    if any(kw in text for kw in keywords_lower):
                        filtered.append(job)
                jobs = filtered or jobs

            listings: List[JobListing] = []
            for job in jobs[:max_results]:
                listing = JobListing(
                    title=job.get("title") or "Untitled",
                    company=job.get("company_name") or "Unknown",
                    location=job.get("location") or "Remote",
                    description=job.get("description") or "",
                    job_link=job.get("url") or "",
                    source="workingnomads",
                    source_id=job.get("url"),
                    posted_date=self._parse_date(job.get("pub_date")),
                    salary_range=None,
                    job_type=None,
                    remote_type="remote",
                )
                listings.append(self.normalize_job(listing))

            logger.info(f"WorkingNomads: fetched {len(listings)} jobs")
            return listings
        except Exception as e:
            logger.error(f"WorkingNomads scraping failed: {e}", exc_info=True)
            return []

    def _parse_date(self, dt_str: Optional[str]) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            dt = datetime.fromisoformat(str(dt_str))
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except Exception:
            return None

    def normalize_job(self, job: JobListing) -> JobListing:
        if not job.normalized_title:
            job.normalized_title = self.normalize_title(job.title)
        if job.location and not job.normalized_location:
            job.normalized_location = self.normalize_location(job.location)
        job.remote_type = "remote"
        return job

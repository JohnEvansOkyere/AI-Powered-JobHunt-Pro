"""
Himalayas Job Scraper

Scrapes remote jobs from the Himalayas public API (free, no API key needed).
API Docs: https://himalayas.app/api
"""

from typing import List, Optional
from datetime import datetime
import httpx

from app.scrapers.base import BaseScraper, JobListing
from app.core.logging import get_logger

logger = get_logger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


class HimalayasScraper(BaseScraper):
    """Himalayas remote jobs scraper using their public JSON API."""

    BASE_URL = "https://himalayas.app/jobs/api"

    def __init__(self):
        super().__init__("himalayas")

    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs
    ) -> List[JobListing]:
        params = {"limit": min(max_results, 100)}
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=HEADERS, follow_redirects=True) as client:
                resp = await client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                jobs = resp.json().get("jobs", [])

            if keywords:
                keywords_lower = [kw.lower() for kw in keywords]
                filtered = []
                for job in jobs:
                    cats = " ".join(job.get("categories") or []) + " " + " ".join(job.get("parentCategories") or [])
                    text = f"{job.get('title', '')} {cats} {job.get('excerpt', '')}".lower()
                    if any(kw in text for kw in keywords_lower):
                        filtered.append(job)
                jobs = filtered or jobs

            listings: List[JobListing] = []
            for job in jobs[:max_results]:
                locations = job.get("locationRestrictions") or []
                listing = JobListing(
                    title=job.get("title") or "Untitled",
                    company=job.get("companyName") or "Unknown",
                    location=", ".join(locations) if locations else "Remote",
                    description=job.get("description") or job.get("excerpt") or "",
                    job_link=job.get("applicationLink") or job.get("guid") or "",
                    source="himalayas",
                    source_id=str(job.get("guid") or job.get("applicationLink")),
                    posted_date=self._parse_epoch(job.get("pubDate")),
                    salary_range=self._format_salary(job),
                    job_type=job.get("employmentType"),
                    remote_type="remote",
                )
                listings.append(self.normalize_job(listing))

            logger.info(f"Himalayas: fetched {len(listings)} jobs")
            return listings
        except Exception as e:
            logger.error(f"Himalayas scraping failed: {e}", exc_info=True)
            return []

    def _parse_epoch(self, value) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.utcfromtimestamp(int(value))
        except Exception:
            return None

    def _format_salary(self, job: dict) -> Optional[str]:
        smin, smax = job.get("minSalary"), job.get("maxSalary")
        if smin and smax:
            currency = job.get("currency") or "USD"
            return f"{currency} {int(smin):,} - {int(smax):,}"
        return None

    def normalize_job(self, job: JobListing) -> JobListing:
        if not job.normalized_title:
            job.normalized_title = self.normalize_title(job.title)
        if job.location and not job.normalized_location:
            job.normalized_location = self.normalize_location(job.location)
        job.remote_type = "remote"
        return job

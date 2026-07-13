"""
Jobicy Job Scraper

Scrapes remote jobs from the Jobicy public API (free, no API key needed).
Covers tech and non-tech roles (support, marketing, HR, finance, etc.).
API Docs: https://jobicy.com/jobs-rss-feed
"""

from typing import List, Optional
from datetime import datetime, timezone
import httpx

from app.scrapers.base import BaseScraper, JobListing
from app.core.logging import get_logger

logger = get_logger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


class JobicyScraper(BaseScraper):
    """Jobicy remote jobs scraper using their public JSON API."""

    BASE_URL = "https://jobicy.com/api/v2/remote-jobs"

    def __init__(self):
        super().__init__("jobicy")

    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs
    ) -> List[JobListing]:
        params = {"count": min(max_results, 100)}
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=HEADERS, follow_redirects=True) as client:
                resp = await client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                jobs = resp.json().get("jobs", [])

            if keywords:
                keywords_lower = [kw.lower() for kw in keywords]
                filtered = []
                for job in jobs:
                    text = f"{job.get('jobTitle', '')} {job.get('jobIndustry', '')} {job.get('jobExcerpt', '')}".lower()
                    if any(kw in text for kw in keywords_lower):
                        filtered.append(job)
                jobs = filtered or jobs

            listings: List[JobListing] = []
            for job in jobs[:max_results]:
                listing = JobListing(
                    title=job.get("jobTitle") or "Untitled",
                    company=job.get("companyName") or "Unknown",
                    location=job.get("jobGeo") or "Remote",
                    description=job.get("jobDescription") or job.get("jobExcerpt") or "",
                    job_link=job.get("url") or "",
                    source="jobicy",
                    source_id=str(job.get("id")),
                    posted_date=self._parse_date(job.get("pubDate")),
                    salary_range=self._format_salary(job),
                    job_type=(job.get("jobType") or [None])[0] if isinstance(job.get("jobType"), list) else job.get("jobType"),
                    remote_type="remote",
                )
                listings.append(self.normalize_job(listing))

            logger.info(f"Jobicy: fetched {len(listings)} jobs")
            return listings
        except Exception as e:
            logger.error(f"Jobicy scraping failed: {e}", exc_info=True)
            return []

    def _parse_date(self, dt_str: Optional[str]) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            dt = datetime.fromisoformat(str(dt_str).replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except Exception:
            return None

    def _format_salary(self, job: dict) -> Optional[str]:
        smin, smax = job.get("salaryMin"), job.get("salaryMax")
        if smin and smax:
            currency = job.get("salaryCurrency") or "USD"
            return f"{currency} {int(smin):,} - {int(smax):,}"
        return None

    def normalize_job(self, job: JobListing) -> JobListing:
        if not job.normalized_title:
            job.normalized_title = self.normalize_title(job.title)
        if job.location and not job.normalized_location:
            job.normalized_location = self.normalize_location(job.location)
        job.remote_type = "remote"
        return job

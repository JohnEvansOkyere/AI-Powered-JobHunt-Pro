"""
SerpAPI Google Jobs Scraper

Uses SerpAPI's google_jobs engine to fetch listings.
Docs: https://serpapi.com/google-jobs-results
"""

from typing import List, Optional
from datetime import datetime
import requests

from app.scrapers.base import BaseScraper, JobListing
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class SerpAPIScraper(BaseScraper):
    """Scraper that pulls Google Jobs results via SerpAPI."""

    BASE_URL = "https://serpapi.com/search"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__("serpapi")
        self.api_key = api_key or settings.SERPAPI_API_KEY

    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs,
    ) -> List[JobListing]:
        if not self.api_key:
            logger.warning("SerpAPI API key not configured; skipping SerpAPI scraping.")
            return []

        # Limit keywords to first 3 to avoid query too long errors (400 Bad Request)
        # SerpAPI/Google Jobs works best with focused queries
        query_keywords = keywords[:3] if keywords else []
        query = " ".join(query_keywords) if query_keywords else "software engineer"

        # Handle location - "Worldwide" is not valid for Google Jobs
        # Use a default location or omit for worldwide searches
        search_location = location
        if not location or location.lower() in ["worldwide", "remote", "anywhere"]:
            search_location = "United States"  # Default to US for broad searches

        params = {
            "engine": "google_jobs",
            "q": query,
            "api_key": self.api_key,
            "location": search_location,
            "hl": "en",
        }

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            jobs = data.get("jobs_results", [])[:max_results]

            listings: List[JobListing] = []
            for job in jobs:
                listing = JobListing(
                    title=job.get("title") or "Untitled",
                    company=(job.get("company_name") or job.get("via") or "Unknown"),
                    location=job.get("location") or location,
                    description=job.get("description") or "",
                    job_link=self._extract_link(job),
                    source="serpapi",
                    source_id=job.get("job_id") or job.get("id"),
                    posted_date=self._parse_date(job.get("detected_extensions", {})),
                    salary_range=self._extract_salary(job),
                    job_type=self._extract_schedule(job),
                    remote_type=self._extract_remote(job),
                )
                listings.append(self.normalize_job(listing))

            logger.info(f"SerpAPI: fetched {len(listings)} jobs for query='{query}' location='{params['location']}'")
            return listings
        except Exception as e:
            logger.error(f"SerpAPI scraping failed: {e}", exc_info=True)
            return []

    def _extract_link(self, job: dict) -> str:
        # Prefer the Google job link; fall back to the first apply option
        if job.get("share_link"):
            return job["share_link"]
        apply_options = job.get("apply_options") or []
        if apply_options and apply_options[0].get("link"):
            return apply_options[0]["link"]
        return job.get("apply_link") or ""

    def _parse_date(self, detected_extensions: dict) -> Optional[datetime]:
        # detected_extensions may contain "posted_at" like "3 days ago"
        posted_at = detected_extensions.get("posted_at") if isinstance(detected_extensions, dict) else None
        if not posted_at:
            return None
        try:
            # Convert relative times conservatively to a datetime
            # e.g., "3 days ago", "15 hours ago"
            now = datetime.utcnow()
            parts = posted_at.split()
            if len(parts) >= 2 and parts[0].isdigit():
                num = int(parts[0])
                unit = parts[1]
                from datetime import timedelta
                if "day" in unit:
                    return now - timedelta(days=num)
                if "hour" in unit:
                    return now - timedelta(hours=num)
                if "week" in unit:
                    return now - timedelta(weeks=num)
            return now
        except Exception:
            return None

    def _extract_salary(self, job: dict) -> Optional[str]:
        detected_extensions = job.get("detected_extensions") or {}
        return detected_extensions.get("salary")

    def _extract_schedule(self, job: dict) -> Optional[str]:
        detected_extensions = job.get("detected_extensions") or {}
        return detected_extensions.get("schedule_type")

    def _extract_remote(self, job: dict) -> Optional[str]:
        detected_extensions = job.get("detected_extensions") or {}
        remote = detected_extensions.get("work_from_home") or detected_extensions.get("remote")
        if remote:
            return "remote"
        return None

    def normalize_job(self, job: JobListing) -> JobListing:
        if not job.normalized_title:
            job.normalized_title = self.normalize_title(job.title)

        if job.location and not job.normalized_location:
            job.normalized_location = self.normalize_location(job.location)

        if job.description:
            if not job.salary_range:
                job.salary_range = self.extract_salary(job.description) or job.salary_range
            if not job.job_type:
                job.job_type = self.extract_job_type(job.description) or job.job_type
            if not job.remote_type:
                job.remote_type = self.extract_remote_type(job.description) or job.remote_type

        return job


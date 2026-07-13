"""
The Muse Job Scraper

Scrapes jobs from The Muse public API (free, no API key needed).
Strong non-tech coverage: customer service, marketing, sales, HR, healthcare, etc.
API Docs: https://www.themuse.com/developers/api/v2
"""

from typing import List, Optional
from datetime import datetime, timezone
import httpx

from app.scrapers.base import BaseScraper, JobListing
from app.core.logging import get_logger

logger = get_logger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


class TheMuseScraper(BaseScraper):
    """The Muse jobs scraper using their public JSON API."""

    BASE_URL = "https://www.themuse.com/api/public/jobs"
    PAGES = 4  # 20 jobs per page

    def __init__(self):
        super().__init__("themuse")

    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs
    ) -> List[JobListing]:
        jobs: List[dict] = []
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=HEADERS, follow_redirects=True) as client:
                for page in range(1, self.PAGES + 1):
                    resp = await client.get(self.BASE_URL, params={"page": page, "descending": "true"})
                    if resp.status_code != 200:
                        break
                    results = resp.json().get("results", [])
                    if not results:
                        break
                    jobs.extend(results)
                    if len(jobs) >= max_results * 2:
                        break

            if keywords:
                keywords_lower = [kw.lower() for kw in keywords]
                filtered = []
                for job in jobs:
                    cats = " ".join(c.get("name", "") for c in job.get("categories") or [])
                    text = f"{job.get('name', '')} {cats}".lower()
                    if any(kw in text for kw in keywords_lower):
                        filtered.append(job)
                jobs = filtered or jobs

            listings: List[JobListing] = []
            for job in jobs[:max_results]:
                company = (job.get("company") or {}).get("name") or "Unknown"
                locations = [l.get("name", "") for l in job.get("locations") or []]
                landing = (job.get("refs") or {}).get("landing_page") or ""
                remote = any("flexible" in l.lower() or "remote" in l.lower() for l in locations)
                listing = JobListing(
                    title=job.get("name") or "Untitled",
                    company=company,
                    location=", ".join(locations) or None,
                    description=self._strip_html(job.get("contents") or ""),
                    job_link=landing,
                    source="themuse",
                    source_id=str(job.get("id")),
                    posted_date=self._parse_date(job.get("publication_date")),
                    salary_range=None,
                    job_type=None,
                    remote_type="remote" if remote else None,
                )
                listings.append(self.normalize_job(listing))

            logger.info(f"TheMuse: fetched {len(listings)} jobs")
            return listings
        except Exception as e:
            logger.error(f"TheMuse scraping failed: {e}", exc_info=True)
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

    def _strip_html(self, html: str) -> str:
        import re
        clean = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", clean).strip()

    def normalize_job(self, job: JobListing) -> JobListing:
        if not job.normalized_title:
            job.normalized_title = self.normalize_title(job.title)
        if job.location and not job.normalized_location:
            job.normalized_location = self.normalize_location(job.location)
        if job.description and not job.remote_type:
            job.remote_type = self.extract_remote_type(job.description)
        return job

"""
Arbeitnow Job Scraper

Scrapes remote jobs from Arbeitnow API - completely free, no API key required.
Focuses on remote and tech jobs.

Docs: https://arbeitnow.com/api
API: https://arbeitnow.com/api/job-board-api (FREE, no key needed)
"""

from typing import List, Optional
from datetime import datetime
import httpx

from app.scrapers.base import BaseScraper, JobListing
from app.core.logging import get_logger

logger = get_logger(__name__)


class ArbeitnowScraper(BaseScraper):
    """
    Arbeitnow job scraper using their free public API.

    No API key required! Great source for remote tech jobs.
    """

    BASE_URL = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(self):
        """Initialize Arbeitnow scraper."""
        super().__init__("arbeitnow")

    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs
    ) -> List[JobListing]:
        """
        Scrape jobs from Arbeitnow API.

        Args:
            keywords: Search keywords (used for filtering results)
            location: Location filter (optional)
            max_results: Maximum number of results

        Returns:
            List[JobListing]: Scraped job listings
        """
        # Only use first 5 keywords for filtering to avoid over-filtering
        query_terms = set(kw.lower() for kw in keywords[:5]) if keywords else set()

        listings: List[JobListing] = []

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                page = 1
                max_pages = 5

                while len(listings) < max_results and page <= max_pages:
                    url = f"{self.BASE_URL}?page={page}"
                    resp = await client.get(url)
                    resp.raise_for_status()
                    data = resp.json()

                    jobs = data.get("data", [])

                    if not jobs:
                        break

                    for job in jobs:
                        if len(listings) >= max_results:
                            break

                        # Filter by keywords if provided
                        if query_terms:
                            job_text = f"{job.get('title', '')} {job.get('description', '')} {', '.join(job.get('tags', []))}".lower()
                            if not any(term in job_text for term in query_terms):
                                continue

                        listing = JobListing(
                            title=job.get("title") or "Untitled",
                            company=job.get("company_name") or "Unknown",
                            location=job.get("location") or "Remote",
                            description=job.get("description") or "",
                            job_link=job.get("url") or "",
                            source="arbeitnow",
                            source_id=job.get("slug") or str(job.get("url", ""))[:100],
                            posted_date=self._parse_date(job.get("created_at")),
                            salary_range=None,  # Arbeitnow doesn't provide salary
                            job_type=self._extract_job_type(job.get("job_types", [])),
                            remote_type=self._detect_remote(job),
                        )
                        listings.append(self.normalize_job(listing))

                    # Check if there are more pages
                    links = data.get("links", {})
                    if not links.get("next"):
                        break

                    page += 1

            logger.info(f"Arbeitnow: fetched {len(listings)} jobs")
            return listings

        except httpx.HTTPStatusError as e:
            logger.error(f"Arbeitnow API HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Arbeitnow scraping failed: {e}", exc_info=True)
            return []

    def _parse_date(self, timestamp: Optional[int]) -> Optional[datetime]:
        """Parse Arbeitnow timestamp (Unix timestamp)."""
        if not timestamp:
            return None
        try:
            return datetime.utcfromtimestamp(timestamp)
        except Exception:
            return None

    def _extract_job_type(self, job_types: List[str]) -> Optional[str]:
        """Extract standardized job type from list."""
        if not job_types:
            return None

        # Arbeitnow returns types like ["Full-Time", "Remote"]
        for jt in job_types:
            jt_lower = jt.lower()
            if "full" in jt_lower:
                return "full-time"
            elif "part" in jt_lower:
                return "part-time"
            elif "contract" in jt_lower:
                return "contract"
            elif "freelance" in jt_lower:
                return "freelance"
            elif "intern" in jt_lower:
                return "internship"
        return None

    def _detect_remote(self, job: dict) -> Optional[str]:
        """Detect remote type from job data."""
        job_types = job.get("job_types", [])
        remote_flag = job.get("remote", False)
        location = job.get("location", "").lower()

        # Check job_types array
        types_lower = [t.lower() for t in job_types]
        if "remote" in types_lower or remote_flag:
            return "remote"
        elif "hybrid" in types_lower:
            return "hybrid"

        # Check location
        if "remote" in location or "anywhere" in location:
            return "remote"
        elif "hybrid" in location:
            return "hybrid"

        return "onsite"

    def normalize_job(self, job: JobListing) -> JobListing:
        """Normalize Arbeitnow job data."""
        if not job.normalized_title:
            job.normalized_title = self.normalize_title(job.title)

        if job.location and not job.normalized_location:
            job.normalized_location = self.normalize_location(job.location)

        if job.description:
            if not job.salary_range:
                job.salary_range = self.extract_salary(job.description)
            if not job.job_type:
                job.job_type = self.extract_job_type(job.description)
            if not job.remote_type:
                job.remote_type = self.extract_remote_type(job.description)

        return job

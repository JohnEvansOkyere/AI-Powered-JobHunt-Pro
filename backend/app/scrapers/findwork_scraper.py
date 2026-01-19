"""
FindWork.dev Job Scraper

Scrapes software developer jobs from FindWork.dev API.
Free tier available with 50 requests/day.

Docs: https://findwork.dev/developers/
API: https://findwork.dev/api/jobs/
"""

from typing import List, Optional
from datetime import datetime
import httpx

from app.scrapers.base import BaseScraper, JobListing
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class FindWorkScraper(BaseScraper):
    """
    FindWork.dev job scraper using their API.

    Focuses on software developer and tech jobs.
    Free tier: 50 requests/day (API key required).
    """

    BASE_URL = "https://findwork.dev/api/jobs/"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize FindWork scraper.

        Args:
            api_key: FindWork API key (optional, uses settings if not provided)
        """
        super().__init__("findwork")
        self.api_key = api_key or getattr(settings, 'FINDWORK_API_KEY', None)

        if not self.api_key:
            logger.warning("FINDWORK_API_KEY not set - FindWork scraper will not work")

    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs
    ) -> List[JobListing]:
        """
        Scrape jobs from FindWork.dev API.

        Args:
            keywords: Search keywords
            location: Location filter
            max_results: Maximum number of results

        Returns:
            List[JobListing]: Scraped job listings
        """
        if not self.api_key:
            logger.warning("FindWork API key not configured - skipping")
            return []

        query = " ".join(keywords) if keywords else "developer"

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }

        params = {
            "search": query,
            "sort_by": "date",
        }

        if location:
            params["location"] = location

        listings: List[JobListing] = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                page = 1

                while len(listings) < max_results:
                    params["page"] = page

                    resp = await client.get(self.BASE_URL, headers=headers, params=params)

                    if resp.status_code == 404:
                        # No more pages
                        break

                    resp.raise_for_status()
                    data = resp.json()

                    jobs = data.get("results", [])

                    if not jobs:
                        break

                    for job in jobs:
                        if len(listings) >= max_results:
                            break

                        listing = JobListing(
                            title=job.get("role") or "Untitled",
                            company=job.get("company_name") or "Unknown",
                            location=job.get("location") or "Remote",
                            description=job.get("text") or job.get("description") or "",
                            job_link=job.get("url") or "",
                            source="findwork",
                            source_id=str(job.get("id")) or job.get("url", "")[:100],
                            posted_date=self._parse_date(job.get("date_posted")),
                            salary_range=self._extract_salary(job),
                            job_type=job.get("employment_type"),
                            remote_type=self._detect_remote(job),
                        )
                        listings.append(self.normalize_job(listing))

                    # Check for next page
                    if not data.get("next"):
                        break

                    page += 1

            logger.info(f"FindWork: fetched {len(listings)} jobs for query='{query}'")
            return listings

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("FindWork API rate limit exceeded")
            else:
                logger.error(f"FindWork API HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"FindWork scraping failed: {e}", exc_info=True)
            return []

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse FindWork date format."""
        if not date_str:
            return None
        try:
            # FindWork returns dates like "2024-01-15T10:30:00Z"
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None

    def _extract_salary(self, job: dict) -> Optional[str]:
        """Extract salary from job data."""
        min_sal = job.get("salary_min")
        max_sal = job.get("salary_max")
        currency = job.get("salary_currency", "USD")

        if min_sal and max_sal:
            return f"{currency} {min_sal:,} - {max_sal:,}"
        elif min_sal:
            return f"{currency} {min_sal:,}+"
        elif max_sal:
            return f"Up to {currency} {max_sal:,}"
        return None

    def _detect_remote(self, job: dict) -> Optional[str]:
        """Detect remote type from job data."""
        remote = job.get("remote", False)
        location = job.get("location", "").lower()
        keywords = job.get("keywords", [])

        if remote:
            return "remote"

        keywords_lower = [k.lower() for k in keywords]
        if "remote" in keywords_lower:
            return "remote"

        if "remote" in location or "anywhere" in location:
            return "remote"
        elif "hybrid" in location:
            return "hybrid"

        return "onsite"

    def normalize_job(self, job: JobListing) -> JobListing:
        """Normalize FindWork job data."""
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

"""
Jooble Job Scraper

Scrapes jobs from Jooble API - a large job aggregator.
Free API with generous limits.

Docs: https://jooble.org/api/about
To get API key: Register at https://jooble.org/api/about
"""

from typing import List, Optional
from datetime import datetime, timedelta
import httpx

from app.scrapers.base import BaseScraper, JobListing
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class JoobleScraper(BaseScraper):
    """
    Jooble job scraper using their free API.

    Jooble aggregates jobs from thousands of job boards worldwide.
    Free API key available at: https://jooble.org/api/about
    """

    BASE_URL = "https://jooble.org/api"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Jooble scraper.

        Args:
            api_key: Jooble API key (optional, uses settings if not provided)
        """
        super().__init__("jooble")
        self.api_key = api_key or getattr(settings, 'JOOBLE_API_KEY', None)

        if not self.api_key:
            logger.warning("JOOBLE_API_KEY not set - Jooble scraper will not work")

    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs
    ) -> List[JobListing]:
        """
        Scrape jobs from Jooble API.

        Args:
            keywords: Search keywords
            location: Location filter (e.g., "United States", "Remote")
            max_results: Maximum number of results

        Returns:
            List[JobListing]: Scraped job listings
        """
        if not self.api_key:
            logger.warning("Jooble API key not configured - skipping")
            return []

        query = " ".join(keywords) if keywords else "software developer"

        # Jooble API endpoint
        url = f"{self.BASE_URL}/{self.api_key}"

        payload = {
            "keywords": query,
            "location": location or "Remote",
            "radius": 25,
            "page": 1,
        }

        listings: List[JobListing] = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Jooble returns ~20 jobs per page, fetch multiple pages
                pages_to_fetch = min(5, (max_results // 20) + 1)

                for page in range(1, pages_to_fetch + 1):
                    payload["page"] = page

                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()

                    jobs = data.get("jobs", [])

                    if not jobs:
                        break

                    for job in jobs:
                        if len(listings) >= max_results:
                            break

                        listing = JobListing(
                            title=job.get("title") or "Untitled",
                            company=job.get("company") or "Unknown",
                            location=job.get("location") or location or "Remote",
                            description=job.get("snippet") or "",
                            job_link=job.get("link") or "",
                            source="jooble",
                            source_id=job.get("id") or job.get("link", "")[:100],
                            posted_date=self._parse_date(job.get("updated")),
                            salary_range=job.get("salary") or None,
                            job_type=self._extract_job_type(job.get("type")),
                            remote_type=self._detect_remote(job),
                        )
                        listings.append(self.normalize_job(listing))

                    if len(listings) >= max_results:
                        break

            logger.info(f"Jooble: fetched {len(listings)} jobs for query='{query}'")
            return listings

        except httpx.HTTPStatusError as e:
            logger.error(f"Jooble API HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Jooble scraping failed: {e}", exc_info=True)
            return []

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse Jooble date format."""
        if not date_str:
            return None
        try:
            # Jooble returns dates like "2024-01-15T10:30:00"
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            # Try relative date parsing (e.g., "2 days ago")
            if "day" in str(date_str).lower():
                try:
                    days = int(''.join(filter(str.isdigit, date_str)) or 1)
                    return datetime.utcnow() - timedelta(days=days)
                except Exception:
                    pass
            return None

    def _extract_job_type(self, job_type: Optional[str]) -> Optional[str]:
        """Extract standardized job type."""
        if not job_type:
            return None

        job_type_lower = job_type.lower()
        if "full" in job_type_lower:
            return "full-time"
        elif "part" in job_type_lower:
            return "part-time"
        elif "contract" in job_type_lower:
            return "contract"
        elif "temp" in job_type_lower:
            return "temporary"
        elif "intern" in job_type_lower:
            return "internship"
        return job_type

    def _detect_remote(self, job: dict) -> Optional[str]:
        """Detect if job is remote from various fields."""
        text = f"{job.get('title', '')} {job.get('location', '')} {job.get('snippet', '')}".lower()

        if any(word in text for word in ['remote', 'work from home', 'wfh', 'distributed']):
            return 'remote'
        elif any(word in text for word in ['hybrid', 'flexible']):
            return 'hybrid'
        elif any(word in text for word in ['onsite', 'on-site', 'office']):
            return 'onsite'
        return None

    def normalize_job(self, job: JobListing) -> JobListing:
        """Normalize Jooble job data."""
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

"""
HiringCafe Job Scraper

Scrapes tech jobs from HiringCafe - completely free, no API key required.
Aggregates jobs from various tech companies.

API: https://hiring.cafe/api/jobs (FREE, no key needed)
"""

from typing import List, Optional
from datetime import datetime, timedelta
import httpx

from app.scrapers.base import BaseScraper, JobListing
from app.core.logging import get_logger

logger = get_logger(__name__)


class HiringCafeScraper(BaseScraper):
    """
    HiringCafe job scraper - free, no API key required.

    Good source for startup and tech company jobs.
    """

    BASE_URL = "https://hiring.cafe/api/jobs"

    def __init__(self):
        """Initialize HiringCafe scraper."""
        super().__init__("hiringcafe")

    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs
    ) -> List[JobListing]:
        """
        Scrape jobs from HiringCafe.

        Args:
            keywords: Search keywords (used for filtering)
            location: Location filter (optional)
            max_results: Maximum number of results

        Returns:
            List[JobListing]: Scraped job listings
        """
        query_terms = set(kw.lower() for kw in keywords) if keywords else set()
        location_lower = location.lower() if location else None

        listings: List[JobListing] = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # HiringCafe uses cursor-based pagination
                params = {"limit": min(100, max_results)}

                resp = await client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

                jobs = data.get("jobs", data.get("data", data if isinstance(data, list) else []))

                for job in jobs:
                    if len(listings) >= max_results:
                        break

                    title = job.get("title") or job.get("position") or ""
                    company = job.get("company") or job.get("company_name") or ""
                    job_location = job.get("location") or ""
                    description = job.get("description") or job.get("text") or ""

                    # Filter by keywords if provided
                    if query_terms:
                        job_text = f"{title} {description} {company}".lower()
                        if not any(term in job_text for term in query_terms):
                            continue

                    # Filter by location if provided
                    if location_lower and location_lower not in job_location.lower():
                        # Allow remote jobs through
                        if "remote" not in job_location.lower():
                            continue

                    listing = JobListing(
                        title=title or "Untitled",
                        company=company or "Unknown",
                        location=job_location or "Unknown",
                        description=description,
                        job_link=job.get("url") or job.get("link") or job.get("apply_url") or "",
                        source="hiringcafe",
                        source_id=str(job.get("id")) or job.get("url", "")[:100],
                        posted_date=self._parse_date(job.get("posted_at") or job.get("created_at") or job.get("date")),
                        salary_range=job.get("salary") or self._extract_salary_from_job(job),
                        job_type=self._extract_job_type_from_job(job),
                        remote_type=self._detect_remote(job),
                    )
                    listings.append(self.normalize_job(listing))

            logger.info(f"HiringCafe: fetched {len(listings)} jobs")
            return listings

        except httpx.HTTPStatusError as e:
            logger.error(f"HiringCafe API HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"HiringCafe scraping failed: {e}", exc_info=True)
            return []

    def _parse_date(self, date_val) -> Optional[datetime]:
        """Parse various date formats from HiringCafe."""
        if not date_val:
            return None

        # Handle Unix timestamp (int or string)
        if isinstance(date_val, (int, float)):
            try:
                return datetime.utcfromtimestamp(date_val)
            except Exception:
                pass

        if isinstance(date_val, str):
            # Try ISO format
            try:
                return datetime.fromisoformat(date_val.replace("Z", "+00:00"))
            except Exception:
                pass

            # Try relative format like "2 days ago"
            if "day" in date_val.lower():
                try:
                    days = int(''.join(filter(str.isdigit, date_val)) or 1)
                    return datetime.utcnow() - timedelta(days=days)
                except Exception:
                    pass

        return None

    def _extract_salary_from_job(self, job: dict) -> Optional[str]:
        """Extract salary from various job fields."""
        # Check common salary fields
        for field in ['salary_range', 'compensation', 'salary_min', 'salary_max']:
            if job.get(field):
                return str(job[field])

        # Check for min/max pair
        min_sal = job.get("salary_min") or job.get("min_salary")
        max_sal = job.get("salary_max") or job.get("max_salary")

        if min_sal and max_sal:
            return f"${min_sal:,} - ${max_sal:,}"
        elif min_sal:
            return f"${min_sal:,}+"
        elif max_sal:
            return f"Up to ${max_sal:,}"

        return None

    def _extract_job_type_from_job(self, job: dict) -> Optional[str]:
        """Extract job type from job data."""
        job_type = job.get("type") or job.get("job_type") or job.get("employment_type")

        if not job_type:
            return None

        job_type_lower = job_type.lower()
        if "full" in job_type_lower:
            return "full-time"
        elif "part" in job_type_lower:
            return "part-time"
        elif "contract" in job_type_lower:
            return "contract"
        elif "freelance" in job_type_lower:
            return "freelance"
        elif "intern" in job_type_lower:
            return "internship"

        return job_type

    def _detect_remote(self, job: dict) -> Optional[str]:
        """Detect remote type from job data."""
        remote = job.get("remote", False)
        location = job.get("location", "").lower()
        title = job.get("title", "").lower()

        # Check explicit remote flag
        if remote is True or remote == "true" or remote == 1:
            return "remote"

        # Check location and title for remote indicators
        text = f"{location} {title}"
        if any(word in text for word in ['remote', 'anywhere', 'work from home', 'wfh']):
            return "remote"
        elif "hybrid" in text:
            return "hybrid"

        return "onsite"

    def normalize_job(self, job: JobListing) -> JobListing:
        """Normalize HiringCafe job data."""
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

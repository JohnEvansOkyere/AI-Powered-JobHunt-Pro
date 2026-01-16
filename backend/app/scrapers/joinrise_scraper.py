"""
Joinrise (Free Jobs API) Scraper

Free job listings API that may include Ghana jobs.
No API key required for basic usage.

API: https://api.joinrise.io/api/v1/jobs/public
"""

from typing import List, Optional
from datetime import datetime
import requests
from app.scrapers.base import BaseScraper, JobListing
from app.core.logging import get_logger

logger = get_logger(__name__)


class JoinriseScraper(BaseScraper):
    """Joinrise job scraper using their free public API."""

    BASE_URL = "https://api.joinrise.io/api/v1/jobs/public"

    def __init__(self):
        """Initialize Joinrise scraper."""
        super().__init__("joinrise")

    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs
    ) -> List[JobListing]:
        """
        Scrape jobs from Joinrise API.

        Args:
            keywords: Search keywords
            location: Location filter (e.g., "Ghana")
            max_results: Maximum number of results

        Returns:
            List[JobListing]: Scraped job listings
        """
        try:
            all_jobs = []
            
            # Build query from keywords
            query = " ".join(keywords[:5]) if keywords else "developer"  # Limit keywords
            
            params = {
                "page": 1,
                "limit": min(100, max_results * 2),  # Get more to filter
            }
            
            # Add location if specified
            if location:
                params["jobLoc"] = location
            
            # Add search query if provided
            if query:
                params["search"] = query

            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; JobBot/1.0)',
                'Accept': 'application/json',
            }

            response = requests.get(self.BASE_URL, params=params, headers=headers, timeout=15)
            
            # Check if API is available
            if response.status_code == 404:
                logger.warning("Joinrise API endpoint not available")
                return []
            
            response.raise_for_status()
            data = response.json()

            # Handle different response formats
            if isinstance(data, dict):
                jobs_data = data.get("data", data.get("jobs", data.get("results", [])))
            elif isinstance(data, list):
                jobs_data = data
            else:
                jobs_data = []

            for job in jobs_data[:max_results]:
                try:
                    listing = JobListing(
                        title=job.get("title") or job.get("jobTitle") or "Untitled",
                        company=job.get("company") or job.get("companyName") or "Unknown",
                        location=job.get("location") or job.get("jobLoc") or location or "Remote",
                        description=self._clean_text(job.get("description") or job.get("jobDescription") or ""),
                        job_link=job.get("url") or job.get("link") or job.get("applyUrl") or "",
                        source="joinrise",
                        source_id=str(job.get("id") or job.get("jobId") or ""),
                        posted_date=self._parse_date(job.get("postedDate") or job.get("createdAt") or job.get("date")),
                        salary_range=job.get("salary") or None,
                        job_type=job.get("jobType") or None,
                        remote_type=self._detect_remote(job),
                    )
                    
                    if listing.job_link:  # Only add if we have a valid link
                        all_jobs.append(self.normalize_job(listing))
                        
                except Exception as e:
                    logger.warning(f"Error parsing Joinrise job: {e}")
                    continue

            logger.info(f"Joinrise: fetched {len(all_jobs)} jobs for location='{location}'")
            return all_jobs

        except Exception as e:
            logger.warning(f"Joinrise scraping failed: {e}")
            # Don't fail completely - just log and return empty
            return []

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse various date formats."""
        if not date_str:
            return None
        try:
            # Try ISO format
            if "T" in str(date_str):
                return datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
            # Try common formats
            for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"]:
                try:
                    return datetime.strptime(str(date_str), fmt)
                except ValueError:
                    continue
        except Exception:
            pass
        return None

    def _clean_text(self, text: str) -> str:
        """Clean and strip text."""
        if not text:
            return ""
        # Remove HTML tags if present
        import re
        text = re.sub(r'<[^>]+>', '', str(text))
        return text.strip()

    def _detect_remote(self, job: dict) -> str:
        """Detect if job is remote, hybrid, or onsite."""
        text = " ".join([
            str(job.get("title", "")),
            str(job.get("description", "")),
            str(job.get("location", "")),
        ]).lower()
        
        if any(keyword in text for keyword in ["remote", "work from home", "wfh", "distributed"]):
            if any(keyword in text for keyword in ["hybrid", "flexible"]):
                return "hybrid"
            return "remote"
        return "onsite"

    def normalize_job(self, job: JobListing) -> JobListing:
        """Normalize Joinrise job data."""
        if not job.normalized_title:
            job.normalized_title = self.normalize_title(job.title)
        if job.location and not job.normalized_location:
            job.normalized_location = self.normalize_location(job.location)
        return job

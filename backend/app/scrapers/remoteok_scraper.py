"""
RemoteOK Job Scraper

Scrapes remote jobs from RemoteOK.com public API (free, no API key needed).
Website: https://remoteok.com
API Docs: https://remoteok.com/api
"""

from typing import List, Optional
from datetime import datetime
import requests
import time

from app.scrapers.base import BaseScraper, JobListing
from app.core.logging import get_logger

logger = get_logger(__name__)


class RemoteOKScraper(BaseScraper):
    """RemoteOK job scraper using their public API (completely free)."""

    BASE_URL = "https://remoteok.com/api"

    def __init__(self):
        """Initialize RemoteOK scraper."""
        super().__init__("remoteok")

    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs
    ) -> List[JobListing]:
        """
        Scrape jobs from RemoteOK public API.

        Args:
            keywords: Search keywords (will filter by tags/title)
            location: Location filter (ignored - RemoteOK is remote-only)
            max_results: Maximum number of results

        Returns:
            List[JobListing]: Scraped job listings
        """
        try:
            # RemoteOK API returns all jobs, we filter client-side
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; JobBot/1.0)',
            }

            resp = requests.get(self.BASE_URL, headers=headers, timeout=20)
            resp.raise_for_status()
            data = resp.json()

            # First item is metadata, skip it
            jobs_data = data[1:] if isinstance(data, list) and len(data) > 1 else []

            # Filter jobs by keywords if provided
            # Only use first 10 keywords to avoid over-filtering
            if keywords:
                filtered_jobs = []
                keywords_lower = [kw.lower() for kw in keywords[:10]]

                for job in jobs_data:
                    # Check if any keyword matches position, company, or tags
                    position = (job.get('position') or '').lower()
                    company = (job.get('company') or '').lower()
                    tags = job.get('tags', [])
                    tags_str = ' '.join([str(t).lower() for t in tags]) if tags else ''

                    # Match if keyword appears in position, company, or tags
                    if any(kw in position or kw in company or kw in tags_str for kw in keywords_lower):
                        filtered_jobs.append(job)

                jobs_data = filtered_jobs

            # Limit results
            jobs_data = jobs_data[:max_results]

            listings: List[JobListing] = []
            for job in jobs_data:
                try:
                    listing = JobListing(
                        title=job.get('position') or job.get('title') or 'Untitled',
                        company=job.get('company') or 'Unknown',
                        location=job.get('location') or 'Remote',
                        description=self._clean_html(job.get('description') or ''),
                        job_link=job.get('url') or f"https://remoteok.com/remote-jobs/{job.get('slug', '')}",
                        source="remoteok",
                        source_id=str(job.get('id')),
                        posted_date=self._parse_epoch(job.get('date')),
                        salary_range=None,  # RemoteOK doesn't provide salary in API
                        job_type=None,
                        remote_type="remote",
                    )
                    listings.append(self.normalize_job(listing))
                except Exception as e:
                    logger.warning(f"Error parsing RemoteOK job: {e}")
                    continue

            logger.info(f"RemoteOK: fetched {len(listings)} jobs (filtered from {len(data)-1} total)")
            return listings

        except Exception as e:
            logger.error(f"RemoteOK scraping failed: {e}", exc_info=True)
            return []

    def _parse_epoch(self, timestamp: Optional[int]) -> Optional[datetime]:
        """Parse Unix timestamp to datetime."""
        if not timestamp:
            return None
        try:
            return datetime.fromtimestamp(int(timestamp))
        except Exception:
            return None

    def _clean_html(self, html: str) -> str:
        """Remove HTML tags from description."""
        if not html:
            return ""

        import re
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', html)
        # Remove extra whitespace
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()

    def normalize_job(self, job: JobListing) -> JobListing:
        """Normalize RemoteOK job data."""
        if not job.normalized_title:
            job.normalized_title = self.normalize_title(job.title)

        if job.location and not job.normalized_location:
            job.normalized_location = self.normalize_location(job.location)

        # RemoteOK jobs are always remote
        job.remote_type = "remote"

        return job

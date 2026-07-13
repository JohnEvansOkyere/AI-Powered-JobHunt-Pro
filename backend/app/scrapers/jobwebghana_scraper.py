"""
JobWeb Ghana Job Scraper

Scrapes jobs from the JobWeb Ghana WordPress RSS feed (free, no API key needed).
Feed: https://jobwebghana.com/feed/
Item titles are formatted "Job Title at Company".
"""

from typing import List, Optional
import httpx

from app.scrapers.base import BaseScraper, JobListing
from app.scrapers.feed_utils import parse_rss_items, parse_rfc822_date, strip_html
from app.core.logging import get_logger

logger = get_logger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


class JobWebGhanaScraper(BaseScraper):
    """JobWeb Ghana scraper using their public RSS feed."""

    FEED_URL = "https://jobwebghana.com/feed/"

    def __init__(self):
        super().__init__("jobwebghana")

    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs
    ) -> List[JobListing]:
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=HEADERS, follow_redirects=True) as client:
                resp = await client.get(self.FEED_URL)
                resp.raise_for_status()
                items = parse_rss_items(resp.text)

            # Small local feed (~10 items): take everything fresh rather than
            # keyword-filtering Ghana roles away.
            listings: List[JobListing] = []
            for item in items[:max_results]:
                raw_title = item.get("title") or "Untitled"
                title, _, company = raw_title.rpartition(" at ")
                if not title:
                    title, company = raw_title, "Unknown"
                listing = JobListing(
                    title=title.strip(),
                    company=company.strip(),
                    location="Ghana",
                    description=strip_html(item.get("encoded") or item.get("description") or ""),
                    job_link=item.get("link") or "",
                    source="jobwebghana",
                    source_id=item.get("link"),
                    posted_date=parse_rfc822_date(item.get("pubDate")),
                    salary_range=None,
                    job_type=None,
                    remote_type=None,
                )
                listings.append(self.normalize_job(listing))

            logger.info(f"JobWebGhana: fetched {len(listings)} jobs")
            return listings
        except Exception as e:
            logger.error(f"JobWebGhana scraping failed: {e}", exc_info=True)
            return []

    def normalize_job(self, job: JobListing) -> JobListing:
        if not job.normalized_title:
            job.normalized_title = self.normalize_title(job.title)
        if job.location and not job.normalized_location:
            job.normalized_location = self.normalize_location(job.location)
        if job.description and not job.remote_type:
            job.remote_type = self.extract_remote_type(job.description) or "onsite"
        return job

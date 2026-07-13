"""
We Work Remotely Job Scraper

Scrapes remote jobs from the We Work Remotely RSS feed (free, no API key needed).
Feed: https://weworkremotely.com/remote-jobs.rss
Item titles are formatted "Company: Job Title".
"""

from typing import List, Optional
import httpx

from app.scrapers.base import BaseScraper, JobListing
from app.scrapers.feed_utils import parse_rss_items, parse_rfc822_date, strip_html
from app.core.logging import get_logger

logger = get_logger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


class WeWorkRemotelyScraper(BaseScraper):
    """We Work Remotely scraper using their public RSS feed."""

    FEED_URL = "https://weworkremotely.com/remote-jobs.rss"

    def __init__(self):
        super().__init__("weworkremotely")

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

            if keywords:
                keywords_lower = [kw.lower() for kw in keywords]
                filtered = []
                for item in items:
                    text = f"{item.get('title', '')} {item.get('category', '')}".lower()
                    if any(kw in text for kw in keywords_lower):
                        filtered.append(item)
                items = filtered or items

            listings: List[JobListing] = []
            for item in items[:max_results]:
                raw_title = item.get("title") or "Untitled"
                company, _, title = raw_title.partition(": ")
                if not title:  # no "Company: Title" separator
                    company, title = "Unknown", raw_title
                listing = JobListing(
                    title=title.strip(),
                    company=company.strip(),
                    location=item.get("region") or "Remote",
                    description=strip_html(item.get("description") or ""),
                    job_link=item.get("link") or "",
                    source="weworkremotely",
                    source_id=item.get("guid") or item.get("link"),
                    posted_date=parse_rfc822_date(item.get("pubDate")),
                    salary_range=None,
                    job_type=item.get("type"),
                    remote_type="remote",
                )
                listings.append(self.normalize_job(listing))

            logger.info(f"WeWorkRemotely: fetched {len(listings)} jobs")
            return listings
        except Exception as e:
            logger.error(f"WeWorkRemotely scraping failed: {e}", exc_info=True)
            return []

    def normalize_job(self, job: JobListing) -> JobListing:
        if not job.normalized_title:
            job.normalized_title = self.normalize_title(job.title)
        if job.location and not job.normalized_location:
            job.normalized_location = self.normalize_location(job.location)
        job.remote_type = "remote"
        return job

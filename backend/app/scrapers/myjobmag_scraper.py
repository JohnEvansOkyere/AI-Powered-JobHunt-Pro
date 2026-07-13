"""
MyJobMag Job Scraper (Ghana / Africa)

Scrapes jobs from MyJobMag's public jobs XML feed (free, no API key needed).
Ghana feed: https://www.myjobmagghana.com/jobsxml.xml
Also serves Nigeria (myjobmag.com), Kenya (myjobmag.co.ke), South Africa (myjobmag.co.za).
Item titles are formatted "Job Title at Company"; <industry> carries the category.
All kinds of roles: customer support, marketing, finance, logistics, IT, etc.
"""

from typing import List, Optional
import httpx

from app.scrapers.base import BaseScraper, JobListing
from app.scrapers.feed_utils import parse_rss_items, parse_rfc822_date, fix_mojibake
from app.core.logging import get_logger

logger = get_logger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


COUNTRY_FEEDS = {
    "gh": ("https://www.myjobmagghana.com/jobsxml.xml", "Ghana"),
    "ng": ("https://www.myjobmag.com/jobsxml.xml", "Nigeria"),
    "ke": ("https://www.myjobmag.co.ke/jobsxml.xml", "Kenya"),
    "za": ("https://www.myjobmag.co.za/jobsxml.xml", "South Africa"),
}


class MyJobMagScraper(BaseScraper):
    """MyJobMag scraper using the public jobs XML feed. One instance per country."""

    def __init__(self, country: str = "gh"):
        feed_url, location = COUNTRY_FEEDS[country]
        self.feed_url = feed_url
        self.default_location = location
        source_name = "myjobmag" if country == "gh" else f"myjobmag_{country}"
        super().__init__(source_name)

    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs
    ) -> List[JobListing]:
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=HEADERS, follow_redirects=True) as client:
                resp = await client.get(self.feed_url)
                resp.raise_for_status()
                items = parse_rss_items(resp.text)

            # Local board with modest volume: keyword-filter but keep everything
            # if nothing matches, so Ghana roles aren't zeroed by a tech-heavy list.
            if keywords:
                keywords_lower = [kw.lower() for kw in keywords]
                filtered = []
                for item in items:
                    text = f"{item.get('title', '')} {item.get('industry', '')}".lower()
                    if any(kw in text for kw in keywords_lower):
                        filtered.append(item)
                items = filtered or items

            listings: List[JobListing] = []
            for item in items[:max_results]:
                raw_title = fix_mojibake(item.get("title") or "Untitled")
                title, _, company = raw_title.rpartition(" at ")
                if not title:  # no " at Company" suffix
                    title, company = raw_title, "Unknown"
                listing = JobListing(
                    title=title.strip(),
                    company=company.strip(),
                    location=self.default_location,
                    description=fix_mojibake(item.get("description") or ""),
                    job_link=item.get("link") or item.get("guid") or "",
                    source=self.source_name,
                    source_id=item.get("guid") or item.get("link"),
                    posted_date=parse_rfc822_date(item.get("pubDate")),
                    salary_range=None,
                    job_type=None,
                    remote_type=None,
                )
                listings.append(self.normalize_job(listing))

            logger.info(f"MyJobMag[{self.default_location}]: fetched {len(listings)} jobs")
            return listings
        except Exception as e:
            logger.error(f"MyJobMag scraping failed: {e}", exc_info=True)
            return []

    def normalize_job(self, job: JobListing) -> JobListing:
        if not job.normalized_title:
            job.normalized_title = self.normalize_title(job.title)
        if job.location and not job.normalized_location:
            job.normalized_location = self.normalize_location(job.location)
        if job.description and not job.remote_type:
            job.remote_type = self.extract_remote_type(job.description) or "onsite"
        return job

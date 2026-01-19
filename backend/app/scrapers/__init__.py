"""
Job Scrapers Package

Contains scrapers for various job boards.

Available Scrapers (FREE - No API Key Required):
- RemotiveScraper: Remote jobs from Remotive.io
- RemoteOKScraper: Remote jobs from RemoteOK.com
- AdzunaScraper: Jobs from Adzuna
- JoinriseScraper: Jobs from Joinrise (Ghana focus)
- ArbeitnowScraper: Remote tech jobs from Arbeitnow.com
- HiringCafeScraper: Startup/tech jobs from HiringCafe

Available Scrapers (API Key Required):
- SerpAPIScraper: Google Jobs via SerpAPI (PAID)
- JoobleScraper: Job aggregator (FREE key from jooble.org/api/about)
- FindWorkScraper: Dev jobs from FindWork.dev (FREE tier: 50 req/day)

Stub Scrapers (Not Implemented):
- LinkedInScraper: Requires auth
- IndeedScraper: Requires auth
- AIScraper: Custom AI scraper (placeholder)
"""

from app.scrapers.base import BaseScraper, JobListing
from app.scrapers.remotive_scraper import RemotiveScraper
from app.scrapers.remoteok_scraper import RemoteOKScraper
from app.scrapers.adzuna_scraper import AdzunaScraper
from app.scrapers.joinrise_scraper import JoinriseScraper
from app.scrapers.serpapi_scraper import SerpAPIScraper
from app.scrapers.jooble_scraper import JoobleScraper
from app.scrapers.arbeitnow_scraper import ArbeitnowScraper
from app.scrapers.findwork_scraper import FindWorkScraper
from app.scrapers.hiringcafe_scraper import HiringCafeScraper

__all__ = [
    "BaseScraper",
    "JobListing",
    # FREE scrapers (no API key)
    "RemotiveScraper",
    "RemoteOKScraper",
    "AdzunaScraper",
    "JoinriseScraper",
    "ArbeitnowScraper",
    "HiringCafeScraper",
    # Scrapers requiring API key
    "SerpAPIScraper",
    "JoobleScraper",
    "FindWorkScraper",
]


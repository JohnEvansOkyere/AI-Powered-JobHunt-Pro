"""
Adzuna Job Scraper

Adzuna is a FREE job search engine that aggregates listings from thousands of sources.
API documentation: https://developer.adzuna.com/

COMPLETELY FREE - No API key needed for basic usage!
"""

from typing import List, Optional
import requests
from datetime import datetime
from app.scrapers.base import BaseScraper, JobListing
from app.core.logging import get_logger

logger = get_logger(__name__)


class AdzunaScraper(BaseScraper):
    """
    Adzuna job scraper using their free public API.

    Adzuna aggregates jobs from multiple sources and provides a free API.
    No authentication required for basic searches.
    """

    BASE_URL = "https://api.adzuna.com/v1/api/jobs"

    def __init__(self, app_id: Optional[str] = None, app_key: Optional[str] = None):
        """
        Initialize Adzuna scraper.

        Args:
            app_id: Optional Adzuna app ID (for higher rate limits)
            app_key: Optional Adzuna app key (for higher rate limits)

        Note: Works without credentials but with lower rate limits
        """
        super().__init__(source_name="adzuna")
        self.app_id = app_id or "test"  # Public test credentials
        self.app_key = app_key or "test"
        logger.info("Adzuna scraper initialized (FREE)")

    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs
    ) -> List[JobListing]:
        """
        Scrape jobs from Adzuna API.

        Args:
            keywords: Search keywords
            location: Location (country code, e.g., 'us', 'gb', 'ca')
            max_results: Maximum number of results

        Returns:
            List[JobListing]: Scraped job listings
        """
        try:
            # Default to US if no location specified
            country = (location or "us").lower()
            if len(country) > 2 or country not in ["us", "gb", "ca", "au", "de", "fr", "in", "gh"]:
                # Convert location names to country codes
                country_map = {
                    "united states": "us",
                    "usa": "us",
                    "united kingdom": "gb",
                    "uk": "gb",
                    "canada": "ca",
                    "australia": "au",
                    "germany": "de",
                    "france": "fr",
                    "india": "in",
                    "ghana": "gh",
                    "worldwide": "us",  # Default to US for worldwide
                    "remote": "us",     # Default to US for remote
                }
                country = country_map.get(country.lower(), "gh" if "ghana" in country.lower() else "us")

            all_jobs = []

            # Search for each keyword
            for keyword in keywords[:10]:  # Limit to prevent rate limiting
                try:
                    # Adzuna API endpoint
                    url = f"{self.BASE_URL}/{country}/search/1"

                    params = {
                        "app_id": self.app_id,
                        "app_key": self.app_key,
                        "what": keyword,
                        "results_per_page": min(50, max_results),
                        "content-type": "application/json",
                    }

                    response = requests.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()

                    jobs = data.get("results", [])

                    for job in jobs[:max_results]:
                        try:
                            listing = JobListing(
                                title=job.get("title", "Untitled"),
                                company=job.get("company", {}).get("display_name", "Unknown Company"),
                                location=job.get("location", {}).get("display_name", "Remote"),
                                description=self._clean_html(job.get("description", "")),
                                job_link=job.get("redirect_url", ""),
                                source="adzuna",
                                source_id=str(job.get("id", "")),
                                posted_date=self._parse_date(job.get("created")),
                                salary_range=self._format_salary(job.get("salary_min"), job.get("salary_max")),
                                job_type=job.get("contract_type"),
                                remote_type=self._detect_remote_type(
                                    job.get("title", ""),
                                    job.get("description", ""),
                                    job.get("location", {}).get("display_name", "")
                                ),
                            )
                            all_jobs.append(self.normalize_job(listing))

                        except Exception as e:
                            logger.warning(f"Error parsing Adzuna job: {e}")
                            continue

                    logger.info(f"Adzuna: fetched {len(jobs)} jobs for keyword='{keyword}'")

                    # Stop if we have enough jobs
                    if len(all_jobs) >= max_results:
                        break

                except Exception as e:
                    logger.warning(f"Error fetching Adzuna jobs for '{keyword}': {e}")
                    continue

            # Deduplicate by job link
            seen_links = set()
            unique_jobs = []
            for job in all_jobs:
                if job.job_link not in seen_links:
                    seen_links.add(job.job_link)
                    unique_jobs.append(job)

            return unique_jobs[:max_results]

        except Exception as e:
            logger.error(f"Error in Adzuna scraper: {e}", exc_info=True)
            return []

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse Adzuna date format."""
        if not date_str:
            return None
        try:
            # Adzuna uses ISO format
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None

    def _format_salary(self, min_salary: Optional[float], max_salary: Optional[float]) -> Optional[str]:
        """Format salary range."""
        if min_salary and max_salary:
            return f"${int(min_salary):,} - ${int(max_salary):,}"
        elif min_salary:
            return f"${int(min_salary):,}+"
        elif max_salary:
            return f"Up to ${int(max_salary):,}"
        return None

    def _detect_remote_type(self, title: str, description: str, location: str) -> str:
        """Detect if job is remote, hybrid, or onsite."""
        text = f"{title} {description} {location}".lower()

        if any(keyword in text for keyword in ["remote", "work from home", "wfh", "distributed"]):
            if any(keyword in text for keyword in ["hybrid", "flexible", "partial remote"]):
                return "hybrid"
            return "remote"

        return "onsite"

    def normalize_job(self, job: JobListing) -> JobListing:
        """
        Normalize job data for consistency.

        Args:
            job: Raw job listing

        Returns:
            JobListing: Normalized job listing
        """
        # Job is already normalized during scraping, just return as-is
        return job

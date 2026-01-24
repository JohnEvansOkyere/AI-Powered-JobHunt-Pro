"""
Job Description Scraper

Extracts job descriptions from job posting URLs.
Supports major job boards and company career pages.
"""

import re
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class JobDescriptionScraper:
    """Scrapes job descriptions from URLs."""
    
    def __init__(self):
        """Initialize the scraper."""
        self.timeout = 15
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def scrape_job_from_url(self, url: str) -> Dict[str, Any]:
        """
        Scrape job description from a URL.
        
        Args:
            url: Job posting URL
            
        Returns:
            dict: Contains 'description', 'title', 'company', 'location', etc.
            
        Raises:
            ValueError: If URL is invalid or scraping fails
        """
        try:
            # Validate URL
            if not url or not url.strip():
                raise ValueError("URL cannot be empty")
            
            url = url.strip()
            
            # Basic URL validation
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format. Please provide a complete URL (e.g., https://...)")
            
            logger.info(f"Scraping job from URL: {url}")
            
            # Fetch the page
            try:
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
            except requests.exceptions.Timeout:
                raise ValueError("Request timed out. The job posting website might be slow or unavailable.")
            except requests.exceptions.ConnectionError:
                raise ValueError("Could not connect to the job posting website. Please check the URL.")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    raise ValueError("Job posting not found (404). The link might be expired or invalid.")
                elif e.response.status_code == 403:
                    raise ValueError("Access denied (403). The website might be blocking automated access.")
                else:
                    raise ValueError(f"Failed to access job posting (HTTP {e.response.status_code})")
            except Exception as e:
                raise ValueError(f"Failed to fetch job posting: {str(e)}")
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Detect job board and extract accordingly
            domain = parsed.netloc.lower()
            
            if 'linkedin.com' in domain:
                return self._scrape_linkedin(soup, url)
            elif 'indeed.com' in domain:
                return self._scrape_indeed(soup, url)
            elif 'glassdoor.com' in domain:
                return self._scrape_glassdoor(soup, url)
            elif 'greenhouse.io' in domain:
                return self._scrape_greenhouse(soup, url)
            elif 'lever.co' in domain:
                return self._scrape_lever(soup, url)
            else:
                # Generic scraping for unknown sites
                return self._scrape_generic(soup, url)
                
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error scraping job from URL: {e}", exc_info=True)
            raise ValueError(f"Failed to extract job description: {str(e)}")
    
    def _scrape_linkedin(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract job info from LinkedIn."""
        try:
            # Title
            title_elem = soup.find('h1', class_=re.compile('job.*title|top.*card.*title'))
            title = title_elem.get_text(strip=True) if title_elem else None
            
            # Company
            company_elem = soup.find('a', class_=re.compile('company|topcard.*org'))
            if not company_elem:
                company_elem = soup.find('span', class_=re.compile('company|topcard.*org'))
            company = company_elem.get_text(strip=True) if company_elem else None
            
            # Location
            location_elem = soup.find('span', class_=re.compile('location|topcard.*location'))
            location = location_elem.get_text(strip=True) if location_elem else None
            
            # Description
            desc_elem = soup.find('div', class_=re.compile('description|job.*description'))
            if not desc_elem:
                desc_elem = soup.find('article')
            description = self._clean_text(desc_elem.get_text()) if desc_elem else None
            
            if not description:
                raise ValueError("Could not extract job description from LinkedIn")
            
            return {
                'title': title,
                'company': company,
                'location': location,
                'description': description,
                'source': 'LinkedIn'
            }
        except Exception as e:
            logger.error(f"LinkedIn scraping failed: {e}")
            raise ValueError("Could not extract job details from LinkedIn. The page structure might have changed.")
    
    def _scrape_indeed(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract job info from Indeed."""
        try:
            # Title
            title_elem = soup.find('h1', class_=re.compile('jobsearch.*JobInfoHeader'))
            if not title_elem:
                title_elem = soup.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else None
            
            # Company
            company_elem = soup.find('div', class_=re.compile('company|employer'))
            company = company_elem.get_text(strip=True) if company_elem else None
            
            # Location
            location_elem = soup.find('div', class_=re.compile('location'))
            location = location_elem.get_text(strip=True) if location_elem else None
            
            # Description
            desc_elem = soup.find('div', id=re.compile('jobDescriptionText'))
            if not desc_elem:
                desc_elem = soup.find('div', class_=re.compile('jobsearch.*JobComponent'))
            description = self._clean_text(desc_elem.get_text()) if desc_elem else None
            
            if not description:
                raise ValueError("Could not extract job description from Indeed")
            
            return {
                'title': title,
                'company': company,
                'location': location,
                'description': description,
                'source': 'Indeed'
            }
        except Exception as e:
            logger.error(f"Indeed scraping failed: {e}")
            raise ValueError("Could not extract job details from Indeed. The page structure might have changed.")
    
    def _scrape_glassdoor(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract job info from Glassdoor."""
        try:
            # Title
            title_elem = soup.find('div', class_=re.compile('job.*title'))
            if not title_elem:
                title_elem = soup.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else None
            
            # Company
            company_elem = soup.find('div', class_=re.compile('employer|company'))
            company = company_elem.get_text(strip=True) if company_elem else None
            
            # Location
            location_elem = soup.find('div', class_=re.compile('location'))
            location = location_elem.get_text(strip=True) if location_elem else None
            
            # Description
            desc_elem = soup.find('div', class_=re.compile('job.*desc|desc.*content'))
            description = self._clean_text(desc_elem.get_text()) if desc_elem else None
            
            if not description:
                raise ValueError("Could not extract job description from Glassdoor")
            
            return {
                'title': title,
                'company': company,
                'location': location,
                'description': description,
                'source': 'Glassdoor'
            }
        except Exception as e:
            logger.error(f"Glassdoor scraping failed: {e}")
            raise ValueError("Could not extract job details from Glassdoor. The page structure might have changed.")
    
    def _scrape_greenhouse(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract job info from Greenhouse ATS."""
        try:
            # Title
            title_elem = soup.find('h1', class_='app-title')
            if not title_elem:
                title_elem = soup.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else None
            
            # Company (usually in meta or title)
            company = None
            company_meta = soup.find('meta', {'property': 'og:site_name'})
            if company_meta:
                company = company_meta.get('content')
            
            # Location
            location_elem = soup.find('div', class_='location')
            location = location_elem.get_text(strip=True) if location_elem else None
            
            # Description
            desc_elem = soup.find('div', id='content')
            if not desc_elem:
                desc_elem = soup.find('div', class_='content')
            description = self._clean_text(desc_elem.get_text()) if desc_elem else None
            
            if not description:
                raise ValueError("Could not extract job description")
            
            return {
                'title': title,
                'company': company,
                'location': location,
                'description': description,
                'source': 'Greenhouse'
            }
        except Exception as e:
            logger.error(f"Greenhouse scraping failed: {e}")
            return self._scrape_generic(soup, url)
    
    def _scrape_lever(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract job info from Lever ATS."""
        try:
            # Title
            title_elem = soup.find('h2', class_='posting-headline')
            if not title_elem:
                title_elem = soup.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else None
            
            # Company (from URL or meta)
            company = None
            company_meta = soup.find('meta', {'property': 'og:site_name'})
            if company_meta:
                company = company_meta.get('content')
            
            # Location
            location_elem = soup.find('div', class_='posting-categories')
            location = location_elem.get_text(strip=True) if location_elem else None
            
            # Description
            desc_elem = soup.find('div', class_='content')
            if not desc_elem:
                desc_elem = soup.find('div', class_='posting-description')
            description = self._clean_text(desc_elem.get_text()) if desc_elem else None
            
            if not description:
                raise ValueError("Could not extract job description")
            
            return {
                'title': title,
                'company': company,
                'location': location,
                'description': description,
                'source': 'Lever'
            }
        except Exception as e:
            logger.error(f"Lever scraping failed: {e}")
            return self._scrape_generic(soup, url)
    
    def _scrape_generic(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Generic scraping for unknown sites."""
        try:
            # Try to find title
            title = None
            title_elem = soup.find('h1')
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Try to find company from meta tags
            company = None
            company_meta = soup.find('meta', {'property': 'og:site_name'})
            if company_meta:
                company = company_meta.get('content')
            
            # Try to extract main content
            # Remove script, style, nav, header, footer
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'iframe']):
                tag.decompose()
            
            # Try to find the main content area
            main_content = None
            for selector in ['main', 'article', '[role="main"]', '.content', '#content', '.job-description', '.description']:
                elem = soup.select_one(selector)
                if elem:
                    main_content = elem
                    break
            
            if not main_content:
                # Fallback to body
                main_content = soup.find('body')
            
            if not main_content:
                raise ValueError("Could not extract content from page")
            
            description = self._clean_text(main_content.get_text())
            
            if not description or len(description) < 100:
                raise ValueError("Extracted content is too short or empty")
            
            return {
                'title': title,
                'company': company,
                'location': None,
                'description': description,
                'source': 'Generic'
            }
        except Exception as e:
            logger.error(f"Generic scraping failed: {e}")
            raise ValueError(f"Could not extract job description from this website. Please paste the job description manually.")
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive newlines
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Strip
        text = text.strip()
        
        return text


# Global instance
_scraper: Optional[JobDescriptionScraper] = None


def get_job_scraper() -> JobDescriptionScraper:
    """Get or create the global job scraper instance."""
    global _scraper
    if _scraper is None:
        _scraper = JobDescriptionScraper()
    return _scraper

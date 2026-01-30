"""
External Job Parser Service

Parses job postings from URLs or raw text using AI to extract structured data.

Strategy for URL parsing:
1. Try direct HTTP fetch + BeautifulSoup (handles static pages)
2. Try extracting JSON-LD structured data from raw HTML (works for many SPAs)
3. Fall back to Jina Reader API for JavaScript-rendered pages (free)
4. Send extracted content to AI for structured field extraction
"""

import re
import json
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.ai.router import get_model_router
from app.ai.base import TaskType

logger = get_logger(__name__)

# Domains that require authentication and cannot be scraped
AUTH_REQUIRED_DOMAINS = [
    'linkedin.com', 'www.linkedin.com',
    'indeed.com', 'www.indeed.com',
    'glassdoor.com', 'www.glassdoor.com',
]

# Jina Reader API (free tier) - renders JavaScript and returns markdown
JINA_READER_URL = "https://r.jina.ai/"


class ExternalJobParser:
    """Service to parse external job postings from URLs or raw text."""

    def __init__(self):
        self.timeout = 20.0  # Increased timeout for slower career pages
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
        }

    def _is_auth_required_domain(self, url: str) -> bool:
        """Check if the URL domain requires authentication (LinkedIn, Indeed, etc.)."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return any(domain == d or domain.endswith('.' + d) for d in AUTH_REQUIRED_DOMAINS)

    async def parse_from_url(self, url: str) -> Dict[str, Any]:
        """
        Fetch and parse a job posting from a URL.

        Uses a multi-strategy approach:
        1. Direct HTTP fetch + BeautifulSoup
        2. JSON-LD structured data extraction
        3. Jina Reader API fallback (for JS-rendered pages)

        Args:
            url: The job posting URL

        Returns:
            Dictionary with extracted job details
        """
        # Check if URL requires authentication (check domain, not query params)
        if self._is_auth_required_domain(url):
            raise ValueError(
                "This URL requires authentication (LinkedIn/Indeed/Glassdoor block direct access). "
                "Please copy the job description text and use the 'From Text' option instead."
            )

        domain = urlparse(url).netloc
        clean_text = None

        # Strategy 1: Direct HTTP fetch + BeautifulSoup
        try:
            clean_text = await self._fetch_with_beautifulsoup(url)
            if clean_text and len(clean_text) >= 200:
                logger.info(f"Strategy 1 (BeautifulSoup) succeeded for {domain}: {len(clean_text)} chars")
            else:
                clean_text = None
        except Exception as e:
            logger.debug(f"Strategy 1 (BeautifulSoup) failed for {domain}: {e}")
            clean_text = None

        # Strategy 2: Try JSON-LD structured data from the raw HTML
        if not clean_text:
            try:
                clean_text = await self._extract_jsonld(url)
                if clean_text and len(clean_text) >= 100:
                    logger.info(f"Strategy 2 (JSON-LD) succeeded for {domain}: {len(clean_text)} chars")
                else:
                    clean_text = None
            except Exception as e:
                logger.debug(f"Strategy 2 (JSON-LD) failed for {domain}: {e}")
                clean_text = None

        # Strategy 3: Jina Reader API (renders JavaScript, returns markdown)
        if not clean_text:
            try:
                clean_text = await self._fetch_with_jina_reader(url)
                if clean_text and len(clean_text) >= 200:
                    logger.info(f"Strategy 3 (Jina Reader) succeeded for {domain}: {len(clean_text)} chars")
                else:
                    clean_text = None
            except Exception as e:
                logger.debug(f"Strategy 3 (Jina Reader) failed for {domain}: {e}")
                clean_text = None

        # If all strategies failed, give a helpful error
        if not clean_text:
            raise ValueError(
                "Could not extract job content from this URL. The page may use heavy JavaScript rendering "
                "or have anti-bot protection. Please copy the job description text and use the 'From Text' option instead."
            )

        # Reject minimal/generic content (e.g. Dayforce "Find your next adventure" shell)
        if len(clean_text) < 300 or clean_text.strip().lower() in (
            'find your next adventure', 'apply now', 'job details',
        ):
            raise ValueError(
                "This URL returned very little content (likely a JavaScript-heavy or login-required page). "
                "Please open the job in your browser, copy the full job description, and use the 'Paste job description' tab instead."
            )

        # Parse the extracted text using AI
        job_data = await self._parse_with_ai(clean_text, url, domain)
        return job_data

    async def _fetch_with_beautifulsoup(self, url: str) -> Optional[str]:
        """
        Strategy 1: Direct HTTP fetch and parse with BeautifulSoup.
        Works for static HTML pages.
        """
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            html_content = response.text

        soup = BeautifulSoup(html_content, 'html.parser')

        # Check for login/auth pages
        page_title = soup.find('title')
        if page_title:
            title_text = page_title.get_text().lower()
            if any(kw in title_text for kw in ['login', 'sign in', 'sign up', 'authenticate', 'access denied']):
                return None

        # Remove non-content elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
            tag.decompose()

        # Try to find the main content area first
        main_content = (
            soup.find('main') or
            soup.find('article') or
            soup.find('div', class_=re.compile(r'job|posting|description|content|detail', re.I)) or
            soup.find('div', id=re.compile(r'job|posting|description|content|detail', re.I))
        )

        if main_content and len(main_content.get_text(strip=True)) >= 200:
            text = main_content.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)

        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_text = '\n'.join(lines)

        return clean_text if len(clean_text) >= 200 else None

    async def _extract_jsonld(self, url: str) -> Optional[str]:
        """
        Strategy 2: Extract structured data from JSON-LD (Schema.org).
        Many career pages include JobPosting schema even in SPAs.
        """
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            html_content = response.text

        soup = BeautifulSoup(html_content, 'html.parser')

        # Look for JSON-LD script tags
        jsonld_scripts = soup.find_all('script', type='application/ld+json')

        for script in jsonld_scripts:
            try:
                data = json.loads(script.string)

                # Handle arrays of structured data
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                            return self._jsonld_to_text(item)
                elif isinstance(data, dict):
                    if data.get('@type') == 'JobPosting':
                        return self._jsonld_to_text(data)
                    # Check nested @graph
                    if '@graph' in data:
                        for item in data['@graph']:
                            if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                                return self._jsonld_to_text(item)
            except (json.JSONDecodeError, TypeError):
                continue

        # Also try Open Graph and meta tags as a lighter fallback (only if substantive)
        og_title = soup.find('meta', property='og:title')
        og_description = soup.find('meta', property='og:description')
        meta_description = soup.find('meta', attrs={'name': 'description'})

        if og_title and og_description:
            desc = (og_description.get('content') or '').strip()
            # Skip generic/empty descriptions (e.g. "Find your next adventure" from Dayforce)
            if len(desc) >= 200 and desc.lower() not in ('find your next adventure', 'apply now', ''):
                parts = [
                    f"Title: {og_title.get('content', '')}",
                    f"Description: {desc}",
                ]
                if meta_description:
                    parts.append(f"Details: {meta_description.get('content', '')}")
                text = '\n'.join(parts)
                if len(text) >= 200:
                    return text

        return None

    def _jsonld_to_text(self, job_data: Dict[str, Any]) -> str:
        """Convert a JSON-LD JobPosting object to readable text."""
        parts = []

        if job_data.get('title'):
            parts.append(f"Job Title: {job_data['title']}")
        if job_data.get('hiringOrganization'):
            org = job_data['hiringOrganization']
            if isinstance(org, dict):
                parts.append(f"Company: {org.get('name', '')}")
            else:
                parts.append(f"Company: {org}")
        if job_data.get('jobLocation'):
            loc = job_data['jobLocation']
            if isinstance(loc, dict):
                address = loc.get('address', {})
                if isinstance(address, dict):
                    parts.append(f"Location: {address.get('addressLocality', '')} {address.get('addressRegion', '')} {address.get('addressCountry', '')}")
                else:
                    parts.append(f"Location: {address}")
            elif isinstance(loc, list):
                locations = []
                for l in loc:
                    if isinstance(l, dict):
                        addr = l.get('address', {})
                        if isinstance(addr, dict):
                            locations.append(f"{addr.get('addressLocality', '')} {addr.get('addressCountry', '')}")
                if locations:
                    parts.append(f"Location: {', '.join(locations)}")
            else:
                parts.append(f"Location: {loc}")
        if job_data.get('description'):
            desc = job_data['description']
            # Strip HTML from description if present
            if '<' in desc:
                desc_soup = BeautifulSoup(desc, 'html.parser')
                desc = desc_soup.get_text(separator='\n', strip=True)
            parts.append(f"Description:\n{desc}")
        if job_data.get('employmentType'):
            parts.append(f"Employment Type: {job_data['employmentType']}")
        if job_data.get('baseSalary'):
            salary = job_data['baseSalary']
            if isinstance(salary, dict):
                value = salary.get('value', {})
                if isinstance(value, dict):
                    parts.append(f"Salary: {value.get('minValue', '')} - {value.get('maxValue', '')} {salary.get('currency', '')}")
        if job_data.get('datePosted'):
            parts.append(f"Posted: {job_data['datePosted']}")
        if job_data.get('qualifications'):
            parts.append(f"Qualifications: {job_data['qualifications']}")
        if job_data.get('skills'):
            parts.append(f"Skills: {job_data['skills']}")
        if job_data.get('experienceRequirements'):
            parts.append(f"Experience: {job_data['experienceRequirements']}")

        return '\n'.join(parts)

    async def _fetch_with_jina_reader(self, url: str) -> Optional[str]:
        """
        Strategy 3: Use Jina Reader API to render JavaScript and get markdown.
        Free tier handles most career pages that require JS rendering.
        """
        jina_url = f"{JINA_READER_URL}{url}"

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                jina_url,
                headers={
                    'Accept': 'text/plain',
                    'User-Agent': 'Mozilla/5.0 (compatible; JobHuntPro/1.0)',
                }
            )
            response.raise_for_status()
            text = response.text

        # Clean the response - Jina returns markdown
        if not text or len(text.strip()) < 200:
            return None

        # Truncate if too long (keep first 6000 chars for AI processing)
        clean_text = text.strip()
        if len(clean_text) > 6000:
            clean_text = clean_text[:6000]

        return clean_text

    async def parse_from_text(self, text: str, source_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse a job posting from raw text.

        Args:
            text: The job posting text
            source_url: Optional source URL

        Returns:
            Dictionary with extracted job details
        """
        try:
            clean_text = text.strip()

            if len(clean_text) < 50:
                raise ValueError("Job description is too short. Please provide more details.")

            job_data = await self._parse_with_ai(clean_text, source_url)
            return job_data

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error parsing job from text: {e}")
            raise ValueError(f"Failed to parse job posting: {str(e)}")

    async def _parse_with_ai(
        self,
        text: str,
        source_url: Optional[str] = None,
        domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Use AI to extract structured job data from text.

        Args:
            text: The job posting text
            source_url: Optional source URL
            domain: Optional domain for company hint

        Returns:
            Dictionary with extracted job details
        """
        # Truncate text if too long, keeping first 5000 chars for efficiency
        truncated_text = text[:5000]
        char_limit_note = " [Note: Text was truncated to 5000 characters]" if len(text) > 5000 else ""
        
        prompt = f"""You are a professional job posting analyst. Extract structured data from the job posting below.

TASK: Parse the job posting and return ONLY a valid JSON object with the following exact structure.

REQUIRED FIELDS:
{{
  "title": "Job title (extract exactly as written)",
  "company": "Company/organization name"{f' (hint: domain is {domain})' if domain else ''},
  "description": "A concise 2-3 sentence summary of the role and company",
  "location": "City, State/Country OR 'Remote' if fully remote OR 'Hybrid' if hybrid",
  "job_type": "full-time|part-time|contract|internship|temporary",
  "salary_min": "Minimum salary as number (e.g., 80000) or null",
  "salary_max": "Maximum salary as number (e.g., 120000) or null",
  "salary_currency": "Currency code (USD, GBP, EUR, CAD, etc.) or null",
  "experience_level": "entry|mid|senior|lead|executive",
  "remote_option": true or false,
  "requirements": ["Requirement 1", "Requirement 2", "..."],
  "responsibilities": ["Responsibility 1", "Responsibility 2", "..."],
  "skills": ["Skill 1", "Skill 2", "Skill 3", "..."]
}}

EXTRACTION RULES:
1. Title: Extract exact job title from the posting (e.g., "Senior Software Engineer", not "Software Engineer")
2. Company: Extract the company name. Use domain hint if provided.
3. Description: Create a 2-3 sentence summary combining the company mission and role overview
4. Location: If mentions "remote", "work from home", or "WFH", use "Remote". If hybrid, use "Hybrid". Otherwise extract city/state/country.
5. Job Type: Default to "full-time" unless explicitly stated otherwise
6. Salary: 
   - Extract ONLY numeric values (e.g., "$100k-$150k" → min: 100000, max: 150000)
   - If range like "up to $X", set max only
   - If "competitive" or not mentioned, set both to null
   - Always include currency if salary is present
7. Experience Level:
   - "0-2 years" or "junior" → entry
   - "3-5 years" or no mention → mid
   - "5-8 years" or "senior" → senior
   - "8+ years" or "staff/principal" → lead
   - "C-level" or "director" → executive
8. Remote Option: true if remote/hybrid mentioned anywhere
9. Requirements: Extract 5-8 key qualifications/requirements (education, years of experience, must-haves)
10. Responsibilities: Extract 5-8 main duties/what you'll do
11. Skills: Extract technical skills, tools, technologies, programming languages (be specific)

CRITICAL RULES:
- Return ONLY valid JSON (no markdown, no explanations, no code blocks)
- If a field is not found, use null for strings/numbers or [] for arrays
- For numeric fields (salary_min, salary_max), use numbers not strings
- For boolean fields (remote_option), use true or false not strings
- Requirements, responsibilities, and skills MUST be arrays of strings
- Each array item should be a complete, clear sentence or phrase

JOB POSTING TEXT:{char_limit_note}
{truncated_text}

JSON OUTPUT:"""

        try:
            router = get_model_router()
            response = await router.generate(
                task_type=TaskType.JOB_ANALYSIS,
                prompt=prompt,
                preferred_provider="openai",
                optimize_cost=True,
                max_tokens=2500,  # Increased for better extraction
                temperature=0.1  # Low temperature for consistent, factual extraction
            )

            # Extract JSON from response
            json_str = response.strip()

            # Remove markdown code blocks if present
            if json_str.startswith('```'):
                json_str = re.sub(r'^```(?:json)?\s*\n', '', json_str)
                json_str = re.sub(r'\n```\s*$', '', json_str)
            
            # Remove any leading/trailing whitespace or "JSON OUTPUT:" prefix
            json_str = re.sub(r'^JSON OUTPUT:\s*', '', json_str, flags=re.IGNORECASE)
            json_str = json_str.strip()

            # Parse JSON
            try:
                job_data = json.loads(json_str)
            except json.JSONDecodeError as e:
                # Try to extract JSON if wrapped in other text
                # Use raw string with escaped braces to avoid f-string interpretation
                pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                json_match = re.search(pattern, json_str, re.DOTALL)
                if json_match:
                    job_data = json.loads(json_match.group())
                else:
                    raise e

            # Normalize common AI response keys
            if not job_data.get('title') and job_data.get('job_title'):
                job_data['title'] = job_data.pop('job_title', '')
            if not job_data.get('company') and job_data.get('company_name'):
                job_data['company'] = job_data.pop('company_name', '')

            # Fallbacks from input text when AI didn't extract required fields
            if not job_data.get('title') or (isinstance(job_data.get('title'), str) and not job_data['title'].strip()):
                match = re.search(r'Title:\s*(.+?)(?:\n|$)', truncated_text, re.IGNORECASE)
                if match:
                    job_data['title'] = match.group(1).strip()
            if not job_data.get('company') or (isinstance(job_data.get('company'), str) and not job_data['company'].strip()):
                if domain and domain not in ('localhost', '127.0.0.1'):
                    job_data['company'] = domain.replace('www.', '').split('.')[0].title()
                else:
                    job_data['company'] = 'Company'
            if not job_data.get('description') or (isinstance(job_data.get('description'), str) and not job_data['description'].strip()):
                job_data['description'] = truncated_text[:500].strip() or 'Job description not extracted. Please add details.'

            # Validate and clean data
            # 1. Ensure required fields exist and are not empty
            required_fields = ['title', 'company', 'description']
            for field in required_fields:
                value = job_data.get(field)
                if not value or (isinstance(value, str) and not value.strip()):
                    raise ValueError(f"AI failed to extract required field: {field}")
                # Clean string fields
                if isinstance(value, str):
                    job_data[field] = value.strip()

            # 2. Validate and normalize optional fields
            # Job type validation
            valid_job_types = ['full-time', 'part-time', 'contract', 'internship', 'temporary']
            if job_data.get('job_type') not in valid_job_types:
                job_data['job_type'] = 'full-time'

            # Experience level validation
            valid_exp_levels = ['entry', 'mid', 'senior', 'lead', 'executive']
            if job_data.get('experience_level') not in valid_exp_levels:
                job_data['experience_level'] = 'mid'

            # Salary validation (ensure numeric or null)
            for salary_field in ['salary_min', 'salary_max']:
                if job_data.get(salary_field):
                    try:
                        # Convert to int if it's a string
                        if isinstance(job_data[salary_field], str):
                            # Remove common formatting (commas, currency symbols)
                            clean_salary = re.sub(r'[^\d.]', '', job_data[salary_field])
                            job_data[salary_field] = int(float(clean_salary))
                        elif isinstance(job_data[salary_field], (int, float)):
                            job_data[salary_field] = int(job_data[salary_field])
                        else:
                            job_data[salary_field] = None
                    except (ValueError, TypeError):
                        job_data[salary_field] = None

            # Remote option validation (ensure boolean)
            remote = job_data.get('remote_option')
            if isinstance(remote, str):
                job_data['remote_option'] = remote.lower() in ['true', 'yes', '1', 'remote']
            elif not isinstance(remote, bool):
                job_data['remote_option'] = False

            # Array fields validation (ensure they're arrays of strings)
            array_fields = ['requirements', 'responsibilities', 'skills']
            for field in array_fields:
                value = job_data.get(field, [])
                if not isinstance(value, list):
                    job_data[field] = []
                else:
                    # Filter out empty strings and ensure all items are strings
                    job_data[field] = [
                        str(item).strip() 
                        for item in value 
                        if item and str(item).strip()
                    ][:20]  # Limit to 20 items max

            # 3. Set defaults for missing optional fields
            job_data.setdefault('location', 'Not specified')
            job_data.setdefault('job_type', 'full-time')
            job_data.setdefault('salary_min', None)
            job_data.setdefault('salary_max', None)
            job_data.setdefault('salary_currency', None)
            job_data.setdefault('requirements', [])
            job_data.setdefault('responsibilities', [])
            job_data.setdefault('skills', [])
            job_data.setdefault('experience_level', 'mid')
            job_data.setdefault('remote_option', False)

            # 4. Add metadata
            job_data['source'] = 'external'
            job_data['source_url'] = source_url

            # 5. Final validation
            if len(job_data['title']) < 3:
                raise ValueError("Job title is too short (minimum 3 characters)")
            if len(job_data['company']) < 2:
                raise ValueError("Company name is too short (minimum 2 characters)")
            if len(job_data['description']) < 20:
                raise ValueError("Job description is too short (minimum 20 characters)")

            logger.info(
                f"Successfully parsed external job: {job_data.get('title')} at {job_data.get('company')}",
                requirements_count=len(job_data.get('requirements', [])),
                skills_count=len(job_data.get('skills', [])),
                has_salary=bool(job_data.get('salary_max'))
            )

            return job_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"AI Response (first 500 chars): {response[:500]}")
            raise ValueError("AI failed to return valid JSON. Please try again or use 'From Text' with a cleaner description.")
        except ValueError as e:
            # Re-raise validation errors with original message
            logger.error(f"Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in AI job parsing: {e}", exc_info=True)
            raise ValueError(f"Failed to parse job posting: {str(e)}")


# Singleton instance
_parser = None

def get_job_parser() -> ExternalJobParser:
    """Get the singleton job parser instance."""
    global _parser
    if _parser is None:
        _parser = ExternalJobParser()
    return _parser

"""
Base Scraper Interface

Defines the common interface for all job board scrapers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class JobListing:
    """Standardized job listing data structure."""
    title: str
    company: str
    location: Optional[str]
    description: str
    job_link: str
    source: str
    source_id: Optional[str] = None
    posted_date: Optional[datetime] = None
    salary_range: Optional[str] = None
    job_type: Optional[str] = None  # 'full-time', 'contract', etc.
    remote_type: Optional[str] = None  # 'remote', 'hybrid', 'onsite'
    normalized_title: Optional[str] = None
    normalized_location: Optional[str] = None


class BaseScraper(ABC):
    """Base class for all job board scrapers."""
    
    def __init__(self, source_name: str):
        """
        Initialize scraper.
        
        Args:
            source_name: Name of the job board source
        """
        self.source_name = source_name
    
    @abstractmethod
    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs
    ) -> List[JobListing]:
        """
        Scrape jobs from the job board.
        
        Args:
            keywords: Search keywords
            location: Location filter (optional)
            max_results: Maximum number of results
            **kwargs: Additional source-specific parameters
            
        Returns:
            List[JobListing]: List of scraped job listings
        """
        pass
    
    @abstractmethod
    def normalize_job(self, job: JobListing) -> JobListing:
        """
        Normalize job data for consistency.
        
        Args:
            job: Raw job listing
            
        Returns:
            JobListing: Normalized job listing
        """
        pass
    
    def extract_salary(self, text: str) -> Optional[str]:
        """
        Extract salary range from text.
        
        Args:
            text: Text containing salary information
            
        Returns:
            str: Extracted salary range, or None
        """
        # Common salary patterns
        import re
        patterns = [
            r'\$(\d{1,3}(?:,\d{3})*(?:k|K)?)\s*-\s*\$(\d{1,3}(?:,\d{3})*(?:k|K)?)',
            r'(\d{1,3}(?:,\d{3})*(?:k|K)?)\s*-\s*(\d{1,3}(?:,\d{3})*(?:k|K)?)\s*(?:USD|usd|\$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        return None
    
    def extract_job_type(self, text: str) -> Optional[str]:
        """
        Extract job type from text.
        
        Args:
            text: Text containing job type information
            
        Returns:
            str: Job type ('full-time', 'contract', etc.)
        """
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['full-time', 'full time', 'permanent']):
            return 'full-time'
        elif any(word in text_lower for word in ['contract', 'contractor']):
            return 'contract'
        elif any(word in text_lower for word in ['part-time', 'part time']):
            return 'part-time'
        elif any(word in text_lower for word in ['freelance', 'freelancer']):
            return 'freelance'
        elif any(word in text_lower for word in ['internship', 'intern']):
            return 'internship'
        
        return None
    
    def extract_remote_type(self, text: str) -> Optional[str]:
        """
        Extract remote work type from text.
        
        Args:
            text: Text containing remote work information
            
        Returns:
            str: Remote type ('remote', 'hybrid', 'onsite')
        """
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['remote', 'work from home', 'wfh', 'distributed']):
            return 'remote'
        elif any(word in text_lower for word in ['hybrid', 'flexible', 'partially remote']):
            return 'hybrid'
        elif any(word in text_lower for word in ['onsite', 'on-site', 'on site', 'office']):
            return 'onsite'
        
        return None
    
    def normalize_title(self, title: str) -> str:
        """
        Normalize job title for consistency.
        
        Args:
            title: Raw job title
            
        Returns:
            str: Normalized job title
        """
        # Remove common prefixes/suffixes
        title = title.strip()
        
        # Remove location suffixes (e.g., "Software Engineer - San Francisco")
        if ' - ' in title:
            parts = title.split(' - ')
            # Keep the first part if it looks like a title
            if len(parts[0]) > 5:
                title = parts[0]
        
        # Remove common suffixes
        suffixes = [' - Remote', ' (Remote)', ' - Hybrid', ' (Hybrid)']
        for suffix in suffixes:
            if title.endswith(suffix):
                title = title[:-len(suffix)]
        
        return title.strip()
    
    def normalize_location(self, location: str) -> str:
        """
        Normalize location string.
        
        Args:
            location: Raw location string
            
        Returns:
            str: Normalized location
        """
        if not location:
            return ""
        
        location = location.strip()
        
        # Remove common prefixes
        prefixes = ['Location: ', '📍 ', '🌍 ']
        for prefix in prefixes:
            if location.startswith(prefix):
                location = location[len(prefix):]
        
        return location.strip()


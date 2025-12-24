"""
Job Scrapers Package

Contains scrapers for various job boards.
"""

from app.scrapers.base import BaseScraper, JobListing
from app.scrapers.remotive_scraper import RemotiveScraper
from app.scrapers.serpapi_scraper import SerpAPIScraper

__all__ = ["BaseScraper", "JobListing", "RemotiveScraper", "SerpAPIScraper"]


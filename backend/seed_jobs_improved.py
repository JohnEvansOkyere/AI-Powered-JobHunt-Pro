#!/usr/bin/env python3
"""
Improved Job Seeding Script

This script populates the database with initial jobs from available scrapers.
Uses simpler queries to avoid API errors.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any
import time

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.logging import get_logger, bind_request_context
from app.scrapers.remotive_scraper import RemotiveScraper
from app.scrapers.serpapi_scraper import SerpAPIScraper
from app.models.job import Job
from app.core.config import settings

logger = get_logger(__name__)


async def scrape_from_remotive_simple() -> List[Dict[str, Any]]:
    """
    Scrape jobs from Remotive with simple queries.

    Uses separate queries for different job categories to avoid overwhelming the API.
    """
    scraper = RemotiveScraper()
    all_jobs = []

    # Use simpler, separate queries
    queries = [
        ["python"],
        ["javascript"],
        ["developer"],
        ["engineer"],
    ]

    for keywords in queries:
        try:
            logger.info("remotive_query", keywords=keywords)
            jobs = await scraper.scrape(
                keywords=keywords,
                location="remote",
                max_results=50
            )
            all_jobs.extend(jobs)
            logger.info("remotive_query_success", keywords=keywords, jobs_found=len(jobs))

            # Small delay between requests
            await asyncio.sleep(1)

        except Exception as e:
            logger.error("remotive_query_failed", keywords=keywords, error=str(e))
            continue

    # Remove duplicates by job_link
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        job_link = job.get("job_link")
        if job_link and job_link not in seen:
            seen.add(job_link)
            unique_jobs.append(job)

    logger.info("remotive_complete", total_jobs=len(unique_jobs))
    return unique_jobs


async def scrape_from_serpapi_simple(location: str = "Ghana") -> List[Dict[str, Any]]:
    """
    Scrape jobs from SerpAPI with simple queries.
    """
    if not settings.SERPAPI_API_KEY:
        logger.warning("serpapi_key_missing")
        return []

    scraper = SerpAPIScraper()
    all_jobs = []

    # Use simpler, separate queries
    queries = [
        ["python developer"],
        ["software engineer"],
        ["data scientist"],
    ]

    for keywords in queries:
        try:
            logger.info("serpapi_query", keywords=keywords, location=location)
            jobs = await scraper.scrape(
                keywords=keywords,
                location=location,
                max_results=30
            )
            all_jobs.extend(jobs)
            logger.info("serpapi_query_success", keywords=keywords, jobs_found=len(jobs))

            # Delay between requests to respect rate limits
            await asyncio.sleep(2)

        except Exception as e:
            logger.error("serpapi_query_failed", keywords=keywords, error=str(e))
            continue

    # Remove duplicates by job_link
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        job_link = job.get("job_link")
        if job_link and job_link not in seen:
            seen.add(job_link)
            unique_jobs.append(job)

    logger.info("serpapi_complete", total_jobs=len(unique_jobs))
    return unique_jobs


def save_jobs_to_db(jobs: List[Dict[str, Any]], db: Session) -> int:
    """Save scraped jobs to database."""
    saved_count = 0
    skipped_count = 0

    for job_data in jobs:
        try:
            # Check if job already exists (by job_link)
            job_link = job_data.get("job_link")
            if not job_link:
                skipped_count += 1
                continue

            existing_job = db.query(Job).filter(Job.job_link == job_link).first()
            if existing_job:
                logger.debug("job_already_exists", job_link=job_link)
                skipped_count += 1
                continue

            # Create new job
            job = Job(
                title=job_data.get("title", "Unknown Title"),
                company=job_data.get("company", "Unknown Company"),
                location=job_data.get("location", "Remote"),
                description=job_data.get("description", ""),
                job_link=job_link,
                source=job_data.get("source", "unknown"),
                source_id=job_data.get("source_id"),
                job_type=job_data.get("job_type"),
                salary_min=job_data.get("salary_min"),
                salary_max=job_data.get("salary_max"),
                salary_currency=job_data.get("salary_currency"),
                posted_date=job_data.get("posted_date"),
                requirements=job_data.get("requirements", []),
                benefits=job_data.get("benefits", []),
                tags=job_data.get("tags", []),
                processing_status="pending"
            )

            db.add(job)
            saved_count += 1

        except Exception as e:
            logger.error("job_save_failed", error=str(e), job_title=job_data.get("title"))
            skipped_count += 1
            continue

    # Commit all jobs
    try:
        db.commit()
        logger.info("jobs_saved", saved=saved_count, skipped=skipped_count)
    except Exception as e:
        db.rollback()
        logger.error("db_commit_failed", error=str(e))
        raise

    return saved_count


async def seed_jobs():
    """Seed jobs from available scrapers."""
    bind_request_context(operation="job_seeding_improved")

    logger.info("starting_improved_seeding")

    all_jobs = []

    # Try Remotive first (no API key needed)
    print("🔄 Scraping from Remotive (multiple queries)...")
    try:
        remotive_jobs = await scrape_from_remotive_simple()
        all_jobs.extend(remotive_jobs)
        print(f"   ✅ Remotive: {len(remotive_jobs)} unique jobs")
    except Exception as e:
        print(f"   ❌ Remotive failed: {e}")
        logger.error("remotive_failed", error=str(e))

    # Try SerpAPI if key is available
    if settings.SERPAPI_API_KEY:
        print("\n🔄 Scraping from SerpAPI (multiple queries)...")
        try:
            serpapi_jobs = await scrape_from_serpapi_simple(location="Ghana")
            all_jobs.extend(serpapi_jobs)
            print(f"   ✅ SerpAPI: {len(serpapi_jobs)} unique jobs")
        except Exception as e:
            print(f"   ❌ SerpAPI failed: {e}")
            logger.error("serpapi_failed", error=str(e))
    else:
        print("\nℹ️  SerpAPI key not configured, skipping")

    logger.info("total_jobs_scraped", count=len(all_jobs))

    if len(all_jobs) == 0:
        print("\n⚠️  No jobs scraped. Both scrapers failed.")
        print("\nTroubleshooting:")
        print("1. Check internet connection")
        print("2. Remotive might be rate limiting - try again in a few minutes")
        print("3. Verify SERPAPI_API_KEY is correct in .env")
        return 0

    # Save to database
    print(f"\n💾 Saving {len(all_jobs)} jobs to database...")
    db = SessionLocal()
    try:
        saved_count = save_jobs_to_db(all_jobs, db)
        logger.info("seeding_complete", jobs_saved=saved_count)
        return saved_count
    finally:
        db.close()


async def main():
    """Main entry point."""
    print("=" * 70)
    print("Improved Job Seeding Script")
    print("=" * 70)
    print()

    # Check database connection
    try:
        db = SessionLocal()
        existing_jobs_count = db.query(Job).count()
        db.close()

        print(f"📊 Current jobs in database: {existing_jobs_count}")
        print()

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Please check your DATABASE_URL in .env file")
        return

    # Start seeding
    try:
        saved_count = await seed_jobs()

        print()
        print("=" * 70)
        if saved_count > 0:
            print(f"✅ SUCCESS! Saved {saved_count} new jobs to database")
        else:
            print(f"⚠️  No new jobs saved (scrapers failed or all jobs already exist)")
        print("=" * 70)
        print()

        if saved_count > 0:
            print("Next steps:")
            print("1. Jobs are ready in the database!")
            print("2. Visit http://localhost:3000/dashboard/jobs")
            print("3. Jobs will be automatically matched to user profiles")
        else:
            print("Troubleshooting:")
            print("1. Wait a few minutes and try again (rate limiting)")
            print("2. Check if jobs already exist: SELECT COUNT(*) FROM jobs;")
            print("3. Try manual scraping via API endpoint")
        print()

    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ ERROR: {e}")
        print("=" * 70)
        logger.error("seeding_failed", error=str(e), exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())

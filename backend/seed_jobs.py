#!/usr/bin/env python3
"""
Job Seeding Script

This script populates the database with initial jobs from available scrapers.
Use this to seed the database on fresh installation or when jobs table is empty.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.core.logging import get_logger, bind_request_context
from app.scrapers.remotive_scraper import RemotiveScraper
from app.scrapers.serpapi_scraper import SerpAPIScraper
from app.models.job import Job
from app.core.config import settings

logger = get_logger(__name__)


async def scrape_from_remotive(
    keywords: List[str],
    max_results: int = 100
) -> List[Dict[str, Any]]:
    """
    Scrape jobs from Remotive (no API key needed).

    Args:
        keywords: Search keywords
        max_results: Maximum jobs to fetch

    Returns:
        List of job data dictionaries
    """
    logger.info("scraping_remotive", keywords=keywords, max_results=max_results)

    scraper = RemotiveScraper()
    jobs = await scraper.scrape(
        keywords=keywords,
        location="remote",
        max_results=max_results
    )

    logger.info("remotive_scrape_complete", jobs_found=len(jobs))
    return jobs


async def scrape_from_serpapi(
    keywords: List[str],
    location: str = "remote",
    max_results: int = 50
) -> List[Dict[str, Any]]:
    """
    Scrape jobs from SerpAPI (requires API key).

    Args:
        keywords: Search keywords
        location: Job location
        max_results: Maximum jobs to fetch

    Returns:
        List of job data dictionaries
    """
    if not settings.SERPAPI_API_KEY:
        logger.warning("serpapi_key_missing", message="SERPAPI_API_KEY not set, skipping SerpAPI")
        return []

    logger.info("scraping_serpapi", keywords=keywords, location=location, max_results=max_results)

    scraper = SerpAPIScraper()
    jobs = await scraper.scrape(
        keywords=keywords,
        location=location,
        max_results=max_results
    )

    logger.info("serpapi_scrape_complete", jobs_found=len(jobs))
    return jobs


def save_jobs_to_db(jobs: List[Dict[str, Any]], db: Session) -> int:
    """
    Save scraped jobs to database.

    Args:
        jobs: List of job data dictionaries
        db: Database session

    Returns:
        Number of jobs saved
    """
    saved_count = 0
    skipped_count = 0

    for job_data in jobs:
        try:
            # Check if job already exists (by job_link)
            job_link = job_data.get("job_link")
            if not job_link:
                logger.warning("job_missing_link", title=job_data.get("title"))
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


async def seed_jobs(
    sources: List[str] = None,
    keywords: List[str] = None,
    location: str = "remote",
    max_results_per_source: int = 100
):
    """
    Seed jobs from specified sources.

    Args:
        sources: List of sources to scrape from ['remotive', 'serpapi']
        keywords: Search keywords
        location: Job location
        max_results_per_source: Max results per source
    """
    # Default sources
    if sources is None:
        sources = ["remotive"]
        if settings.SERPAPI_API_KEY:
            sources.append("serpapi")

    # Default keywords
    if keywords is None:
        keywords = [
            "python", "developer", "engineer", "data scientist",
            "software engineer", "backend", "frontend", "fullstack"
        ]

    bind_request_context(operation="job_seeding")

    logger.info(
        "starting_job_seeding",
        sources=sources,
        keywords=keywords,
        location=location,
        max_results_per_source=max_results_per_source
    )

    all_jobs = []

    # Scrape from each source
    for source in sources:
        if source == "remotive":
            jobs = await scrape_from_remotive(keywords, max_results_per_source)
            all_jobs.extend(jobs)

        elif source == "serpapi":
            jobs = await scrape_from_serpapi(keywords, location, max_results_per_source)
            all_jobs.extend(jobs)

        else:
            logger.warning("unknown_source", source=source)

    logger.info("total_jobs_scraped", count=len(all_jobs))

    # Save to database
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
    print("Job Seeding Script")
    print("=" * 70)
    print()

    # Check database connection
    try:
        db = SessionLocal()
        existing_jobs_count = db.query(Job).count()
        db.close()

        print(f"📊 Current jobs in database: {existing_jobs_count}")
        print()

        if existing_jobs_count > 0:
            response = input(f"⚠️  Database already has {existing_jobs_count} jobs. Continue anyway? (y/n): ")
            if response.lower() != 'y':
                print("❌ Seeding cancelled.")
                return
            print()

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Please check your DATABASE_URL in .env file")
        return

    # Determine sources
    sources = ["remotive"]
    if settings.SERPAPI_API_KEY:
        sources.append("serpapi")
        print(f"✅ SerpAPI key found - will use both Remotive and SerpAPI")
    else:
        print(f"ℹ️  No SerpAPI key - will use Remotive only")
        print(f"   To enable SerpAPI, add SERPAPI_API_KEY to .env")

    print()
    print(f"🔄 Scraping from: {', '.join(sources)}")
    print(f"🔍 Keywords: python, developer, engineer, data scientist, etc.")
    print(f"📍 Location: remote")
    print(f"📊 Max per source: 100")
    print()

    # Seed jobs
    try:
        saved_count = await seed_jobs(
            sources=sources,
            keywords=[
                "python", "developer", "engineer", "data scientist",
                "software engineer", "backend", "frontend", "fullstack",
                "machine learning", "AI", "devops"
            ],
            location="remote",
            max_results_per_source=100
        )

        print()
        print("=" * 70)
        print(f"✅ SUCCESS! Saved {saved_count} new jobs to database")
        print("=" * 70)
        print()
        print("Next steps:")
        print("1. Start the backend: uvicorn app.main:app --reload")
        print("2. Visit the jobs page in your frontend")
        print("3. Jobs will be automatically matched to user profiles")
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

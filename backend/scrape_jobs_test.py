"""
Test script to scrape jobs without date restrictions.
This bypasses the 2-day filter to get any available jobs for testing.

Usage:
    cd backend
    python scrape_jobs_test.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.services.job_scraper_service import JobScraperService


async def main():
    """Scrape jobs without date restrictions for testing."""
    print("=" * 80)
    print("🚀 TEST JOB SCRAPING (No Date Filter)")
    print("=" * 80)
    print()
    print("This will scrape ANY available jobs from RemoteOK")
    print("(Ignoring the 2-day posted date filter)")
    print()

    db = SessionLocal()
    scraper = JobScraperService()

    try:
        # Scrape from RemoteOK only (most reliable free source)
        result = await scraper.scrape_jobs(
            sources=["remoteok"],
            keywords=["software engineer", "python developer", "react developer", "backend developer"],
            location="Worldwide",
            max_results_per_source=50,
            db=db,
            min_posted_date=None  # No date filter - get any jobs
        )

        print()
        print("=" * 80)
        print("✅ SCRAPING COMPLETED")
        print("=" * 80)
        print()
        print(f"📊 Results:")
        print(f"   - Total jobs found: {result.get('total_found', 0)}")
        print(f"   - New jobs stored: {result.get('stored', 0)}")
        print(f"   - Duplicates skipped: {result.get('duplicates', 0)}")
        print(f"   - Failed: {result.get('failed', 0)}")
        print()

        if result.get('stored', 0) > 0:
            print("✅ Jobs are now in the database!")
            print()
            print("Next steps:")
            print("   1. Check database: python check_database.py")
            print("   2. Generate recommendations: python generate_recommendations.py")
        else:
            print("⚠️  No new jobs were stored.")
            print()
            print("Trying alternative approach - direct RemoteOK scrape...")

            # Try alternative direct scrape
            from app.scrapers.remoteok_scraper import RemoteOKScraper
            from datetime import datetime, timezone as tz

            remoteok = RemoteOKScraper()
            jobs = remoteok.scrape(
                keywords=["developer"],
                location="",
                max_results=50
            )

            print(f"   Found {len(jobs)} jobs from RemoteOK")

            if jobs:
                # Store jobs manually
                from app.models.job import Job
                stored = 0

                for job_data in jobs[:20]:  # Store first 20
                    try:
                        job = Job(
                            title=job_data.get('title', 'Unknown'),
                            company=job_data.get('company', 'Unknown'),
                            location=job_data.get('location', 'Remote'),
                            description=job_data.get('description', ''),
                            job_link=job_data.get('job_link', ''),
                            source='remoteok',
                            source_id=job_data.get('source_id', ''),
                            scraped_at=datetime.now(tz.utc),
                            posted_date=job_data.get('posted_date')
                        )
                        db.add(job)
                        stored += 1
                    except Exception as e:
                        print(f"   ⚠️  Failed to store job: {e}")
                        continue

                db.commit()
                print(f"   ✅ Stored {stored} jobs!")
                print()
                print("Next steps:")
                print("   1. Check database: python check_database.py")
                print("   2. Generate recommendations: python generate_recommendations.py")

        print("=" * 80)

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ ERROR OCCURRED")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

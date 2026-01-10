"""
Scrape jobs posted within the last 5 days.
This gives a wider window than the default 2 days.

Usage:
    cd backend
    python scrape_jobs_5days.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.services.job_scraper_service import JobScraperService


async def main():
    """Scrape jobs from last 5 days."""
    print("=" * 80)
    print("🚀 JOB SCRAPING (Last 5 Days)")
    print("=" * 80)
    print()

    db = SessionLocal()
    scraper = JobScraperService()

    try:
        # Calculate 5 days ago
        min_date = datetime.now(timezone.utc) - timedelta(days=5)

        print(f"Scraping jobs posted after: {min_date.strftime('%Y-%m-%d %H:%M')} UTC")
        print("Sources: RemoteOK (most reliable free source)")
        print("Expected time: 1-2 minutes")
        print()

        # Scrape from RemoteOK with 5-day window
        result = await scraper.scrape_jobs(
            sources=["remoteok"],
            keywords=[
                "software engineer", "developer", "python", "react",
                "backend", "frontend", "full stack", "devops"
            ],
            location="Worldwide",
            max_results_per_source=100,
            db=db,
            min_posted_date=min_date  # 5 days ago
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
            print("   3. Test in frontend: Jobs page → 'Recommended for You' tab")
        else:
            print("⚠️  No new jobs stored from last 5 days.")
            print()
            print("Let me try getting ANY available jobs for testing...")
            print()

            # Fallback: Get any jobs without date filter
            from app.scrapers.remoteok_scraper import RemoteOKScraper

            remoteok = RemoteOKScraper()
            print("Fetching jobs from RemoteOK (no date filter)...")

            jobs = await remoteok.scrape(
                keywords=["developer"],
                location="",
                max_results=50
            )

            print(f"Found {len(jobs)} jobs")
            print()

            if jobs:
                from app.models.job import Job

                stored = 0
                for job_data in jobs[:30]:  # Store first 30
                    try:
                        # Check if already exists
                        exists = db.query(Job).filter(
                            Job.source_id == job_data.get('source_id')
                        ).first()

                        if exists:
                            continue

                        job = Job(
                            title=job_data.get('title', 'Unknown'),
                            company=job_data.get('company', 'Unknown'),
                            location=job_data.get('location', 'Remote'),
                            description=job_data.get('description', ''),
                            job_link=job_data.get('job_link', ''),
                            source='remoteok',
                            source_id=job_data.get('source_id', ''),
                            scraped_at=datetime.now(timezone.utc),
                            posted_date=job_data.get('posted_date')
                        )
                        db.add(job)
                        stored += 1
                    except Exception as e:
                        continue

                if stored > 0:
                    db.commit()
                    print(f"✅ Stored {stored} jobs!")
                    print()
                    print("Next steps:")
                    print("   1. Check database: python check_database.py")
                    print("   2. Generate recommendations: python generate_recommendations.py")
                else:
                    print("⚠️  All jobs were duplicates")

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

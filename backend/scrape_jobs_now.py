"""
Manual script to trigger job scraping immediately.

This bypasses the scheduler and scrapes jobs right now.
Useful for testing or getting fresh jobs on-demand.

Usage:
    cd backend
    python scrape_jobs_now.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.scheduler.job_scheduler import JobScraperScheduler


async def main():
    """Manually trigger job scraping."""
    print("=" * 80)
    print("🚀 MANUAL JOB SCRAPING")
    print("=" * 80)
    print()
    print("Starting job scraper...")
    print("This will scrape jobs from free sources (Remotive, RemoteOK, Adzuna)")
    print("Expected time: 1-3 minutes")
    print()

    scheduler = JobScraperScheduler()

    try:
        # Trigger manual scrape
        result = await scheduler.scrape_recent_jobs()

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
            print("✅ Fresh jobs are now in the database!")
            print()
            print("Next step: Generate recommendations")
            print("   Command: python generate_recommendations.py")
        else:
            print("⚠️  No new jobs were stored.")
            print("   Possible reasons:")
            print("   - All found jobs were duplicates")
            print("   - No jobs matched the search criteria")
            print("   - Sources returned no results")

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


if __name__ == "__main__":
    asyncio.run(main())

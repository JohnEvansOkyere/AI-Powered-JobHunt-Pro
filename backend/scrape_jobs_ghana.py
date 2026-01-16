"""
Manual script to scrape jobs for Ghana - NO DATE FILTER for initial seeding.

This script scrapes jobs without filtering by posted date, useful for
populating an empty database or getting a wider range of jobs.

Usage:
    cd backend
    python scrape_jobs_ghana.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.services.job_scraper_service import JobScraperService

# Tech job keywords covering all tech roles
TECH_KEYWORDS = [
    # Software Engineering
    "software engineer", "software developer", "backend engineer",
    "backend developer", "frontend engineer", "frontend developer",
    "full stack developer", "full stack engineer", "web developer",
    "mobile developer", "ios developer", "android developer",
    "react developer", "python developer", "java developer",
    "node developer", ".net developer", "golang developer",
    
    # Data & AI
    "data scientist", "data analyst", "data engineer",
    "machine learning engineer", "ai engineer", "ml engineer",
    
    # DevOps & Infrastructure
    "devops engineer", "site reliability engineer", "sre",
    "cloud engineer", "aws engineer", "systems engineer",
]


async def main():
    """Scrape jobs for Ghana without date filtering."""
    print("=" * 80)
    print("🚀 JOB SCRAPING FOR GHANA (NO DATE FILTER)")
    print("=" * 80)
    print()
    print("This will scrape jobs from:")
    print("  - Remotive (remote jobs worldwide)")
    print("  - RemoteOK (remote tech jobs)")
    print("  - Adzuna (Ghana-specific jobs)")
    print()
    print("⚠️  NOTE: No date filter - will include older jobs for initial seeding")
    print("Expected time: 2-5 minutes")
    print()

    db = SessionLocal()
    scraper = JobScraperService()

    try:
        # Scrape from multiple sources WITHOUT date filter
        # Try multiple sources: free APIs + Ghana-specific
        sources = ["remotive", "remoteok", "adzuna", "joinrise"]
        
        print(f"Scraping from: {', '.join(sources)}")
        print(f"Location: Ghana (where applicable)")
        print(f"Keywords: {len(TECH_KEYWORDS)} tech job categories")
        print()
        
        result = await scraper.scrape_jobs(
            sources=sources,
            keywords=TECH_KEYWORDS,
            location="Ghana",  # Focus on Ghana for Adzuna/Joinrise
            max_results_per_source=100,
            db=db,
            min_posted_date=None  # NO DATE FILTER - include all jobs
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
            print("Next step: Generate recommendations")
            print("   Command: python generate_recommendations.py")
        else:
            print("⚠️  No new jobs were stored.")
            print()
            print("Possible reasons:")
            print("   - All found jobs were duplicates")
            print("   - Sources returned no results")
            print("   - Network/API issues")
            print()
            print("Try again in a few minutes, or check your internet connection.")

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

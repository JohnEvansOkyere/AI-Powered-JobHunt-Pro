#!/usr/bin/env python3
"""
Script to manually run job scraping and recommendation generation.

Usage:
    # Run from backend directory:
    cd backend
    python scripts/run_scrape_and_recommend.py

    # Or with options:
    python scripts/run_scrape_and_recommend.py --scrape-only
    python scripts/run_scrape_and_recommend.py --recommend-only
    python scripts/run_scrape_and_recommend.py --user-id <user_uuid>
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.core.config import settings
from app.services.job_scraper_service import JobScraperService
from app.services.recommendation_generator import RecommendationGenerator
from app.core.logging import get_logger

logger = get_logger(__name__)


# Import keywords from scheduler to keep them in sync
from app.scheduler.job_scheduler import TECH_JOB_KEYWORDS


async def run_scraping(db, sources: list = None, max_per_source: int = 100):
    """Run job scraping from all available sources."""
    print("\n" + "=" * 70)
    print("🚀 STARTING JOB SCRAPING")
    print(f"⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 70)

    scraper_service = JobScraperService()

    # Default to all FREE sources (no API key required)
    # Note: HiringCafe removed - API not publicly available (returns 429)
    # Note: Adzuna requires free API credentials
    if sources is None:
        sources = [
            "remotive",     # FREE - Remote jobs
            "remoteok",     # FREE - Remote jobs
            "joinrise",     # FREE - Ghana + global
            "arbeitnow",    # FREE - Remote tech jobs
        ]

        # Add API-key sources if configured
        if getattr(settings, 'JOOBLE_API_KEY', None) and settings.JOOBLE_API_KEY.strip():
            sources.append("jooble")
            print("✅ Jooble API key found - including Jooble")

        if getattr(settings, 'FINDWORK_API_KEY', None) and settings.FINDWORK_API_KEY.strip():
            sources.append("findwork")
            print("✅ FindWork API key found - including FindWork")

        if getattr(settings, 'SERPAPI_API_KEY', None) and settings.SERPAPI_API_KEY.strip():
            sources.append("serpapi")
            print("✅ SerpAPI key found - including SerpAPI")

        if getattr(settings, 'ADZUNA_APP_ID', None) and settings.ADZUNA_APP_ID.strip() and \
           getattr(settings, 'ADZUNA_APP_KEY', None) and settings.ADZUNA_APP_KEY.strip():
            sources.append("adzuna")
            print("✅ Adzuna API keys found - including Adzuna")

    print(f"\n📡 Sources to scrape: {', '.join(sources)}")
    print(f"🔑 Keywords: {len(TECH_JOB_KEYWORDS)} tech job categories")
    print(f"📊 Max per source: {max_per_source}")

    # Calculate cutoff date (3 days ago)
    cutoff_date = datetime.utcnow() - timedelta(days=3)
    print(f"📅 Filtering jobs posted after: {cutoff_date.strftime('%Y-%m-%d')}")

    try:
        result = await scraper_service.scrape_jobs(
            sources=sources,
            keywords=TECH_JOB_KEYWORDS,
            location="Worldwide",
            max_results_per_source=max_per_source,
            db=db,
            min_posted_date=cutoff_date
        )

        print("\n" + "=" * 70)
        print("✅ SCRAPING COMPLETED")
        print("=" * 70)
        print(f"📊 Results:")
        print(f"   - Total jobs found: {result.get('total_found', 0)}")
        print(f"   - New jobs stored: {result.get('stored', 0)}")
        print(f"   - Duplicates skipped: {result.get('duplicates', 0)}")
        print("=" * 70)

        return result

    except Exception as e:
        print(f"\n❌ Scraping failed: {e}")
        logger.error(f"Scraping failed: {e}", exc_info=True)
        return None


async def run_recommendations(db, user_id: str = None):
    """Generate recommendations for users."""
    print("\n" + "=" * 70)
    print("🎯 STARTING RECOMMENDATION GENERATION")
    print(f"⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 70)

    try:
        generator = RecommendationGenerator(db)

        if user_id:
            # Generate for specific user
            print(f"👤 Generating recommendations for user: {user_id}")
            count = await generator.generate_recommendations_for_user(user_id)
            print(f"\n✅ Generated {count} recommendations for user {user_id}")
            return {"user_id": user_id, "recommendations": count}
        else:
            # Generate for all users
            print("👥 Generating recommendations for ALL eligible users...")
            stats = await generator.generate_recommendations_for_all_users()

            print("\n" + "=" * 70)
            print("✅ RECOMMENDATION GENERATION COMPLETED")
            print("=" * 70)
            print(f"📊 Results:")
            print(f"   - Total users processed: {stats.get('total_users', 0)}")
            print(f"   - Successful: {stats.get('successful', 0)}")
            print(f"   - Failed: {stats.get('failed', 0)}")
            print(f"   - Total recommendations: {stats.get('total_recommendations', 0)}")
            print("=" * 70)

            return stats

    except Exception as e:
        print(f"\n❌ Recommendation generation failed: {e}")
        logger.error(f"Recommendation generation failed: {e}", exc_info=True)
        return None


async def main():
    parser = argparse.ArgumentParser(
        description="Run job scraping and/or recommendation generation"
    )
    parser.add_argument(
        "--scrape-only",
        action="store_true",
        help="Only run scraping, skip recommendations"
    )
    parser.add_argument(
        "--recommend-only",
        action="store_true",
        help="Only run recommendations, skip scraping"
    )
    parser.add_argument(
        "--user-id",
        type=str,
        help="Generate recommendations for a specific user ID"
    )
    parser.add_argument(
        "--max-per-source",
        type=int,
        default=100,
        help="Maximum jobs to scrape per source (default: 100)"
    )
    parser.add_argument(
        "--sources",
        type=str,
        help="Comma-separated list of sources (e.g., 'remotive,remoteok,adzuna')"
    )

    args = parser.parse_args()

    # Parse sources if provided
    sources = None
    if args.sources:
        sources = [s.strip() for s in args.sources.split(",")]

    print("\n" + "=" * 70)
    print("🔧 JOB SCRAPING & RECOMMENDATION SCRIPT")
    print("=" * 70)
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Database: {settings.DATABASE_URL[:50]}...")

    # Check OpenAI key for recommendations
    if not args.scrape_only:
        if not getattr(settings, 'OPENAI_API_KEY', None) or not settings.OPENAI_API_KEY.strip():
            print("\n⚠️  WARNING: OPENAI_API_KEY not set - recommendations will fail!")
            if not args.recommend_only:
                print("   Continuing with scraping only...")
                args.scrape_only = True

    db = SessionLocal()

    try:
        # Run scraping
        if not args.recommend_only:
            await run_scraping(db, sources=sources, max_per_source=args.max_per_source)

        # Run recommendations
        if not args.scrape_only:
            await run_recommendations(db, user_id=args.user_id)

        print("\n" + "=" * 70)
        print("✅ ALL TASKS COMPLETED")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Script failed: {e}")
        logger.error(f"Script failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

"""
Manual script to generate recommendations for all users.

Usage:
    cd backend
    python generate_recommendations.py

This script:
- Generates job recommendations for all users with CVs
- Uses the same logic as the daily scheduler
- Useful for initial population or manual refresh
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.services.recommendation_generator import RecommendationGenerator


async def main():
    """Generate recommendations for all users."""
    print("=" * 80)
    print("🎯 MANUAL RECOMMENDATION GENERATION")
    print("=" * 80)
    print()

    db = SessionLocal()

    try:
        generator = RecommendationGenerator(db)

        print("Starting recommendation generation for all users...")
        print("This may take a few seconds depending on the number of users and jobs.")
        print()

        stats = await generator.generate_recommendations_for_all_users()

        print()
        print("=" * 80)
        print("✅ GENERATION COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"   Users with CVs: {stats['total_users']}")
        print(f"   Successfully processed: {stats['successful']}")
        print(f"   Failed: {stats['failed']}")
        print(f"   Total recommendations created: {stats['total_recommendations']}")
        print()

        if stats['total_recommendations'] > 0:
            avg_per_user = stats['total_recommendations'] / max(stats['successful'], 1)
            print(f"   Average recommendations per user: {avg_per_user:.1f}")

        print("=" * 80)
        print()

        if stats['failed'] > 0:
            print("⚠️  Some users failed. Check backend logs for details.")

        if stats['total_recommendations'] == 0:
            print("⚠️  No recommendations created. Possible reasons:")
            print("   - No users have uploaded CVs")
            print("   - No jobs in database (run job scraper first)")
            print("   - Check backend logs for errors")
        else:
            print("✅ Recommendations are now available!")
            print("   Go to Jobs page → 'Recommended for You' tab")

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ ERROR OCCURRED")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        print("Full traceback:")
        import traceback
        traceback.print_exc()
        print()
        print("Troubleshooting:")
        print("1. Ensure database is accessible")
        print("2. Check OpenAI API key in .env")
        print("3. Verify users have CVs uploaded")
        print("4. Check that jobs exist in database")

    finally:
        db.close()
        print()


if __name__ == "__main__":
    asyncio.run(main())

"""
Manual script to trigger job scraping immediately.

After the Phase 2 scheduler migration the logic lives in the Celery task
`scheduler.scrape_recent_jobs`. This script runs that task inline (no broker,
no worker) so developers can scrape on demand without Redis.

Usage:
    cd backend
    python scrape_jobs_now.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.tasks.periodic_tasks import scrape_recent_jobs


def main() -> None:
    print("=" * 80)
    print("🚀 MANUAL JOB SCRAPING")
    print("=" * 80)
    print()
    print("Running `scheduler.scrape_recent_jobs` inline...")
    print("This will scrape jobs from all configured sources.")
    print("Expected time: 1–3 minutes")
    print()

    try:
        result = scrape_recent_jobs.run()
    except Exception as exc:  # pragma: no cover - manual diagnostic
        print("=" * 80)
        print("❌ ERROR OCCURRED")
        print("=" * 80)
        print(f"Error: {exc}")
        import traceback

        traceback.print_exc()
        return

    print()
    print("=" * 80)
    print("✅ SCRAPING COMPLETED")
    print("=" * 80)
    print()
    print("📊 Results:")
    print(f"   - Total jobs found: {result.get('total_found', 0)}")
    print(f"   - New jobs stored: {result.get('stored', 0)}")
    print(f"   - Duplicates skipped: {result.get('duplicates', 0)}")
    print(f"   - Failed: {result.get('failed', 0)}")
    print()

    if result.get("stored", 0) > 0:
        print("✅ Fresh jobs are now in the database.")
        print("Next step: python generate_recommendations.py")
    else:
        print("⚠️  No new jobs stored — likely all duplicates or no matches.")

    print("=" * 80)


if __name__ == "__main__":
    main()

"""
Quick database diagnostic script.
Checks if you have users, CVs, and jobs in the database.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models.cv import CV
from app.models.job import Job
from sqlalchemy import func
from datetime import timezone


def main():
    print("=" * 80)
    print("📊 DATABASE DIAGNOSTIC")
    print("=" * 80)
    print()

    db = SessionLocal()

    try:
        # Check CVs
        cv_count = db.query(CV).count()
        print(f"✓ CVs in database: {cv_count}")

        if cv_count > 0:
            # Show unique users with CVs
            users_with_cvs = db.query(CV.user_id).distinct().count()
            print(f"  → Unique users with CVs: {users_with_cvs}")

            # Show sample CV
            sample_cv = db.query(CV).first()
            print(f"  → Sample CV user_id: {sample_cv.user_id}")
        else:
            print("  ⚠️  NO CVs FOUND - You need to upload a CV first!")
            print("     Go to: Profile → Upload CV")

        print()

        # Check Jobs
        job_count = db.query(Job).count()
        print(f"✓ Jobs in database: {job_count}")

        if job_count > 0:
            # Show recent jobs (last 7 days)
            from datetime import datetime, timedelta
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            recent_jobs = db.query(Job).filter(Job.scraped_at >= cutoff).count()
            print(f"  → Jobs from last 7 days: {recent_jobs}")

            if recent_jobs == 0:
                print("  ⚠️  No recent jobs! Recommendation generation uses jobs from last 7 days.")

            # Show sample job
            sample_job = db.query(Job).first()
            print(f"  → Sample job: {sample_job.title} at {sample_job.company}")
        else:
            print("  ⚠️  NO JOBS FOUND - You need to scrape jobs first!")
            print("     The scheduler will scrape at 6 AM UTC, or run manual scrape.")

        print()
        print("=" * 80)
        print("DIAGNOSIS:")
        print("=" * 80)

        if cv_count == 0:
            print("❌ MISSING: No CVs uploaded")
            print("   → Upload a CV at: Profile → Upload CV")
            print()

        if job_count == 0:
            print("❌ MISSING: No jobs in database")
            print("   → Wait for scheduler (6 AM UTC) OR manually trigger scraping")
            print()

        if cv_count > 0 and job_count > 0:
            from datetime import datetime, timedelta
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            recent_jobs = db.query(Job).filter(Job.scraped_at >= cutoff).count()

            if recent_jobs == 0:
                print("⚠️  ISSUE: Jobs exist but none from last 7 days")
                print("   → Recommendation generator only uses recent jobs")
                print("   → Run job scraper to get fresh jobs")
                print()
            else:
                print("✅ ALL READY: You have CVs and recent jobs!")
                print("   → You can now generate recommendations")
                print()
                print("Run:")
                print("   python generate_recommendations.py")

        print("=" * 80)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()

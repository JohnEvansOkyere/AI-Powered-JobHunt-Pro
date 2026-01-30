"""
Manual script to delete jobs older than 7 days.

This is useful for:
- Initial cleanup of old jobs
- Testing the auto-cleanup feature
- Manual database maintenance

Usage:
    cd backend
    python cleanup_old_jobs.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models.job import Job
from app.models.application import Application


def main():
    """Delete jobs older than 7 days."""
    print("=" * 80)
    print("🧹 MANUAL CLEANUP: Old Jobs (>7 days)")
    print("=" * 80)
    print()

    db = SessionLocal()

    try:
        # Calculate cutoff date (7 days ago)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
        print(f"📅 Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"   Jobs scraped before this date will be deleted")
        print(f"   (Skipping jobs with saved/applied applications)")
        print(f"   (Skipping user-added external jobs - only scraped jobs are deleted)")
        print()

        # Find old scraped jobs only (never delete user-added external jobs)
        old_jobs = db.query(Job).filter(
            Job.scraped_at < cutoff_date,
            Job.source != "external",
        ).all()

        # Filter out jobs that have applications
        jobs_with_apps = []
        jobs_to_delete = []

        for job in old_jobs:
            has_apps = db.query(Application).filter(
                Application.job_id == job.id
            ).count() > 0

            if has_apps:
                jobs_with_apps.append(job)
            else:
                jobs_to_delete.append(job)

        if not jobs_to_delete:
            if not old_jobs:
                print("✅ No old jobs found! Database is already clean.")
            else:
                print(f"⚠️  Found {len(old_jobs)} old jobs, but all have applications")
                print("   Cannot delete jobs with saved/applied applications")
                print(f"   Jobs with applications: {len(jobs_with_apps)}")

            print()

            # Show current job count
            total_jobs = db.query(Job).count()
            print(f"💾 Total jobs in database: {total_jobs}")

            if total_jobs > 0:
                recent_jobs = db.query(Job).filter(
                    Job.scraped_at >= cutoff_date
                ).count()
                print(f"   - Recent jobs (last 7 days): {recent_jobs}")

            return

        # Show summary
        print(f"📊 Old jobs summary:")
        print(f"   - Total old jobs: {len(old_jobs)}")
        print(f"   - Safe to delete: {len(jobs_to_delete)}")
        print(f"   - Has applications (skipped): {len(jobs_with_apps)}")
        print()

        # Show what will be deleted
        print(f"⚠️  Will delete {len(jobs_to_delete)} old jobs:")
        print()

        # Show first 5 as examples
        print("   Sample jobs to be deleted:")
        for i, job in enumerate(jobs_to_delete[:5], 1):
            days_old = (datetime.now(timezone.utc) - job.scraped_at).days
            print(f"   {i}. {job.title} at {job.company}")
            print(f"      Scraped: {job.scraped_at.strftime('%Y-%m-%d')} ({days_old} days ago)")

        if len(jobs_to_delete) > 5:
            print(f"   ... and {len(jobs_to_delete) - 5} more")

        if jobs_with_apps:
            print()
            print(f"   ℹ️  Skipping {len(jobs_with_apps)} jobs with applications")

        print()

        # Confirm deletion
        response = input("⚠️  Delete these jobs? (yes/no): ").strip().lower()

        if response != 'yes':
            print("❌ Cleanup cancelled by user")
            return

        print()
        print("🗑️  Deleting old jobs...")

        # Delete old jobs (only those without applications)
        deleted_count = 0
        for job in jobs_to_delete:
            db.delete(job)
            deleted_count += 1

            # Show progress every 10 jobs
            if deleted_count % 10 == 0:
                print(f"   Deleted {deleted_count}/{len(jobs_to_delete)}...")

        db.commit()

        print()
        print("=" * 80)
        print("✅ CLEANUP COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"   Deleted: {deleted_count} old jobs")
        print()

        # Show remaining jobs
        remaining_jobs = db.query(Job).count()
        recent_jobs = db.query(Job).filter(
            Job.scraped_at >= cutoff_date
        ).count()

        print(f"💾 Database status:")
        print(f"   - Total jobs remaining: {remaining_jobs}")
        print(f"   - Recent jobs (last 7 days): {recent_jobs}")
        print()

        if remaining_jobs == 0:
            print("⚠️  No jobs left in database!")
            print("   You need to scrape fresh jobs:")
            print("   1. Wait for scheduler (6 AM UTC)")
            print("   2. Or manually trigger scraping via API/frontend")
        else:
            print("✅ Database is now clean and optimized!")
            print("   Only recent jobs remain for recommendations")

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
        db.rollback()

    finally:
        db.close()
        print()


if __name__ == "__main__":
    main()

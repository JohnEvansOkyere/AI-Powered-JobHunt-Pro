"""
Job Cleanup Script - Application-Aware

Smart cleanup strategy:
1. KEEP jobs that users have applied to (have applications)
2. DELETE jobs older than 7 days that have NO applications
3. Clean old job matches (cache) older than 90 days

This ensures:
- Users can track their applications forever
- Database stays lean by removing jobs nobody applied to
- Active applications are never lost

Run daily via cron.
"""

import sys
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

sys.path.insert(0, '/home/grejoy/Projects/AI-Powered-JobHunt-Pro/backend')

from app.core.database import get_db
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.application import Application
from app.core.logging import get_logger

logger = get_logger(__name__)


def delete_unapplied_old_jobs(db: Session, days_old: int = 7):
    """
    Delete jobs older than X days that have NO applications.

    Jobs with applications are KEPT forever so users can track their application history.

    Args:
        days_old: Number of days after which to delete unapplied jobs (default: 7)
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)

    # Find jobs older than cutoff that have NO applications
    jobs_to_delete = db.query(Job).filter(
        and_(
            Job.created_at < cutoff_date,
            ~Job.id.in_(
                db.query(Application.job_id).distinct()
            )
        )
    ).all()

    if jobs_to_delete:
        job_ids = [job.id for job in jobs_to_delete]

        # Delete associated matches first (foreign key constraint)
        deleted_matches = db.query(JobMatch).filter(
            JobMatch.job_id.in_(job_ids)
        ).delete(synchronize_session=False)

        # Delete jobs
        for job in jobs_to_delete:
            logger.info(
                f"Deleting unapplied job: {job.title} at {job.company} "
                f"(posted {job.created_at.strftime('%Y-%m-%d')})"
            )
            db.delete(job)

        db.commit()

        logger.info(
            f"✅ Deleted {len(jobs_to_delete)} unapplied jobs older than {days_old} days"
        )
        logger.info(f"   Also deleted {deleted_matches} associated job matches")

        print(f"✅ Deleted {len(jobs_to_delete)} unapplied jobs older than {days_old} days")
        print(f"   (Jobs with applications are kept for tracking)")

    else:
        logger.info(f"No unapplied jobs to delete (checked jobs older than {days_old} days)")
        print(f"No unapplied jobs to delete (checked jobs older than {days_old} days)")

    return len(jobs_to_delete)


def clean_old_matches(db: Session, days_to_keep: int = 90):
    """
    Delete very old job match cache to keep job_matches table lean.
    Keep only matches from last X days.

    Args:
        days_to_keep: Number of days of matches to keep (default: 90)
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

    old_matches = db.query(JobMatch).filter(
        JobMatch.created_at < cutoff_date
    ).delete(synchronize_session=False)

    db.commit()

    if old_matches > 0:
        logger.info(f"✅ Deleted {old_matches} job match cache entries older than {days_to_keep} days")
        print(f"✅ Deleted {old_matches} cached matches older than {days_to_keep} days")
    else:
        logger.info(f"No old match cache to delete (checked matches older than {days_to_keep} days)")
        print(f"No old cached matches to delete")

    return old_matches


def print_db_stats(db: Session):
    """Print database statistics."""
    total_jobs = db.query(Job).count()

    # Jobs with applications (kept forever)
    jobs_with_apps = db.query(Job).filter(
        Job.id.in_(db.query(Application.job_id).distinct())
    ).count()

    # Jobs without applications (will be deleted after 7 days)
    jobs_without_apps = total_jobs - jobs_with_apps

    # Count jobs by age
    week_ago = datetime.utcnow() - timedelta(days=7)
    old_unapplied = db.query(Job).filter(
        and_(
            Job.created_at < week_ago,
            ~Job.id.in_(db.query(Application.job_id).distinct())
        )
    ).count()

    total_matches = db.query(JobMatch).count()
    total_applications = db.query(Application).count()

    print(f"\n{'='*70}")
    print(f"📊 Database Statistics:")
    print(f"{'='*70}")
    print(f"  Total jobs: {total_jobs}")
    print(f"  ├─ Jobs with applications (kept): {jobs_with_apps}")
    print(f"  └─ Jobs without applications: {jobs_without_apps}")
    print(f"       └─ Old unapplied jobs (>7 days): {old_unapplied} (will be deleted)")
    print(f"")
    print(f"  Total applications: {total_applications}")
    print(f"  Cached job matches: {total_matches}")
    print(f"{'='*70}\n")


def main():
    """Run cleanup tasks."""
    print(f"\n🧹 Starting application-aware job cleanup...")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    db = next(get_db())

    try:
        # Print before stats
        print("BEFORE CLEANUP:")
        print_db_stats(db)

        # 1. Delete unapplied jobs older than 7 days
        print("Step 1: Deleting old unapplied jobs...")
        deleted = delete_unapplied_old_jobs(db, days_old=7)

        # 2. Clean old job match cache (optional - keeps DB lean)
        print("\nStep 2: Cleaning up old cached matches...")
        deleted_matches = clean_old_matches(db, days_to_keep=90)

        # Print after stats
        print("\nAFTER CLEANUP:")
        print_db_stats(db)

        print("✅ Cleanup completed successfully!")
        print(f"   Summary:")
        print(f"   - Deleted: {deleted} unapplied jobs (>7 days old)")
        print(f"   - Cleaned: {deleted_matches} old cached matches (>90 days)")
        print(f"   - Kept: All jobs with applications (for tracking)\n")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        print(f"❌ Error during cleanup: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

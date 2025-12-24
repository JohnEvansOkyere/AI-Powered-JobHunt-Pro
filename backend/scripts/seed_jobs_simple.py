#!/usr/bin/env python3
"""
Simple Job Seeding Script - Fallback Version

This script fetches ALL jobs from Remotive (no search query) to avoid API errors.
This is the most reliable way to get initial job data.
"""

import asyncio
import sys
from pathlib import Path
import requests
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.job import Job

def fetch_all_remotive_jobs():
    """Fetch all jobs from Remotive API (no search query)."""
    url = "https://remotive.io/api/remote-jobs"

    try:
        print("🔄 Fetching all jobs from Remotive API...")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("jobs", [])
        print(f"   ✅ Received {len(jobs)} jobs from Remotive")
        return jobs
    except Exception as e:
        print(f"   ❌ Failed to fetch from Remotive: {e}")
        return []


def parse_remotive_date(dt_str):
    """Parse Remotive date string."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


def save_jobs_to_db(jobs_data, db: Session):
    """Save Remotive jobs to database."""
    saved = 0
    skipped = 0

    for job_data in jobs_data:
        try:
            job_link = job_data.get("url") or job_data.get("slug")
            if not job_link:
                skipped += 1
                continue

            # Check if exists
            existing = db.query(Job).filter(Job.job_link == job_link).first()
            if existing:
                skipped += 1
                continue

            # Create new job
            job = Job(
                title=job_data.get("title", "Unknown"),
                company=job_data.get("company_name", "Unknown"),
                location=job_data.get("candidate_required_location", "Remote"),
                description=job_data.get("description", ""),
                job_link=job_link,
                source="remotive",
                source_id=str(job_data.get("id")),
                posted_date=parse_remotive_date(job_data.get("publication_date")),
                job_type=job_data.get("job_type"),
                remote_type="remote",
                processing_status="pending"
            )

            db.add(job)
            saved += 1

        except Exception as e:
            print(f"   ⚠️  Skipped job: {e}")
            skipped += 1
            continue

    # Commit
    try:
        db.commit()
        print(f"\n💾 Database commit successful")
        print(f"   ✅ Saved: {saved} new jobs")
        print(f"   ⏭️  Skipped: {skipped} (duplicates or errors)")
    except Exception as e:
        db.rollback()
        print(f"   ❌ Database commit failed: {e}")
        raise

    return saved


def main():
    """Main entry point."""
    print("=" * 70)
    print("Simple Job Seeding - Remotive All Jobs")
    print("=" * 70)
    print()

    # Check database
    try:
        db = SessionLocal()
        existing_count = db.query(Job).count()
        print(f"📊 Current jobs in database: {existing_count}")
        print()
        db.close()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return

    # Fetch jobs from Remotive
    jobs_data = fetch_all_remotive_jobs()

    if not jobs_data:
        print("\n❌ No jobs fetched. Please check:")
        print("   1. Internet connection")
        print("   2. Remotive.io is accessible")
        print("   3. Try again in a few minutes (rate limiting)")
        return

    # Save to database
    print(f"\n💾 Saving {len(jobs_data)} jobs to database...")
    db = SessionLocal()
    try:
        saved_count = save_jobs_to_db(jobs_data, db)

        print()
        print("=" * 70)
        if saved_count > 0:
            print(f"✅ SUCCESS! Added {saved_count} new jobs to database")
        else:
            print(f"ℹ️  No new jobs added (all {len(jobs_data)} jobs already exist)")
        print("=" * 70)
        print()

        if saved_count > 0:
            print("Next steps:")
            print("1. Visit: http://localhost:3000/dashboard/jobs")
            print("2. Jobs will be matched to user profiles automatically")
            print()
        else:
            print("Database already has jobs! Check with:")
            print("  SELECT title, company, source FROM jobs LIMIT 10;")
            print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

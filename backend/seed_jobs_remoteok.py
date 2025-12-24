#!/usr/bin/env python3
"""
RemoteOK Job Seeding Script

Uses RemoteOK.com's free public API (no API key needed).
Alternative to Remotive when it's down.
"""

import sys
from pathlib import Path
import requests
from datetime import datetime
import time

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.job import Job


def fetch_remoteok_jobs():
    """
    Fetch jobs from RemoteOK public API.

    API: https://remoteok.com/api
    Documentation: https://github.com/remoteok/remote-jobs
    """
    url = "https://remoteok.com/api"

    # RemoteOK requires a user agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; JobHuntBot/1.0; +https://github.com/yourusername/jobhunt)'
    }

    try:
        print("🔄 Fetching jobs from RemoteOK API...")
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()

        # RemoteOK returns JSON array, first item is metadata
        data = resp.json()

        # Skip first item (it's metadata/legal notice)
        jobs = data[1:] if len(data) > 1 else []

        print(f"   ✅ Received {len(jobs)} jobs from RemoteOK")
        return jobs

    except Exception as e:
        print(f"   ❌ Failed to fetch from RemoteOK: {e}")
        return []


def parse_remoteok_date(timestamp):
    """Parse RemoteOK timestamp (epoch seconds)."""
    if not timestamp:
        return None
    try:
        return datetime.fromtimestamp(int(timestamp))
    except Exception:
        return None


def extract_tags(job_data):
    """Extract tags from RemoteOK job."""
    tags = []

    # RemoteOK has tags array
    if 'tags' in job_data and isinstance(job_data['tags'], list):
        tags.extend(job_data['tags'])

    return tags[:10]  # Limit to 10 tags


def save_jobs_to_db(jobs_data, db: Session):
    """Save RemoteOK jobs to database."""
    saved = 0
    skipped = 0

    for job_data in jobs_data:
        try:
            # RemoteOK provides 'url' field
            job_link = job_data.get('url')
            if not job_link:
                skipped += 1
                continue

            # Check if exists
            existing = db.query(Job).filter(Job.job_link == job_link).first()
            if existing:
                skipped += 1
                continue

            # Extract location
            location = job_data.get('location', 'Remote')
            if not location or location == 'false':
                location = 'Remote'

            # Create new job
            job = Job(
                title=job_data.get('position', 'Unknown Position'),
                company=job_data.get('company', 'Unknown Company'),
                location=location,
                description=job_data.get('description', ''),
                job_link=job_link,
                source="remoteok",
                source_id=str(job_data.get('id', '')),
                posted_date=parse_remoteok_date(job_data.get('date')),
                job_type=None,  # RemoteOK doesn't specify job type
                remote_type="remote",  # All RemoteOK jobs are remote
                processing_status="pending"
            )

            db.add(job)
            saved += 1

        except Exception as e:
            print(f"   ⚠️  Skipped job '{job_data.get('position', 'unknown')}': {e}")
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
    print("RemoteOK Job Seeding")
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

    # Fetch jobs from RemoteOK
    jobs_data = fetch_remoteok_jobs()

    if not jobs_data:
        print("\n❌ No jobs fetched. Please check:")
        print("   1. Internet connection")
        print("   2. RemoteOK.com is accessible")
        print("   3. Try alternative: python seed_jobs_adzuna.py")
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

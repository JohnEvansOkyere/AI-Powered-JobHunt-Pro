"""
Daily Job Scraper

Automatically scrapes jobs from multiple sources daily.
Run via cron to keep job database fresh.

Features:
- Scrapes from RemoteOK (free, no API key)
- Scrapes from SerpAPI (requires API key)
- Removes duplicates
- Logs results
"""

import sys
import requests
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

sys.path.insert(0, '/home/grejoy/Projects/AI-Powered-JobHunt-Pro/backend')

from app.core.database import get_db
from app.models.job import Job
from app.core.logging import get_logger

logger = get_logger(__name__)


def scrape_remoteok(db: Session):
    """Scrape jobs from RemoteOK API (free, no auth required)."""
    print("🔍 Scraping RemoteOK...")

    url = "https://remoteok.com/api"
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; JobHuntBot/1.0; +https://github.com/yourusername/jobhunt)'
    }

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # First item is metadata, skip it
        jobs_data = data[1:] if len(data) > 1 else []

        new_jobs = 0
        duplicates = 0

        for job_data in jobs_data:
            # Check for duplicates by job_link
            job_link = job_data.get('url', '')
            if not job_link:
                continue

            # Skip if already exists
            existing = db.query(Job).filter(Job.job_link == job_link).first()
            if existing:
                duplicates += 1
                continue

            # Create new job
            location = job_data.get('location', 'Remote')
            if not location or location == 'false':
                location = 'Remote'

            job = Job(
                title=job_data.get('position', 'Unknown Position'),
                company=job_data.get('company', 'Unknown Company'),
                location=location,
                description=job_data.get('description', ''),
                job_link=job_link,
                source="remoteok",
                source_id=str(job_data.get('id', '')),
                posted_date=None,  # RemoteOK doesn't provide exact date
                job_type=None,
                remote_type="remote",
                processing_status="pending"
            )

            db.add(job)
            new_jobs += 1

        db.commit()

        logger.info(f"✅ RemoteOK: Added {new_jobs} new jobs, skipped {duplicates} duplicates")
        print(f"   ✅ Added {new_jobs} new jobs")
        print(f"   ⏭️  Skipped {duplicates} duplicates")

        return new_jobs

    except Exception as e:
        logger.error(f"Error scraping RemoteOK: {e}")
        print(f"   ❌ Error: {e}")
        db.rollback()
        return 0


def scrape_serpapi(db: Session):
    """Scrape jobs from Google Jobs via SerpAPI (requires API key)."""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv('SERPAPI_API_KEY')

    if not api_key:
        logger.warning("SERPAPI_API_KEY not configured, skipping SerpAPI scraping")
        print("   ⚠️  SERPAPI_API_KEY not configured, skipping")
        return 0

    print("🔍 Scraping SerpAPI (Google Jobs)...")

    # Search for tech jobs
    search_queries = [
        "software engineer remote",
        "data scientist remote",
        "machine learning engineer remote",
        "devops engineer remote",
        "full stack developer remote"
    ]

    total_new_jobs = 0

    for query in search_queries:
        try:
            url = "https://serpapi.com/search"
            params = {
                'engine': 'google_jobs',
                'q': query,
                'api_key': api_key,
                'num': 10  # Limit to 10 per query to save API costs
            }

            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            jobs_data = data.get('jobs_results', [])

            new_jobs = 0
            for job_data in jobs_data:
                job_link = job_data.get('share_url') or job_data.get('related_links', [{}])[0].get('link', '')

                if not job_link:
                    continue

                # Check duplicates
                existing = db.query(Job).filter(Job.job_link == job_link).first()
                if existing:
                    continue

                job = Job(
                    title=job_data.get('title', 'Unknown Position'),
                    company=job_data.get('company_name', 'Unknown Company'),
                    location=job_data.get('location', 'Remote'),
                    description=job_data.get('description', ''),
                    job_link=job_link,
                    source="serpapi",
                    source_id=job_data.get('job_id', ''),
                    posted_date=None,
                    job_type=None,
                    remote_type="remote" if 'remote' in query.lower() else None,
                    processing_status="pending"
                )

                db.add(job)
                new_jobs += 1

            db.commit()
            total_new_jobs += new_jobs

            logger.info(f"SerpAPI '{query}': Added {new_jobs} new jobs")

        except Exception as e:
            logger.error(f"Error scraping SerpAPI for '{query}': {e}")
            db.rollback()

    print(f"   ✅ Added {total_new_jobs} new jobs from SerpAPI")
    return total_new_jobs


def main():
    """Run daily job scraping."""
    print(f"\n{'='*60}")
    print(f"🤖 Daily Job Scraper - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    db = next(get_db())

    try:
        # Count before
        jobs_before = db.query(Job).filter(Job.processing_status != "archived").count()
        print(f"📊 Active jobs before scraping: {jobs_before}\n")

        # Scrape from sources
        remoteok_count = scrape_remoteok(db)
        serpapi_count = scrape_serpapi(db)

        # Count after
        jobs_after = db.query(Job).filter(Job.processing_status != "archived").count()

        print(f"\n{'='*60}")
        print(f"✅ Scraping completed!")
        print(f"{'='*60}")
        print(f"  RemoteOK: +{remoteok_count} jobs")
        print(f"  SerpAPI: +{serpapi_count} jobs")
        print(f"  Total new: +{remoteok_count + serpapi_count} jobs")
        print(f"  Active jobs now: {jobs_after}")
        print(f"{'='*60}\n")

    except Exception as e:
        logger.error(f"Error during daily scraping: {e}")
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()

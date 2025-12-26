"""
Periodic Tasks for Automated Job Scraping

Scheduled tasks that run automatically to keep the job database fresh.
"""

import uuid
from datetime import datetime
from celery.schedules import crontab
from sqlalchemy.orm import Session

try:
    from app.tasks.celery_app import celery_app
except ImportError:
    # Celery not installed - create mock
    class MockCelery:
        def task(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
        def on_after_configure(self):
            def decorator(func):
                return func
            return decorator
    celery_app = MockCelery()

from app.core.logging import get_logger
from app.core.database import SessionLocal
from app.models.scraping_job import ScrapingJob
from app.tasks.job_scraping import scrape_jobs_task

logger = get_logger(__name__)


# Tech-related job keywords to scrape
TECH_JOB_KEYWORDS = [
    # Software Engineering
    "software engineer",
    "backend engineer",
    "frontend engineer",
    "full stack developer",
    "mobile developer",
    "devops engineer",

    # Data & AI
    "data scientist",
    "data analyst",
    "machine learning engineer",
    "ai engineer",
    "data engineer",
    "business intelligence analyst",

    # Product & Design
    "product manager",
    "ux designer",
    "ui designer",
    "product designer",

    # Other Tech Roles
    "cloud engineer",
    "security engineer",
    "qa engineer",
    "site reliability engineer",
]


@celery_app.task(name="scheduled_tech_job_scraping")
def scheduled_tech_job_scraping():
    """
    Scheduled task that runs every 3 days to scrape fresh tech jobs.

    Scrapes from multiple FREE sources:
    - Remotive (Remote jobs - no API key needed)
    - RemoteOK (Remote jobs - no API key needed)

    Returns:
        dict: Summary of all scraping results
    """
    logger.info("Starting scheduled tech job scraping...")

    db: Session = SessionLocal()

    try:
        # Create a scraping job record for tracking
        scraping_job = ScrapingJob(
            user_id=None,  # System-initiated scraping
            sources=["remotive", "remoteok"],  # Both FREE - No API keys needed
            keywords=TECH_JOB_KEYWORDS,
            filters={
                "location": "Worldwide",
                "max_results_per_source": 200,  # 200 per source = ~400 total jobs
                "job_type": "tech"
            },
            status="pending"
        )

        db.add(scraping_job)
        db.commit()
        db.refresh(scraping_job)

        logger.info(f"Created scraping job {scraping_job.id} for scheduled tech job scraping")

        # Trigger the scraping task
        result = scrape_jobs_task.delay(
            scraping_job_id=str(scraping_job.id),
            sources=["remotive", "remoteok"],  # Both FREE - No API keys needed
            keywords=TECH_JOB_KEYWORDS,
            location="Worldwide",
            max_results_per_source=200
        )

        logger.info(f"Scheduled tech job scraping task triggered: {result}")

        return {
            "status": "started",
            "scraping_job_id": str(scraping_job.id),
            "task_id": str(result.id) if hasattr(result, 'id') else None,
            "sources": ["remotive", "remoteok"],  # Both FREE - No API keys needed
            "keyword_count": len(TECH_JOB_KEYWORDS),
        }

    except Exception as e:
        logger.error(f"Failed to start scheduled tech job scraping: {e}", exc_info=True)
        raise

    finally:
        db.close()


# Configure Celery Beat schedule
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Configure periodic tasks to run automatically.

    Schedule:
    - Tech job scraping: Every 3 days at 2 AM UTC
    """

    # Schedule tech job scraping every 3 days at 2 AM UTC
    sender.add_periodic_task(
        crontab(hour=2, minute=0, day_of_week='*/3'),  # Every 3 days at 2 AM
        scheduled_tech_job_scraping.s(),
        name='scrape-tech-jobs-every-3-days'
    )

    logger.info("Periodic task scheduled: Tech job scraping every 3 days at 2 AM UTC")

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
    "software developer",
    "backend engineer",
    "backend developer",
    "frontend engineer",
    "frontend developer",
    "full stack developer",
    "full stack engineer",
    "web developer",
    "mobile developer",
    "ios developer",
    "android developer",
    "react developer",
    "python developer",
    "java developer",
    "node developer",
    ".net developer",
    "golang developer",
    "ruby developer",

    # Data & AI
    "data scientist",
    "data analyst",
    "data engineer",
    "machine learning engineer",
    "ai engineer",
    "ml engineer",
    "deep learning engineer",
    "nlp engineer",
    "computer vision engineer",
    "business intelligence analyst",
    "bi analyst",
    "analytics engineer",
    "big data engineer",

    # DevOps & Infrastructure
    "devops engineer",
    "site reliability engineer",
    "sre",
    "platform engineer",
    "infrastructure engineer",
    "cloud engineer",
    "aws engineer",
    "azure engineer",
    "gcp engineer",
    "kubernetes engineer",
    "docker engineer",
    "systems engineer",
    "network engineer",

    # Design
    "ux designer",
    "ui designer",
    "ui/ux designer",
    "product designer",
    "graphic designer",
    "web designer",
    "visual designer",
    "interaction designer",
    "motion designer",
    "design lead",

    # Product & Management
    "product manager",
    "technical product manager",
    "product owner",
    "program manager",
    "engineering manager",
    "tech lead",
    "technical lead",

    # Quality & Testing
    "qa engineer",
    "quality assurance engineer",
    "test engineer",
    "automation engineer",
    "sdet",
    "performance engineer",

    # Security & Compliance
    "security engineer",
    "cybersecurity engineer",
    "infosec engineer",
    "security analyst",
    "penetration tester",
    "compliance engineer",

    # Specialized Engineering
    "embedded engineer",
    "firmware engineer",
    "hardware engineer",
    "robotics engineer",
    "game developer",
    "blockchain developer",
    "smart contract developer",

    # Database & Architecture
    "database engineer",
    "database administrator",
    "dba",
    "solutions architect",
    "software architect",
    "system architect",
    "enterprise architect",
]


@celery_app.task(name="scheduled_tech_job_scraping")
def scheduled_tech_job_scraping():
    """
    Scheduled task that runs every 3 days to scrape fresh tech jobs.

    Scrapes from multiple FREE sources:
    - Remotive (Remote jobs - no API key needed)
    - RemoteOK (Remote jobs - no API key needed)
    - Adzuna (Job aggregator - no API key needed)

    Returns:
        dict: Summary of all scraping results
    """
    logger.info("Starting scheduled tech job scraping...")

    db: Session = SessionLocal()

    try:
        # Create a scraping job record for tracking
        scraping_job = ScrapingJob(
            user_id=None,  # System-initiated scraping
            sources=["remotive", "remoteok", "adzuna"],  # All 3 FREE - No API keys needed
            keywords=TECH_JOB_KEYWORDS,
            filters={
                "location": "Worldwide",
                "max_results_per_source": 100,  # 100 per source x 3 sources = ~300 total jobs
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
            sources=["remotive", "remoteok", "adzuna"],  # All 3 FREE - No API keys needed
            keywords=TECH_JOB_KEYWORDS,
            location="Worldwide",
            max_results_per_source=100
        )

        logger.info(f"Scheduled tech job scraping task triggered: {result}")

        return {
            "status": "started",
            "scraping_job_id": str(scraping_job.id),
            "task_id": str(result.id) if hasattr(result, 'id') else None,
            "sources": ["remotive", "remoteok", "adzuna"],  # All 3 FREE - No API keys needed
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

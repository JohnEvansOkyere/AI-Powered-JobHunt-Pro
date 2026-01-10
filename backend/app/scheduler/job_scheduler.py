"""
Job Scraping Scheduler using APScheduler

Schedules automated job scraping daily at 6 AM to fetch jobs posted within the last 2 days.
Prevents database duplication through proper deduplication logic.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.database import SessionLocal
from app.services.job_scraper_service import JobScraperService
from app.services.recommendation_generator import RecommendationGenerator

logger = get_logger(__name__)

# Tech job keywords (100+ covering all tech roles)
TECH_JOB_KEYWORDS = [
    # Software Engineering
    "software engineer", "software developer", "backend engineer",
    "backend developer", "frontend engineer", "frontend developer",
    "full stack developer", "full stack engineer", "web developer",
    "mobile developer", "ios developer", "android developer",
    "react developer", "python developer", "java developer",
    "node developer", ".net developer", "golang developer", "ruby developer",

    # Data & AI
    "data scientist", "data analyst", "data engineer",
    "machine learning engineer", "ai engineer", "ml engineer",
    "deep learning engineer", "nlp engineer", "computer vision engineer",
    "business intelligence analyst", "bi analyst", "analytics engineer",
    "big data engineer",

    # DevOps & Infrastructure
    "devops engineer", "site reliability engineer", "sre",
    "platform engineer", "infrastructure engineer", "cloud engineer",
    "aws engineer", "azure engineer", "gcp engineer",
    "kubernetes engineer", "docker engineer", "systems engineer",
    "network engineer",

    # Design
    "ux designer", "ui designer", "ui/ux designer",
    "product designer", "graphic designer", "web designer",
    "visual designer", "interaction designer", "motion designer",
    "design lead",

    # Product & Management
    "product manager", "technical product manager", "product owner",
    "program manager", "engineering manager", "tech lead",
    "technical lead",

    # Quality & Testing
    "qa engineer", "quality assurance engineer", "test engineer",
    "automation engineer", "sdet", "performance engineer",

    # Security & Compliance
    "security engineer", "cybersecurity engineer", "infosec engineer",
    "security analyst", "penetration tester", "compliance engineer",

    # Specialized Engineering
    "embedded engineer", "firmware engineer", "hardware engineer",
    "robotics engineer", "game developer", "blockchain developer",
    "smart contract developer",

    # Database & Architecture
    "database engineer", "database administrator", "dba",
    "solutions architect", "software architect", "system architect",
    "enterprise architect",
]


class JobScraperScheduler:
    """
    Manages scheduled job scraping using APScheduler.

    Features:
    - Daily scraping at 6 AM
    - Only scrapes jobs posted within last 2 days
    - Automatic deduplication
    - 3 FREE sources (Remotive, RemoteOK, Adzuna)
    """

    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self.scraper_service = JobScraperService()
        logger.info("Job scraper scheduler initialized")

    async def generate_recommendations(self):
        """
        Generate job recommendations for all users.

        Runs daily at 7 AM UTC (after job scraping at 6 AM).
        """
        db: Session = SessionLocal()

        try:
            generator = RecommendationGenerator(db)
            stats = await generator.generate_recommendations_for_all_users()
            return stats

        except Exception as e:
            logger.error(f"❌ Error generating recommendations: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()

    async def cleanup_expired_saved_jobs(self):
        """
        Delete expired saved jobs (older than 10 days).

        Runs daily at midnight to remove saved jobs that have expired.
        """
        logger.info("=" * 60)
        logger.info("🧹 CLEANUP: Expired Saved Jobs")
        logger.info(f"⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info("=" * 60)

        from app.models.application import Application

        db: Session = SessionLocal()

        try:
            # Find expired saved jobs
            now = datetime.utcnow()
            expired_apps = db.query(Application).filter(
                Application.status == 'saved',
                Application.expires_at < now
            ).all()

            if not expired_apps:
                logger.info("✅ No expired saved jobs to clean up")
                return

            # Delete expired jobs
            deleted_count = len(expired_apps)
            for app in expired_apps:
                logger.info(f"🗑️  Deleting expired saved job: job_id={app.job_id}, expired_at={app.expires_at}")
                db.delete(app)

            db.commit()

            logger.info("=" * 60)
            logger.info(f"✅ CLEANUP COMPLETED: Deleted {deleted_count} expired saved jobs")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
            db.rollback()
        finally:
            db.close()

    async def cleanup_expired_recommendations(self):
        """
        Delete expired job recommendations (older than 3 days).

        Runs daily at midnight to remove expired recommendations.
        """
        logger.info("=" * 60)
        logger.info("🧹 CLEANUP: Expired Recommendations")
        logger.info(f"⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info("=" * 60)

        db: Session = SessionLocal()

        try:
            generator = RecommendationGenerator(db)
            deleted_count = generator.cleanup_expired_recommendations()

            logger.info("=" * 60)
            logger.info(f"✅ CLEANUP COMPLETED: Deleted {deleted_count} expired recommendations")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
            db.rollback()
        finally:
            db.close()

    async def cleanup_old_jobs(self):
        """
        Delete jobs older than 7 days.

        Runs daily at midnight to keep database fresh and performant.
        Only keeps recent jobs that are still relevant.
        """
        logger.info("=" * 60)
        logger.info("🧹 CLEANUP: Old Jobs (>7 days)")
        logger.info(f"⏰ Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info("=" * 60)

        from app.models.job import Job
        from app.models.application import Application

        db: Session = SessionLocal()

        try:
            # Calculate cutoff date (7 days ago)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
            logger.info(f"📅 Deleting jobs scraped before: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            logger.info("   (Skipping jobs with saved/applied applications)")

            # Find old jobs
            old_jobs = db.query(Job).filter(
                Job.scraped_at < cutoff_date
            ).all()

            if not old_jobs:
                logger.info("✅ No old jobs to clean up")
                return 0

            # Filter out jobs that have applications
            jobs_to_delete = []
            jobs_skipped = 0

            for job in old_jobs:
                has_apps = db.query(Application).filter(
                    Application.job_id == job.id
                ).count() > 0

                if has_apps:
                    jobs_skipped += 1
                    logger.debug(f"⏭️  Skipping job with applications: {job.title} at {job.company}")
                else:
                    jobs_to_delete.append(job)

            if not jobs_to_delete:
                logger.info(f"⚠️  All {len(old_jobs)} old jobs have applications - skipped deletion")
                return 0

            # Delete old jobs (only those without applications)
            deleted_count = len(jobs_to_delete)
            for job in jobs_to_delete:
                logger.debug(f"🗑️  Deleting old job: {job.title} at {job.company} (scraped: {job.scraped_at})")
                db.delete(job)

            db.commit()

            logger.info("=" * 60)
            logger.info(f"✅ CLEANUP COMPLETED: Deleted {deleted_count} old jobs")
            if jobs_skipped > 0:
                logger.info(f"⏭️  Skipped {jobs_skipped} jobs with saved/applied applications")
            logger.info(f"💾 Database now contains only recent jobs")
            logger.info("=" * 60)

            return deleted_count

        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
            db.rollback()
            return 0
        finally:
            db.close()

    async def scrape_recent_jobs(self):
        """
        Scrape jobs posted within the last 2 days.

        This runs daily at 6 AM to keep the database fresh with recent jobs only.
        """
        logger.info("=" * 60)
        logger.info("🚀 SCHEDULED JOB SCRAPING STARTED")
        logger.info(f"⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info("=" * 60)

        db: Session = SessionLocal()

        try:
            # Calculate cutoff date (2 days ago)
            cutoff_date = datetime.utcnow() - timedelta(days=2)
            logger.info(f"📅 Scraping jobs posted after: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")

            # Scrape from all 3 FREE sources
            sources = ["remotive", "remoteok", "adzuna"]
            logger.info(f"📡 Sources: {', '.join(sources)}")
            logger.info(f"🔑 Keywords: {len(TECH_JOB_KEYWORDS)} tech job categories")

            result = await self.scraper_service.scrape_jobs(
                sources=sources,
                keywords=TECH_JOB_KEYWORDS,
                location="Worldwide",
                max_results_per_source=100,  # 100 per source = ~300 total
                db=db,
                min_posted_date=cutoff_date  # Only jobs from last 2 days
            )

            logger.info("=" * 60)
            logger.info("✅ SCRAPING COMPLETED")
            logger.info(f"📊 Results:")
            logger.info(f"   - Total found: {result.get('total_found', 0)}")
            logger.info(f"   - New jobs stored: {result.get('stored', 0)}")
            logger.info(f"   - Duplicates skipped: {result.get('duplicates', 0)}")
            logger.info(f"   - Failed: {result.get('failed', 0)}")
            logger.info("=" * 60)

            # Log per-source breakdown
            if 'source_breakdown' in result:
                logger.info("📈 Source Breakdown:")
                for source, stats in result['source_breakdown'].items():
                    logger.info(f"   {source}: {stats.get('found', 0)} found, "
                              f"{stats.get('stored', 0)} stored, "
                              f"{stats.get('duplicates', 0)} duplicates")

            return result

        except Exception as e:
            logger.error(f"❌ Scheduled job scraping failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "total_found": 0,
                "stored": 0,
                "duplicates": 0,
                "failed": 1
            }
        finally:
            db.close()

    def start(self):
        """
        Start the scheduler.

        Schedules:
        - Daily job scraping at 6 AM UTC
        - Daily recommendation generation at 7 AM UTC (after scraping)
        - Daily cleanup of expired saved jobs at midnight UTC
        - Daily cleanup of expired recommendations at midnight UTC
        """
        try:
            # Schedule daily scraping at 6 AM UTC
            self.scheduler.add_job(
                func=self.scrape_recent_jobs,
                trigger=CronTrigger(hour=6, minute=0),  # 6:00 AM UTC daily
                id="daily_job_scraping",
                name="Daily Tech Job Scraping (6 AM UTC)",
                replace_existing=True,
                max_instances=1,  # Prevent concurrent runs
            )

            # Schedule daily recommendation generation at 7 AM UTC (1 hour after scraping)
            self.scheduler.add_job(
                func=self.generate_recommendations,
                trigger=CronTrigger(hour=7, minute=0),  # 7:00 AM UTC daily
                id="daily_recommendation_generation",
                name="Daily Recommendation Generation (7 AM UTC)",
                replace_existing=True,
                max_instances=1,
            )

            # Schedule daily cleanup at midnight UTC
            self.scheduler.add_job(
                func=self.cleanup_expired_saved_jobs,
                trigger=CronTrigger(hour=0, minute=0),  # Midnight UTC daily
                id="daily_saved_jobs_cleanup",
                name="Daily Saved Jobs Cleanup (Midnight UTC)",
                replace_existing=True,
                max_instances=1,
            )

            # Schedule daily cleanup of expired recommendations at midnight UTC
            self.scheduler.add_job(
                func=self.cleanup_expired_recommendations,
                trigger=CronTrigger(hour=0, minute=5),  # 12:05 AM UTC daily
                id="daily_recommendations_cleanup",
                name="Daily Recommendations Cleanup (Midnight UTC)",
                replace_existing=True,
                max_instances=1,
            )

            # Schedule daily cleanup of old jobs (>7 days) at midnight UTC
            self.scheduler.add_job(
                func=self.cleanup_old_jobs,
                trigger=CronTrigger(hour=0, minute=10),  # 12:10 AM UTC daily
                id="daily_old_jobs_cleanup",
                name="Daily Old Jobs Cleanup (>7 days)",
                replace_existing=True,
                max_instances=1,
            )

            self.scheduler.start()

            logger.info("✅ Job scraper scheduler started successfully")
            logger.info("⏰ Job Scraping: Daily at 6:00 AM UTC")
            logger.info("🎯 Recommendations: Daily at 7:00 AM UTC")
            logger.info("🧹 Cleanup: Daily at 12:00 AM UTC (midnight)")
            logger.info("   - Saved jobs cleanup: 12:00 AM")
            logger.info("   - Recommendations cleanup: 12:05 AM")
            logger.info("   - Old jobs cleanup (>7 days): 12:10 AM")
            logger.info("📅 Scrapes jobs posted within last 2 days")
            logger.info("💾 Keeps only jobs from last 7 days in database")
            logger.info("🔄 Next scraping: " + str(self.scheduler.get_job('daily_job_scraping').next_run_time))
            logger.info("🔄 Next recommendations: " + str(self.scheduler.get_job('daily_recommendation_generation').next_run_time))

        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}", exc_info=True)
            raise

    def stop(self):
        """Stop the scheduler."""
        try:
            self.scheduler.shutdown(wait=True)
            logger.info("Job scraper scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}", exc_info=True)

    async def trigger_manual_scrape(self):
        """
        Manually trigger a scrape job (useful for testing or on-demand scraping).

        Returns:
            dict: Scraping results
        """
        logger.info("🔧 Manual scrape triggered")
        return await self.scrape_recent_jobs()


# Global scheduler instance
_scheduler_instance = None


def get_scheduler() -> JobScraperScheduler:
    """Get the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = JobScraperScheduler()
    return _scheduler_instance


def start_scheduler():
    """Start the global scheduler."""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler


def stop_scheduler():
    """Stop the global scheduler."""
    global _scheduler_instance
    if _scheduler_instance:
        _scheduler_instance.stop()
        _scheduler_instance = None

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

# Tech job keywords: all tech roles + entry-level, internship, junior, mid, senior
# First ~15 are used by some scrapers for search/filter; keep role + level mix.
TECH_JOB_KEYWORDS = [
    # Core tech roles + levels (first 10–15 used by RemoteOK/Arbeitnow/SerpAPI)
    "software engineer", "software developer", "developer", "engineer",
    "internship", "entry level", "junior", "senior", "backend", "frontend",
    "full stack", "data scientist", "data engineer", "devops", "product manager",

    # More experience levels & role types
    "intern", "entry-level", "graduate", "new grad", "new graduate", "associate",
    "mid level", "mid-level", "intermediate", "staff engineer", "principal engineer",
    "lead engineer", "experienced",

    # Software Engineering - General
    "backend engineer", "backend developer", "frontend engineer", "frontend developer",
    "full stack developer", "full stack engineer", "fullstack developer",
    "web developer", "web engineer", "application developer",

    # Entry-level & junior tech (explicit)
    "junior software engineer", "junior developer", "junior engineer",
    "entry level developer", "entry level engineer", "graduate developer",
    "graduate engineer", "software engineer internship", "developer internship",
    "engineering internship", "tech internship", "co-op", "coop",

    # Mobile Development
    "mobile developer", "mobile engineer", "ios developer", "ios engineer",
    "android developer", "android engineer", "react native developer",
    "flutter developer", "mobile app developer", "swift developer",
    "kotlin developer",

    # Frontend & JavaScript
    "react developer", "react engineer", "vue developer", "angular developer",
    "javascript developer", "typescript developer", "nextjs developer",
    "frontend architect",

    # Backend & Languages
    "python developer", "python engineer", "java developer", "java engineer",
    "node developer", "nodejs developer", ".net developer", "c# developer",
    "golang developer", "go developer", "ruby developer", "rails developer",
    "php developer", "rust developer", "scala developer",

    # Data Science & Analytics (all levels)
    "data scientist", "data analyst", "senior data scientist",
    "junior data scientist", "junior data analyst", "entry level data analyst",
    "data science engineer", "data science internship", "analytics internship",
    "quantitative analyst", "research scientist", "research intern",
    "business intelligence analyst", "bi analyst", "bi developer",
    "analytics engineer", "data analytics", "statistical analyst",

    # AI & Machine Learning (all levels)
    "ai engineer", "ai developer", "ai/ml engineer", "ml engineer",
    "machine learning engineer", "machine learning scientist",
    "junior ml engineer", "ml internship", "ai internship",
    "deep learning engineer", "nlp engineer", "natural language processing",
    "computer vision engineer", "cv engineer", "ai researcher",
    "applied scientist", "research engineer", "llm engineer",
    "generative ai engineer", "prompt engineer",

    # Data Engineering
    "data engineer", "big data engineer", "etl developer",
    "data pipeline engineer", "data platform engineer",
    "dataops engineer", "analytics engineer",

    # DevOps & Infrastructure (all levels)
    "devops engineer", "site reliability engineer", "sre",
    "junior devops", "devops internship", "platform engineer",
    "infrastructure engineer", "cloud engineer", "aws engineer",
    "azure engineer", "gcp engineer", "kubernetes engineer", "k8s engineer",
    "docker engineer", "systems engineer", "linux engineer", "unix administrator",
    "network engineer", "network administrator",

    # Design & UX (all levels)
    "ux designer", "ui designer", "ui/ux designer", "ux/ui designer",
    "product designer", "senior product designer", "junior designer",
    "design internship", "ux internship", "ui internship",
    "lead designer", "graphic designer", "web designer", "visual designer",
    "interaction designer", "motion designer", "ux researcher",
    "design lead", "design manager", "creative director",
    "brand designer", "digital designer",

    # Product & Management
    "product manager", "senior product manager", "technical product manager",
    "product owner", "program manager", "project manager",
    "engineering manager", "tech lead", "technical lead",
    "team lead", "director of engineering", "vp engineering",
    "cto", "chief technology officer", "head of engineering",

    # Quality & Testing (all levels)
    "qa engineer", "quality assurance engineer", "test engineer",
    "junior qa engineer", "qa internship", "automation engineer",
    "test automation engineer", "sdet", "performance engineer",
    "qa analyst", "quality engineer", "test lead", "qa lead",

    # Security
    "security engineer", "cybersecurity engineer", "infosec engineer",
    "security analyst", "penetration tester", "security architect",
    "application security engineer", "devsecops engineer",
    "cloud security engineer", "soc analyst",

    # Specialized Engineering
    "embedded engineer", "embedded software engineer", "firmware engineer",
    "hardware engineer", "robotics engineer", "iot engineer",
    "game developer", "game engineer", "unity developer",
    "unreal developer", "graphics engineer",

    # Blockchain & Web3
    "blockchain developer", "blockchain engineer", "smart contract developer",
    "solidity developer", "web3 developer", "crypto developer",
    "defi developer",

    # Database & Architecture
    "database engineer", "database administrator", "dba",
    "sql developer", "database developer",
    "solutions architect", "software architect", "system architect",
    "enterprise architect", "cloud architect", "technical architect",

    # Support & Operations
    "technical support engineer", "support engineer", "it support",
    "systems administrator", "sysadmin", "it administrator",
    "helpdesk engineer", "technical consultant",

    # Emerging Tech
    "ar/vr developer", "xr developer", "metaverse developer",
    "quantum computing engineer", "edge computing engineer",
]


class JobScraperScheduler:
    """
    Manages scheduled job scraping using APScheduler.

    Schedule:
    - 6:00 AM UTC (every 3 days): Scrape jobs posted in last 3 days
    - 7:00 AM UTC (every 2 days): Generate recommendations for users with CV OR profile
    - Midnight UTC (daily): Cleanup data older than 7 days

    Features:
    - 4 FREE sources (Remotive, RemoteOK, Joinrise, Arbeitnow)
    - Optional API-key sources (SerpAPI, Jooble, FindWork, Adzuna) if keys are set
    - Uses both CV and profile data for matching
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

            # Find old jobs (only scraped jobs - never delete user-added external jobs)
            old_jobs = db.query(Job).filter(
                Job.scraped_at < cutoff_date,
                Job.source != "external",
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
        Scrape jobs posted within the last 3 days.

        Runs every 3 days at 6 AM UTC to keep the database fresh.
        """
        logger.info("=" * 60)
        logger.info("🚀 SCHEDULED JOB SCRAPING STARTED (Every 3 Days)")
        logger.info(f"⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info("=" * 60)

        db: Session = SessionLocal()

        try:
            # Calculate cutoff date (3 days ago - matches scraping interval)
            cutoff_date = datetime.utcnow() - timedelta(days=3)
            logger.info(f"📅 Scraping jobs posted after: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")

            # Scrape from all FREE sources (4 sources, no API key required)
            # Note: HiringCafe removed - API not publicly available (returns 429)
            # Note: Adzuna moved to API-key section - requires free credentials
            sources = [
                "remotive",     # Remote jobs (FREE)
                "remoteok",     # Remote jobs (FREE)
                "joinrise",     # Ghana + global jobs (FREE)
                "arbeitnow",    # Remote tech jobs (FREE)
            ]

            # Add API-key sources if configured
            from app.core.config import settings
            if getattr(settings, 'JOOBLE_API_KEY', None):
                sources.append("jooble")
            if getattr(settings, 'FINDWORK_API_KEY', None):
                sources.append("findwork")
            if getattr(settings, 'SERPAPI_API_KEY', None):
                sources.append("serpapi")
            if getattr(settings, 'ADZUNA_APP_ID', None) and getattr(settings, 'ADZUNA_APP_KEY', None):
                sources.append("adzuna")

            logger.info(f"📡 Sources: {', '.join(sources)} ({len(sources)} total)")
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

            # Run cleanup after every scrape so old jobs are removed even if
            # the midnight cron didn't run (e.g. process sleeping in production)
            logger.info("🧹 Running cleanup of old jobs (>7 days)...")
            deleted = await self.cleanup_old_jobs()
            if deleted > 0:
                logger.info(f"   Cleaned {deleted} old jobs")

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
        - Job scraping every 3 days at 6 AM UTC (scrapes jobs from last 3 days)
        - Recommendation generation every 2 days at 7 AM UTC (uses CV + profile)
        - Daily cleanup at midnight UTC (removes data older than 7 days)
        """
        try:
            # Schedule job scraping every 3 days at 6 AM UTC
            # Using day_of_month='*/3' to run every 3 days
            self.scheduler.add_job(
                func=self.scrape_recent_jobs,
                trigger=CronTrigger(day='*/3', hour=6, minute=0),  # Every 3 days at 6 AM UTC
                id="periodic_job_scraping",
                name="Job Scraping (Every 3 Days at 6 AM UTC)",
                replace_existing=True,
                max_instances=1,
            )

            # Schedule recommendation generation every 2 days at 7 AM UTC
            self.scheduler.add_job(
                func=self.generate_recommendations,
                trigger=CronTrigger(day='*/2', hour=7, minute=0),  # Every 2 days at 7 AM UTC
                id="periodic_recommendation_generation",
                name="Recommendation Generation (Every 2 Days at 7 AM UTC)",
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
            logger.info("=" * 60)
            logger.info("📅 SCHEDULE:")
            logger.info("   🚀 Job Scraping: Every 3 days at 6:00 AM UTC")
            logger.info("   🎯 Recommendations: Every 2 days at 7:00 AM UTC")
            logger.info("   🧹 Cleanup: Daily at midnight UTC")
            logger.info("      - Saved jobs cleanup: 12:00 AM")
            logger.info("      - Recommendations cleanup: 12:05 AM")
            logger.info("      - Old jobs cleanup (>7 days): 12:10 AM")
            logger.info("=" * 60)
            logger.info("📊 SETTINGS:")
            logger.info("   - Scrapes jobs posted within last 3 days")
            logger.info("   - Keeps only jobs from last 7 days in database")
            logger.info("   - Uses CV + Profile data for recommendations")
            logger.info("=" * 60)
            logger.info("🔄 Next scraping: " + str(self.scheduler.get_job('periodic_job_scraping').next_run_time))
            logger.info("🔄 Next recommendations: " + str(self.scheduler.get_job('periodic_recommendation_generation').next_run_time))

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

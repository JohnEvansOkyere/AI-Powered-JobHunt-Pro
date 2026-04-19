"""Database models."""

from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.cv import CV
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.job_recommendation import JobRecommendation
from app.models.application import Application
from app.models.scraping_job import ScrapingJob
from app.models.embeddings import JobEmbedding, UserEmbedding

__all__ = [
    "User",
    "UserProfile",
    "CV",
    "Job",
    "JobMatch",
    "JobRecommendation",
    "Application",
    "ScrapingJob",
    "JobEmbedding",
    "UserEmbedding",
]


"""Database models."""

from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.cv import CV
from app.models.cv_generation import CVGeneration, CVGenerationRevision
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.job_recommendation import JobRecommendation
from app.models.application import Application
from app.models.scraping_job import ScrapingJob
from app.models.embeddings import JobEmbedding, UserEmbedding
from app.models.notification import (
    EmailMessage,
    EmailSuppression,
    NotificationPreferences,
    WhatsappIncomingEvent,
    WhatsappMessage,
)
from app.models.analytics import AnalyticsEvent, AnalyticsSession

__all__ = [
    "User",
    "UserProfile",
    "CV",
    "CVGeneration",
    "CVGenerationRevision",
    "Job",
    "JobMatch",
    "JobRecommendation",
    "Application",
    "ScrapingJob",
    "JobEmbedding",
    "UserEmbedding",
    "NotificationPreferences",
    "EmailMessage",
    "EmailSuppression",
    "WhatsappMessage",
    "WhatsappIncomingEvent",
    "AnalyticsEvent",
    "AnalyticsSession",
]

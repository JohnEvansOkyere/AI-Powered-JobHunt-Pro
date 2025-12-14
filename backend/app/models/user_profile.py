"""
User Profile Model

Represents comprehensive user profile information including career targeting,
skills, experience, preferences, and AI settings.
"""

from sqlalchemy import Column, String, Integer, Boolean, Text, ARRAY, JSON, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class UserProfile(Base):
    """User profile model with comprehensive career and preference data."""

    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)

    # Career Targeting
    primary_job_title = Column(Text, nullable=True)
    secondary_job_titles = Column(ARRAY(Text), nullable=True)
    seniority_level = Column(
        String(20),
        CheckConstraint("seniority_level IN ('entry', 'mid', 'senior', 'lead', 'executive')"),
        nullable=True,
    )
    desired_industries = Column(ARRAY(Text), nullable=True)
    company_size_preference = Column(
        String(20),
        CheckConstraint(
            "company_size_preference IN ('startup', 'small', 'medium', 'large', 'enterprise', 'any')"
        ),
        nullable=True,
    )
    salary_range_min = Column(Integer, nullable=True)
    salary_range_max = Column(Integer, nullable=True)
    contract_type = Column(ARRAY(Text), nullable=True)
    work_preference = Column(
        String(20),
        CheckConstraint("work_preference IN ('remote', 'hybrid', 'onsite', 'flexible')"),
        nullable=True,
    )

    # Skills & Tools
    technical_skills = Column(JSONB, nullable=True)  # [{skill, years, confidence}]
    soft_skills = Column(ARRAY(Text), nullable=True)
    tools_technologies = Column(ARRAY(Text), nullable=True)

    # Experience Breakdown
    experience = Column(JSONB, nullable=True)  # [{role, company, duration, achievements, metrics}]

    # Job Filtering Preferences
    preferred_keywords = Column(ARRAY(Text), nullable=True)
    excluded_keywords = Column(ARRAY(Text), nullable=True)
    blacklisted_companies = Column(ARRAY(Text), nullable=True)
    job_boards_include = Column(ARRAY(Text), nullable=True)
    job_boards_exclude = Column(ARRAY(Text), nullable=True)
    job_freshness_days = Column(Integer, default=30)

    # Application Style
    writing_tone = Column(
        String(20),
        CheckConstraint("writing_tone IN ('formal', 'friendly', 'confident', 'professional')"),
        nullable=True,
    )
    personal_branding_summary = Column(Text, nullable=True)
    first_person = Column(Boolean, default=True)
    email_length_preference = Column(
        String(10),
        CheckConstraint("email_length_preference IN ('short', 'medium', 'long')"),
        nullable=True,
    )

    # Language & Localization
    preferred_language = Column(String(10), default="en")
    local_job_market = Column(Text, nullable=True)

    # AI Preferences
    ai_preferences = Column(JSONB, nullable=True)  # {job_matching, cv_tailoring, etc.}

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


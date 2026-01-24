"""
Job Model

Represents scraped job listings from various job boards and user-added external jobs.
"""

from sqlalchemy import Column, String, Text, CheckConstraint, Index, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, ARRAY
from sqlalchemy.sql import func
import uuid
import json

from app.core.database import Base


class Job(Base):
    """Job model storing scraped job listings."""

    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Job Information
    title = Column(Text, nullable=False)
    company = Column(Text, nullable=False)
    location = Column(Text, nullable=True)
    description = Column(Text, nullable=False)
    job_link = Column(Text, nullable=True, unique=False, index=True)  # Made optional for external jobs

    # Source Information
    source = Column(String(50), nullable=False, index=True)  # 'linkedin', 'indeed', 'external', etc.
    source_id = Column(Text, nullable=True)  # ID from source platform
    source_url = Column(Text, nullable=True)  # Original URL for external jobs
    posted_date = Column(TIMESTAMP(timezone=True), nullable=True, index=True)
    scraped_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    added_by_user_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # User who added external job

    # Normalized Data
    normalized_title = Column(Text, nullable=True)
    normalized_location = Column(Text, nullable=True)
    salary_range = Column(Text, nullable=True)
    salary_min = Column(Text, nullable=True)  # For external jobs
    salary_max = Column(Text, nullable=True)  # For external jobs
    salary_currency = Column(String(10), nullable=True)  # USD, GBP, EUR, etc.
    job_type = Column(String(50), nullable=True)  # 'full-time', 'contract', etc.
    remote_type = Column(String(20), nullable=True)  # 'remote', 'hybrid', 'onsite'
    remote_option = Column(String(10), nullable=True)  # Boolean as string for external jobs
    experience_level = Column(String(20), nullable=True)  # 'entry', 'mid', 'senior', etc.
    
    # Parsed Data (for external jobs)
    requirements = Column(Text, nullable=True)  # JSON array as text
    responsibilities = Column(Text, nullable=True)  # JSON array as text
    skills = Column(Text, nullable=True)  # JSON array as text

    # Processing Status
    processing_status = Column(
        String(20),
        CheckConstraint("processing_status IN ('pending', 'processed', 'archived')"),
        default="pending",
        index=True,
    )

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Composite index for search
    __table_args__ = (
        Index("idx_jobs_title_company", "title", "company"),
    )


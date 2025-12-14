"""
Job Model

Represents scraped job listings from various job boards.
"""

from sqlalchemy import Column, String, Text, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.sql import func
import uuid

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
    job_link = Column(Text, nullable=False, unique=True, index=True)

    # Source Information
    source = Column(String(50), nullable=False, index=True)  # 'linkedin', 'indeed', etc.
    source_id = Column(Text, nullable=True)  # ID from source platform
    posted_date = Column(TIMESTAMP(timezone=True), nullable=True, index=True)
    scraped_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Normalized Data
    normalized_title = Column(Text, nullable=True)
    normalized_location = Column(Text, nullable=True)
    salary_range = Column(Text, nullable=True)
    job_type = Column(String(50), nullable=True)  # 'full-time', 'contract', etc.
    remote_type = Column(String(20), nullable=True)  # 'remote', 'hybrid', 'onsite'

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


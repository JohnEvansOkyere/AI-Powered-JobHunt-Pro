"""
Scraping Job Model

Tracks background job scraping tasks.
"""

from sqlalchemy import Column, String, Integer, Text, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, ARRAY, JSONB
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class ScrapingJob(Base):
    """Scraping job model tracking background scraping tasks."""

    __tablename__ = "scraping_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users", ondelete="CASCADE"), nullable=True, index=True)

    # Job Configuration
    sources = Column(ARRAY(Text), nullable=False)  # Which job boards to scrape
    keywords = Column(ARRAY(Text), nullable=True)
    filters = Column(JSONB, nullable=True)  # Additional filters

    # Status
    status = Column(
        String(20),
        CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')"),
        default="pending",
        index=True,
    )
    progress = Column(Integer, default=0)  # 0-100
    jobs_found = Column(Integer, default=0)
    jobs_processed = Column(Integer, default=0)

    # Results
    error_message = Column(Text, nullable=True)
    result_summary = Column(JSONB, nullable=True)

    # Metadata
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


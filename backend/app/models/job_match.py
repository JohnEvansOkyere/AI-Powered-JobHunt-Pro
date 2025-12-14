"""
Job Match Model

Represents job matching results for users with relevance scores.
"""

from sqlalchemy import Column, String, Text, Numeric, CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class JobMatch(Base):
    """Job match model storing matching results and scores."""

    __tablename__ = "job_matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Matching Scores
    relevance_score = Column(Numeric(5, 2), nullable=False, index=True)  # 0.00 to 100.00
    skill_match_score = Column(Numeric(5, 2), nullable=True)
    experience_match_score = Column(Numeric(5, 2), nullable=True)
    preference_match_score = Column(Numeric(5, 2), nullable=True)

    # Match Details
    match_reasons = Column(JSONB, nullable=True)  # Array of match reasons

    # User Actions
    status = Column(
        String(20),
        CheckConstraint("status IN ('new', 'viewed', 'applied', 'saved', 'dismissed')"),
        default="new",
        index=True,
    )
    user_notes = Column(Text, nullable=True)

    # Metadata
    matched_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    job = relationship("Job", backref="matches")

    # Unique constraint: one match per user-job pair
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="unique_user_job_match"),)


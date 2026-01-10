"""
Job Recommendation Model

Stores pre-computed job recommendations for users to avoid real-time AI matching delays.
"""

from sqlalchemy import Column, String, Text, Float, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class JobRecommendation(Base):
    """Pre-computed job recommendations for users."""

    __tablename__ = "job_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)

    # Match scoring
    match_score = Column(Float, nullable=False)  # 0.0 to 1.0
    match_reason = Column(Text, nullable=True)  # Brief explanation

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False, index=True)

    # Relationships
    job = relationship("Job", backref="recommendations")

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'job_id', name='unique_user_job_recommendation'),
    )

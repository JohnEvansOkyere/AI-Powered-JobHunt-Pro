"""Job Recommendation Model.

Stores pre-computed, tiered job recommendations for users. Tiering and
sub-scores were introduced in Recommendations V2
(see ``docs/RECOMMENDATIONS_V2_PLAN.md`` §5.1-§5.3 and
``migrations/008_recommendations_v2.sql``).
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


TIER_VALUES = ("tier1", "tier2", "tier3")


class JobRecommendation(Base):
    """Pre-computed, tier-labeled job recommendations for users."""

    __tablename__ = "job_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Composite match score used for ordering within a tier. 0..1.
    match_score = Column(Float, nullable=False)
    match_reason = Column(Text, nullable=True)

    # Recommendations V2 columns (migration 008) ----------------------------
    tier = Column(Text, nullable=False, default="tier2")
    semantic_fit = Column(Float, nullable=True)
    title_alignment = Column(Float, nullable=True)
    skill_overlap = Column(Float, nullable=True)
    freshness = Column(Float, nullable=True)
    channel_bonus = Column(Float, nullable=True)
    interest_affinity = Column(Float, nullable=True)
    llm_rerank_score = Column(Float, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False, index=True)

    job = relationship("Job", backref="recommendations")

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="unique_user_job_recommendation"),
        CheckConstraint(
            "tier IN ('tier1', 'tier2', 'tier3')",
            name="job_recommendations_tier_check",
        ),
        Index(
            "idx_recommendations_user_tier_score",
            "user_id",
            "tier",
            "match_score",
        ),
    )

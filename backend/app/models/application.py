"""
Application Model

 Tracks a candidate's relationship with a job: saved, applied externally,
interviewing, offer, dismissed, hidden. CV tailoring was removed in v2
(see docs/RECOMMENDATIONS_V2_PLAN.md).
"""

import uuid

from sqlalchemy import CheckConstraint, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cv_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cvs.id", ondelete="SET NULL"),
        nullable=True,
    )

    status = Column(
        String(20),
        CheckConstraint(
            "status IN ('saved', 'applied', 'dismissed', 'hidden', "
            "'interviewing', 'rejected', 'offer')"
        ),
        default="saved",
        index=True,
    )

    saved_at = Column(TIMESTAMP(timezone=True), nullable=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    job = relationship("Job", backref="applications")
    cv = relationship("CV", backref="applications")

"""
Application Model

Represents generated application materials (CV, cover letter, email).
"""

from sqlalchemy import Column, String, Text, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Application(Base):
    """Application model storing generated materials for job applications."""

    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    cv_id = Column(UUID(as_uuid=True), ForeignKey("cvs.id", ondelete="SET NULL"), nullable=True)

    # Generated Materials
    tailored_cv_path = Column(Text, nullable=True)  # Path to generated CV in storage
    cover_letter = Column(Text, nullable=True)
    application_email = Column(Text, nullable=True)

    # Generation Metadata
    ai_model_used = Column(String(50), nullable=True)  # Which AI model was used
    generation_prompt = Column(Text, nullable=True)  # Prompt used
    generation_settings = Column(JSONB, nullable=True)  # Settings (tone, length, etc.)

    # Status
    status = Column(
        String(20),
        CheckConstraint("status IN ('saved', 'draft', 'reviewed', 'finalized', 'sent', 'submitted', 'interviewing', 'rejected', 'offer')"),
        default="saved",
        index=True,
    )

    # Saved Job Tracking
    saved_at = Column(TIMESTAMP(timezone=True), nullable=True)  # When job was saved
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)  # Expiry date (saved_at + 10 days)

    # User Customizations
    user_edits = Column(JSONB, nullable=True)  # User modifications

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    job = relationship("Job", backref="applications")
    cv = relationship("CV", backref="applications")


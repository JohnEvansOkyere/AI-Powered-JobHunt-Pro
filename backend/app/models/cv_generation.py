"""Private, editable CV drafts generated for a specific job."""

import uuid

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CVGeneration(Base):
    __tablename__ = "cv_generations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_cv_id = Column(
        UUID(as_uuid=True), ForeignKey("cvs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content = Column(JSONB, nullable=False)
    ai_content = Column(JSONB, nullable=False)
    source_content_hash = Column(Text, nullable=False)
    revision = Column(Integer, nullable=False, default=1)
    ai_provider = Column(Text, nullable=True)
    prompt_version = Column(Text, nullable=False, default="cv-tailor-v1")
    validation_warnings = Column(JSONB, nullable=False, default=list)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    source_cv = relationship("CV")
    job = relationship("Job")
    revisions = relationship(
        "CVGenerationRevision", cascade="all, delete-orphan", back_populates="generation"
    )

    __table_args__ = (
        CheckConstraint("revision >= 1", name="cv_generations_revision_positive"),
    )


class CVGenerationRevision(Base):
    __tablename__ = "cv_generation_revisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cv_generations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revision = Column(Integer, nullable=False)
    content = Column(JSONB, nullable=False)
    change_source = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    generation = relationship("CVGeneration", back_populates="revisions")

    __table_args__ = (
        CheckConstraint(
            "change_source IN ('ai', 'user', 'reset', 'restore')",
            name="cv_generation_revisions_source_check",
        ),
        UniqueConstraint("generation_id", "revision", name="uq_cv_generation_revision"),
    )

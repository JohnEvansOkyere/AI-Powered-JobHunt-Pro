"""
CV Model

Represents uploaded CV files and their parsed content.
"""

from sqlalchemy import Column, String, Integer, Boolean, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class CV(Base):
    """CV model storing file metadata and parsed content."""

    __tablename__ = "cvs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # File Information
    file_name = Column(Text, nullable=False)
    file_path = Column(Text, nullable=False)  # Supabase Storage path
    file_size = Column(Integer, nullable=True)  # Size in bytes
    file_type = Column(String(10), nullable=True)  # 'pdf' or 'docx'
    mime_type = Column(String(100), nullable=True)

    # Parsed Content
    parsed_content = Column(JSONB, nullable=True)  # Structured data
    raw_text = Column(Text, nullable=True)  # Full text content

    # Status
    parsing_status = Column(
        String(20),
        CheckConstraint("parsing_status IN ('pending', 'processing', 'completed', 'failed')"),
        default="pending",
        index=True,
    )
    parsing_error = Column(Text, nullable=True)

    # Metadata
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


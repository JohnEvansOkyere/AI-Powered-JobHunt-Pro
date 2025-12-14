"""
User Model

Represents user information synced from Supabase Auth.
This extends auth.users with additional metadata accessible via SQLAlchemy.
"""

from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class User(Base):
    """User model synced from Supabase Auth."""

    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True)  # References auth.users(id)
    
    # User Information
    email = Column(Text, nullable=True, index=True)
    full_name = Column(Text, nullable=True)
    avatar_url = Column(Text, nullable=True)
    
    # Account Status
    is_active = Column(Boolean, default=True, index=True)
    email_verified = Column(Boolean, default=False)
    
    # Metadata
    last_login_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Additional metadata (renamed from 'metadata' to avoid SQLAlchemy conflict)
    user_metadata = Column("metadata", JSONB, default={}, nullable=True)


"""First-party product analytics models."""

import uuid

from sqlalchemy import Column, Integer, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.core.database import Base


class AnalyticsSession(Base):
    __tablename__ = "analytics_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True)
    anonymous_id = Column(String(80), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    landing_path = Column(Text, nullable=True)
    last_path = Column(Text, nullable=True)
    referrer = Column(Text, nullable=True)
    acquisition_source = Column(String(80), nullable=True, index=True)
    acquisition_medium = Column(String(80), nullable=True)
    acquisition_campaign = Column(String(160), nullable=True)
    acquisition_content = Column(String(160), nullable=True)
    acquisition_term = Column(String(160), nullable=True)
    user_agent = Column(Text, nullable=True)
    page_views = Column(Integer, nullable=False, default=0)
    event_count = Column(Integer, nullable=False, default=0)
    engaged_seconds = Column(Integer, nullable=False, default=0)
    first_seen_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    last_seen_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    ended_at = Column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_analytics_sessions_anonymous_first_seen", "anonymous_id", "first_seen_at"),
        Index("idx_analytics_sessions_user_last_seen", "user_id", "last_seen_at"),
        Index("idx_analytics_sessions_acquisition", "acquisition_source", "acquisition_medium", "first_seen_at"),
    )


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    anonymous_id = Column(String(80), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    event_name = Column(String(60), nullable=False, index=True)
    path = Column(Text, nullable=False)
    referrer = Column(Text, nullable=True)
    target = Column(Text, nullable=True)
    label = Column(Text, nullable=True)
    event_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    duration_ms = Column(Integer, nullable=True)
    user_agent = Column(Text, nullable=True)
    occurred_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_analytics_events_name_occurred", "event_name", "occurred_at"),
        Index("idx_analytics_events_path_occurred", "path", "occurred_at"),
    )

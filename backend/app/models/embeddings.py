"""Cached vector embeddings for jobs and users.

Mirrors the ``job_embeddings`` and ``user_embeddings`` tables created in
``migrations/008_recommendations_v2.sql`` (see ``docs/RECOMMENDATIONS_V2_PLAN.md`` §5.1).

Dimension is fixed at 768 (Gemini ``text-embedding-004``). Every row is
model-tagged; queries against these tables MUST filter on ``model`` so a
mid-migration dataset with mixed providers doesn't silently mix dims.
"""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.core.database import Base

# pgvector.sqlalchemy.Vector is the canonical SQLAlchemy type for pgvector
# columns. If the library is missing (e.g. in a thin test environment),
# fall back to ARRAY(DOUBLE PRECISION) so the ORM still loads; behavior at
# the DB level is still driven by the pgvector migration.
try:  # pragma: no cover - import-time fallback
    from pgvector.sqlalchemy import Vector as _VectorCol

    def _vector_column(dim: int) -> Column:
        return Column(_VectorCol(dim), nullable=False)
except ImportError:  # pragma: no cover - import-time fallback
    from sqlalchemy import ARRAY, Float

    def _vector_column(dim: int) -> Column:  # noqa: ARG001 - dim enforced at DB
        return Column(ARRAY(Float), nullable=False)


EMBEDDING_DIM = 768  # Gemini text-embedding-004


class JobEmbedding(Base):
    """One vector per job, produced by a single embedding model."""

    __tablename__ = "job_embeddings"

    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    embedding = _vector_column(EMBEDDING_DIM)
    model = Column(Text, nullable=False, default="text-embedding-004")
    source_hash = Column(Text, nullable=False)
    embedded_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_job_embeddings_model", "model"),
    )


class UserEmbedding(Base):
    """One vector per user, refreshed when the profile or CV changes."""

    __tablename__ = "user_embeddings"

    user_id = Column(UUID(as_uuid=True), primary_key=True)
    embedding = _vector_column(EMBEDDING_DIM)
    model = Column(Text, nullable=False, default="text-embedding-004")
    source_hash = Column(Text, nullable=False)
    embedded_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_user_embeddings_model", "model"),
    )

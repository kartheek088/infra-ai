import uuid
from sqlalchemy import Column, Integer, Float, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class RAGMetrics(Base):
    __tablename__ = "rag_metrics"
    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id              = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id         = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    chunks_retrieved    = Column(Integer, default=0)
    chunks_used         = Column(Integer, default=0)
    context_fill_pct    = Column(Float, default=0.0)
    avg_relevance_score = Column(Float, default=0.0)
    embedding_tokens    = Column(Integer, default=0)
    has_duplicates      = Column(Boolean, default=False)
    recorded_at         = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    DateTime, Text, JSON, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query = Column(Text, nullable=False)
    final_answer = Column(Text, nullable=True)

    hallucination_score = Column(Integer, nullable=True)
    retry_count = Column(Integer, default=0)

    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)

    wall_time_ms = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    trigger_source = Column(String(32), default="api")

    celery_task_id = Column(String(64), nullable=True)

    status = Column(String(16), default="running")
    error_message = Column(Text, nullable=True)

    raw_state = Column(JSON, nullable=True)

    agent_events = relationship(
        "AgentEvent", back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_pipeline_runs_created_at", "created_at"),
        Index("ix_pipeline_runs_status", "status"),
        Index("ix_pipeline_runs_celery_task_id", "celery_task_id"),
    )


class AgentEvent(Base):
    __tablename__ = "agent_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
    )

    agent_name = Column(String(32), nullable=False)
    latency_ms = Column(Float, nullable=True)
    hallucination_score = Column(Integer, nullable=True)
    rag_used = Column(Boolean, default=False)
    output_preview = Column(String(500), nullable=True)

    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    run = relationship("PipelineRun", back_populates="agent_events")

    __table_args__ = (
        Index("ix_agent_events_run_id", "run_id"),
        Index("ix_agent_events_agent_name", "agent_name"),
    )

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime

from db.session import get_session
from db import repository as repo

router = APIRouter(prefix="/history", tags=["history"])


# ── Response models ───────────────────────────────────────────────────────────

class AgentEventOut(BaseModel):
    agent_name: str
    latency_ms: Optional[float]
    hallucination_score: Optional[int]
    rag_used: bool
    output_preview: Optional[str]
    prompt_tokens: int
    completion_tokens: int
    created_at: datetime

    class Config:
        from_attributes = True


class RunOut(BaseModel):
    id: uuid.UUID
    query: str
    status: str
    hallucination_score: Optional[int]
    retry_count: int
    prompt_tokens: int
    completion_tokens: int
    wall_time_ms: Optional[float]
    trigger_source: str
    celery_task_id: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    agent_events: list[AgentEventOut] = []

    class Config:
        from_attributes = True


class RunSummary(BaseModel):
    id: uuid.UUID
    query: str
    status: str
    hallucination_score: Optional[int]
    wall_time_ms: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[RunSummary])
async def list_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
):
    async with get_session() as session:
        runs = await repo.list_runs(session, limit=limit, offset=offset, status=status)
    return runs


@router.get("/stats")
async def get_stats():
    async with get_session() as session:
        return await repo.get_stats(session)


@router.get("/{run_id}", response_model=RunOut)
async def get_run(run_id: uuid.UUID):
    async with get_session() as session:
        run = await repo.get_run(session, run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run

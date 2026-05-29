from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import PipelineRun, AgentEvent


async def create_run(
    session: AsyncSession,
    query: str,
    trigger_source: str = "api",
    celery_task_id: str | None = None,
) -> PipelineRun:
    run = PipelineRun(
        query=query,
        trigger_source=trigger_source,
        celery_task_id=celery_task_id,
        status="running",
    )
    session.add(run)
    await session.flush()
    return run


async def complete_run(
    session: AsyncSession,
    run: PipelineRun,
    result: dict,
) -> PipelineRun:
    run.final_answer = result.get("final_answer", "")
    run.hallucination_score = result.get("hallucination_score")
    run.retry_count = result.get("retry_count", 0)
    run.prompt_tokens = result.get("token_usage", {}).get("prompt", 0)
    run.completion_tokens = result.get("token_usage", {}).get("completion", 0)
    run.wall_time_ms = result.get("wall_time_ms")
    run.completed_at = datetime.now(timezone.utc)
    run.status = "success"
    run.raw_state = {
        "latency_ms": result.get("latency_ms", {}),
        "token_usage": result.get("token_usage", {}),
    }

    for agent_name, latency in result.get("latency_ms", {}).items():
        event = AgentEvent(
            run_id=run.id,
            agent_name=agent_name,
            latency_ms=latency,
            hallucination_score=result.get("hallucination_score") if agent_name == "critic" else None,
        )
        session.add(event)

    return run


async def fail_run(
    session: AsyncSession,
    run: PipelineRun,
    error: str,
) -> PipelineRun:
    run.status = "error"
    run.error_message = error[:1000]
    run.completed_at = datetime.now(timezone.utc)
    return run


async def get_run(
    session: AsyncSession,
    run_id: uuid.UUID,
) -> Optional[PipelineRun]:
    result = await session.execute(
        select(PipelineRun)
        .options(selectinload(PipelineRun.agent_events))
        .where(PipelineRun.id == run_id)
    )
    return result.scalar_one_or_none()


async def list_runs(
    session: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
) -> list[PipelineRun]:
    q = select(PipelineRun).order_by(desc(PipelineRun.created_at)).limit(limit).offset(offset)
    if status:
        q = q.where(PipelineRun.status == status)
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_stats(session: AsyncSession) -> dict:
    total = await session.scalar(select(func.count(PipelineRun.id)))
    success = await session.scalar(
        select(func.count(PipelineRun.id)).where(PipelineRun.status == "success")
    )
    avg_score = await session.scalar(
        select(func.avg(PipelineRun.hallucination_score)).where(
            PipelineRun.status == "success"
        )
    )
    avg_wall = await session.scalar(
        select(func.avg(PipelineRun.wall_time_ms)).where(PipelineRun.status == "success")
    )
    return {
        "total_runs": total or 0,
        "successful_runs": success or 0,
        "error_runs": (total or 0) - (success or 0),
        "avg_hallucination_score": round(float(avg_score), 2) if avg_score else None,
        "avg_wall_time_ms": round(float(avg_wall), 2) if avg_wall else None,
    }

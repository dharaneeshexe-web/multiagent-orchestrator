"""
api/jobs.py — Job submission and result polling endpoints.

Endpoints:
  POST /jobs              — submit query as background Celery task, returns job_id
  GET  /jobs/{job_id}     — poll task status and result
  GET  /jobs/{job_id}/wait — long-poll until complete (up to timeout seconds)
  GET  /worker/health     — ping Celery worker via smoke test task
"""

from __future__ import annotations

import asyncio
import time

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from worker.celery_app import celery_app
from worker.tasks import run_agent_pipeline, health_check

router = APIRouter()


# ── Models ────────────────────────────────────────────────────────────────────

class JobRequest(BaseModel):
    query: str
    priority: bool = False


class JobSubmitted(BaseModel):
    job_id: str
    status: str
    queue: str


class JobStatus(BaseModel):
    job_id: str
    status: str          # PENDING | STARTED | SUCCESS | FAILURE | RETRY
    result: dict | None = None
    error: str | None = None
    ready: bool = False


# ── Helpers ───────────────────────────────────────────────────────────────────

def _serialize_result(res: AsyncResult) -> JobStatus:
    state = res.state
    result = None
    error = None

    if state == "SUCCESS":
        result = res.result
    elif state == "FAILURE":
        error = str(res.result)

    return JobStatus(
        job_id=res.id,
        status=state,
        result=result,
        error=error,
        ready=res.ready(),
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/jobs", response_model=JobSubmitted)
async def submit_job(req: JobRequest):
    """
    Submit a query as a background task.
    Returns immediately with a job_id — poll /jobs/{job_id} for the result.
    """
    task_name = "worker.tasks.run_agent_pipeline_priority" if req.priority else "worker.tasks.run_agent_pipeline"
    queue = "priority" if req.priority else "default"

    task = celery_app.send_task(task_name, args=[req.query], queue=queue)

    return JobSubmitted(job_id=task.id, status="PENDING", queue=queue)


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str):
    """Poll job status. Call repeatedly until ready=true."""
    res = AsyncResult(job_id, app=celery_app)
    return _serialize_result(res)


@router.get("/jobs/{job_id}/wait", response_model=JobStatus)
async def wait_for_job(job_id: str, timeout: int = 120):
    """
    Long-poll — waits up to `timeout` seconds for the job to complete.
    Polls every 2 seconds internally. Returns as soon as ready.
    """
    deadline = time.time() + timeout
    res = AsyncResult(job_id, app=celery_app)

    while time.time() < deadline:
        if res.ready():
            return _serialize_result(res)
        await asyncio.sleep(2)
        res = AsyncResult(job_id, app=celery_app)  # refresh

    raise HTTPException(status_code=408, detail=f"Job {job_id} not ready after {timeout}s")


@router.get("/worker/health")
async def worker_health():
    """
    Sends a smoke test task to Celery and waits up to 10s for a response.
    Returns worker alive status.
    """
    try:
        result = health_check.apply_async(timeout=10)
        response = await asyncio.to_thread(result.get, timeout=10)
        return {"status": "ok", "worker": response}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Worker unreachable: {str(exc)}")

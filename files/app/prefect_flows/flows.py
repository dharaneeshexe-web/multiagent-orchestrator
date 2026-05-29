from __future__ import annotations

import asyncio
import time
from typing import Optional

from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from datetime import timedelta

from graph.state import AgentState
from graph.workflow import workflow
from db.session import get_session
from db.repository import create_run, complete_run, fail_run, get_stats
from rag.ingest import ingest_raw


# ── Tasks ─────────────────────────────────────────────────────────────────────

@task(
    name="run-agent-pipeline",
    retries=2,
    retry_delay_seconds=10,
    cache_key_fn=None,
    timeout_seconds=180,
)
def run_pipeline_task(query: str) -> dict:
    logger = get_run_logger()
    logger.info("Running pipeline for: %s", query[:80])

    t0 = time.time()
    state = AgentState(query=query)
    result = workflow.invoke(state)
    result["wall_time_ms"] = round((time.time() - t0) * 1000, 2)

    logger.info(
        "Pipeline complete — score=%s retries=%s wall_time=%.0fms",
        result["hallucination_score"],
        result["retry_count"],
        result["wall_time_ms"],
    )
    return result


@task(name="persist-run-result", retries=1, retry_delay_seconds=5)
async def persist_result_task(query: str, result: dict, trigger_source: str = "prefect") -> str:
    async with get_session() as session:
        run = await create_run(session, query=query, trigger_source=trigger_source)
        await complete_run(session, run, result)
    return str(run.id)


@task(name="ingest-url", retries=1, retry_delay_seconds=5)
async def ingest_url_task(url: str) -> int:
    import httpx, re
    logger = get_run_logger()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
    text = re.sub(r"<[^>]+>", " ", resp.text)
    text = re.sub(r"\s+", " ", text).strip()
    n = ingest_raw(text, source=url)
    logger.info("Ingested %d vectors from %s", n, url)
    return n


@task(name="db-purge-old-runs")
async def purge_old_runs_task(days: int = 30) -> int:
    from sqlalchemy import delete, text
    from db.session import get_session

    async with get_session() as session:
        result = await session.execute(
            text(
                "DELETE FROM pipeline_runs "
                "WHERE created_at < NOW() - INTERVAL ':days days' "
                "AND status != 'running'"
            ).bindparams(days=days)
        )
        deleted = result.rowcount
    return deleted


@task(name="db-compute-stats")
async def compute_stats_task() -> dict:
    async with get_session() as session:
        return await get_stats(session)


# ── Flows ─────────────────────────────────────────────────────────────────────

@flow(
    name="scheduled-pipeline-run",
    description="Run the agent pipeline for a query on a schedule",
    retries=1,
    retry_delay_seconds=30,
)
async def scheduled_pipeline_run(query: str, trigger_source: str = "prefect_schedule") -> dict:
    logger = get_run_logger()
    logger.info("Scheduled run starting for: %s", query)

    result = run_pipeline_task(query)
    run_id = await persist_result_task(query, result, trigger_source)

    logger.info("Run persisted with id: %s", run_id)
    return {"run_id": run_id, **result}


@flow(
    name="db-maintenance",
    description="Purge old runs and log aggregate stats",
)
async def db_maintenance_flow(purge_days: int = 30) -> dict:
    logger = get_run_logger()
    deleted = await purge_old_runs_task(purge_days)
    stats = await compute_stats_task()
    logger.info("Maintenance complete — deleted=%d stats=%s", deleted, stats)
    return {"deleted_runs": deleted, "stats": stats}


@flow(
    name="bulk-ingest",
    description="Ingest multiple URLs into Qdrant in parallel",
)
async def bulk_ingest_flow(urls: list[str]) -> dict:
    logger = get_run_logger()
    logger.info("Bulk ingesting %d URLs", len(urls))

    total = 0
    for i in range(0, len(urls), 5):
        batch = urls[i:i+5]
        counts = await asyncio.gather(*[ingest_url_task(url) for url in batch])
        total += sum(counts)

    logger.info("Bulk ingest complete — %d total vectors", total)
    return {"urls_processed": len(urls), "vectors_added": total}

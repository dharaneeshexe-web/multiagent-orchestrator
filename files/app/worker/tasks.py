"""
worker/tasks.py — Celery task definitions.

Tasks:
  run_agent_pipeline          — submit a query, run full agent DAG in background
  run_agent_pipeline_priority — same, but routed to priority queue
  health_check                — smoke test task for monitoring
"""

from __future__ import annotations

import time
from typing import Any

from celery import Task
from celery.utils.log import get_task_logger

from worker.celery_app import celery_app
from graph.state import AgentState
from graph.workflow import workflow

logger = get_task_logger(__name__)


# ── Base task with retry behaviour ────────────────────────────────────────────

class AgentTask(Task):
    """
    Base class for all agent tasks.
    Provides structured error logging and dead-letter routing on final failure.
    """
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            "Task %s FAILED after all retries. Error: %s",
            task_id, str(exc), exc_info=True
        )
        # Route to dead-letter queue for inspection
        celery_app.send_task(
            "worker.tasks.dead_letter_sink",
            args=[task_id, str(exc), kwargs],
            queue="dead_letter",
        )

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning("Task %s RETRYING. Reason: %s", task_id, str(exc))

    def on_success(self, retval, task_id, args, kwargs):
        logger.info("Task %s SUCCEEDED. Wall time: %s ms", task_id, retval.get("wall_time_ms"))


# ── Tasks ─────────────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    base=AgentTask,
    name="worker.tasks.run_agent_pipeline",
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(Exception,),
    retry_backoff=True,          # exponential: 5s, 10s, 20s
    retry_backoff_max=60,
    retry_jitter=True,
)
def run_agent_pipeline(self, query: str) -> dict[str, Any]:
    """
    Run the full LangGraph multi-agent pipeline as a background Celery task.

    Returns a result dict stored in Redis backend, retrievable by task_id.
    """
    logger.info("Starting agent pipeline for query: %s", query[:80])
    t0 = time.time()

    try:
        initial_state = AgentState(query=query)
        result = workflow.invoke(initial_state)

        wall_time = round((time.time() - t0) * 1000, 2)

        return {
            "query": query,
            "final_answer": result["final_answer"],
            "hallucination_score": result["hallucination_score"],
            "retry_count": result["retry_count"],
            "token_usage": result["token_usage"],
            "latency_ms": result["latency_ms"],
            "wall_time_ms": wall_time,
            "task_id": self.request.id,
        }

    except Exception as exc:
        logger.error("Pipeline error: %s", str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    base=AgentTask,
    name="worker.tasks.run_agent_pipeline_priority",
    max_retries=3,
    default_retry_delay=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=30,
    retry_jitter=True,
)
def run_agent_pipeline_priority(self, query: str) -> dict[str, Any]:
    """Priority variant — identical logic, different queue for SLA separation."""
    return run_agent_pipeline.run(self, query)


@celery_app.task(
    name="worker.tasks.dead_letter_sink",
    queue="dead_letter",
    ignore_result=True,
)
def dead_letter_sink(failed_task_id: str, error: str, kwargs: dict) -> None:
    """Receives exhausted tasks for logging/alerting. Extend to Slack/PagerDuty in Phase 5."""
    logger.critical(
        "DEAD LETTER — task_id=%s error=%s kwargs=%s",
        failed_task_id, error, kwargs
    )


@celery_app.task(name="worker.tasks.health_check")
def health_check() -> dict:
    """Smoke test — used by /worker/health endpoint."""
    return {"status": "ok", "worker": "alive", "timestamp": time.time()}

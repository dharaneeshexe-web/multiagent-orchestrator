"""
observability/metrics.py — Custom business metrics for the agent pipeline.

Metrics exposed on /metrics (Prometheus scrape):
  agent_latency_ms          histogram  — per-agent wall time
  pipeline_tokens_total     counter    — prompt + completion tokens
  hallucination_score       histogram  — critic score distribution
  pipeline_retries_total    counter    — retry loop count
  pipeline_runs_total       counter    — total pipeline invocations
  rag_chunks_retrieved      histogram  — RAG retrieval count per query
  job_queue_depth           gauge      — Celery queue depth (sampled)
"""

from __future__ import annotations

from opentelemetry import metrics

_meter = metrics.get_meter("multiagent.orchestrator")

# ── Histograms ────────────────────────────────────────────────────────────────
agent_latency = _meter.create_histogram(
    name="agent_latency_ms",
    description="Per-agent execution latency in milliseconds",
    unit="ms",
)

hallucination_score_hist = _meter.create_histogram(
    name="hallucination_score",
    description="Critic hallucination score (1=clean, 10=severe)",
    unit="1",
)

rag_chunks_hist = _meter.create_histogram(
    name="rag_chunks_retrieved",
    description="Number of RAG chunks retrieved per query",
    unit="1",
)

# ── Counters ──────────────────────────────────────────────────────────────────
tokens_counter = _meter.create_counter(
    name="pipeline_tokens_total",
    description="Total LLM tokens consumed (prompt + completion)",
    unit="1",
)

retry_counter = _meter.create_counter(
    name="pipeline_retries_total",
    description="Total hallucination-triggered research retries",
    unit="1",
)

pipeline_runs_counter = _meter.create_counter(
    name="pipeline_runs_total",
    description="Total pipeline invocations",
    unit="1",
)

error_counter = _meter.create_counter(
    name="pipeline_errors_total",
    description="Total pipeline errors by stage",
    unit="1",
)

# ── Gauges ────────────────────────────────────────────────────────────────────
queue_depth_gauge = _meter.create_up_down_counter(
    name="job_queue_depth",
    description="Current Celery job queue depth",
    unit="1",
)


# ── Recording helpers ─────────────────────────────────────────────────────────

def record_pipeline_result(result: dict) -> None:
    """
    Record all metrics from a completed pipeline result dict.
    Called from run_endpoint, stream_workflow final event, and Celery task.
    """
    pipeline_runs_counter.add(1, {"status": "success"})

    # Per-agent latency
    for agent, ms in result.get("latency_ms", {}).items():
        agent_latency.record(ms, {"agent": agent})

    # Token usage
    usage = result.get("token_usage", {})
    if usage.get("prompt"):
        tokens_counter.add(usage["prompt"], {"type": "prompt"})
    if usage.get("completion"):
        tokens_counter.add(usage["completion"], {"type": "completion"})

    # Hallucination score
    score = result.get("hallucination_score", 0)
    if score:
        hallucination_score_hist.record(score)

    # Retries
    retries = result.get("retry_count", 0)
    if retries:
        retry_counter.add(retries)


def record_pipeline_error(stage: str) -> None:
    pipeline_runs_counter.add(1, {"status": "error"})
    error_counter.add(1, {"stage": stage})


def record_rag_retrieval(n_chunks: int) -> None:
    rag_chunks_hist.record(n_chunks)

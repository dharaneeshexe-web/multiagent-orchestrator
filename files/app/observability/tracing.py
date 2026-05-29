"""
observability/tracing.py — Span helpers for agent nodes and API handlers.

Usage:
    from observability.tracing import traced_agent

    @traced_agent("planner")
    def planner_node(state): ...
"""

from __future__ import annotations

import functools
import time
from typing import Callable, Any

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from observability.telemetry import get_tracer


def traced_agent(agent_name: str):
    """
    Decorator for LangGraph agent node functions.
    Creates a span with agent name, records latency + hallucination score as attributes.
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(state, *args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(f"agent.{agent_name}") as span:
                span.set_attribute("agent.name", agent_name)
                span.set_attribute("query.length", len(state.query))
                span.set_attribute("retry_count", state.retry_count)

                t0 = time.time()
                try:
                    result = fn(state, *args, **kwargs)
                    elapsed = round((time.time() - t0) * 1000, 2)

                    span.set_attribute("latency_ms", elapsed)

                    if agent_name == "critic" and isinstance(result, dict):
                        score = result.get("hallucination_score", 0)
                        span.set_attribute("hallucination_score", score)

                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as exc:
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    span.record_exception(exc)
                    raise

        return wrapper
    return decorator


def traced_endpoint(operation_name: str):
    """
    Decorator for FastAPI route handlers.
    Adds query text and result metadata as span attributes.
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(f"http.{operation_name}") as span:
                # Extract query from kwargs if present
                req = kwargs.get("req")
                if req and hasattr(req, "query"):
                    span.set_attribute("query", req.query[:200])

                try:
                    result = await fn(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as exc:
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    span.record_exception(exc)
                    raise

        return wrapper
    return decorator


def get_current_span() -> trace.Span:
    return trace.get_current_span()


def add_span_event(name: str, attributes: dict[str, Any] | None = None) -> None:
    span = trace.get_current_span()
    span.add_event(name, attributes=attributes or {})

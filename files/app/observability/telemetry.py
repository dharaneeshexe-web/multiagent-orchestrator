"""
observability/telemetry.py — OpenTelemetry SDK bootstrap.

Sets up:
  - TracerProvider  → OTLP gRPC exporter → Jaeger / OTEL Collector
  - MeterProvider   → Prometheus exporter (scraped by Prometheus on /metrics)
  - Automatic instrumentation for FastAPI, httpx, redis

Call setup_telemetry() once at application startup.
"""

from __future__ import annotations

import os
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

from config.settings import settings

_tracer: Optional[trace.Tracer] = None
_meter: Optional[metrics.Meter] = None


def setup_telemetry(app=None) -> None:
    """
    Initialise OTEL tracing + Prometheus metrics.
    Call once at FastAPI startup.
    """
    global _tracer, _meter

    resource = Resource.create({
        "service.name": "multiagent-orchestrator",
        "service.version": "5.0.0",
        "deployment.environment": os.getenv("ENV", "development"),
    })

    # ── Tracing → OTLP (Jaeger) ───────────────────────────────────────────
    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.otlp_endpoint,
        insecure=True,
    )
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(tracer_provider)
    _tracer = trace.get_tracer("multiagent.orchestrator")

    # ── Metrics → Prometheus ──────────────────────────────────────────────
    prometheus_reader = PrometheusMetricReader()
    meter_provider = MeterProvider(resource=resource, metric_readers=[prometheus_reader])
    metrics.set_meter_provider(meter_provider)
    _meter = metrics.get_meter("multiagent.orchestrator")

    # ── Auto-instrument libraries ─────────────────────────────────────────
    if app is not None:
        FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    RedisInstrumentor().instrument()


def get_tracer() -> trace.Tracer:
    if _tracer is None:
        return trace.get_tracer("multiagent.orchestrator")
    return _tracer


def get_meter() -> metrics.Meter:
    if _meter is None:
        return metrics.get_meter("multiagent.orchestrator")
    return _meter

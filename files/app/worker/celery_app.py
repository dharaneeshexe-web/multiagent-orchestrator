"""
worker/celery_app.py — Celery application factory.

Broker  : Redis (task queue)
Backend : Redis (result storage)
Retries : exponential backoff, max 3 attempts
Dead-letter: tasks that exhaust retries are routed to a dead_letter queue
"""

from __future__ import annotations

from celery import Celery
from kombu import Exchange, Queue

from config.settings import settings

# ── Queues ────────────────────────────────────────────────────────────────────
default_exchange = Exchange("default", type="direct")
dead_letter_exchange = Exchange("dead_letter", type="direct")

CELERY_QUEUES = (
    Queue("default",     default_exchange,     routing_key="default"),
    Queue("priority",    default_exchange,     routing_key="priority"),
    Queue("dead_letter", dead_letter_exchange, routing_key="dead_letter"),
)

# ── App ───────────────────────────────────────────────────────────────────────
celery_app = Celery(
    "multiagent",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["worker.tasks"],
)

celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Queues
    task_queues=CELERY_QUEUES,
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",

    # Routing: priority tasks get their own queue
    task_routes={
        "worker.tasks.run_agent_pipeline": {"queue": "default"},
        "worker.tasks.run_agent_pipeline_priority": {"queue": "priority"},
    },

    # Results
    result_expires=3600,          # keep results 1 hour
    task_track_started=True,

    # Retries & timeouts
    task_acks_late=True,          # ack only after task completes (safe retries)
    task_reject_on_worker_lost=True,
    task_soft_time_limit=120,     # soft kill at 2 min
    task_time_limit=180,          # hard kill at 3 min

    # Worker
    worker_prefetch_multiplier=1, # one task per worker at a time (fair dispatch)
    worker_max_tasks_per_child=50,# recycle worker after 50 tasks (memory safety)

    # Timezone
    timezone="UTC",
    enable_utc=True,
)

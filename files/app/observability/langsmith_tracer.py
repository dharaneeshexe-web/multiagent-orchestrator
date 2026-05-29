"""
observability/langsmith_tracer.py — LangSmith run tracing for LangGraph pipeline.

When LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY is set, every LangGraph
invocation is automatically traced by LangChain's callback system.

This module provides:
  - setup_langsmith()     — configure env vars so LangGraph picks up tracing
  - get_run_url()         — return the LangSmith URL for the latest run
  - LangSmithCallbackHandler — explicit callback for manual instrumentation
"""

from __future__ import annotations

import os
import logging

logger = logging.getLogger(__name__)


def setup_langsmith() -> bool:
    """
    Configure LangSmith tracing via environment variables.
    Returns True if tracing is enabled, False otherwise.
    LangGraph reads these env vars automatically at invoke time.
    """
    from config.settings import settings

    if not settings.langchain_tracing_v2 or not settings.langchain_api_key:
        logger.info("LangSmith tracing disabled (LANGCHAIN_TRACING_V2=false or no API key)")
        return False

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"

    logger.info("LangSmith tracing enabled → project: %s", settings.langchain_project)
    return True


def get_langsmith_callback():
    """
    Return a LangSmith callback handler for explicit use in LLM calls.
    Returns None if tracing is not configured.
    """
    try:
        from langsmith import Client
        from langchain_core.tracers import LangChainTracer
        from config.settings import settings

        if not settings.langchain_api_key:
            return None

        client = Client(api_key=settings.langchain_api_key)
        return LangChainTracer(
            project_name=settings.langchain_project,
            client=client,
        )
    except Exception as exc:
        logger.warning("Could not create LangSmith callback: %s", exc)
        return None

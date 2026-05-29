"""
agents/planner.py — Decomposes the user query into an ordered research plan.
Retries with fallback model on failure.
"""

from __future__ import annotations

import time
import re

from tenacity import retry, stop_after_attempt, wait_exponential
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import AgentState
from config.settings import settings
from observability.tracing import traced_agent

_SYSTEM = """You are a strategic planning agent in a multi-agent AI system.

Given a user query, decompose it into 3–5 concrete, sequential research sub-tasks.
Each sub-task should be on its own numbered line.
Be specific — each step should be resolvable by a research agent.

Respond ONLY with the numbered list. No preamble, no explanation."""


def _build_llm(model: str) -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=model,
        temperature=0.3,
        max_tokens=512,
    )


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
def _call_llm(query: str) -> tuple[str, dict]:
    """Try primary model, fallback on second attempt handled by tenacity retry wrapper."""
    try:
        llm = _build_llm(settings.primary_model)
        response = llm.invoke([
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=query),
        ])
    except Exception:
        llm = _build_llm(settings.fallback_model)
        response = llm.invoke([
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=query),
        ])

    usage = {}
    if hasattr(response, "response_metadata"):
        meta = response.response_metadata.get("token_usage", {})
        usage = {
            "prompt": meta.get("prompt_tokens", 0),
            "completion": meta.get("completion_tokens", 0),
        }
    return response.content, usage


@traced_agent("planner")
def planner_node(state: AgentState) -> dict:
    t0 = time.time()
    content, usage = _call_llm(state.query)

    # Parse numbered list into clean plan steps
    plan = [
        re.sub(r"^\d+[\.\)]\s*", "", line).strip()
        for line in content.strip().splitlines()
        if line.strip() and re.match(r"^\d", line.strip())
    ]

    latency = round((time.time() - t0) * 1000, 2)

    return {
        "plan": plan,
        "messages": [{"role": "planner", "content": content}],
        "token_usage": {
            "prompt": state.token_usage.get("prompt", 0) + usage.get("prompt", 0),
            "completion": state.token_usage.get("completion", 0) + usage.get("completion", 0),
        },
        "latency_ms": {**state.latency_ms, "planner": latency},
    }

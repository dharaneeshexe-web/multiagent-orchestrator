"""
graph/state.py — Shared state schema for all agents in the LangGraph DAG.

Dict fields (latency_ms, token_usage, cost_breakdown) use a custom merge
reducer so parallel nodes (critic + cost_monitor) can update them concurrently
without raising INVALID_CONCURRENT_GRAPH_UPDATE.
"""

from __future__ import annotations

import operator
import time
from typing import Annotated, Any
from pydantic import BaseModel, Field


def _merge_dicts(current: dict, new: dict) -> dict:
    """Merge two dicts — new keys overwrite current keys on conflict."""
    merged = dict(current)
    merged.update(new)
    return merged


class AgentState(BaseModel):
    """
    Immutable-style shared state threaded through every node in the graph.
    LangGraph merges updates using the annotated reducer.
    """

    # The original user query — never mutated
    query: str = ""

    # Accumulating message log — each agent appends its output
    messages: Annotated[list[dict[str, Any]], operator.add] = Field(default_factory=list)

    # Planner output: ordered list of sub-tasks
    plan: list[str] = Field(default_factory=list)

    # Researcher output: raw context string
    research_context: str = ""

    # Critic output
    critique: str = ""
    hallucination_score: int = 0   # 1–10; higher = more hallucinated

    # Cost monitor
    cost_estimate: float = 0.0
    cost_breakdown: Annotated[dict[str, Any], _merge_dicts] = Field(default_factory=dict)

    # Executor output: final synthesised answer
    final_answer: str = ""

    # Routing control
    retry_count: int = 0

    # Observability (all use merge reducer for safe parallel updates)
    token_usage: Annotated[dict[str, int], _merge_dicts] = Field(
        default_factory=lambda: {"prompt": 0, "completion": 0}
    )
    latency_ms: Annotated[dict[str, float], _merge_dicts] = Field(default_factory=dict)
    start_time: float = Field(default_factory=time.time)

    class Config:
        arbitrary_types_allowed = True

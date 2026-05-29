"""
api/dispatcher.py — Async dispatcher wrapping the LangGraph workflow.

run_workflow_sync  — runs the full pipeline, returns final state dict
stream_workflow    — async generator yielding per-agent events as they complete

LangGraph's .astream() yields state snapshots after each node completes,
so we emit one SSE/WS event per agent with its output + metadata.
"""

from __future__ import annotations

import asyncio
import time
from typing import AsyncGenerator, Any

from graph.state import AgentState
from graph.workflow import workflow

# Map node names → friendly display names
_AGENT_LABELS = {
    "planner": "Planner",
    "researcher": "Researcher",
    "critic": "Critic",
    "cost_monitor": "Cost Monitor",
    "router_node": "Router",
    "increment_retry": "Retry Counter",
    "executor": "Executor",
}


async def run_workflow_sync(query: str) -> dict[str, Any]:
    """
    Run the full workflow asynchronously and return the final state as a dict.
    Uses asyncio.to_thread so the synchronous LangGraph invoke doesn't block the event loop.
    """
    initial_state = AgentState(query=query)
    result = await asyncio.to_thread(workflow.invoke, initial_state)
    return result


async def stream_workflow(query: str) -> AsyncGenerator[dict[str, Any], None]:
    """
    Async generator that streams per-agent completion events.

    Each yielded dict has the shape:
    {
        "event":     "agent_complete" | "agent_start" | "final" | "error",
        "agent":     str,
        "data":      str,   # agent output or summary
        "meta":      dict,  # latency, score, tokens etc.
        "timestamp": float,
    }
    """
    initial_state = AgentState(query=query)
    seen_agents: set[str] = set()
    last_state: dict[str, Any] = {}

    try:
        # astream yields (node_name, state_update) tuples after each node completes
        async for chunk in workflow.astream(initial_state, stream_mode="updates"):
            for node_name, state_update in chunk.items():
                label = _AGENT_LABELS.get(node_name, node_name)

                # Extract the relevant output for this agent
                agent_output = _extract_output(node_name, state_update)
                meta = _extract_meta(node_name, state_update)

                yield {
                    "event": "agent_complete",
                    "agent": label,
                    "node": node_name,
                    "data": agent_output,
                    "meta": meta,
                    "timestamp": time.time(),
                }

                seen_agents.add(node_name)
                last_state.update(state_update)

        # Emit final summary event
        yield {
            "event": "final",
            "agent": "orchestrator",
            "data": last_state.get("final_answer", ""),
            "meta": {
                "hallucination_score": last_state.get("hallucination_score", 0),
                "retry_count": last_state.get("retry_count", 0),
                "token_usage": last_state.get("token_usage", {}),
                "latency_ms": last_state.get("latency_ms", {}),
                "cost_estimate": last_state.get("cost_estimate", 0),
            },
            "timestamp": time.time(),
        }

    except Exception as exc:
        yield {
            "event": "error",
            "agent": "orchestrator",
            "data": str(exc),
            "meta": {},
            "timestamp": time.time(),
        }


def _extract_output(node_name: str, state_update: dict) -> str:
    """Pull the most relevant text output for a given node's state update."""
    if node_name == "planner":
        plan = state_update.get("plan", [])
        return "\n".join(f"{i+1}. {s}" for i, s in enumerate(plan))
    elif node_name == "researcher":
        return state_update.get("research_context", "")[:500] + "..."
    elif node_name == "critic":
        score = state_update.get("hallucination_score", "?")
        critique = state_update.get("critique", "")[:300]
        return f"[Score {score}/10] {critique}"
    elif node_name == "cost_monitor":
        cost = state_update.get("cost_estimate", 0)
        return f"Estimated cost: ${cost:.6f}"
    elif node_name == "executor":
        return state_update.get("final_answer", "")[:500] + "..."
    elif node_name == "increment_retry":
        return f"Retry #{state_update.get('retry_count', '?')} triggered"
    elif node_name == "router_node":
        return "Routing decision..."
    return str(state_update)[:200]


def _extract_meta(node_name: str, state_update: dict) -> dict:
    """Pull latency and token metadata for a node's update."""
    latency_ms = state_update.get("latency_ms", {})
    agent_latency = latency_ms.get(node_name)
    token_usage = state_update.get("token_usage", {})

    meta: dict = {}
    if agent_latency is not None:
        meta["latency_ms"] = agent_latency
    if node_name == "critic":
        meta["hallucination_score"] = state_update.get("hallucination_score", 0)
    if node_name == "cost_monitor":
        meta["cost_estimate"] = state_update.get("cost_estimate", 0)
    if token_usage:
        meta["tokens"] = token_usage
    return meta

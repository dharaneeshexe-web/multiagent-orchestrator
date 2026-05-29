"""
graph/routing.py — Conditional router after critic node.
If hallucination_score > threshold AND retries remaining → re-run researcher.
Otherwise → executor.
"""

from graph.state import AgentState
from config.settings import settings


def route_after_critic(state: AgentState) -> str:
    """
    Returns:
        "retry_research" — score too high and retries left
        "execute"        — score acceptable or retries exhausted
    """
    score = state.hallucination_score
    retries = state.retry_count
    threshold = settings.hallucination_threshold
    max_retries = settings.max_retry_loops

    if score > threshold and retries < max_retries:
        return "retry_research"

    return "execute"


def increment_retry(state: AgentState) -> dict:
    """Node injected before researcher on retry path — increments counter."""
    return {"retry_count": state.retry_count + 1}


def router_node(state: AgentState) -> dict:
    """Sync point — both critic and cost_monitor have completed.
    Returns empty dict; state changes were already applied by the parallel nodes."""
    return {}

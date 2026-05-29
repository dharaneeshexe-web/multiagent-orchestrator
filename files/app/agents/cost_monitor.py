from __future__ import annotations

import time

from graph.state import AgentState
from config.settings import settings
from observability.tracing import traced_agent


@traced_agent("cost_monitor")
def cost_monitor_node(state: AgentState) -> dict:
    t0 = time.time()

    usage = state.token_usage
    prompt_tokens = usage.get("prompt", 0)
    completion_tokens = usage.get("completion", 0)

    is_fallback = getattr(settings, "primary_model", "") == settings.fallback_model
    in_rate = settings.fallback_input_rate if is_fallback else settings.primary_input_rate
    out_rate = settings.fallback_output_rate if is_fallback else settings.primary_output_rate

    input_cost = (prompt_tokens / 1000) * in_rate
    output_cost = (completion_tokens / 1000) * out_rate
    total = round(input_cost + output_cost, 8)

    latency = round((time.time() - t0) * 1000, 2)

    return {
        "cost_estimate": total,
        "cost_breakdown": {
            "input_cost": round(input_cost, 8),
            "output_cost": round(output_cost, 8),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "model": settings.primary_model,
        },
        "messages": [{
            "role": "cost_monitor",
            "content": f"Estimated inference cost: ${total:.6f}",
            "total_cost": total,
        }],
        "latency_ms": {**state.latency_ms, "cost_monitor": latency},
    }

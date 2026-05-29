"""
agents/critic.py — Scores research context for hallucination risk and provides critique.
Uses temp=0 for deterministic scoring. Parses HALLUCINATION_SCORE from output.
"""

from __future__ import annotations

import re
import time

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import AgentState
from config.settings import settings
from observability.tracing import traced_agent

_SYSTEM = """You are a rigorous fact-checking and hallucination detection agent.

You will receive:
1. The original user query
2. A research context produced by another AI agent

Your job:
- Identify any claims that are speculative, unverifiable, contradictory, or likely hallucinated
- Provide a concise CRITIQUE listing specific issues (or confirm it is solid)
- Assign a HALLUCINATION_SCORE from 1 (no hallucination) to 10 (severe hallucination)

You MUST end your response with exactly this line (replace N with your score):
HALLUCINATION_SCORE: N

Be strict. A score of 5 or above means the research needs to be redone."""


def _build_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.primary_model,
        temperature=0.0,   # deterministic
        max_tokens=800,
    )


@traced_agent("critic")
def critic_node(state: AgentState) -> dict:
    t0 = time.time()

    prompt = (
        f"Original query: {state.query}\n\n"
        f"Research context to evaluate:\n{state.research_context}"
    )

    llm = _build_llm()
    response = llm.invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=prompt),
    ])

    content = response.content

    # Parse HALLUCINATION_SCORE reliably
    match = re.search(r"HALLUCINATION_SCORE\s*:\s*(\d+)", content)
    score = int(match.group(1)) if match else 5  # default conservative

    usage = {}
    if hasattr(response, "response_metadata"):
        meta = response.response_metadata.get("token_usage", {})
        usage = {
            "prompt": meta.get("prompt_tokens", 0),
            "completion": meta.get("completion_tokens", 0),
        }

    latency = round((time.time() - t0) * 1000, 2)

    return {
        "critique": content,
        "hallucination_score": score,
        "messages": [{"role": "critic", "content": content, "score": score}],
        "token_usage": {
            "prompt": state.token_usage.get("prompt", 0) + usage.get("prompt", 0),
            "completion": state.token_usage.get("completion", 0) + usage.get("completion", 0),
        },
        "latency_ms": {**state.latency_ms, "critic": latency},
    }

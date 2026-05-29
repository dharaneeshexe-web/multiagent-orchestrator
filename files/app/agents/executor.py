"""
agents/executor.py — Synthesises a final answer using the research context and critic feedback.
"""

from __future__ import annotations

import time

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import AgentState
from config.settings import settings
from observability.tracing import traced_agent

_SYSTEM = """You are the final synthesis agent in a multi-agent AI pipeline.

You will receive:
1. The original user query
2. Research context gathered by a research agent
3. A critique and hallucination score from a critic agent

Your job:
- Produce a comprehensive, accurate, well-structured final answer to the user query
- Incorporate the critic's feedback — avoid or correct any flagged hallucinations
- Use clear sections with headers where appropriate
- Be thorough but concise — no filler, no repetition

This is the final output the user will see. Make it excellent."""


def _build_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.primary_model,
        temperature=0.4,
        max_tokens=2000,
    )


@traced_agent("executor")
def executor_node(state: AgentState) -> dict:
    t0 = time.time()

    prompt = (
        f"User query: {state.query}\n\n"
        f"Research context:\n{state.research_context}\n\n"
        f"Critic feedback (hallucination score {state.hallucination_score}/10):\n{state.critique}"
    )

    llm = _build_llm()
    response = llm.invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=prompt),
    ])

    usage = {}
    if hasattr(response, "response_metadata"):
        meta = response.response_metadata.get("token_usage", {})
        usage = {
            "prompt": meta.get("prompt_tokens", 0),
            "completion": meta.get("completion_tokens", 0),
        }

    latency = round((time.time() - t0) * 1000, 2)

    return {
        "final_answer": response.content,
        "messages": [{"role": "executor", "content": response.content}],
        "token_usage": {
            "prompt": state.token_usage.get("prompt", 0) + usage.get("prompt", 0),
            "completion": state.token_usage.get("completion", 0) + usage.get("completion", 0),
        },
        "latency_ms": {**state.latency_ms, "executor": latency},
    }

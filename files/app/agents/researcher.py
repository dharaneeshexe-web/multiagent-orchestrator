"""
agents/researcher.py — Executes each plan step and aggregates context.
Phase 4: injects Qdrant RAG context before LLM call.
Falls back gracefully if Qdrant is empty or unreachable.
"""

from __future__ import annotations

import time

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import AgentState
from config.settings import settings
from rag.retriever import retrieve_as_context
from observability.tracing import traced_agent

_SYSTEM = """You are a deep research agent with broad knowledge across science, engineering, and technology.

You will be given:
1. A research plan (list of sub-tasks)
2. The original user query
3. (Optionally) retrieved context chunks from a knowledge base — use these as authoritative sources when available

For EACH sub-task, provide a concise but thorough factual summary (3–5 sentences).
Label each section clearly with the sub-task number.
If retrieved context is provided, cite it and prefer it over general knowledge.
Be factual. Do not hallucinate. If uncertain, say so explicitly."""


def _build_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.primary_model,
        temperature=0.2,
        max_tokens=1500,
    )


@traced_agent("researcher")
def researcher_node(state: AgentState) -> dict:
    t0 = time.time()

    plan_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(state.plan))

    # ── RAG context injection ─────────────────────────────────────────────
    rag_context = retrieve_as_context(state.query, top_k=5)
    rag_section = (
        f"\n\nRetrieved knowledge base context (use as primary source):\n{rag_context}"
        if rag_context and not rag_context.startswith("[RAG unavailable")
        else "\n\n[No RAG context available — using general knowledge]"
    )

    prompt = (
        f"Original query: {state.query}\n\n"
        f"Research plan:\n{plan_text}"
        f"{rag_section}"
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
    rag_used = bool(rag_context and not rag_context.startswith("[RAG unavailable"))

    return {
        "research_context": response.content,
        "messages": [{"role": "researcher", "content": response.content, "rag_used": rag_used}],
        "token_usage": {
            "prompt": state.token_usage.get("prompt", 0) + usage.get("prompt", 0),
            "completion": state.token_usage.get("completion", 0) + usage.get("completion", 0),
        },
        "latency_ms": {**state.latency_ms, "researcher": latency},
    }

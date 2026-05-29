"""
run.py — CLI entry point for Phase 1.
Usage: python run.py "Your query here"
"""

import sys
import time
import json

from dotenv import load_dotenv
load_dotenv()

from graph.state import AgentState
from graph.workflow import workflow


def run(query: str) -> None:
    print("\n" + "=" * 60)
    print(f"  MULTIAGENT ORCHESTRATOR — Phase 1")
    print("=" * 60)
    print(f"  Query: {query}")
    print("=" * 60 + "\n")

    initial_state = AgentState(query=query)
    t0 = time.time()

    result = workflow.invoke(initial_state)

    wall_time = round((time.time() - t0) * 1000, 2)

    # ── Final Answer ──────────────────────────────────────────
    print("\n━━━ FINAL ANSWER ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(result["final_answer"])

    # ── Observability ─────────────────────────────────────────
    print("\n━━━ OBSERVABILITY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Hallucination score : {result['hallucination_score']}/10")
    print(f"  Retry loops         : {result['retry_count']}")
    print(f"  Prompt tokens       : {result['token_usage'].get('prompt', 0)}")
    print(f"  Completion tokens   : {result['token_usage'].get('completion', 0)}")
    print(f"  Wall time           : {wall_time} ms")
    print(f"\n  Per-agent latency:")
    for agent, ms in result.get("latency_ms", {}).items():
        print(f"    {agent:<20} {ms} ms")

    # ── Agent Message Log ─────────────────────────────────────
    print("\n━━━ AGENT MESSAGE LOG ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for msg in result.get("messages", []):
        role = msg.get("role", "unknown").upper()
        preview = msg.get("content", "")[:200].replace("\n", " ")
        print(f"  [{role}] {preview}...")

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Explain how LangGraph works"
    run(query)

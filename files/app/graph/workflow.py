"""
graph/workflow.py — Assembles and compiles the LangGraph StateGraph DAG.

Flow:
  planner → researcher → critic → router_node → [route_decision]
                      ↘ cost_monitor ↗               ├── retry_research → increment_retry → researcher
                                                      └── execute → executor → END

cost_monitor runs in parallel with critic (both after researcher).
router_node is a sync barrier — it fires after both critic and cost_monitor finish.
"""

from langgraph.graph import StateGraph, END

from graph.state import AgentState
from agents.planner import planner_node
from agents.researcher import researcher_node
from agents.critic import critic_node
from agents.cost_monitor import cost_monitor_node
from agents.executor import executor_node
from graph.routing import route_after_critic, increment_retry, router_node


def _route_decision(state: AgentState) -> str:
    """Thin wrapper so the graph can reference it as a callable."""
    return route_after_critic(state)


def build_workflow() -> StateGraph:
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("critic", critic_node)
    graph.add_node("cost_monitor", cost_monitor_node)
    graph.add_node("router_node", router_node)
    graph.add_node("increment_retry", increment_retry)
    graph.add_node("executor", executor_node)

    # Entry point
    graph.set_entry_point("planner")

    # Linear edges
    graph.add_edge("planner", "researcher")

    # Parallel fan-out: researcher → critic + cost_monitor
    graph.add_edge("researcher", "critic")
    graph.add_edge("researcher", "cost_monitor")

    # Sync barrier — waits for BOTH critic and cost_monitor
    graph.add_edge("critic", "router_node")
    graph.add_edge("cost_monitor", "router_node")

    # Conditional routing after sync
    graph.add_conditional_edges(
        "router_node",
        _route_decision,
        {
            "retry_research": "increment_retry",
            "execute": "executor",
        },
    )

    # Retry loop: increment_retry → researcher (loops back)
    graph.add_edge("increment_retry", "researcher")

    # Terminal edge
    graph.add_edge("executor", END)

    return graph.compile()


# Singleton — imported by run.py and later by FastAPI gateway
workflow = build_workflow()

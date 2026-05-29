from __future__ import annotations

import re
from unittest.mock import MagicMock, patch, ANY

import pytest
from langchain_core.messages import AIMessage

from graph.state import AgentState


# ── Planner ────────────────────────────────────────────────────────────────────

class TestPlannerNode:
    @pytest.mark.asyncio
    async def test_planner_generates_plan(self, agent_state: AgentState):
        with patch("agents.planner.ChatGroq") as mock_groq:
            instance = MagicMock()
            instance.invoke.return_value = AIMessage(
                content="1. Explain qubits\n2. Describe entanglement\n3. List applications",
                response_metadata={
                    "token_usage": {"prompt_tokens": 30, "completion_tokens": 45}
                },
            )
            mock_groq.return_value = instance

            from agents.planner import planner_node
            result = planner_node(agent_state)

        assert "plan" in result
        assert len(result["plan"]) == 3
        assert result["plan"][0] == "Explain qubits"
        assert result["token_usage"]["prompt"] == 30
        assert result["token_usage"]["completion"] == 45
        assert "latency_ms" in result

    @pytest.mark.asyncio
    async def test_planner_handles_empty_response(self, agent_state: AgentState):
        with patch("agents.planner.ChatGroq") as mock_groq:
            instance = MagicMock()
            instance.invoke.return_value = AIMessage(
                content="",
                response_metadata={"token_usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            )
            mock_groq.return_value = instance

            from agents.planner import planner_node
            result = planner_node(agent_state)

        assert result["plan"] == []
        assert result["token_usage"]["prompt"] == 0

    @pytest.mark.asyncio
    async def test_planner_accumulates_tokens(self):
        state = AgentState(query="test")
        state.token_usage = {"prompt": 100, "completion": 50}

        with patch("agents.planner.ChatGroq") as mock_groq:
            instance = MagicMock()
            instance.invoke.return_value = AIMessage(
                content="1. Step one",
                response_metadata={
                    "token_usage": {"prompt_tokens": 20, "completion_tokens": 10}
                },
            )
            mock_groq.return_value = instance

            from agents.planner import planner_node
            result = planner_node(state)

        assert result["token_usage"]["prompt"] == 120
        assert result["token_usage"]["completion"] == 60

    @pytest.mark.asyncio
    async def test_planner_strips_numbering(self):
        variants = ["1. Item", "1) Item", "1.Item"]
        state = AgentState(query="test")

        for variant in variants:
            state.plan = []
            with patch("agents.planner.ChatGroq") as mock_groq:
                instance = MagicMock()
                instance.invoke.return_value = AIMessage(
                    content=variant,
                    response_metadata={"token_usage": {}},
                )
                mock_groq.return_value = instance

                from agents.planner import planner_node
                result = planner_node(state)

            assert result["plan"][0] == "Item"


# ── Researcher ─────────────────────────────────────────────────────────────────

class TestResearcherNode:
    @pytest.mark.asyncio
    async def test_researcher_produces_context(self, agent_state: AgentState):
        agent_state.plan = ["Explain qubits"]
        with patch("agents.researcher.ChatGroq") as mock_groq, \
             patch("agents.researcher.retrieve_as_context") as mock_rag:

            mock_rag.return_value = "[RAG unavailable — using general knowledge]"
            instance = MagicMock()
            instance.invoke.return_value = AIMessage(
                content="Qubits are quantum bits that can exist in superposition.",
                response_metadata={"token_usage": {"prompt_tokens": 60, "completion_tokens": 120}},
            )
            mock_groq.return_value = instance

            from agents.researcher import researcher_node
            result = researcher_node(agent_state)

        assert "research_context" in result
        assert "superposition" in result["research_context"]
        assert result["token_usage"]["prompt"] == 60

    @pytest.mark.asyncio
    async def test_researcher_injects_rag_context(self, agent_state: AgentState):
        agent_state.plan = ["Explain qubits"]
        with patch("agents.researcher.ChatGroq") as mock_groq, \
             patch("agents.researcher.retrieve_as_context") as mock_rag:

            mock_rag.return_value = "Authoritative context about qubits from knowledge base."
            instance = MagicMock()
            instance.invoke.return_value = AIMessage(
                content="Research output with RAG.",
                response_metadata={"token_usage": {}},
            )
            mock_groq.return_value = instance

            from agents.researcher import researcher_node
            result = researcher_node(agent_state)

        assert result["messages"][0]["rag_used"] is True

    @pytest.mark.asyncio
    async def test_researcher_without_rag_labels_false(self, agent_state: AgentState):
        agent_state.plan = ["Explain qubits"]
        with patch("agents.researcher.ChatGroq") as mock_groq, \
             patch("agents.researcher.retrieve_as_context") as mock_rag:

            mock_rag.return_value = "[RAG unavailable — using general knowledge]"
            instance = MagicMock()
            instance.invoke.return_value = AIMessage(
                content="Research output.",
                response_metadata={},
            )
            mock_groq.return_value = instance

            from agents.researcher import researcher_node
            result = researcher_node(agent_state)

        assert result["messages"][0]["rag_used"] is False


# ── Critic ─────────────────────────────────────────────────────────────────────

class TestCriticNode:
    @pytest.mark.asyncio
    async def test_critic_parses_score(self, populated_state: AgentState):
        with patch("agents.critic.ChatGroq") as mock_groq:
            instance = MagicMock()
            instance.invoke.return_value = AIMessage(
                content="The research is accurate but lacks detail.\nHALLUCINATION_SCORE: 3",
                response_metadata={"token_usage": {"prompt_tokens": 40, "completion_tokens": 20}},
            )
            mock_groq.return_value = instance

            from agents.critic import critic_node
            result = critic_node(populated_state)

        assert result["hallucination_score"] == 3
        assert "critique" in result

    @pytest.mark.asyncio
    async def test_critic_defaults_to_conservative_score(self, populated_state: AgentState):
        with patch("agents.critic.ChatGroq") as mock_groq:
            instance = MagicMock()
            instance.invoke.return_value = AIMessage(
                content="No score line in this response.",
                response_metadata={},
            )
            mock_groq.return_value = instance

            from agents.critic import critic_node
            result = critic_node(populated_state)

        assert result["hallucination_score"] == 5

    @pytest.mark.asyncio
    async def test_critic_score_with_various_formats(self, populated_state: AgentState):
        formats = [
            ("HALLUCINATION_SCORE: 7", 7),
            ("HALLUCINATION_SCORE: 10", 10),
            ("HALLUCINATION_SCORE:1", 1),
            ("score is HALLUCINATION_SCORE : 4", 4),
        ]

        for content, expected in formats:
            with patch("agents.critic.ChatGroq") as mock_groq:
                instance = MagicMock()
                instance.invoke.return_value = AIMessage(
                    content=content,
                    response_metadata={},
                )
                mock_groq.return_value = instance

                from agents.critic import critic_node
                result = critic_node(populated_state)

            assert result["hallucination_score"] == expected, f"Failed for: {content!r}"


# ── Executor ───────────────────────────────────────────────────────────────────

class TestExecutorNode:
    @pytest.mark.asyncio
    async def test_executor_synthesises_answer(self, populated_state: AgentState):
        with patch("agents.executor.ChatGroq") as mock_groq:
            instance = MagicMock()
            instance.invoke.return_value = AIMessage(
                content="Quantum computing is a revolutionary computing paradigm...",
                response_metadata={"token_usage": {"prompt_tokens": 200, "completion_tokens": 150}},
            )
            mock_groq.return_value = instance

            from agents.executor import executor_node
            result = executor_node(populated_state)

        assert "final_answer" in result
        assert "quantum" in result["final_answer"].lower()
        assert result["token_usage"]["prompt"] == 300
        assert result["token_usage"]["completion"] == 350

    @pytest.mark.asyncio
    async def test_executor_handles_empty_state(self):
        state = AgentState(query="test")
        with patch("agents.executor.ChatGroq") as mock_groq:
            instance = MagicMock()
            instance.invoke.return_value = AIMessage(
                content="",
                response_metadata={},
            )
            mock_groq.return_value = instance

            from agents.executor import executor_node
            result = executor_node(state)

        assert result["final_answer"] == ""
        assert result["token_usage"]["prompt"] == 0

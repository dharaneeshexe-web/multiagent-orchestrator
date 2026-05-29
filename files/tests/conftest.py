from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from graph.state import AgentState
from config.settings import settings


# ── Environment ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _env():
    old = dict(os.environ)
    os.environ.setdefault("GROQ_API_KEY", "test-key")
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
    os.environ.setdefault("OTLP_ENDPOINT", "http://localhost:4317")
    yield
    os.environ.clear()
    os.environ.update(old)


# ── Mock LLM ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_chat_groq():
    with patch("agents.planner.ChatGroq") as mock_cls, \
         patch("agents.researcher.ChatGroq") as mock_res_cls, \
         patch("agents.critic.ChatGroq") as mock_crit_cls, \
         patch("agents.executor.ChatGroq") as mock_exec_cls:

        for m in [mock_cls, mock_res_cls, mock_crit_cls, mock_exec_cls]:
            instance = MagicMock()
            instance.invoke.return_value = AIMessage(
                content="Mocked LLM response",
                response_metadata={
                    "token_usage": {"prompt_tokens": 50, "completion_tokens": 100}
                },
            )
            m.return_value = instance

        yield


@pytest.fixture
def mock_chat_groq_with_content(content: str = "Mocked LLM response"):
    def _make(content: str = content):
        with patch("agents.planner.ChatGroq") as mock_cls, \
             patch("agents.researcher.ChatGroq") as mock_res_cls, \
             patch("agents.critic.ChatGroq") as mock_crit_cls, \
             patch("agents.executor.ChatGroq") as mock_exec_cls:

            for m in [mock_cls, mock_res_cls, mock_crit_cls, mock_exec_cls]:
                instance = MagicMock()
                instance.invoke.return_value = AIMessage(
                    content=content,
                    response_metadata={
                        "token_usage": {"prompt_tokens": 50, "completion_tokens": 100}
                    },
                )
                m.return_value = instance

            return mock_cls, mock_res_cls, mock_crit_cls, mock_exec_cls
    return _make


# ── Mock RAG retriever ─────────────────────────────────────────────────────────

@pytest.fixture
def mock_rag_retriever():
    with patch("agents.researcher.retrieve_as_context") as mock_ret:
        mock_ret.return_value = "[RAG unavailable — using general knowledge]"
        yield mock_ret


@pytest.fixture
def mock_rag_retriever_with_data():
    with patch("agents.researcher.retrieve_as_context") as mock_ret:
        mock_ret.return_value = "Retrieved context from knowledge base about AI safety."
        yield mock_ret


# ── AgentState factory ─────────────────────────────────────────────────────────

@pytest.fixture
def agent_state() -> AgentState:
    return AgentState(query="What is quantum computing?")


@pytest.fixture
def populated_state(agent_state: AgentState) -> AgentState:
    agent_state.plan = [
        "Explain qubits and superposition",
        "Describe quantum entanglement",
        "List real-world applications",
    ]
    agent_state.research_context = (
        "Quantum computing uses qubits that can exist in superposition. "
        "Entanglement allows correlated states across distance."
    )
    agent_state.critique = "The research is solid. HALLUCINATION_SCORE: 2"
    agent_state.hallucination_score = 2
    agent_state.retry_count = 0
    agent_state.token_usage = {"prompt": 100, "completion": 200}
    agent_state.latency_ms = {"planner": 150.0, "researcher": 800.0}
    return agent_state


# ── Mock DB session ────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db_session():
    from db.models import PipelineRun

    def _assign_id(obj):
        if isinstance(obj, PipelineRun) and obj.id is None:
            obj.id = uuid.uuid4()
        if hasattr(obj, "created_at") and obj.created_at is None:
            obj.created_at = datetime.now(timezone.utc)

    session = AsyncMock()
    session.add = MagicMock(side_effect=_assign_id)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()

    from sqlalchemy import Result
    result = MagicMock(spec=Result)
    result.scalar_one_or_none = MagicMock(return_value=None)
    result.scalars = MagicMock()
    result.scalars.return_value.all = MagicMock(return_value=[])
    session.execute.return_value = result

    session.scalar = AsyncMock(return_value=10)

    return session


@pytest.fixture
def mock_get_session(mock_db_session):
    with patch("api.history.get_session") as mock_ctx, \
         patch("api.main.get_session") as mock_main_ctx:

        async def _mock_enter(*args, **kwargs):
            return mock_db_session

        for m in [mock_ctx, mock_main_ctx]:
            m.return_value.__aenter__ = _mock_enter
            m.return_value.__aexit__ = AsyncMock(return_value=None)

        yield mock_db_session

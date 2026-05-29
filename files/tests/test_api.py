from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from api.main import app
from graph.state import AgentState


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "multiagent-orchestrator"


@pytest.mark.asyncio
async def test_health_returns_phase(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.json()["phase"] == 6


@pytest.mark.asyncio
async def test_run_endpoint_success(mock_get_session, client: AsyncClient):
    from api.main import run_workflow_sync

    fake_result = {
        "final_answer": "Quantum computing uses qubits.",
        "hallucination_score": 2,
        "retry_count": 0,
        "token_usage": {"prompt": 150, "completion": 300},
        "latency_ms": {"planner": 120.5, "researcher": 650.2},
        "wall_time_ms": 850.3,
        "query": "What is quantum computing?",
    }

    with patch("api.main.run_workflow_sync", return_value=fake_result):
        resp = await client.post("/run", json={"query": "What is quantum computing?"})

    assert resp.status_code == 200
    data = resp.json()
    assert "final_answer" in data
    assert data["hallucination_score"] == 2
    assert data["retry_count"] == 0
    assert data["query"] == "What is quantum computing?"


@pytest.mark.asyncio
async def test_run_endpoint_empty_query(mock_get_session, client: AsyncClient):
    with patch("api.main.run_workflow_sync") as mock_run:
        mock_run.return_value = {
            "final_answer": "",
            "hallucination_score": 0,
            "retry_count": 0,
            "token_usage": {},
            "latency_ms": {},
            "wall_time_ms": 0.0,
            "query": "",
        }
        resp = await client.post("/run", json={"query": ""})

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_run_endpoint_error(mock_get_session, client: AsyncClient):
    with patch("api.main.run_workflow_sync", side_effect=ValueError("LLM failure")):
        resp = await client.post("/run", json={"query": "test"})

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_history_list_runs(client: AsyncClient):
    resp = await client.get("/history")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_history_list_with_limit(mock_get_session, client: AsyncClient):
    resp = await client.get("/history?limit=5&status=success")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_history_stats(mock_get_session, client: AsyncClient):
    resp = await client.get("/history/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_runs" in data
    assert "successful_runs" in data


@pytest.mark.asyncio
async def test_history_get_run_not_found(mock_get_session, client: AsyncClient):
    rid = uuid.uuid4()
    resp = await client.get(f"/history/{rid}")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_history_get_run_found(mock_get_session, client: AsyncClient):
    from db import repository as repo
    from db.models import PipelineRun

    rid = uuid.uuid4()
    fake_run = PipelineRun(
        id=rid,
        query="test query",
        status="success",
        created_at=datetime.now(timezone.utc),
        agent_events=[],
        retry_count=0,
        prompt_tokens=100,
        completion_tokens=200,
        trigger_source="api",
    )
    mock_get_session.execute.return_value.scalar_one_or_none.return_value = fake_run
    mock_get_session.execute.return_value.scalars.return_value.all.return_value = []

    with patch.object(repo, "get_run") as mock_get:
        mock_get.return_value = fake_run
        resp = await client.get(f"/history/{rid}")

    assert resp.status_code == 200
    assert resp.json()["id"] == str(rid)


@pytest.mark.asyncio
async def test_metrics_endpoint(client: AsyncClient):
    resp = await client.get("/metrics/")
    assert resp.status_code == 200
    body = resp.text
    assert "python_info" in body or "# HELP" in body

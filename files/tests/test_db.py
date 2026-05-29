from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest


pytestmark = pytest.mark.asyncio


# ── create_run ─────────────────────────────────────────────────────────────────

class TestCreateRun:
    async def test_creates_run_with_query(self, mock_db_session):
        from db.repository import create_run

        result = await create_run(mock_db_session, query="What is AI?")
        assert result is not None
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_awaited_once()

    async def test_creates_run_with_trigger(self, mock_db_session):
        from db.repository import create_run

        await create_run(
            mock_db_session,
            query="Test",
            trigger_source="celery",
            celery_task_id="task-123",
        )
        added = mock_db_session.add.call_args[0][0]
        assert added.trigger_source == "celery"
        assert added.celery_task_id == "task-123"
        assert added.status == "running"

    async def test_creates_run_default_trigger(self, mock_db_session):
        from db.repository import create_run

        await create_run(mock_db_session, query="Default")
        added = mock_db_session.add.call_args[0][0]
        assert added.trigger_source == "api"


# ── complete_run ───────────────────────────────────────────────────────────────

class TestCompleteRun:
    async def test_completes_run_with_result(self, mock_db_session):
        from db.repository import complete_run
        from db.models import PipelineRun

        run = PipelineRun(id=uuid.uuid4(), query="test")
        result = {
            "final_answer": "42",
            "hallucination_score": 2,
            "retry_count": 1,
            "token_usage": {"prompt": 100, "completion": 200},
            "wall_time_ms": 500.0,
            "latency_ms": {"planner": 100.0, "researcher": 400.0},
        }

        output = await complete_run(mock_db_session, run, result)

        assert output.status == "success"
        assert output.final_answer == "42"
        assert output.hallucination_score == 2
        assert output.retry_count == 1
        assert output.prompt_tokens == 100
        assert output.completion_tokens == 200
        assert output.wall_time_ms == 500.0
        assert output.completed_at is not None

    async def test_complete_run_adds_agent_events(self, mock_db_session):
        from db.repository import complete_run
        from db.models import PipelineRun

        run = PipelineRun(id=uuid.uuid4(), query="test")
        result = {
            "final_answer": "Answer",
            "hallucination_score": 3,
            "retry_count": 0,
            "token_usage": {"prompt": 50, "completion": 100},
            "wall_time_ms": 300.0,
            "latency_ms": {"planner": 100.0, "critic": 50.0},
        }

        await complete_run(mock_db_session, run, result)

        # Should have added 2 AgentEvent rows
        call_count = sum(
            1 for call in mock_db_session.add.call_args_list
            if call[0][0].__class__.__name__ == "AgentEvent"
        )
        assert call_count == 2


# ── fail_run ───────────────────────────────────────────────────────────────────

class TestFailRun:
    async def test_fails_run_with_error(self, mock_db_session):
        from db.repository import fail_run
        from db.models import PipelineRun

        run = PipelineRun(id=uuid.uuid4(), query="test")

        output = await fail_run(mock_db_session, run, "LLM timeout")

        assert output.status == "error"
        assert output.error_message == "LLM timeout"
        assert output.completed_at is not None

    async def test_fail_run_truncates_long_error(self, mock_db_session):
        from db.repository import fail_run
        from db.models import PipelineRun

        run = PipelineRun(id=uuid.uuid4(), query="test")
        long_error = "x" * 2000

        output = await fail_run(mock_db_session, run, long_error)

        assert len(output.error_message) == 1000


# ── get_run ────────────────────────────────────────────────────────────────────

class TestGetRun:
    async def test_get_run_returns_none_when_missing(self, mock_db_session):
        from db.repository import get_run

        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        result = await get_run(mock_db_session, uuid.uuid4())
        assert result is None

    async def test_get_run_returns_run_when_found(self, mock_db_session):
        from db.repository import get_run
        from db.models import PipelineRun

        rid = uuid.uuid4()
        fake_run = PipelineRun(id=rid, query="found")
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = fake_run

        result = await get_run(mock_db_session, rid)
        assert result is not None
        assert result.id == rid
        assert result.query == "found"


# ── list_runs ──────────────────────────────────────────────────────────────────

class TestListRuns:
    async def test_list_runs_returns_list(self, mock_db_session):
        from db.repository import list_runs

        mock_db_session.execute.return_value.scalars.return_value.all.return_value = []

        result = await list_runs(mock_db_session)
        assert result == []

    async def test_list_runs_filters_by_status(self, mock_db_session):
        from db.repository import list_runs

        mock_db_session.execute.return_value.scalars.return_value.all.return_value = []

        result = await list_runs(mock_db_session, status="success")
        assert result == []

    async def test_list_runs_applies_pagination(self, mock_db_session):
        from db.repository import list_runs

        mock_db_session.execute.return_value.scalars.return_value.all.return_value = []

        result = await list_runs(mock_db_session, limit=10, offset=5)
        assert result == []

    async def test_list_runs_without_status_returns_all(self, mock_db_session):
        from db.repository import list_runs

        mock_db_session.execute.return_value.scalars.return_value.all.return_value = []

        result = await list_runs(mock_db_session)
        assert result == []


# ── get_stats ──────────────────────────────────────────────────────────────────

class TestGetStats:
    async def test_get_stats_returns_aggregates(self, mock_db_session):
        from db.repository import get_stats

        mock_db_session.scalar = AsyncMock()
        mock_db_session.scalar.side_effect = [20, 15, 3.5, 1200.0]

        result = await get_stats(mock_db_session)

        assert result["total_runs"] == 20
        assert result["successful_runs"] == 15
        assert result["error_runs"] == 5
        assert result["avg_hallucination_score"] == 3.5
        assert result["avg_wall_time_ms"] == 1200.0

    async def test_get_stats_handles_empty_db(self, mock_db_session):
        from db.repository import get_stats

        mock_db_session.scalar = AsyncMock()
        mock_db_session.scalar.side_effect = [0, None, None, None]

        result = await get_stats(mock_db_session)

        assert result["total_runs"] == 0
        assert result["successful_runs"] == 0
        assert result["error_runs"] == 0
        assert result["avg_hallucination_score"] is None
        assert result["avg_wall_time_ms"] is None

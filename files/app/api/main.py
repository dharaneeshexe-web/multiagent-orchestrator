from __future__ import annotations

import asyncio
import json
import time
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from prometheus_client import make_asgi_app
from pydantic import BaseModel

from graph.state import AgentState
from api.dispatcher import stream_workflow, run_workflow_sync
from api.jobs import router as jobs_router
from api.rag_routes import router as rag_router
from api.history import router as history_router
from db.session import init_db, get_session
from db.repository import create_run, complete_run, fail_run
from observability.telemetry import setup_telemetry
from observability.langsmith_tracer import setup_langsmith
from observability.metrics import record_pipeline_result, record_pipeline_error

app = FastAPI(
    title="MultiAgent Orchestrator",
    description="LangGraph multi-agent pipeline — Phase 6 persistence",
    version="6.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# ── Observability (must run before app starts) ────────────────────────────────
setup_telemetry(app)
setup_langsmith()

app.include_router(jobs_router)
app.include_router(rag_router)
app.include_router(history_router)


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    await init_db()


# ── Models ────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    query: str
    final_answer: str
    hallucination_score: int
    retry_count: int
    token_usage: dict
    latency_ms: dict
    wall_time_ms: float
    run_id: str | None = None


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "multiagent-orchestrator", "phase": 6}


@app.post("/run", response_model=QueryResponse)
async def run_endpoint(req: QueryRequest):
    t0 = time.time()
    run_id = None

    async with get_session() as session:
        db_run = await create_run(session, query=req.query, trigger_source="api")
        run_id = str(db_run.id)

    try:
        result = await run_workflow_sync(req.query)
        wall_time = round((time.time() - t0) * 1000, 2)
        result["wall_time_ms"] = wall_time

        async with get_session() as session:
            from db.models import PipelineRun
            import uuid
            db_run = await session.get(PipelineRun, uuid.UUID(run_id))
            if db_run:
                await complete_run(session, db_run, result)

        record_pipeline_result(result)
        return QueryResponse(
            query=req.query,
            final_answer=result["final_answer"],
            hallucination_score=result["hallucination_score"],
            retry_count=result["retry_count"],
            token_usage=result["token_usage"],
            latency_ms=result["latency_ms"],
            wall_time_ms=wall_time,
            run_id=run_id,
        )
    except Exception as exc:
        async with get_session() as session:
            from db.models import PipelineRun
            import uuid
            db_run_fresh = await session.get(PipelineRun, uuid.UUID(run_id))
            if db_run_fresh:
                await fail_run(session, db_run_fresh, str(exc))
        record_pipeline_error("run_endpoint")
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )


@app.get("/stream")
async def stream_endpoint(query: str):
    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in stream_workflow(query):
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("event") == "final":
                record_pipeline_result(event.get("meta", {}))
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                query = data.get("query", "").strip()
            except json.JSONDecodeError:
                query = raw.strip()

            if not query:
                await websocket.send_json({"event": "error", "data": "Empty query"})
                continue

            await websocket.send_json({"event": "start", "data": f"Processing: {query}", "timestamp": time.time()})

            async for event in stream_workflow(query):
                await websocket.send_json(event)
                if event.get("event") == "final":
                    record_pipeline_result(event.get("meta", {}))

            await websocket.send_json({"event": "done", "timestamp": time.time()})

    except WebSocketDisconnect:
        pass

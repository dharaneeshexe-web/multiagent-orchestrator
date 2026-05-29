# MultiAgent Orchestrator — Agent Instructions

## Project Structure
- `files/` — all source + tests + docker config
- `files/app/` — Python source
- `files/tests/` — pytest suite (38 tests, all mocked)
- `files/nginx/` — reverse proxy config + Dockerfile
- `.github/workflows/` — CI/CD (3 workflows)
- `k8s/` — Kubernetes manifests (base + overlays dev/prod)
- `infra/` / `docker/` — deployment topology docs

## Quick Commands
```bash
cd C:\Users\me\Documents\MULTIAGENT-LANGRAPH\files

# Restart API after code changes (volume-mounted)
docker compose restart api

# Run tests
docker compose exec api python -m pytest tests/ -v --asyncio-mode=auto

# Build images (after dependency changes)
docker compose build api nginx

# Full start
docker compose up -d

# View logs
docker compose logs -f api nginx
```

## Architecture (12 containers)
redis → postgres → qdrant → jaeger → prometheus → grafana → prefect → nginx (port 80) → api → worker → worker_dlq → flower

## Pipeline Flow
`POST /api/run` → `create_run` (DB) → `run_workflow_sync` → **planner** → **researcher** (RAG injected) → **critic** (hallucination score) + **cost_monitor** (parallel) → **router_node** (sync barrier) → **executor** (final answer) → `complete_run` (DB)

## Key Conventions
- All agents use `@traced_agent` decorator from `observability/tracing.py`
- State uses `_merge_dicts` reducer for parallel-safe dict fields (`latency_ms`, `token_usage`, `cost_breakdown`)
- DB sessions use `async with get_session()` from `db/session.py`
- Tests mock ChatGroq, RAG retriever, and DB session — no real LLM/DB calls
- Nginx handles rate limiting (30r/s general, 10r/s RAG), WS/SSE passthrough, metrics isolation

## Known Issues
- Cost model pricing moved to `config/settings.py` (`primary_input_rate`, etc.)
- First RAG call downloads `all-MiniLM-L6-v2` (~80MB)  
- Prefect UI at :4200 may be slow first load

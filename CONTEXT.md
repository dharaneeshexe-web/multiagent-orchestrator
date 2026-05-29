# MultiAgent Orchestrator — Session Context

## Last State
- **All containers healthy** — 12/12 running, API confirmed with real pipeline run (qubit query returned answer with hallucination_score=2, cost_estimate=$0.000848)
- **38/38 tests passing** (pytest, all mocked — no external deps needed)
- **Nginx on port 80** — rate limiting (30r/s API, 10r/s RAG), WS/SSE buffering off, metrics internal-only, JSON logging
- **Cost monitoring agent** — runs in parallel with critic, estimates inference cost from token usage
- **CI/CD complete** — 3 GitHub Actions workflows (CI, CD, PR check)

## Project Root
`C:\Users\me\Documents\MULTIAGENT-LANGRAPH\files\`
All Python source lives under `files/app/`.

## Quick Start (no build needed for code changes)
```
cd C:\Users\me\Documents\MULTIAGENT-LANGRAPH\files
docker compose restart api        # after editing .py files (volume-mounted)
docker compose up -d              # full start
docker compose exec api python -m pytest tests/ -v --asyncio-mode=auto   # run tests
```

## Key Files
| File | Purpose |
|------|---------|
| `docker-compose.yml` | 12 services (nginx added P7) |
| `.env` | GROQ_API_KEY, DATABASE_URL, OTLP_ENDPOINT, etc |
| `nginx/nginx.conf` | Reverse proxy, rate limiting, WS/SSE, metrics isolation |
| `nginx/Dockerfile` | Minimal nginx:alpine image |
| `.github/workflows/ci.yml` | Lint → mypy → pytest → docker push to GHCR |
| `.github/workflows/cd.yml` | Kustomize deploy to K8s dev/prod |
| `.github/workflows/pr-check.yml` | Fast lint + typecheck + import smoke test |
| `app/Dockerfile` | Single image for api/worker/flower (range pins, pip upgrade) |
| `app/api/main.py` | FastAPI gateway — `/run`, `/stream`, `/ws`, `/health`, `/metrics` |
| `app/api/history.py` | GET /history, /history/{id}, /history/stats |
| `app/api/rag_routes.py` | RAG ingest/search/collection endpoints |
| `app/api/jobs.py` | Celery job submission/polling |
| `app/api/dispatcher.py` | LangGraph workflow runner + cost_monitor label |
| `app/agents/planner.py` | @traced_agent — query decomposition |
| `app/agents/researcher.py` | @traced_agent — injects RAG context |
| `app/agents/critic.py` | @traced_agent — hallucination scoring |
| `app/agents/executor.py` | @traced_agent — final synthesis |
| `app/agents/cost_monitor.py` | @traced_agent — token-based cost estimation (no LLM call) |
| `app/graph/workflow.py` | build_workflow() — 5-agent DAG, parallel critic+cost_monitor |
| `app/graph/state.py` | AgentState + `_merge_dicts` reducer for parallel-safe dict fields |
| `app/graph/routing.py` | route_after_critic() + router_node() sync barrier |
| `app/db/models.py` | PipelineRun + AgentEvent ORM (SQLAlchemy) |
| `app/db/session.py` | async engine + session factory + init_db() |
| `app/db/repository.py` | create/complete/fail/list/get_stats |
| `app/worker/celery_app.py` | Celery with 3 queues |
| `app/worker/tasks.py` | run_agent_pipeline task |
| `app/rag/ingest.py` | ingest_raw() for Qdrant vector storage |
| `app/rag/retriever.py` | retrieve() + RetrievedChunk |
| `app/observability/telemetry.py` | OTEL TracerProvider + MeterProvider |
| `app/observability/metrics.py` | Prometheus histograms/counters/gauges |
| `app/observability/tracing.py` | @traced_agent + @traced_endpoint decorators |
| `app/prefect_flows/flows.py` | scheduled_pipeline_run, db_maintenance, bulk_ingest |
| `app/prefect_flows/deployments.py` | Cron schedule registration |
| `app/config/settings.py` | Central config from ENV + .env |
| `app/requirements.txt` | Range pins (langchain-core>=1.2.21, etc.) to avoid dep conflicts |
| `app/alembic.ini` | Alembic config for DB migrations |
| `app/alembic/env.py` | Async Alembic env |
| `tests/conftest.py` | Mock ChatGroq, RAG retriever, DB session, AgentState factories |
| `tests/test_api.py` | 13 tests — health, /run, /history, /metrics |
| `tests/test_agents.py` | 12 tests — planner, researcher, critic, executor |
| `tests/test_db.py` | 11 tests — CRUD, list, stats |
| `infra/README.md` | Deployment topology + scaling notes |
| `docker/README.md` | Override compose, .dockerignore, registry config |
| `k8s/base/secret.yaml` | GROQ_API_KEY base64 verified |
| `k8s/overlays/prod/kustomization.yaml` | Tagged v1.0.0 with GHCR path |

## Docker Compose Services (12 total)
- redis:7-alpine — Redis/Celery broker + cache
- postgres:16-alpine — Primary DB (run history + Prefect)
- qdrant/qdrant:v1.13.3 — Vector store for RAG
- jaegertracing/all-in-one:1.62.0 — Distributed tracing (OTLP)
- prom/prometheus:v3.3.1 — Metrics scraping
- grafana/grafana:11.6.1 — Dashboards (admin/admin)
- prefecthq/prefect:3-latest — Workflow orchestration
- files-nginx — Reverse proxy on :80 (rate limit, WS/SSE, metrics isolation)
- files-api — FastAPI gateway (uvicorn --reload on mount)
- files-worker — Celery worker (default + priority queues)
- files-worker_dlq — Celery dead-letter worker
- files-flower — Celery monitoring UI

## Kubernetes (separate stack)
All manifests under `k8s/`:
- `deploy.sh` — `./deploy.sh dev` or `./deploy.sh prod`
- `k8s/base/` — namespace, configmap, secret, ingress, 10 service manifests
- `k8s/overlays/dev/` — 1 replica each
- `k8s/overlays/prod/` — 3 API / 4 worker replicas, image tag v1.0.0
- Image: `ghcr.io/multiagent-orchestrator/multiagent-api`

## Known Quirks
- First RAG call downloads `all-MiniLM-L6-v2` (~80MB) — takes 60+ seconds
- Jaeger UI at http://localhost:16686
- Grafana at http://localhost:3000 (admin/admin)
- Prefect UI at http://localhost:4200 (may be slow on first load)
- Flower at http://localhost:5555
- Nginx on :80 — access via http://localhost (not :8000 for external)
- Cost model pricing is hardcoded in `agents/cost_monitor.py` (not yet in settings.py)

## Fixed in This Session
- docker-compose.yml: dropped `version: "3.9"`, fixed jaeger tag to `1.62.0`
- main.py: `setup_telemetry(app)` moved to module level to avoid FastAPIInstrumentor middleware crash
- main.py: `/run` error handler returns `JSONResponse` instead of `raise` (bypasses OTel middleware propagation)
- requirements.txt: loosened tight version pins to range pins (langchain-core>=1.2.21, etc.) — fixes pip dep resolution
- Dockerfile: added `pip install --upgrade pip` + `--default-timeout=300` to prevent timeouts
- docker-compose.yml: added nginx service, tests volume mount on api
- Cleaned stale duplicate dirs: `files/graph/`, `files/config/`, `files/worker/`, `files/agents/`, `files/api/`
- conftest.py: `session.add` mock sets `id` + `created_at` on PipelineRun objects for proper UUID handling
- Tests: all history endpoints now use `mock_get_session`, import paths fixed, required fields set
- CI/CD: 3 workflows created (CI build+pytest+push, CD kustomize deploy, PR fast checks)
- Nginx: rate limiting, WS/SSE buffering off, metrics internal, JSON logging
- Cost agent: added as 5th node in parallel with critic, `_merge_dicts` reducer for concurrent safety

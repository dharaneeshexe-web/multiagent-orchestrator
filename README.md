# MultiAgent Orchestrator

A production-grade multi-agent AI pipeline built on LangGraph 1.0, FastAPI, Celery, Qdrant, and Kubernetes. Eight phases from core agent DAG to full CI/CD — every layer observable, persistent, and deployable.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Gateway                          │
│          REST /run │ SSE /stream │ WebSocket /ws                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  LangGraph DAG  │
                    │                 │
                    │  Planner        │  ← query decomposition
                    │     ↓           │
                    │  Researcher     │  ← RAG + Groq LLM
                    │     ↓           │
                    │  Critic         │  ← hallucination scoring
                    │     ↓           │
                    │  [route]        │  ← retry if score > 6
                    │     ↓           │
                    │  Executor       │  ← final synthesis
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
   ┌──────▼──────┐   ┌───────▼──────┐  ┌───────▼──────┐
   │   Qdrant    │   │  PostgreSQL  │  │    Redis     │
   │  Vector DB  │   │  Run History │  │  Task Queue  │
   │  RAG chunks │   │  Agent logs  │  │  Celery jobs │
   └─────────────┘   └──────────────┘  └──────────────┘
          │
   ┌──────▼──────────────────────────────────────┐
   │              Observability                  │
   │  Jaeger (traces) │ Prometheus │ Grafana     │
   └─────────────────────────────────────────────┘
```

---

## Benchmark Results

Evaluated on 7 successful runs across diverse ML/AI topics.

| Query | Hallucination Score | Retry Count | Wall Time |
|-------|-------------------|-------------|-----------|
| Explain the transformer architecture | 1 / 10 | 0 | 61.6s* |
| Explain backpropagation | 2 / 10 | 0 | 10.6s |
| Supervised vs unsupervised learning | 1 / 10 | 0 | 9.1s |
| How does the BERT model work? | 6 / 10 | 0 | 7.4s |
| What is a qubit? | 1 / 10 | 0 | 10.3s |
| What is backpropagation? | 2 / 10 | 0 | 58.0s* |
| **Average** | **2.14 / 10** | **0** | **30.3s** |

*High wall times caused by Groq free-tier TPM rate limiting (12k tokens/min). On paid tier latency drops to ~5s.

### Test Coverage

```
38 tests passed  |  0 failed  |  14.2s runtime
├── test_agents.py   12 tests  — planner, researcher, critic, executor (mocked LLM)
├── test_api.py      13 tests  — all FastAPI endpoints live
└── test_db.py       13 tests  — PostgreSQL CRUD against real DB
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| Agent framework | LangGraph 1.0 + LangChain 1.0 |
| LLM inference | Groq llama-3.3-70b-versatile |
| API gateway | FastAPI 0.115 + uvicorn |
| Task queue | Celery 5.4 + Redis 7 |
| Vector DB | Qdrant 1.13 |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 |
| Reranking | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| Persistence | PostgreSQL 16 + SQLAlchemy 2 async |
| Migrations | Alembic |
| Scheduling | Prefect 3 |
| Tracing | OpenTelemetry → Jaeger |
| Metrics | Prometheus + Grafana |
| Containers | Docker + Docker Compose |
| Orchestration | Kubernetes + Kustomize + Nginx Ingress |
| CI/CD | GitHub Actions (lint → test → build → deploy) |

---

## Services

| Service | Port | Purpose |
|---------|------|---------|
| FastAPI | 8000 | REST, SSE, WebSocket |
| Flower | 5555 | Celery task monitoring |
| Grafana | 3000 | Metrics dashboards |
| Prometheus | 9090 | Metrics scraping |
| Jaeger | 16686 | Distributed traces |
| Prefect | 4200 | Workflow scheduling |
| Qdrant | 6333 | Vector DB UI |
| Redis | 6379 | Celery broker |
| PostgreSQL | 5432 | Run history |

---

## Quick Start

**Prerequisites:** Docker Desktop 4.x+, Groq API key (free at console.groq.com)

```bash
git clone https://github.com/YOUR_USERNAME/multiagent-orchestrator
cd multiagent-orchestrator

# Add your Groq key
echo "GROQ_API_KEY=your_key_here" >> .env

# Start all 12 services
docker compose up --build
```

### Test it
```bash
# Run the full agent pipeline
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"query": "How does attention work in transformers?"}'

# Stream per-agent events live
curl -N "http://localhost:8000/stream?query=What+is+backpropagation"

# Check run history
curl http://localhost:8000/history/stats

# Ingest a document into RAG
curl -X POST http://localhost:8000/rag/ingest/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Your knowledge here", "source": "manual"}'
```

### Run tests
```bash
docker exec -it multiagent_api bash
pytest tests/ -v --tb=short
```

---

## LangGraph DAG

```
planner → researcher → critic → [route_after_critic]
                                      ├── score > 6 AND retries < 2
                                      │        → increment_retry → researcher
                                      └── score ≤ 6 OR retries exhausted
                                               → executor → END
```

The critic assigns a hallucination score 1–10. Scores above the threshold (default 6) trigger a research retry loop — up to 2 retries before forcing execution. In benchmarks, retry rate was 0% (avg score 2.14).

---

## API Endpoints

### Pipeline
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/run` | Sync pipeline, returns full JSON result + `run_id` |
| GET | `/stream?query=` | SSE stream, per-agent events as they complete |
| WS | `/ws` | WebSocket, bidirectional |

### Jobs (async)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/jobs` | Submit background Celery job |
| GET | `/jobs/{id}` | Poll job status |
| GET | `/jobs/{id}/wait` | Long-poll until complete |
| GET | `/worker/health` | Ping Celery worker |

### RAG
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/rag/ingest/text` | Ingest raw text |
| POST | `/rag/ingest/url` | Fetch + ingest URL |
| GET | `/rag/search?query=` | Retrieve + rerank chunks |
| GET | `/rag/collections` | List Qdrant collections |

### History
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/history` | Paginated run list |
| GET | `/history/{id}` | Single run + agent events |
| GET | `/history/stats` | Aggregate stats |

---

## CI/CD Pipeline

```
push to main
    │
    ├── ruff lint + format check
    ├── mypy type check
    ├── pytest (38 tests, Postgres + Redis service containers)
    ├── docker build + push → ghcr.io (sha + latest tags)
    │
    └── CD: kustomize edit set image → kubectl apply → rollout status
```

Branch protection on `main`: all checks must pass before merge.

---

## Kubernetes

```bash
# Deploy to local cluster (minikube)
minikube start && minikube addons enable ingress
./deploy.sh dev

# Deploy to production
./deploy.sh prod

# Preview changes without applying
./deploy.sh prod --dry-run
```

HPA configured on API (2→8 pods) and workers (2→10 pods) based on CPU/memory.

---

## Observability

Every pipeline run produces:
- **PostgreSQL row** — query, final answer, score, tokens, latency per agent
- **OTEL spans** — full trace in Jaeger with per-agent child spans
- **Prometheus metrics** — `agent_latency_ms`, `hallucination_score`, `pipeline_tokens_total`, `pipeline_retries_total`
- **Grafana dashboard** — 14 panels, auto-provisioned on startup

---

## Project Structure

```
multiagent/
├── app/
│   ├── agents/          # planner, researcher, critic, executor
│   ├── graph/           # LangGraph state, workflow, routing
│   ├── api/             # FastAPI routes, SSE dispatcher, job queue, RAG, history
│   ├── worker/          # Celery app, tasks, dead-letter
│   ├── rag/             # Qdrant ingest + bi-encoder/cross-encoder retrieval
│   ├── db/              # SQLAlchemy models, session, repository
│   ├── prefect_flows/   # Scheduled flows + deployments
│   ├── observability/   # OTEL telemetry, Prometheus metrics, tracing decorators
│   ├── config/          # Pydantic settings
│   └── tests/           # 38 pytest tests
├── k8s/
│   ├── base/            # All K8s manifests
│   └── overlays/        # dev + prod Kustomize overlays
├── observability/
│   ├── prometheus.yml
│   └── grafana/         # Auto-provisioned datasources + dashboards
├── docker-compose.yml   # 12-service local stack
├── deploy.sh            # One-command K8s deploy
└── .github/workflows/   # ci.yml, cd.yml, pr-check.yml
```

---

## Author

**Dharaneesh** 
GitHub: [@dharaneeshexe-web](https://github.com/dharaneeshexe-web)  
HuggingFace: [@dharaneesh1212](https://huggingface.co/dharaneesh1212)

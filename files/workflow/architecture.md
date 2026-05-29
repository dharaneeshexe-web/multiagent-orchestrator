# MULTIAGENT ORCHESTRATION PLATFORM — MASTER ARCHITECTURE CONTEXT

## PROJECT OVERVIEW

This project is an industry-grade distributed multi-agent orchestration platform focused on:

* scalable AI backend systems
* distributed orchestration
* async execution
* streaming inference
* RAG pipelines
* observability
* resilient retries/fallbacks
* production-style infrastructure

The architecture is intentionally designed to resemble real-world AI infrastructure systems used in production environments.

---

# CURRENT PROJECT STATUS

Current completed phases:

✅ Phase 1 — LangGraph Multi-Agent DAG
✅ Phase 2 — FastAPI + REST + SSE + WebSockets
✅ Phase 3 — Redis + Celery Distributed Workers
✅ Phase 4 — Qdrant RAG Pipeline
✅ Phase 5 — LangSmith + OpenTelemetry + Prometheus + Grafana
✅ Phase 6 — PostgreSQL + Prefect + Workflow Persistence
✅ Phase 7 — Nginx + Kubernetes + Kustomize + CI/CD

Next planned phases:

* authentication/RBAC
* semantic caching
* hybrid model routing
* autoscaling workers
* long-term memory

---

# CORE TECH STACK

| Layer            | Technology            | Purpose                |
| ---------------- | --------------------- | ---------------------- |
| Language         | Python 3.11           | Backend runtime        |
| API              | FastAPI               | Async REST + streaming |
| Orchestration    | LangGraph             | DAG workflow engine    |
| Agents           | LangChain             | Agent abstraction      |
| LLM Provider     | Groq                  | Low-latency inference  |
| Queue Broker     | Redis                 | Distributed queues     |
| Workers          | Celery                | Background execution   |
| Vector DB        | Qdrant                | RAG retrieval          |
| Embeddings       | sentence-transformers | Vector embeddings      |
| Observability    | LangSmith             | LLM tracing            |
| Telemetry        | OpenTelemetry         | Distributed tracing    |
| Metrics          | Prometheus            | Metrics collection     |
| Dashboards       | Grafana               | Visualization          |
| Trace UI         | Jaeger                | Span tracing           |
| Containerization | Docker Compose        | Local orchestration    |

---

# HIGH LEVEL ARCHITECTURE

Frontend
↓
REST / SSE / WebSocket
↓
FastAPI Gateway (Nginx reverse proxy)
↓
Dispatcher Layer
↓
LangGraph DAG Workflow
↓
Planner → Researcher → Critic → Executor
↓
Redis + Celery Distributed Workers
↓
Groq Inference Layer
↓
Qdrant Retrieval Layer
↓
Observability Stack

---

# CURRENT CONTAINERS

1. Redis
2. PostgreSQL
3. Qdrant
4. Jaeger
5. Prometheus
6. Grafana
7. Prefect
8. Nginx
9. API
10. Worker
11. Worker DLQ
12. Flower

---

# CURRENT FOLDER STRUCTURE

```text
MULTIAGENT-LANGRAPH/
│
├── files/
│   ├── docker-compose.yml
│   ├── .env
│   ├── nginx/
│   │   ├── Dockerfile
│   │   └── nginx.conf
│   ├── observability/
│   │   ├── prometheus.yml
│   │   └── grafana/
│   │       ├── dashboards/
│   │       └── provisioning/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── planner.py
│   │   │   ├── researcher.py
│   │   │   ├── critic.py
│   │   │   ├── executor.py
│   │   │   └── cost_monitor.py
│   │   ├── graph/
│   │   │   ├── workflow.py
│   │   │   ├── routing.py
│   │   │   └── state.py
│   │   ├── api/
│   │   │   ├── main.py
│   │   │   ├── dispatcher.py
│   │   │   ├── jobs.py
│   │   │   ├── rag_routes.py
│   │   │   └── history.py
│   │   ├── worker/
│   │   │   ├── celery_app.py
│   │   │   └── tasks.py
│   │   ├── rag/
│   │   │   ├── ingest.py
│   │   │   └── retriever.py
│   │   ├── db/
│   │   │   ├── models.py
│   │   │   ├── session.py
│   │   │   └── repository.py
│   │   ├── prefect_flows/
│   │   │   ├── sync_flow.py
│   │   │   └── deployments.py
│   │   ├── observability/
│   │   │   ├── telemetry.py
│   │   │   ├── tracing.py
│   │   │   ├── metrics.py
│   │   │   └── langsmith_tracer.py
│   │   ├── config/
│   │   │   └── settings.py
│   │   ├── data/docs/
│   │   │   └── sample.md
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── run.py
│   └── tests/
│       ├── test_agents.py
│       ├── test_api.py
│       └── test_db.py
├── k8s/
│   ├── base/
│   │   ├── namespace.yaml
│   │   ├── configmap.yaml
│   │   ├── secret.yaml
│   │   ├── postgres-statefulset.yaml
│   │   ├── redis-deployment.yaml
│   │   ├── qdrant-deployment.yaml
│   │   ├── api-deployment.yaml
│   │   ├── worker-deployment.yaml
│   │   ├── worker-dlq-deployment.yaml
│   │   ├── flower-deployment.yaml
│   │   ├── ingress.yaml
│   │   └── hpa.yaml
│   └── overlays/
│       ├── dev/
│       └── prod/
├── infra/
├── docker/
├── .github/workflows/
│   ├── ci.yml
│   ├── cd.yml
│   └── pr-check.yml
├── deploy.sh
├── .env.example
├── .gitignore
├── AGENTS.md
├── CONTEXT.md
└── README.md
```

---

# AGENT RESPONSIBILITIES

## Planner Agent

Responsibilities:

* task decomposition
* execution planning
* workflow routing
* dependency ordering

Never:

* generate final answers
* perform RAG retrieval
* execute retries

---

## Researcher Agent

Responsibilities:

* Qdrant retrieval
* embedding search
* reranking
* context injection
* knowledge aggregation

Uses:

* sentence-transformers
* Qdrant
* RAG pipeline

Never:

* finalize responses
* route workflows

---

## Critic Agent

Responsibilities:

* hallucination scoring
* factual validation
* confidence analysis
* retry recommendations

Can:

* trigger retry loops
* request fallback generation

Never:

* retrieve documents
* synthesize final response

---

## Executor Agent

Responsibilities:

* final synthesis
* response formatting
* aggregation of outputs
* produce final answer

Never:

* directly access vector DB
* manage retries

---

# API ARCHITECTURE

## REST Endpoints

POST /run

* full synchronous orchestration execution

POST /jobs

* async background task execution

GET /jobs/{id}

* task status

GET /jobs/{id}/wait

* blocking result wait

GET /health

* API health check

GET /worker/health

* Celery worker health

---

# STREAMING ARCHITECTURE

Supported:

* Server-Sent Events (SSE)
* WebSockets
* token streaming
* agent event streaming

Streaming order:

1. planner events
2. researcher events
3. critic events
4. executor events
5. completion event

---

# RAG PIPELINE

Research flow:

1. query embedding generation
2. vector search in Qdrant
3. retrieve top-k chunks
4. rerank chunks
5. inject retrieved context
6. send context to LLM

Fallback behavior:

* if retrieval empty → use general LLM knowledge
* system must never crash due to empty retrieval

---

# DISTRIBUTED EXECUTION

Redis:

* queue broker
* pub/sub
* caching potential

Celery:

* distributed workers
* retries
* exponential backoff
* dead-letter queues
* async task execution

Worker queues:

* default
* priority
* dead-letter

---

# OBSERVABILITY STACK

## LangSmith

Tracks:

* prompts
* traces
* agent execution
* token usage

## OpenTelemetry

Tracks:

* distributed spans
* request lifecycle
* service tracing

## Prometheus

Tracks:

* latency
* throughput
* retries
* queue wait time
* failures

## Grafana

Dashboards:

* agent latency
* hallucination score
* token usage
* retries
* workflow timing

## Jaeger

Used for:

* distributed trace inspection
* span analysis

---

# IMPORTANT IMPLEMENTATION RULES

## Docker Rules

Always use:

```yaml
context: .
dockerfile: app/Dockerfile
```

Never:

* use local Python installs
* rely on host pip packages
* create host venv dependencies

Everything runs containerized.

---

# DEPENDENCY RULES

Known compatible versions:

```txt
langchain-core==1.2.8
langchain-groq==1.1.2
groq>=0.30.0
```

Avoid downgrading without dependency review.

---

# ARCHITECTURE PRINCIPLES

The system must prioritize:

1. scalability
2. observability
3. resiliency
4. async execution
5. distributed orchestration
6. fault isolation
7. streaming UX
8. production-grade structure

---

# DEVELOPMENT RULES FOR AGENTS

When modifying code:

* preserve existing architecture
* avoid breaking container compatibility
* preserve async behavior
* maintain observability instrumentation
* preserve streaming support
* maintain separation of concerns
* avoid tight coupling
* avoid monolithic logic
* maintain modular agent boundaries

---

# WHAT THIS PROJECT IS TRYING TO DEMONSTRATE

This project demonstrates:

* distributed systems engineering
* production AI infrastructure
* orchestration systems
* async APIs
* scalable backend architecture
* resilient workflow execution
* observability engineering
* RAG systems
* streaming inference
* multi-agent coordination

This is NOT:

* a toy chatbot
* a notebook demo
* a single-agent assistant
* a simple LangChain wrapper

---

# FUTURE ROADMAP

## Phase 8

* authentication
* RBAC
* API keys
* rate limiting

## Phase 9

* semantic caching
* hybrid routing
* cost-aware model selection
* autoscaling workers

## Phase 10

* long-term memory
* autonomous planning
* persistent conversations

---

# INSTRUCTIONS FOR ALL AI AGENTS

Before modifying anything:

1. understand the existing architecture
2. preserve modular boundaries
3. avoid introducing sync bottlenecks
4. preserve distributed execution
5. preserve tracing + metrics
6. preserve Docker compatibility
7. preserve FastAPI async patterns
8. preserve Celery queue architecture

If uncertain:

* inspect current files first
* avoid assumptions
* avoid replacing working systems
* prefer incremental modifications

The project goal is production-grade AI systems engineering.

# Multi-Agent Orchestrator — Knowledge Base

## Architecture Overview

The Multi-Agent Orchestrator is a LangGraph-based system that processes user
queries through a directed graph of specialized AI agents. Each agent has a
distinct role and contributes to the final answer.

### Agent Pipeline

1. **Planner** — Decomposes the user query into 3-5 ordered sub-tasks.
2. **Researcher** — For each sub-task, generates a thorough factual summary.
3. **Critic** — Evaluates the research for hallucination risk on a scale of 1-10.
4. **Executor** — Synthesises the final answer from the research and critique.

If the critic score exceeds the threshold (default 6), the system retries the
research phase (up to 2 retries) before producing a final answer.

### Key Implementation Details

- All agents use Groq's `llama-3.3-70b-versatile` model via `langchain-groq`.
- The state graph is defined using LangGraph's `StateGraph` with shared state.
- Conditional routing is handled by the `route_after_critic` function.
- Token usage and per-agent latency are tracked for observability.

## API Endpoints

The FastAPI gateway exposes these endpoints:

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /run | Synchronous pipeline execution |
| GET | /stream | Server-Sent Events streaming |
| WS | /ws | WebSocket bidirectional streaming |
| POST | /jobs | Submit background job to Celery |

## Configuration

All configuration is managed through environment variables loaded by
`pydantic-settings`. Key settings include:

- `GROQ_API_KEY` — API key for Groq LLM access
- `PRIMARY_MODEL` — Default LLM model (llama-3.3-70b-versatile)
- `FALLBACK_MODEL` — Fallback model (llama3-8b-8192)
- `MAX_RETRY_LOOPS` — Maximum retry attempts (default: 2)
- `HALLUCINATION_THRESHOLD` — Score threshold for retry (default: 6)
- `QDRANT_URL` — Qdrant vector database URL
- `QDRANT_COLLECTION` — Qdrant collection name

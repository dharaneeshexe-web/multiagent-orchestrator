from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    groq_api_key: str = ""
    primary_model: str = "llama-3.3-70b-versatile"
    fallback_model: str = "llama3-8b-8192"
    max_retry_loops: int = 2
    hallucination_threshold: int = 6

    # Redis / Celery (Phase 3)
    redis_url: str = "redis://redis:6379/0"

    # Qdrant (Phase 4)
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "knowledge"

    # Observability (Phase 5)
    otlp_endpoint: str = "http://jaeger:4317"

    # PostgreSQL (Phase 6)
    database_url: str = "postgresql+asyncpg://multiagent:multiagent@postgres:5432/multiagent"

    # Prefect (Phase 6)
    prefect_api_url: str = "http://prefect:4200/api"

    # Cost model (per 1k tokens USD)
    primary_input_rate: float = 0.00059
    primary_output_rate: float = 0.00079
    fallback_input_rate: float = 0.00005
    fallback_output_rate: float = 0.00008

    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "multiagent-orchestrator"


settings = Settings()

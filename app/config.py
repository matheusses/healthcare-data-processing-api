"""Application settings via Pydantic BaseSettings (12-factor)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/healthcare"

    # OpenTelemetry (empty = disable OTLP export)
    otel_exporter_otlp_endpoint: str = ""
    otel_exporter_otlp_insecure: bool = True  # Use TLS when False (recommended in production)
    otel_service_name: str = "healthcare-api"
    otel_traces_sampler: str = "parentbased_traceidratio"
    otel_traces_sampler_arg: str = "1.0"

    # Environment
    environment: str = "development"

    # Fuzzy search
    pg_trgm_similarity_threshold: float = 0.2

    # Document storage (MinIO / S3-compatible)
    document_storage_endpoint: str = "http://localhost:9000"
    document_storage_bucket: str = "patient-notes"
    document_storage_access_key: str = "minioadmin"
    document_storage_secret_key: str = "minioadmin"
    document_storage_region: str = "us-east-1"
    document_storage_secure: bool = False

    # Vector / embeddings
    vector_embedding_model: str = "text-embedding-3-small"
    vector_embedding_dimensions: int = 1536
    openai_api_key: str = ""

settings = Settings()
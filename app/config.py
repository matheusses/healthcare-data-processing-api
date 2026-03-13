"""Application settings via Pydantic BaseSettings (12-factor)."""

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database: when DATABASE_URL is set (e.g. in Docker), it overrides POSTGRES_* components
    DATABASE_URL: str = ""

    @property
    def database_url(self) -> str:
        """Alias for DATABASE_URL (used by scripts and tests)."""
        return self.DATABASE_URL

    # OpenTelemetry (empty = disable OTLP export)
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    OTEL_EXPORTER_OTLP_INSECURE: bool = True  # Use TLS when False (recommended in production)
    OTEL_SERVICE_NAME: str = "healthcare-api"
    OTEL_TRACES_SAMPLER: str = "parentbased_traceidratio"
    OTEL_TRACES_SAMPLER_ARG: str = "1.0"

    # Environment
    ENVIRONMENT: str = "development"

    # Logging: minimum level sent to OTLP/Loki (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    # Default INFO ensures Loki receives info, warn, error, and exception logs.
    LOG_LEVEL: str = "INFO"

    # Fuzzy search
    PG_TRGM_SIMILARITY_THRESHOLD: float = 0.2
    OPENAI_TEMPERATURE: float = 0
    OPENAI_TOP_P: float = 1

    # Document storage (MinIO / S3-compatible)
    DOCUMENT_STORAGE_ENDPOINT: str = "http://localhost:9000"
    DOCUMENT_STORAGE_BUCKET: str = "patient-notes"
    DOCUMENT_STORAGE_ACCESS_KEY: str = "minioadmin"
    DOCUMENT_STORAGE_SECRET_KEY: str = "minioadmin"
    DOCUMENT_STORAGE_REGION: str = "us-east-1"
    DOCUMENT_STORAGE_SECURE: bool = False

    # Vector / embeddings
    VECTOR_EMBEDDING_MODEL: str = "text-embedding-3-small"
    VECTOR_EMBEDDING_DIMENSIONS: int = 1536
    OPENAI_API_KEY: str = ""
    OPENAI_SUMMARY_MODEL: str = "gpt-4o-mini"
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # Allowed file extensions
    ALLOWED_CONTENT_TYPES: str = "text/plain, application/pdf, image/jpeg, image/jpg, image/png"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_content_types_list(self) -> list[str]:
        return [x.strip() for x in self.ALLOWED_CONTENT_TYPES.split(",")]


settings = Settings()

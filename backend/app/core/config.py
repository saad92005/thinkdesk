from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = "postgresql+asyncpg://thinkdesk:thinkdesk@localhost:5432/thinkdesk"

    # Comma-separated list of allowed frontend origins for CORS.
    cors_origins: str = "http://localhost:3000"

    session_cookie_name: str = "thinkdesk_session"
    session_ttl_days: int = 7

    # Local disk for now; swap for object storage (S3-compatible) before
    # any real multi-instance deployment.
    storage_root: str = "./data/uploads"

    # Free-tier LLM via Groq's OpenAI-compatible API (https://console.groq.com).
    # Left unset until the user provides one; chat/generation degrades to a
    # clear error instead of crashing when it's missing.
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def database_url_sync(self) -> str:
        """Sync driver URL for Alembic, which doesn't need asyncpg."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

    @property
    def cookie_secure(self) -> bool:
        return self.environment != "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()

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
    # Where to redirect the browser back to after an OAuth connector flow.
    frontend_base_url: str = "http://localhost:3000"

    session_cookie_name: str = "thinkdesk_session"
    session_ttl_days: int = 7

    # Local disk for now; swap for object storage (S3-compatible) before
    # any real multi-instance deployment.
    storage_root: str = "./data/uploads"

    # Free-tier LLM via Groq's OpenAI-compatible API (https://console.groq.com).
    # Left unset until the user provides one; chat/generation degrades to a
    # clear error instead of crashing when it's missing. Groq's hosted model
    # lineup changes over time (older llama-3.x models have been retired for
    # some accounts) -- override with GROQ_MODEL in .env if this default
    # ever stops being available; `GET /openai/v1/models` against Groq's API
    # with your key lists what's currently servable.
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"

    # Google OAuth (Gmail connector, Phase 5). Get these from a Google Cloud
    # Console project's OAuth client (Web application type) -- see
    # docs/setup.md. Left unset until configured; connector routes return a
    # clear error instead of crashing when missing.
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://localhost:8000/connectors/google/callback"

    # Slack OAuth (Slack connector, Phase 7). Create a "Blank app" at
    # api.slack.com/apps -- see docs/setup.md.
    slack_client_id: str | None = None
    slack_client_secret: str | None = None
    slack_redirect_uri: str = "http://localhost:8000/connectors/slack/callback"

    # Notion connector (Phase 7). An internal integration token from
    # notion.so/my-integrations -- not OAuth, so there's no client
    # id/secret pair. This is only used by the dev-environment live-check
    # test; each real workspace pastes in its own token via the API,
    # stored per-organization like any other connector.
    notion_api_key: str | None = None

    # Symmetric key (Fernet) used to encrypt connector OAuth tokens at rest.
    # Generate once with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # and never rotate without a migration plan -- rotating invalidates
    # every already-stored token.
    connector_encryption_key: str | None = None

    # Lemon Squeezy billing (Phase 8) -- Merchant of Record, works without a
    # Stripe-supported home country. API key from Settings > API in the
    # Lemon Squeezy dashboard; store ID from GET /v1/stores.
    lemonsqueezy_api_key: str | None = None
    lemonsqueezy_store_id: str | None = None
    lemonsqueezy_webhook_secret: str | None = None
    # The variant (plan) ID for the subscription being sold -- create a
    # Product + Variant in the Lemon Squeezy dashboard first, then find its
    # ID under that variant's own page (or GET /v1/variants with the API key).
    lemonsqueezy_variant_id: str | None = None

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

"""Application settings using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = ""
    database_url_test: str = ""

    # Session / Auth
    session_max_age_hours: int = 720
    login_rate_limit_per_minute: int = 10

    # Token encryption (Fernet key for Oura tokens at rest)
    token_encryption_key: str = ""

    # Auto-migration (dev-only, default false)
    enable_auto_migrate: bool = False

    # Oura OAuth
    oura_client_id: str = ""
    oura_client_secret: str = ""
    oura_redirect_uri: str = "http://localhost:3000/api/oura/callback"

    # Oura API
    oura_api_base_url: str = "https://api.ouraring.com/v2"
    oura_auth_url: str = "https://cloud.ouraring.com/oauth/authorize"
    oura_token_url: str = "https://api.ouraring.com/oauth/token"

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Scopes for Oura API
    oura_scopes: str = "daily heartrate tag session workout personal spo2 heart_health"

    # Runtime DB-role guard (set to "app_user" in prod to verify connection role)
    expected_db_role: str = ""

    # OpenAI (chat agent)
    openai_api_key: str = ""
    chat_enabled: bool = False
    chat_phase1_memory_enabled: bool = True
    chat_long_term_memory_enabled: bool = True
    chat_redis_cache_enabled: bool = False
    chat_max_tool_calls_per_turn: int = 10
    chat_timeout_seconds: int = 60
    chat_max_tokens: int = 4096
    chat_context_budget_tokens: int = 9000
    chat_recent_turns_min: int = 6
    chat_tool_result_max_chars: int = 1200
    chat_summary_trigger_tokens: int = 12000
    chat_summary_max_tokens: int = 300
    chat_memory_retrieval_max_tokens: int = 400
    chat_memory_retrieval_top_k: int = 20
    chat_memory_retrieval_keep_k: int = 6
    chat_memory_similarity_threshold: float = 0.72

    # Redis (optional for chat cache/session state)
    redis_url: str = ""
    chat_cache_ttl_seconds: int = 900
    chat_session_state_ttl_seconds: int = 1800
    chat_embedding_cache_ttl_seconds: int = 300


settings = Settings()

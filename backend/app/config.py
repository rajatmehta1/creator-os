"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for Creator OS backend."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "creator-os"
    app_env: str = "development"
    secret_key: str = "change-me"
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://creator:password@localhost:5432/creator_os"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # Vector DB
    chroma_host: str = "localhost"
    chroma_port: int = 8100

    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    default_llm: str = "claude-sonnet-4-20250514"
    embedding_model: str = "text-embedding-3-small"

    # YouTube
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_redirect_uri: str = "http://localhost:8000/api/v1/auth/youtube/callback"
    youtube_api_key: str = ""

    # Reddit
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "CreatorOS/1.0"

    # External APIs
    news_api_key: str = ""
    google_search_api_key: str = ""
    google_search_cx: str = ""

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()

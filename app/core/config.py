from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, populated from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Enterprise AI Agent Platform"
    environment: str = "development"
    log_level: str = "INFO"

    postgres_user: str = "postgres"
    postgres_password: str = "changeme"
    postgres_db: str = "enterprise_ai_agent"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    upload_dir: str = "uploads"

    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    @property
    def database_url(self) -> str:
        """Build the SQLAlchemy database URL from the individual Postgres settings."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )



@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance so the .env file is only parsed once."""
    return Settings()

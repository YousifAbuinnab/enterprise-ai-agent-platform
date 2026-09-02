from app.core.config import Settings, get_settings


def test_settings_default_values() -> None:
    """Settings should fall back to sensible defaults when no env vars are set."""
    settings = Settings(_env_file=None)

    assert settings.app_name == "Enterprise AI Agent Platform"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"


def test_settings_reads_environment_variables(monkeypatch) -> None:
    """Settings should pick up values from environment variables, overriding defaults."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    settings = Settings(_env_file=None)

    assert settings.environment == "production"
    assert settings.log_level == "WARNING"


def test_get_settings_returns_cached_instance() -> None:
    """get_settings() should return the same cached instance on repeated calls."""
    first = get_settings()
    second = get_settings()

    assert first is second


def test_database_url_is_built_from_postgres_settings() -> None:
    """database_url should be assembled from the individual Postgres settings fields."""
    settings = Settings(
        _env_file=None,
        postgres_user="user",
        postgres_password="pass",
        postgres_host="dbhost",
        postgres_port=5433,
        postgres_db="mydb",
    )

    assert settings.database_url == "postgresql+psycopg://user:pass@dbhost:5433/mydb"

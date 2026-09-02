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

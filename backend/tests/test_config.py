"""Tests for application configuration."""
from app.config import Settings, settings

def test_default_settings():
    s = Settings()
    assert s.app_name == "OnRamp API"
    assert s.debug is False
    assert s.ai_foundry_model == "gpt-4o"
    assert any("localhost:5173" in o for o in s.cors_origins)

def test_env_prefix():
    assert Settings.model_config["env_prefix"] == "ONRAMP_"

def test_settings_singleton():
    assert settings.app_name == "OnRamp API"

def test_database_url_defaults_empty(monkeypatch):
    """Database URL defaults to empty string (dev mode uses SQLite fallback)."""
    monkeypatch.setenv("ONRAMP_DATABASE_URL", "")
    s = Settings()
    assert s.database_url == ""

def test_azure_defaults_empty():
    s = Settings()
    assert s.azure_tenant_id == ""
    assert s.azure_client_id == ""
    assert s.ai_foundry_endpoint == ""

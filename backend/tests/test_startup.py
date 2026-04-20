"""Tests for startup validation."""

from unittest.mock import patch

from app.startup import get_startup_status, validate_environment


def test_validate_environment_dev_mode():
    """In dev mode (no env vars), should return development mode with warnings."""
    result = validate_environment()
    assert result["mode"] == "development"
    assert result["auth"] == "mock"
    assert result["ai"] == "mock"
    assert len(result["warnings"]) > 0
    assert len(result["errors"]) == 0


def test_validate_environment_with_ai_foundry():
    """When AI Foundry endpoint is configured, ai status is ai_foundry."""
    with patch("app.startup.settings") as mock_settings:
        mock_settings.azure_tenant_id = ""
        mock_settings.azure_client_id = ""
        mock_settings.ai_foundry_endpoint = "https://ai.example.com/endpoint"
        mock_settings.database_url = ""
        mock_settings.cors_origins = ["http://localhost:5173"]
        result = validate_environment()
        assert result["ai"] == "ai_foundry"
        assert result["mode"] == "development"


def test_validate_environment_with_database():
    """When database URL is configured, database status is configured."""
    with patch("app.startup.settings") as mock_settings:
        mock_settings.azure_tenant_id = ""
        mock_settings.azure_client_id = ""
        mock_settings.ai_foundry_endpoint = ""
        mock_settings.database_url = "sqlite:///test.db"
        mock_settings.cors_origins = ["http://localhost:5173"]
        result = validate_environment()
        assert result["database"] == "configured"


def test_validate_environment_mssql_entra_auth_with_mi():
    """Entra-authenticated MSSQL URL logs MI client ID."""
    with patch("app.startup.settings") as mock_settings:
        mock_settings.azure_tenant_id = ""
        mock_settings.azure_client_id = ""
        mock_settings.ai_foundry_endpoint = ""
        mock_settings.database_url = "mssql+aioodbc://@server.database.windows.net/onramp"
        mock_settings.managed_identity_client_id = "abcd1234-ef56-7890-abcd-ef1234567890"
        mock_settings.cors_origins = ["http://localhost:5173"]
        result = validate_environment()
        assert result["database"] == "configured"


def test_validate_environment_mssql_entra_auth_without_mi():
    """Entra-authenticated MSSQL URL without MI falls back to DefaultAzureCredential."""
    with patch("app.startup.settings") as mock_settings:
        mock_settings.azure_tenant_id = ""
        mock_settings.azure_client_id = ""
        mock_settings.ai_foundry_endpoint = ""
        mock_settings.database_url = "mssql+aioodbc://@server.database.windows.net/onramp"
        mock_settings.managed_identity_client_id = ""
        mock_settings.cors_origins = ["http://localhost:5173"]
        result = validate_environment()
        assert result["database"] == "configured"


def test_validate_environment_mssql_sql_auth():
    """Standard MSSQL URL with credentials is not Entra auth."""
    with patch("app.startup.settings") as mock_settings:
        mock_settings.azure_tenant_id = "tenant-1234-abcd"
        mock_settings.azure_client_id = "client-1234"
        mock_settings.ai_foundry_endpoint = "https://ai.example.com"
        mock_settings.database_url = "mssql+aioodbc://user:pass@server/db"
        mock_settings.cors_origins = ["https://app.example.com"]
        result = validate_environment()
        assert result["mode"] == "production"
        assert result["database"] == "configured"


def test_validate_environment_production_mode():
    """When Entra ID is configured, runs in production mode."""
    with patch("app.startup.settings") as mock_settings:
        mock_settings.azure_tenant_id = "tenant-1234-abcd"
        mock_settings.azure_client_id = "client-1234"
        mock_settings.ai_foundry_endpoint = "https://ai.example.com"
        mock_settings.database_url = "mssql+aioodbc://server/db"
        mock_settings.cors_origins = ["https://app.example.com"]
        result = validate_environment()
        assert result["mode"] == "production"
        assert result["auth"] == "entra_id"


def test_validate_environment_production_no_ai():
    """Production mode without AI Foundry adds warning."""
    with patch("app.startup.settings") as mock_settings:
        mock_settings.azure_tenant_id = "tenant-1234-abcd"
        mock_settings.azure_client_id = "client-1234"
        mock_settings.ai_foundry_endpoint = ""
        mock_settings.database_url = "mssql+aioodbc://server/db"
        mock_settings.cors_origins = ["https://app.example.com"]
        result = validate_environment()
        assert result["mode"] == "production"
        assert any("AI Foundry" in w for w in result["warnings"])


def test_validate_environment_empty_cors():
    """When CORS origins is empty, adds warning."""
    with patch("app.startup.settings") as mock_settings:
        mock_settings.azure_tenant_id = ""
        mock_settings.azure_client_id = ""
        mock_settings.ai_foundry_endpoint = ""
        mock_settings.database_url = ""
        mock_settings.cors_origins = []
        result = validate_environment()
        assert any("CORS" in w for w in result["warnings"])


def test_validate_environment_production_no_db_exits():
    """Production mode without database should call sys.exit."""
    with patch("app.startup.settings") as mock_settings, \
         patch("app.startup.sys") as mock_sys:
        mock_settings.azure_tenant_id = "tenant-1234-abcd"
        mock_settings.azure_client_id = "client-1234"
        mock_settings.ai_foundry_endpoint = "https://ai.example.com"
        mock_settings.database_url = ""
        mock_settings.cors_origins = ["https://app.example.com"]
        validate_environment()
        mock_sys.exit.assert_called_once_with(1)


def test_get_startup_status_caches():
    """get_startup_status returns cached result on second call."""
    import app.startup
    app.startup._startup_status = None
    result1 = get_startup_status()
    result2 = get_startup_status()
    assert result1 is result2
    app.startup._startup_status = None

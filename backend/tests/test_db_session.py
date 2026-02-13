"""Tests for database session management."""
from app.db.session import get_database_url, get_engine, get_session_factory

def test_sqlite_url_conversion():
    from unittest.mock import patch
    with patch("app.db.session.settings") as mock_settings:
        mock_settings.database_url = "sqlite:///test.db"
        url = get_database_url()
        assert url.startswith("sqlite+aiosqlite:///")

def test_mssql_url_conversion():
    from unittest.mock import patch
    with patch("app.db.session.settings") as mock_settings:
        mock_settings.database_url = "mssql+pyodbc://user:pass@host/db"
        url = get_database_url()
        assert url.startswith("mssql+aioodbc://")

def test_empty_url():
    from unittest.mock import patch
    with patch("app.db.session.settings") as mock_settings:
        mock_settings.database_url = ""
        url = get_database_url()
        assert url == ""

def test_passthrough_url():
    from unittest.mock import patch
    with patch("app.db.session.settings") as mock_settings:
        mock_settings.database_url = "postgresql+asyncpg://user:pass@host/db"
        url = get_database_url()
        assert url == "postgresql+asyncpg://user:pass@host/db"

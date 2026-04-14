"""Tests for database session management."""
import pytest
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


def test_engine_returns_none_for_empty_url():
    """Engine returns None when no database URL is configured."""
    from unittest.mock import patch
    import app.db.session as sess
    old_engine = sess._engine
    sess._engine = None
    try:
        with patch("app.db.session.get_database_url", return_value=""):
            result = get_engine()
            assert result is None
    finally:
        sess._engine = old_engine


def test_session_factory_returns_none_without_engine():
    """Session factory returns None when engine is None."""
    from unittest.mock import patch
    import app.db.session as sess
    old_factory = sess._session_factory
    sess._session_factory = None
    try:
        with patch("app.db.session.get_engine", return_value=None):
            result = get_session_factory()
            assert result is None
    finally:
        sess._session_factory = old_factory



@pytest.mark.asyncio
async def test_get_db_yields_none_without_factory():
    """get_db yields None when no session factory is available."""
    from unittest.mock import patch
    from app.db.session import get_db
    with patch("app.db.session.get_session_factory", return_value=None):
        gen = get_db()
        result = await gen.__anext__()
        assert result is None


@pytest.mark.asyncio
async def test_close_db_resets_globals():
    """close_db resets engine and session factory."""
    from app.db.session import close_db
    import app.db.session as sess
    old_engine = sess._engine
    old_factory = sess._session_factory
    sess._engine = None
    sess._session_factory = None
    try:
        await close_db()
        assert sess._engine is None
        assert sess._session_factory is None
    finally:
        sess._engine = old_engine
        sess._session_factory = old_factory

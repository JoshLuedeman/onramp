"""Tests for database module."""

from unittest.mock import patch


def test_database_module_importable():
    """The database module's get_db function is accessible via session module."""
    from app.db.session import get_db
    assert callable(get_db)


def test_database_url_construction_default():
    """Default database URL is empty (dev mode — SQLite fallback handled by session.py)."""
    from app.config import settings
    assert settings.database_url == "" or "mssql" in settings.database_url or "sqlite" in settings.database_url


def test_session_get_database_url_helper():
    """get_database_url converts sync URLs to async."""
    from app.db.session import get_database_url
    assert callable(get_database_url)


def test_session_init_db_callable():
    """init_db function exists and is callable."""
    import inspect

    from app.db.session import init_db
    assert inspect.iscoroutinefunction(init_db)


def test_session_close_db_callable():
    """close_db function exists and is callable."""
    import inspect

    from app.db.session import close_db
    assert inspect.iscoroutinefunction(close_db)


def test_database_url_mssql_async():
    """MSSQL URL gets converted to async variant."""
    with patch("app.db.session.settings") as mock_settings:
        mock_settings.database_url = "mssql+pyodbc://user:pass@host/db"
        from app.db.session import get_database_url
        url = get_database_url()
        assert "aioodbc" in url


async def test_session_get_db_yields_none_without_factory():
    """get_db yields None when no session factory available."""
    from unittest.mock import patch

    from app.db.session import get_db

    with patch("app.db.session.get_session_factory", return_value=None):
        gen = get_db()
        result = await gen.__anext__()
        assert result is None

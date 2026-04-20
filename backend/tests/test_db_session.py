"""Tests for database session management."""
import struct
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.db.session as sess
from app.db.session import (
    SQL_COPT_SS_ACCESS_TOKEN,
    _is_entra_auth_url,
    _pack_token_for_odbc,
    get_database_url,
    get_engine,
    get_session_factory,
)


# ── URL conversion ──────────────────────────────────────────────────

def test_sqlite_url_conversion():
    with patch("app.db.session.settings") as mock_settings:
        mock_settings.database_url = "sqlite:///test.db"
        url = get_database_url()
        assert url.startswith("sqlite+aiosqlite:///")

def test_mssql_url_conversion():
    with patch("app.db.session.settings") as mock_settings:
        mock_settings.database_url = "mssql+pyodbc://user:pass@host/db"
        url = get_database_url()
        assert url.startswith("mssql+aioodbc://")

def test_empty_url():
    with patch("app.db.session.settings") as mock_settings:
        mock_settings.database_url = ""
        url = get_database_url()
        assert url == ""

def test_passthrough_url():
    with patch("app.db.session.settings") as mock_settings:
        mock_settings.database_url = "postgresql+asyncpg://user:pass@host/db"
        url = get_database_url()
        assert url == "postgresql+asyncpg://user:pass@host/db"


# ── Entra auth URL detection ────────────────────────────────────────

def test_entra_auth_url_detected():
    """Credential-free MSSQL URL is detected as Entra auth."""
    assert _is_entra_auth_url("mssql+aioodbc://@server.database.windows.net/onramp") is True

def test_entra_auth_url_with_query_params():
    """Credential-free URL with driver params is still detected."""
    url = "mssql+aioodbc://@server.database.windows.net/onramp?driver=ODBC+Driver+18"
    assert _is_entra_auth_url(url) is True

def test_sql_auth_url_not_entra():
    """URL with user:pass is not Entra auth."""
    assert _is_entra_auth_url("mssql+aioodbc://user:pass@host/db") is False

def test_sqlite_url_not_entra():
    """SQLite URL is never Entra auth."""
    assert _is_entra_auth_url("sqlite+aiosqlite:///test.db") is False

def test_empty_string_not_entra():
    assert _is_entra_auth_url("") is False

def test_postgresql_not_entra():
    assert _is_entra_auth_url("postgresql+asyncpg://@host/db") is False


# ── Token packing ───────────────────────────────────────────────────

def test_pack_token_for_odbc_format():
    """Token is packed as little-endian uint32 length + UTF-16-LE payload."""
    token = "test-token-abc"
    result = _pack_token_for_odbc(token)

    raw = token.encode("utf-16-le")
    expected_length = len(raw)
    # First 4 bytes = little-endian uint32 length
    length_prefix = struct.unpack("<I", result[:4])[0]
    assert length_prefix == expected_length
    # Remaining bytes = UTF-16-LE encoded token
    assert result[4:] == raw

def test_pack_token_roundtrip():
    """Packed token can be unpacked back to the original string."""
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.example"
    packed = _pack_token_for_odbc(token)
    length = struct.unpack("<I", packed[:4])[0]
    recovered = packed[4:4 + length].decode("utf-16-le")
    assert recovered == token

def test_pack_token_empty_string():
    """Empty token produces zero-length prefix."""
    packed = _pack_token_for_odbc("")
    length = struct.unpack("<I", packed[:4])[0]
    assert length == 0


# ── _get_entra_credential ───────────────────────────────────────────

def test_get_entra_credential_with_client_id():
    """When managed_identity_client_id is set, uses ManagedIdentityCredential."""
    mock_mi_cred = MagicMock()
    with patch("app.db.session.settings") as mock_settings, \
         patch.dict("sys.modules", {"azure": MagicMock(), "azure.identity": MagicMock()}), \
         patch("azure.identity.ManagedIdentityCredential", return_value=mock_mi_cred):
        mock_settings.managed_identity_client_id = "abc-123-def"
        from app.db.session import _get_entra_credential
        cred = _get_entra_credential()
        assert cred is not None

def test_get_entra_credential_without_client_id():
    """When no client_id, falls back to DefaultAzureCredential."""
    mock_dac = MagicMock()
    with patch("app.db.session.settings") as mock_settings, \
         patch.dict("sys.modules", {"azure": MagicMock(), "azure.identity": MagicMock()}), \
         patch("azure.identity.DefaultAzureCredential", return_value=mock_dac):
        mock_settings.managed_identity_client_id = ""
        from app.db.session import _get_entra_credential
        cred = _get_entra_credential()
        assert cred is not None


# ── _attach_entra_token_hook ────────────────────────────────────────

def test_attach_entra_token_hook_registers_event():
    """The hook registers a do_connect listener on the sync engine."""
    mock_engine = MagicMock()
    mock_credential = MagicMock()
    with patch("sqlalchemy.event.listens_for") as mock_listens_for:
        mock_listens_for.return_value = lambda fn: fn
        from app.db.session import _attach_entra_token_hook
        _attach_entra_token_hook(mock_engine, mock_credential)
        mock_listens_for.assert_called_once_with(
            mock_engine.sync_engine, "do_connect"
        )


def test_entra_token_hook_injects_token():
    """The registered do_connect callback injects a token via attrs_before."""
    mock_token = MagicMock()
    mock_token.token = "fake-sql-token"
    mock_credential = MagicMock()
    mock_credential.get_token.return_value = mock_token
    mock_engine = MagicMock()

    captured_listener = None

    def fake_listens_for(target, event_name):
        def decorator(fn):
            nonlocal captured_listener
            captured_listener = fn
            return fn
        return decorator

    with patch("sqlalchemy.event") as mock_event:
        mock_event.listens_for = fake_listens_for
        from app.db.session import _attach_entra_token_hook
        _attach_entra_token_hook(mock_engine, mock_credential)

    assert captured_listener is not None

    cparams = {}
    captured_listener(None, None, [], cparams)

    mock_credential.get_token.assert_called_once_with(
        "https://database.windows.net/.default"
    )
    assert SQL_COPT_SS_ACCESS_TOKEN in cparams["attrs_before"]
    packed = cparams["attrs_before"][SQL_COPT_SS_ACCESS_TOKEN]
    length = struct.unpack("<I", packed[:4])[0]
    recovered = packed[4:4 + length].decode("utf-16-le")
    assert recovered == "fake-sql-token"


# ── get_engine with Entra auth ──────────────────────────────────────

def test_engine_returns_none_for_empty_url():
    """Engine returns None when no database URL is configured."""
    old_engine = sess._engine
    sess._engine = None
    try:
        with patch("app.db.session.get_database_url", return_value=""):
            result = get_engine()
            assert result is None
    finally:
        sess._engine = old_engine


def test_engine_entra_attaches_hook():
    """For Entra auth URLs, engine creation attaches the token hook."""
    old_engine = sess._engine
    old_cred = sess._entra_credential
    sess._engine = None
    sess._entra_credential = None
    try:
        entra_url = "mssql+aioodbc://@server.database.windows.net/onramp"
        mock_cred = MagicMock()
        with patch("app.db.session.get_database_url", return_value=entra_url), \
             patch("app.db.session.create_async_engine") as mock_create, \
             patch("app.db.session._get_entra_credential", return_value=mock_cred), \
             patch("app.db.session._attach_entra_token_hook") as mock_attach:
            mock_create.return_value = MagicMock()
            engine = get_engine()
            assert engine is not None
            mock_attach.assert_called_once_with(engine, mock_cred)
            assert sess._entra_credential is mock_cred
    finally:
        sess._engine = old_engine
        sess._entra_credential = old_cred


def test_engine_entra_uses_pool_recycle():
    """Entra auth engines use pool_recycle, not NullPool."""
    old_engine = sess._engine
    old_cred = sess._entra_credential
    sess._engine = None
    sess._entra_credential = None
    try:
        entra_url = "mssql+aioodbc://@server.database.windows.net/onramp"
        with patch("app.db.session.get_database_url", return_value=entra_url), \
             patch("app.db.session.create_async_engine") as mock_create, \
             patch("app.db.session._get_entra_credential", return_value=MagicMock()), \
             patch("app.db.session._attach_entra_token_hook"):
            mock_create.return_value = MagicMock()
            get_engine()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["pool_recycle"] == 1800
            assert call_kwargs["pool_pre_ping"] is True
            assert "poolclass" not in call_kwargs
    finally:
        sess._engine = old_engine
        sess._entra_credential = old_cred


def test_engine_sqlite_uses_null_pool():
    """SQLite engines still use NullPool (not Entra pooling)."""
    from sqlalchemy.pool import NullPool
    old_engine = sess._engine
    old_cred = sess._entra_credential
    sess._engine = None
    sess._entra_credential = None
    try:
        sqlite_url = "sqlite+aiosqlite:///test.db"
        with patch("app.db.session.get_database_url", return_value=sqlite_url), \
             patch("app.db.session.create_async_engine") as mock_create:
            mock_create.return_value = MagicMock()
            get_engine()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["poolclass"] is NullPool
            assert "pool_recycle" not in call_kwargs
    finally:
        sess._engine = old_engine
        sess._entra_credential = old_cred


# ── Session factory / get_db ────────────────────────────────────────

def test_session_factory_returns_none_without_engine():
    """Session factory returns None when engine is None."""
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
    from app.db.session import get_db
    with patch("app.db.session.get_session_factory", return_value=None):
        gen = get_db()
        result = await gen.__anext__()
        assert result is None


# ── close_db resets Entra credential ────────────────────────────────

@pytest.mark.asyncio
async def test_close_db_resets_globals():
    """close_db resets engine, session factory, and Entra credential."""
    from app.db.session import close_db
    old_engine = sess._engine
    old_factory = sess._session_factory
    old_cred = sess._entra_credential
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    sess._engine = mock_engine
    sess._session_factory = None
    sess._entra_credential = MagicMock()
    try:
        await close_db()
        mock_engine.dispose.assert_awaited_once()
        assert sess._engine is None
        assert sess._session_factory is None
        assert sess._entra_credential is None
    finally:
        sess._engine = old_engine
        sess._session_factory = old_factory
        sess._entra_credential = old_cred


# ── init_db skips _ensure_mssql_database for Entra auth ─────────────

@pytest.mark.asyncio
async def test_init_db_skips_ensure_mssql_for_entra():
    """init_db does not call _ensure_mssql_database for Entra auth URLs."""
    entra_url = "mssql+aioodbc://@server.database.windows.net/onramp"
    with patch("app.db.session.get_engine") as mock_get_engine, \
         patch("app.db.session.get_database_url", return_value=entra_url), \
         patch("app.db.session._is_entra_auth_url", return_value=True), \
         patch("app.db.session._ensure_mssql_database") as mock_ensure, \
         patch("app.db.session._run_migrations", return_value=None):
        mock_get_engine.return_value = MagicMock()
        from app.db.session import init_db
        await init_db()
        mock_ensure.assert_not_called()


@pytest.mark.asyncio
async def test_init_db_calls_ensure_mssql_for_sql_auth():
    """init_db calls _ensure_mssql_database for SQL-auth MSSQL URLs."""
    sql_auth_url = "mssql+aioodbc://user:pass@host/db"
    with patch("app.db.session.get_engine") as mock_get_engine, \
         patch("app.db.session.get_database_url", return_value=sql_auth_url), \
         patch("app.db.session._is_entra_auth_url", return_value=False), \
         patch("app.db.session._ensure_mssql_database") as mock_ensure, \
         patch("app.db.session._run_migrations", return_value=None):
        mock_get_engine.return_value = MagicMock()
        from app.db.session import init_db
        await init_db()
        mock_ensure.assert_called_once_with(sql_auth_url)

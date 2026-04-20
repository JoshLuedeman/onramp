"""Database session management."""

import logging
import struct

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

logger = logging.getLogger(__name__)

# ODBC constant for passing an access token to SQL Server
SQL_COPT_SS_ACCESS_TOKEN = 1256


def _is_entra_auth_url(url: str) -> bool:
    """Detect Entra auth from a credential-free MSSQL URL (no user:pass)."""
    if "mssql" not in url or "aioodbc" not in url:
        return False
    # Credential-free URLs look like mssql+aioodbc://@server/db
    return "://@" in url


def _get_entra_credential():
    """Return an azure-identity credential scoped to the managed identity.

    Uses ManagedIdentityCredential with an explicit client_id so we target the
    correct user-assigned identity without polluting the global AZURE_CLIENT_ID.
    Falls back to DefaultAzureCredential when no client_id is configured (works
    with system-assigned MI, az-cli, etc.).
    """
    try:
        if settings.managed_identity_client_id:
            from azure.identity import ManagedIdentityCredential
            return ManagedIdentityCredential(
                client_id=settings.managed_identity_client_id
            )
        else:
            from azure.identity import DefaultAzureCredential
            return DefaultAzureCredential()
    except ImportError:
        logger.error(
            "azure-identity is required for Entra SQL auth. "
            "Install with: pip install 'onramp-backend[azure]'"
        )
        raise


def _pack_token_for_odbc(token: str) -> bytes:
    """Pack an access token into the struct format expected by SQL_COPT_SS_ACCESS_TOKEN."""
    raw = token.encode("utf-16-le")
    return struct.pack(f"<I{len(raw)}s", len(raw), raw)


def get_database_url() -> str:
    """Get the database URL, converting sync URLs to async if needed."""
    url = settings.database_url
    if not url:
        return ""
    # For SQLite (dev/testing)
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    # For MSSQL
    if url.startswith("mssql+pyodbc://"):
        return url.replace("mssql+pyodbc://", "mssql+aioodbc://", 1)
    return url


# Engine and session factory - created lazily
_engine = None
_session_factory = None
_entra_credential = None


def get_engine():
    global _engine, _entra_credential
    if _engine is None:
        db_url = get_database_url()
        if not db_url:
            return None
        try:
            use_entra = _is_entra_auth_url(db_url)
            engine_kwargs = {
                "echo": False,
            }

            if "sqlite" in db_url:
                engine_kwargs["poolclass"] = NullPool
            elif use_entra:
                # Recycle connections well before the token expires (60 min TTL).
                # pool_pre_ping ensures stale connections are replaced.
                engine_kwargs["pool_recycle"] = 1800
                engine_kwargs["pool_pre_ping"] = True
                engine_kwargs["pool_size"] = 10
                engine_kwargs["max_overflow"] = 20

            _engine = create_async_engine(db_url, **engine_kwargs)

            if use_entra:
                _entra_credential = _get_entra_credential()
                _attach_entra_token_hook(_engine, _entra_credential)
                logger.info("Database engine configured with Entra token auth")

        except Exception:
            return None
    return _engine


def _attach_entra_token_hook(engine, credential):
    """Attach an event listener that injects a fresh Entra token on every new
    DBAPI connection.  This runs on the *sync* engine that backs the async one.
    """
    from sqlalchemy import event

    @event.listens_for(engine.sync_engine, "do_connect")
    def _inject_token(dialect, conn_rec, cargs, cparams):
        token_obj = credential.get_token("https://database.windows.net/.default")
        cparams["attrs_before"] = {
            SQL_COPT_SS_ACCESS_TOKEN: _pack_token_for_odbc(token_obj.token)
        }


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        if engine is None:
            return None
        _session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


async def get_db() -> AsyncSession:
    """FastAPI dependency that provides a database session."""
    factory = get_session_factory()
    if factory is None:
        # In dev mode without a DB, yield None
        yield None
        return
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Initialize database — run Alembic migrations to create/update schema."""
    import asyncio
    engine = get_engine()
    if engine is None:
        return
    db_url = get_database_url()

    # For MSSQL with SQL-auth credentials, ensure the database exists.
    # With Entra auth the database is created by the Bicep template, so skip.
    if "mssql" in db_url and "aioodbc" in db_url and not _is_entra_auth_url(db_url):
        await _ensure_mssql_database(db_url)

    # Run Alembic migrations with retry logic for slow-starting databases
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            await _run_migrations(engine)
            logger.info("Database schema initialized via Alembic migrations")
            return
        except Exception as e:
            if attempt < max_retries:
                logger.info("Migration attempt %d/%d failed: %s — retrying in %ds",
                            attempt, max_retries, e, attempt * 2)
                await asyncio.sleep(attempt * 2)
            else:
                logger.warning("Database initialization failed after %d attempts: %s",
                               max_retries, e)
                logger.warning("Continuing without database — routes will return mock data")


async def _run_migrations(engine):
    """Run Alembic migrations using the given async engine."""
    import os

    from alembic.config import Config

    # Find the alembic.ini relative to this file
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    alembic_ini = os.path.join(backend_dir, "alembic.ini")

    alembic_cfg = Config(alembic_ini)
    # Override the script_location to use our migrations directory
    migrations_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")
    alembic_cfg.set_main_option("script_location", migrations_dir)

    # Run migrations synchronously inside an async connection
    async with engine.connect() as conn:
        await conn.run_sync(lambda sync_conn: _do_upgrade(alembic_cfg, sync_conn))
        await conn.commit()


def _do_upgrade(alembic_cfg, connection):
    """Execute Alembic upgrade head using the provided connection."""
    from alembic import command

    alembic_cfg.attributes["connection"] = connection
    command.upgrade(alembic_cfg, "heads")


async def _ensure_mssql_database(db_url: str):
    """Create the MSSQL database if it doesn't exist, with retries.

    Only used for SQL-auth connections. With Entra auth the database is
    provisioned by the Bicep template.
    """
    import asyncio
    from urllib.parse import unquote, urlparse

    parsed = urlparse(db_url)
    if not parsed.hostname or not parsed.username or not parsed.password or not parsed.path:
        return
    db_name = parsed.path.lstrip("/").split("?")[0]
    if not db_name:
        return
    host = parsed.hostname
    port = parsed.port or 1433
    user = unquote(parsed.username)
    password = unquote(parsed.password)

    def _create_db():
        import pyodbc
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={host},{port};UID={user};PWD={password};"
            f"DATABASE=master;TrustServerCertificate=yes;"
            f"Connection Timeout=10"
        )
        conn = pyodbc.connect(conn_str, autocommit=True, timeout=10)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM sys.databases WHERE name = ?",
            (db_name,),
        )
        database_exists = cursor.fetchone() is not None
        if not database_exists:
            escaped_db_name = db_name.replace("]", "]]")
            cursor.execute(f"CREATE DATABASE [{escaped_db_name}]")
        cursor.close()
        conn.close()

    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            await asyncio.to_thread(_create_db)
            logger.info("Database '%s' ensured", db_name)
            return
        except ImportError:
            logger.warning("pyodbc not available — skipping database creation")
            return
        except Exception as e:
            if attempt < max_retries:
                logger.info(
                    "SQL Server not ready (attempt %d/%d): %s — retrying in %ds",
                    attempt, max_retries, e, attempt * 2,
                )
                await asyncio.sleep(attempt * 2)
            else:
                logger.warning("Could not ensure database '%s' after %d attempts: %s",
                               db_name, max_retries, e)


async def close_db():
    """Close database engine."""
    global _engine, _session_factory, _entra_credential
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        _entra_credential = None

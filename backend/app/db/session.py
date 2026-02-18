"""Database session management."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings


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


def get_engine():
    global _engine
    if _engine is None:
        db_url = get_database_url()
        if not db_url:
            return None
        try:
            _engine = create_async_engine(
                db_url,
                echo=False,
                poolclass=NullPool if "sqlite" in db_url else None,
            )
        except Exception:
            return None
    return _engine


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
    """Initialize database - create tables if needed."""
    engine = get_engine()
    if engine is None:
        return
    # For MSSQL, create the database if it doesn't exist
    db_url = get_database_url()
    if "mssql" in db_url and "aioodbc" in db_url:
        await _ensure_mssql_database(db_url)
    from app.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _ensure_mssql_database(db_url: str):
    """Create the MSSQL database if it doesn't exist."""
    import logging
    import re

    logger = logging.getLogger(__name__)
    match = re.search(r"/(\w+)\?", db_url)
    if not match:
        return
    db_name = match.group(1)
    # Extract connection params from URL
    host_match = re.search(r"@([^/]+)/", db_url)
    user_match = re.search(r"//([^:]+):", db_url)
    pass_match = re.search(r":([^@]+)@", db_url)
    if not (host_match and user_match and pass_match):
        return
    host = host_match.group(1)
    user = user_match.group(1)
    password = pass_match.group(1)
    try:
        import pyodbc
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={host};UID={user};PWD={password};"
            f"DATABASE=master;TrustServerCertificate=yes"
        )
        conn = pyodbc.connect(conn_str, autocommit=True)
        cursor = conn.cursor()
        cursor.execute(
            f"IF NOT EXISTS (SELECT 1 FROM sys.databases WHERE name = '{db_name}') "
            f"CREATE DATABASE [{db_name}]"
        )
        cursor.close()
        conn.close()
        logger.info("Database '%s' ensured", db_name)
    except ImportError:
        logger.warning("pyodbc not available — skipping database creation")
    except Exception as e:
        logger.warning("Could not ensure database '%s': %s", db_name, e)


async def close_db():
    """Close database engine."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None

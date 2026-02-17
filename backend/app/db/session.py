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
    from app.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database engine."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None

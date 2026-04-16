"""Tests for Alembic migrations — verifies migrations produce a schema that
matches the SQLAlchemy models (no drift).
"""

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.models import Base

SQLITE_URL = "sqlite+aiosqlite://"


@pytest.mark.asyncio
async def test_migrations_run_cleanly():
    """Running upgrade head on a fresh DB should not raise."""
    engine = create_async_engine(SQLITE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(_run_upgrade_head)

    # Verify we can query alembic_version
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        versions = [row[0] for row in result]
        assert "007" in versions

    await engine.dispose()


@pytest.mark.asyncio
async def test_migration_creates_all_model_tables():
    """After upgrade head, every model table should exist in the migration DB."""
    engine = create_async_engine(SQLITE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(_run_upgrade_head)

    expected_tables = set(Base.metadata.tables.keys())

    async with engine.connect() as conn:
        actual_tables = set(await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        ))

    # Exclude alembic's own table
    actual_tables.discard("alembic_version")
    assert expected_tables == actual_tables, (
        f"Missing: {expected_tables - actual_tables}, "
        f"Extra: {actual_tables - expected_tables}"
    )

    await engine.dispose()


@pytest.mark.asyncio
async def test_migration_columns_match_models():
    """Every column in the models should exist in the migration-created tables."""
    engine = create_async_engine(SQLITE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(_run_upgrade_head)

    mismatches = []

    async with engine.connect() as conn:
        for table_name, table in Base.metadata.tables.items():
            expected_cols = {col.name for col in table.columns}
            actual_cols = set(await conn.run_sync(
                lambda sync_conn, tn=table_name: {
                    c["name"] for c in inspect(sync_conn).get_columns(tn)
                }
            ))
            missing = expected_cols - actual_cols
            extra = actual_cols - expected_cols
            if missing or extra:
                mismatches.append(
                    f"{table_name}: missing={missing}, extra={extra}"
                )

    assert not mismatches, "Column mismatches:\n" + "\n".join(mismatches)

    await engine.dispose()


@pytest.mark.asyncio
async def test_audit_entries_table_has_indexes():
    """The audit_entries table should have the expected indexes."""
    engine = create_async_engine(SQLITE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(_run_upgrade_head)

    async with engine.connect() as conn:
        indexes = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_indexes("audit_entries")
        )

    index_names = {idx["name"] for idx in indexes}
    assert "ix_audit_entity_time" in index_names
    assert "ix_audit_project_time" in index_names

    await engine.dispose()


@pytest.mark.asyncio
async def test_downgrade_003_drops_audit_entries():
    """Downgrading from 003 to 002 should remove audit_entries."""
    engine = create_async_engine(SQLITE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(_run_upgrade_head)

    # Downgrade to 002
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: _run_downgrade(sync_conn, "002"))

    async with engine.connect() as conn:
        tables = set(await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        ))

    assert "audit_entries" not in tables

    await engine.dispose()


def _run_upgrade_head(connection):
    """Run Alembic upgrade to head using a sync connection."""
    import os

    from alembic import command
    from alembic.config import Config

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_ini = os.path.join(backend_dir, "alembic.ini")
    cfg = Config(alembic_ini)
    migrations_dir = os.path.join(backend_dir, "app", "db", "migrations")
    cfg.set_main_option("script_location", migrations_dir)
    cfg.attributes["connection"] = connection
    command.upgrade(cfg, "head")


def _run_downgrade(connection, target):
    """Run Alembic downgrade to a specific revision using a sync connection."""
    import os

    from alembic import command
    from alembic.config import Config

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_ini = os.path.join(backend_dir, "alembic.ini")
    cfg = Config(alembic_ini)
    migrations_dir = os.path.join(backend_dir, "app", "db", "migrations")
    cfg.set_main_option("script_location", migrations_dir)
    cfg.attributes["connection"] = connection
    command.downgrade(cfg, target)

"""Tests for routes that exercise DB code paths with a real SQLite database.

These tests call route handler functions directly (bypassing ASGI transport) to
ensure pytest-cov correctly tracks coverage of async DB code paths.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import Base
from tests.conftest import SQLITE_TEST_URL


@pytest.fixture
async def db_session():
    """Async fixture providing a real in-memory SQLite session."""
    engine = create_async_engine(SQLITE_TEST_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


# --------------------------------------------------------------------------- #
# questionnaire_state routes                                                    #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_save_state_db_path(db_session):
    """save_questionnaire_state: exercises the DB delete/insert loop (lines 46-58)."""
    from app.api.routes.questionnaire_state import SaveStateRequest, save_questionnaire_state

    req = SaveStateRequest(
        project_id="proj-save-1",
        answers={"q1": "answer_a", "q2": ["opt_1", "opt_2"]},
    )
    result = await save_questionnaire_state(request=req, user={"sub": "dev"}, db=db_session)
    assert result["saved"] is True
    assert "message" not in result  # must be DB path, not in-memory
    await db_session.commit()


@pytest.mark.asyncio
async def test_load_state_db_path_empty(db_session):
    """load_questionnaire_state: exercises the DB path for a project with no data (line 82-83)."""
    from app.api.routes.questionnaire_state import load_questionnaire_state

    result = await load_questionnaire_state(
        project_id="never-saved-project", user={"sub": "dev"}, db=db_session
    )
    assert result["answers"] == {}


@pytest.mark.asyncio
async def test_load_state_db_path_with_data(db_session):
    """load_questionnaire_state: exercises the response-processing loop (lines 85-96)."""
    from app.api.routes.questionnaire_state import SaveStateRequest, save_questionnaire_state, load_questionnaire_state

    req = SaveStateRequest(project_id="proj-load-2", answers={"q1": "val1", "q2": ["a", "b"]})
    await save_questionnaire_state(request=req, user={"sub": "dev"}, db=db_session)
    await db_session.commit()

    result = await load_questionnaire_state(
        project_id="proj-load-2", user={"sub": "dev"}, db=db_session
    )
    assert result["answers"].get("q1") == "val1"
    assert result["answers"].get("q2") == ["a", "b"]


# --------------------------------------------------------------------------- #
# users route                                                                   #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_get_user_projects_db_path(db_session):
    """get_user_projects: exercises the DB select path (lines 30-46)."""
    from app.api.routes.users import get_user_projects

    result = await get_user_projects(user={"sub": "dev", "oid": "user-oid-1"}, db=db_session)
    assert "projects" in result
    assert isinstance(result["projects"], list)


# --------------------------------------------------------------------------- #
# scoring route                                                                 #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_get_project_scoring_db_path(db_session):
    """get_project_compliance_results: exercises the DB join path."""
    from app.api.routes.scoring import get_project_compliance_results

    result = await get_project_compliance_results(
        project_id="nonexistent-proj", user={"sub": "dev", "tenant_id": "t1"}, db=db_session
    )
    assert result["results"] == []


# --------------------------------------------------------------------------- #
# bicep route                                                                   #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_get_project_bicep_db_path(db_session):
    """get_project_bicep_files: exercises the DB join path."""
    from app.api.routes.bicep import get_project_bicep_files

    result = await get_project_bicep_files(
        project_id="nonexistent-proj", user={"sub": "dev", "tenant_id": "t1"}, db=db_session
    )
    assert result["files"] == []

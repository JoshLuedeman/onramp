"""Comprehensive tests for architecture review workflow — models, service, and routes."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models.base import Base

SQLITE_TEST_URL = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def engine():
    eng = create_async_engine(SQLITE_TEST_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture()
async def db_session(engine):
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture()
async def client(engine):
    """AsyncClient backed by in-memory DB with dependency overrides."""
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _override_get_current_user():
        return {
            "oid": "test-user-id",
            "tid": "test-tenant",
            "name": "Tester",
        }

    from app.auth import get_current_user
    from app.db.session import get_db

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

SAMPLE_ARCH_DATA = {
    "management_groups": {
        "root": {"display_name": "Root", "children": {}}
    },
    "subscriptions": [{"name": "Prod", "purpose": "Production"}],
    "network_topology": {"type": "hub-spoke"},
    "policies": {"enforce_tagging": True},
}


async def _seed_full(db_session: AsyncSession) -> tuple[str, str, str]:
    """Insert tenant, user, project, architecture. Return (arch_id, project_id, user_id)."""
    from app.models.architecture import Architecture
    from app.models.project import Project
    from app.models.tenant import Tenant
    from app.models.user import User

    tenant = Tenant(
        id="test-tenant", name="Test Tenant", azure_tenant_id="azure-t"
    )
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        id="test-user-id",
        email="test@example.com",
        display_name="Tester",
        role="architect",
        tenant_id="test-tenant",
        entra_object_id="entra-obj",
    )
    db_session.add(user)
    await db_session.flush()

    project = Project(
        id="proj-test-1",
        name="Test Project",
        status="draft",
        tenant_id="test-tenant",
        created_by="test-user-id",
    )
    db_session.add(project)
    await db_session.flush()

    arch = Architecture(
        architecture_data=SAMPLE_ARCH_DATA,
        project_id="proj-test-1",
        status="draft",
        version=1,
    )
    db_session.add(arch)
    await db_session.flush()

    return arch.id, project.id, user.id


async def _seed_reviewer(db_session: AsyncSession) -> str:
    """Add a second user who acts as reviewer. Return reviewer id."""
    from app.models.user import User

    reviewer = User(
        id="reviewer-1",
        email="reviewer@example.com",
        display_name="Reviewer",
        role="architect",
        tenant_id="test-tenant",
        entra_object_id="entra-reviewer",
    )
    db_session.add(reviewer)
    await db_session.flush()
    return reviewer.id


async def _seed_second_reviewer(db_session: AsyncSession) -> str:
    """Add a third user as second reviewer."""
    from app.models.user import User

    reviewer = User(
        id="reviewer-2",
        email="reviewer2@example.com",
        display_name="Reviewer 2",
        role="architect",
        tenant_id="test-tenant",
        entra_object_id="entra-reviewer-2",
    )
    db_session.add(reviewer)
    await db_session.flush()
    return reviewer.id


# ===========================================================================
# MODEL TESTS
# ===========================================================================


class TestArchitectureReviewModel:
    """Tests for the ArchitectureReview model."""

    @pytest.mark.asyncio
    async def test_create_review(self, db_session):
        arch_id, _, _ = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)

        from app.models.base import generate_uuid
        from app.models.review import ArchitectureReview

        review = ArchitectureReview(
            id=generate_uuid(),
            architecture_id=arch_id,
            reviewer_id=reviewer_id,
            action="approved",
            comments="Looks good",
        )
        db_session.add(review)
        await db_session.flush()
        await db_session.refresh(review)

        assert review.id is not None
        assert review.architecture_id == arch_id
        assert review.reviewer_id == reviewer_id
        assert review.action == "approved"
        assert review.comments == "Looks good"
        assert review.created_at is not None

    @pytest.mark.asyncio
    async def test_review_without_comments(self, db_session):
        arch_id, _, _ = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)

        from app.models.base import generate_uuid
        from app.models.review import ArchitectureReview

        review = ArchitectureReview(
            id=generate_uuid(),
            architecture_id=arch_id,
            reviewer_id=reviewer_id,
            action="rejected",
        )
        db_session.add(review)
        await db_session.flush()
        assert review.comments is None

    @pytest.mark.asyncio
    async def test_review_relationship_to_architecture(self, db_session):
        arch_id, _, _ = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)

        from app.models.base import generate_uuid
        from app.models.review import ArchitectureReview

        review = ArchitectureReview(
            id=generate_uuid(),
            architecture_id=arch_id,
            reviewer_id=reviewer_id,
            action="approved",
        )
        db_session.add(review)
        await db_session.flush()
        await db_session.refresh(review, ["architecture"])
        assert review.architecture is not None
        assert review.architecture.id == arch_id

    @pytest.mark.asyncio
    async def test_review_relationship_to_user(self, db_session):
        arch_id, _, _ = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)

        from app.models.base import generate_uuid
        from app.models.review import ArchitectureReview

        review = ArchitectureReview(
            id=generate_uuid(),
            architecture_id=arch_id,
            reviewer_id=reviewer_id,
            action="approved",
        )
        db_session.add(review)
        await db_session.flush()
        await db_session.refresh(review, ["reviewer"])
        assert review.reviewer is not None
        assert review.reviewer.id == reviewer_id


class TestReviewConfigurationModel:
    """Tests for the ReviewConfiguration model."""

    @pytest.mark.asyncio
    async def test_create_config(self, db_session):
        _, project_id, _ = await _seed_full(db_session)

        from app.models.base import generate_uuid
        from app.models.review import ReviewConfiguration

        config = ReviewConfiguration(
            id=generate_uuid(),
            project_id=project_id,
            required_approvals=2,
        )
        db_session.add(config)
        await db_session.flush()
        await db_session.refresh(config)

        assert config.id is not None
        assert config.project_id == project_id
        assert config.required_approvals == 2
        assert config.created_at is not None

    @pytest.mark.asyncio
    async def test_config_default_approvals(self, db_session):
        _, project_id, _ = await _seed_full(db_session)

        from app.models.base import generate_uuid
        from app.models.review import ReviewConfiguration

        config = ReviewConfiguration(
            id=generate_uuid(),
            project_id=project_id,
        )
        db_session.add(config)
        await db_session.flush()
        assert config.required_approvals == 1


class TestArchitectureReviewStatus:
    """Tests for the review_status field on Architecture."""

    @pytest.mark.asyncio
    async def test_default_review_status(self, db_session):
        arch_id, _, _ = await _seed_full(db_session)

        from sqlalchemy import select

        from app.models.architecture import Architecture

        result = await db_session.execute(
            select(Architecture).where(Architecture.id == arch_id)
        )
        arch = result.scalar_one()
        assert arch.review_status == "draft"

    @pytest.mark.asyncio
    async def test_update_review_status(self, db_session):
        arch_id, _, _ = await _seed_full(db_session)

        from sqlalchemy import select

        from app.models.architecture import Architecture

        result = await db_session.execute(
            select(Architecture).where(Architecture.id == arch_id)
        )
        arch = result.scalar_one()
        arch.review_status = "in_review"
        await db_session.flush()
        await db_session.refresh(arch)
        assert arch.review_status == "in_review"

    @pytest.mark.asyncio
    async def test_architecture_reviews_relationship(self, db_session):
        arch_id, _, _ = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)

        from sqlalchemy import select

        from app.models.architecture import Architecture
        from app.models.base import generate_uuid
        from app.models.review import ArchitectureReview

        review = ArchitectureReview(
            id=generate_uuid(),
            architecture_id=arch_id,
            reviewer_id=reviewer_id,
            action="approved",
        )
        db_session.add(review)
        await db_session.flush()

        result = await db_session.execute(
            select(Architecture).where(Architecture.id == arch_id)
        )
        arch = result.scalar_one()
        await db_session.refresh(arch, ["reviews"])
        assert len(arch.reviews) == 1
        assert arch.reviews[0].action == "approved"


# ===========================================================================
# SCHEMA VALIDATION TESTS
# ===========================================================================


class TestReviewSchemas:
    """Tests for Pydantic schema validation."""

    def test_review_action_request_valid(self):
        from app.schemas.review import ReviewActionRequest

        req = ReviewActionRequest(action="approved", comments="LGTM")
        assert req.action.value == "approved"
        assert req.comments == "LGTM"

    def test_review_action_request_no_comments(self):
        from app.schemas.review import ReviewActionRequest

        req = ReviewActionRequest(action="rejected")
        assert req.comments is None

    def test_review_action_request_invalid_action(self):
        from pydantic import ValidationError

        from app.schemas.review import ReviewActionRequest

        with pytest.raises(ValidationError):
            ReviewActionRequest(action="invalid_action")

    def test_submit_for_review_request_defaults(self):
        from app.schemas.review import SubmitForReviewRequest

        req = SubmitForReviewRequest()
        assert req.reviewer_ids is None

    def test_submit_for_review_with_reviewers(self):
        from app.schemas.review import SubmitForReviewRequest

        req = SubmitForReviewRequest(
            reviewer_ids=["user-1", "user-2"]
        )
        assert req.reviewer_ids == ["user-1", "user-2"]

    def test_review_config_request_defaults(self):
        from app.schemas.review import ReviewConfigurationRequest

        req = ReviewConfigurationRequest()
        assert req.required_approvals == 1

    def test_review_config_request_custom(self):
        from app.schemas.review import ReviewConfigurationRequest

        req = ReviewConfigurationRequest(required_approvals=3)
        assert req.required_approvals == 3

    def test_review_config_request_min_validation(self):
        from pydantic import ValidationError

        from app.schemas.review import ReviewConfigurationRequest

        with pytest.raises(ValidationError):
            ReviewConfigurationRequest(required_approvals=0)

    def test_review_config_request_max_validation(self):
        from pydantic import ValidationError

        from app.schemas.review import ReviewConfigurationRequest

        with pytest.raises(ValidationError):
            ReviewConfigurationRequest(required_approvals=11)

    def test_review_status_enum_values(self):
        from app.schemas.review import ReviewStatus

        assert ReviewStatus.DRAFT.value == "draft"
        assert ReviewStatus.IN_REVIEW.value == "in_review"
        assert ReviewStatus.APPROVED.value == "approved"
        assert ReviewStatus.REJECTED.value == "rejected"
        assert ReviewStatus.DEPLOYED.value == "deployed"

    def test_review_action_enum_values(self):
        from app.schemas.review import ReviewAction

        assert ReviewAction.APPROVED.value == "approved"
        assert ReviewAction.CHANGES_REQUESTED.value == "changes_requested"
        assert ReviewAction.REJECTED.value == "rejected"

    def test_review_response_from_attributes(self):
        from datetime import datetime, timezone

        from app.schemas.review import ReviewResponse

        resp = ReviewResponse(
            id="r-1",
            architecture_id="arch-1",
            reviewer_id="user-1",
            action="approved",
            comments="Good",
            created_at=datetime.now(timezone.utc),
        )
        assert resp.id == "r-1"
        assert resp.action == "approved"

    def test_review_status_response(self):
        from app.schemas.review import ReviewStatusResponse

        resp = ReviewStatusResponse(
            status="in_review",
            is_locked=True,
            can_deploy=False,
            approvals_needed=2,
            approvals_received=1,
        )
        assert resp.is_locked is True
        assert resp.can_deploy is False

    def test_review_history_response(self):
        from app.schemas.review import ReviewHistoryResponse

        resp = ReviewHistoryResponse(
            reviews=[],
            current_status="draft",
            required_approvals=1,
            approvals_received=0,
        )
        assert resp.reviews == []
        assert resp.current_status == "draft"

    def test_review_action_request_long_comments(self):
        from app.schemas.review import ReviewActionRequest

        long_comment = "x" * 5000
        req = ReviewActionRequest(
            action="changes_requested", comments=long_comment
        )
        assert len(req.comments) == 5000

    def test_review_action_request_too_long_comments(self):
        from pydantic import ValidationError

        from app.schemas.review import ReviewActionRequest

        with pytest.raises(ValidationError):
            ReviewActionRequest(
                action="approved", comments="x" * 5001
            )


# ===========================================================================
# SERVICE-LEVEL TESTS
# ===========================================================================


class TestSubmitForReview:
    """Tests for review_service.submit_for_review."""

    @pytest.mark.asyncio
    async def test_submit_draft_architecture(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        from app.services.review_service import review_service

        result = await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        assert result["status"] == "in_review"
        assert result["is_locked"] is True
        assert result["architecture_id"] == arch_id

    @pytest.mark.asyncio
    async def test_submit_nonexistent_architecture(self, db_session):
        await _seed_full(db_session)
        from app.services.review_service import review_service

        with pytest.raises(ValueError, match="not found"):
            await review_service.submit_for_review(
                db_session, "nonexistent-id", "test-user-id"
            )

    @pytest.mark.asyncio
    async def test_cannot_submit_already_in_review(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        with pytest.raises(ValueError, match="Cannot submit"):
            await review_service.submit_for_review(
                db_session, arch_id, user_id
            )

    @pytest.mark.asyncio
    async def test_submit_after_rejection(self, db_session):
        """Can re-submit after rejection → draft → in_review."""
        arch_id, _, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        await review_service.perform_review(
            db_session, arch_id, reviewer_id, "rejected"
        )
        await review_service.withdraw_review(
            db_session, arch_id, user_id
        )
        result = await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        assert result["status"] == "in_review"


class TestWithdrawReview:
    """Tests for review_service.withdraw_review."""

    @pytest.mark.asyncio
    async def test_withdraw_from_in_review(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        result = await review_service.withdraw_review(
            db_session, arch_id, user_id
        )
        assert result["status"] == "draft"
        assert result["is_locked"] is False

    @pytest.mark.asyncio
    async def test_withdraw_from_rejected(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        await review_service.perform_review(
            db_session, arch_id, reviewer_id, "rejected"
        )
        result = await review_service.withdraw_review(
            db_session, arch_id, user_id
        )
        assert result["status"] == "draft"

    @pytest.mark.asyncio
    async def test_cannot_withdraw_from_draft(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        from app.services.review_service import review_service

        with pytest.raises(ValueError, match="Cannot withdraw"):
            await review_service.withdraw_review(
                db_session, arch_id, user_id
            )

    @pytest.mark.asyncio
    async def test_cannot_withdraw_from_approved(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        await review_service.perform_review(
            db_session, arch_id, reviewer_id, "approved"
        )
        with pytest.raises(ValueError, match="Cannot withdraw"):
            await review_service.withdraw_review(
                db_session, arch_id, user_id
            )

    @pytest.mark.asyncio
    async def test_withdraw_nonexistent_architecture(self, db_session):
        await _seed_full(db_session)
        from app.services.review_service import review_service

        with pytest.raises(ValueError, match="not found"):
            await review_service.withdraw_review(
                db_session, "bad-id", "test-user-id"
            )


class TestPerformReview:
    """Tests for review_service.perform_review."""

    @pytest.mark.asyncio
    async def test_approve_review(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        result = await review_service.perform_review(
            db_session, arch_id, reviewer_id, "approved", "LGTM"
        )
        assert result["action"] == "approved"
        assert result["comments"] == "LGTM"
        assert result["reviewer_id"] == reviewer_id

    @pytest.mark.asyncio
    async def test_reject_review(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        result = await review_service.perform_review(
            db_session, arch_id, reviewer_id, "rejected", "Needs work"
        )
        assert result["action"] == "rejected"

    @pytest.mark.asyncio
    async def test_request_changes_review(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        result = await review_service.perform_review(
            db_session, arch_id, reviewer_id, "changes_requested"
        )
        assert result["action"] == "changes_requested"
        assert result["comments"] is None

    @pytest.mark.asyncio
    async def test_invalid_action_raises(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        from app.services.review_service import review_service

        with pytest.raises(ValueError, match="Invalid review action"):
            await review_service.perform_review(
                db_session, arch_id, user_id, "invalid"
            )

    @pytest.mark.asyncio
    async def test_review_on_draft_raises(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        with pytest.raises(ValueError, match="must be in_review"):
            await review_service.perform_review(
                db_session, arch_id, reviewer_id, "approved"
            )

    @pytest.mark.asyncio
    async def test_review_nonexistent_architecture(self, db_session):
        await _seed_full(db_session)
        from app.services.review_service import review_service

        with pytest.raises(ValueError, match="not found"):
            await review_service.perform_review(
                db_session, "bad-id", "test-user-id", "approved"
            )

    @pytest.mark.asyncio
    async def test_rejection_auto_transitions_status(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        await review_service.perform_review(
            db_session, arch_id, reviewer_id, "rejected"
        )
        status = await review_service.get_review_status(
            db_session, arch_id
        )
        assert status["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_approval_auto_transitions_status(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        await review_service.perform_review(
            db_session, arch_id, reviewer_id, "approved"
        )
        status = await review_service.get_review_status(
            db_session, arch_id
        )
        assert status["status"] == "approved"

    @pytest.mark.asyncio
    async def test_changes_requested_stays_in_review(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        await review_service.perform_review(
            db_session, arch_id, reviewer_id, "changes_requested"
        )
        status = await review_service.get_review_status(
            db_session, arch_id
        )
        assert status["status"] == "in_review"


class TestApprovalCounting:
    """Tests for approval counting and multi-approval gates."""

    @pytest.mark.asyncio
    async def test_single_approval_sufficient(self, db_session):
        arch_id, project_id, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        await review_service.perform_review(
            db_session, arch_id, reviewer_id, "approved"
        )
        status = await review_service.get_review_status(
            db_session, arch_id
        )
        assert status["approvals_received"] == 1
        assert status["can_deploy"] is True

    @pytest.mark.asyncio
    async def test_multiple_approvals_required(self, db_session):
        arch_id, project_id, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.configure_requirements(
            db_session, project_id, 2
        )
        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        await review_service.perform_review(
            db_session, arch_id, reviewer_id, "approved"
        )
        status = await review_service.get_review_status(
            db_session, arch_id
        )
        # 1 of 2 — still in_review
        assert status["approvals_received"] == 1
        assert status["approvals_needed"] == 2
        assert status["status"] == "in_review"
        assert status["can_deploy"] is False

    @pytest.mark.asyncio
    async def test_two_approvals_auto_approve(self, db_session):
        arch_id, project_id, user_id = await _seed_full(db_session)
        r1 = await _seed_reviewer(db_session)
        r2 = await _seed_second_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.configure_requirements(
            db_session, project_id, 2
        )
        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        await review_service.perform_review(
            db_session, arch_id, r1, "approved"
        )
        await review_service.perform_review(
            db_session, arch_id, r2, "approved"
        )
        status = await review_service.get_review_status(
            db_session, arch_id
        )
        assert status["status"] == "approved"
        assert status["approvals_received"] == 2
        assert status["can_deploy"] is True

    @pytest.mark.asyncio
    async def test_zero_approvals_on_fresh_architecture(self, db_session):
        arch_id, _, _ = await _seed_full(db_session)
        from app.services.review_service import review_service

        status = await review_service.get_review_status(
            db_session, arch_id
        )
        assert status["approvals_received"] == 0

    @pytest.mark.asyncio
    async def test_changes_requested_not_counted(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        await review_service.perform_review(
            db_session, arch_id, reviewer_id, "changes_requested"
        )
        status = await review_service.get_review_status(
            db_session, arch_id
        )
        assert status["approvals_received"] == 0


class TestCanDeploy:
    """Tests for review_service.can_deploy."""

    @pytest.mark.asyncio
    async def test_cannot_deploy_draft(self, db_session):
        arch_id, _, _ = await _seed_full(db_session)
        from app.services.review_service import review_service

        assert await review_service.can_deploy(
            db_session, arch_id
        ) is False

    @pytest.mark.asyncio
    async def test_cannot_deploy_in_review(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        assert await review_service.can_deploy(
            db_session, arch_id
        ) is False

    @pytest.mark.asyncio
    async def test_can_deploy_approved(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        await review_service.perform_review(
            db_session, arch_id, reviewer_id, "approved"
        )
        assert await review_service.can_deploy(
            db_session, arch_id
        ) is True

    @pytest.mark.asyncio
    async def test_cannot_deploy_rejected(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        await review_service.perform_review(
            db_session, arch_id, reviewer_id, "rejected"
        )
        assert await review_service.can_deploy(
            db_session, arch_id
        ) is False


class TestReviewHistory:
    """Tests for review_service.get_review_history."""

    @pytest.mark.asyncio
    async def test_empty_history(self, db_session):
        arch_id, _, _ = await _seed_full(db_session)
        from app.services.review_service import review_service

        result = await review_service.get_review_history(
            db_session, arch_id
        )
        assert result["reviews"] == []
        assert result["current_status"] == "draft"

    @pytest.mark.asyncio
    async def test_history_with_reviews(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        await review_service.perform_review(
            db_session, arch_id, reviewer_id,
            "changes_requested", "Fix networking",
        )
        result = await review_service.get_review_history(
            db_session, arch_id
        )
        assert len(result["reviews"]) == 1
        assert result["reviews"][0]["action"] == "changes_requested"
        assert result["reviews"][0]["comments"] == "Fix networking"

    @pytest.mark.asyncio
    async def test_history_multiple_reviews(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        r1 = await _seed_reviewer(db_session)
        r2 = await _seed_second_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        await review_service.perform_review(
            db_session, arch_id, r1, "changes_requested"
        )
        await review_service.perform_review(
            db_session, arch_id, r2, "approved"
        )
        result = await review_service.get_review_history(
            db_session, arch_id
        )
        assert len(result["reviews"]) == 2

    @pytest.mark.asyncio
    async def test_history_nonexistent_architecture(self, db_session):
        await _seed_full(db_session)
        from app.services.review_service import review_service

        with pytest.raises(ValueError, match="not found"):
            await review_service.get_review_history(
                db_session, "nonexistent"
            )


class TestGetReviewStatus:
    """Tests for review_service.get_review_status."""

    @pytest.mark.asyncio
    async def test_draft_status(self, db_session):
        arch_id, _, _ = await _seed_full(db_session)
        from app.services.review_service import review_service

        status = await review_service.get_review_status(
            db_session, arch_id
        )
        assert status["status"] == "draft"
        assert status["is_locked"] is False
        assert status["can_deploy"] is False

    @pytest.mark.asyncio
    async def test_in_review_status(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        status = await review_service.get_review_status(
            db_session, arch_id
        )
        assert status["status"] == "in_review"
        assert status["is_locked"] is True
        assert status["can_deploy"] is False

    @pytest.mark.asyncio
    async def test_status_nonexistent_architecture(self, db_session):
        await _seed_full(db_session)
        from app.services.review_service import review_service

        with pytest.raises(ValueError, match="not found"):
            await review_service.get_review_status(
                db_session, "nonexistent"
            )


class TestConfigureRequirements:
    """Tests for review_service.configure_requirements."""

    @pytest.mark.asyncio
    async def test_create_config(self, db_session):
        _, project_id, _ = await _seed_full(db_session)
        from app.services.review_service import review_service

        result = await review_service.configure_requirements(
            db_session, project_id, 3
        )
        assert result["project_id"] == project_id
        assert result["required_approvals"] == 3

    @pytest.mark.asyncio
    async def test_update_config(self, db_session):
        _, project_id, _ = await _seed_full(db_session)
        from app.services.review_service import review_service

        await review_service.configure_requirements(
            db_session, project_id, 2
        )
        result = await review_service.configure_requirements(
            db_session, project_id, 5
        )
        assert result["required_approvals"] == 5

    @pytest.mark.asyncio
    async def test_invalid_zero_approvals(self, db_session):
        _, project_id, _ = await _seed_full(db_session)
        from app.services.review_service import review_service

        with pytest.raises(ValueError, match="at least 1"):
            await review_service.configure_requirements(
                db_session, project_id, 0
            )

    @pytest.mark.asyncio
    async def test_config_affects_status_response(self, db_session):
        arch_id, project_id, _ = await _seed_full(db_session)
        from app.services.review_service import review_service

        await review_service.configure_requirements(
            db_session, project_id, 4
        )
        status = await review_service.get_review_status(
            db_session, arch_id
        )
        assert status["approvals_needed"] == 4


# ===========================================================================
# STATE TRANSITION TESTS
# ===========================================================================


class TestStateTransitions:
    """Tests for full lifecycle state transitions."""

    @pytest.mark.asyncio
    async def test_draft_to_in_review_to_approved(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        await review_service.perform_review(
            db_session, arch_id, reviewer_id, "approved"
        )
        status = await review_service.get_review_status(
            db_session, arch_id
        )
        assert status["status"] == "approved"

    @pytest.mark.asyncio
    async def test_draft_to_rejected_to_draft(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        await review_service.perform_review(
            db_session, arch_id, reviewer_id, "rejected"
        )
        status = await review_service.get_review_status(
            db_session, arch_id
        )
        assert status["status"] == "rejected"

        await review_service.withdraw_review(
            db_session, arch_id, user_id
        )
        status = await review_service.get_review_status(
            db_session, arch_id
        )
        assert status["status"] == "draft"

    @pytest.mark.asyncio
    async def test_full_cycle_reject_then_approve(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        # Submit → reject → withdraw → re-submit → approve
        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        await review_service.perform_review(
            db_session, arch_id, reviewer_id, "rejected"
        )
        await review_service.withdraw_review(
            db_session, arch_id, user_id
        )
        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        await review_service.perform_review(
            db_session, arch_id, reviewer_id, "approved"
        )
        status = await review_service.get_review_status(
            db_session, arch_id
        )
        assert status["status"] == "approved"
        assert status["can_deploy"] is True

    @pytest.mark.asyncio
    async def test_architecture_locked_during_review(self, db_session):
        arch_id, _, user_id = await _seed_full(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        status = await review_service.get_review_status(
            db_session, arch_id
        )
        assert status["is_locked"] is True

    @pytest.mark.asyncio
    async def test_approved_re_submit(self, db_session):
        """Approved architecture can be re-submitted for review."""
        arch_id, _, user_id = await _seed_full(db_session)
        reviewer_id = await _seed_reviewer(db_session)
        from app.services.review_service import review_service

        await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        await review_service.perform_review(
            db_session, arch_id, reviewer_id, "approved"
        )
        # Re-submit
        result = await review_service.submit_for_review(
            db_session, arch_id, user_id
        )
        assert result["status"] == "in_review"


# ===========================================================================
# ROUTE INTEGRATION TESTS
# ===========================================================================


class TestReviewRoutes:
    """Integration tests for review API routes."""

    @pytest.mark.asyncio
    async def test_submit_for_review_route(self, client, db_session):
        arch_id, _, _ = await _seed_full(db_session)
        await db_session.commit()
        resp = await client.post(
            f"/api/architectures/{arch_id}/reviews/submit"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "in_review"

    @pytest.mark.asyncio
    async def test_submit_nonexistent_returns_400(self, client, db_session):
        await _seed_full(db_session)
        await db_session.commit()
        resp = await client.post(
            "/api/architectures/nonexistent/reviews/submit"
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_perform_review_route(self, client, db_session):
        arch_id, _, _ = await _seed_full(db_session)
        await db_session.commit()
        # First submit
        await client.post(
            f"/api/architectures/{arch_id}/reviews/submit"
        )
        # Then review
        resp = await client.post(
            f"/api/architectures/{arch_id}/reviews",
            json={"action": "approved", "comments": "LGTM"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["action"] == "approved"

    @pytest.mark.asyncio
    async def test_perform_review_invalid_action(self, client, db_session):
        arch_id, _, _ = await _seed_full(db_session)
        await db_session.commit()
        await client.post(
            f"/api/architectures/{arch_id}/reviews/submit"
        )
        resp = await client.post(
            f"/api/architectures/{arch_id}/reviews",
            json={"action": "invalid"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_get_review_history_route(self, client, db_session):
        arch_id, _, _ = await _seed_full(db_session)
        await db_session.commit()
        resp = await client.get(
            f"/api/architectures/{arch_id}/reviews"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "reviews" in data
        assert "current_status" in data

    @pytest.mark.asyncio
    async def test_get_review_status_route(self, client, db_session):
        arch_id, _, _ = await _seed_full(db_session)
        await db_session.commit()
        resp = await client.get(
            f"/api/architectures/{arch_id}/reviews/status"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "draft"
        assert data["is_locked"] is False

    @pytest.mark.asyncio
    async def test_withdraw_review_route(self, client, db_session):
        arch_id, _, _ = await _seed_full(db_session)
        await db_session.commit()
        await client.post(
            f"/api/architectures/{arch_id}/reviews/submit"
        )
        resp = await client.post(
            f"/api/architectures/{arch_id}/reviews/withdraw"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "draft"

    @pytest.mark.asyncio
    async def test_withdraw_from_draft_returns_400(self, client, db_session):
        arch_id, _, _ = await _seed_full(db_session)
        await db_session.commit()
        resp = await client.post(
            f"/api/architectures/{arch_id}/reviews/withdraw"
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_configure_requirements_route(self, client, db_session):
        _, project_id, _ = await _seed_full(db_session)
        await db_session.commit()
        resp = await client.put(
            f"/api/projects/{project_id}/review-config",
            json={"required_approvals": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["required_approvals"] == 3

    @pytest.mark.asyncio
    async def test_configure_invalid_approvals(self, client, db_session):
        _, project_id, _ = await _seed_full(db_session)
        await db_session.commit()
        resp = await client.put(
            f"/api/projects/{project_id}/review-config",
            json={"required_approvals": 0},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_full_route_workflow(self, client, db_session):
        """End-to-end: submit → review → check status."""
        arch_id, _, _ = await _seed_full(db_session)
        await db_session.commit()

        # Submit
        resp = await client.post(
            f"/api/architectures/{arch_id}/reviews/submit"
        )
        assert resp.status_code == 200

        # Approve
        resp = await client.post(
            f"/api/architectures/{arch_id}/reviews",
            json={"action": "approved"},
        )
        assert resp.status_code == 201

        # Check status
        resp = await client.get(
            f"/api/architectures/{arch_id}/reviews/status"
        )
        data = resp.json()
        assert data["status"] == "approved"
        assert data["can_deploy"] is True

    @pytest.mark.asyncio
    async def test_review_history_after_actions(self, client, db_session):
        arch_id, _, _ = await _seed_full(db_session)
        await db_session.commit()

        await client.post(
            f"/api/architectures/{arch_id}/reviews/submit"
        )
        await client.post(
            f"/api/architectures/{arch_id}/reviews",
            json={"action": "changes_requested", "comments": "Fix it"},
        )

        resp = await client.get(
            f"/api/architectures/{arch_id}/reviews"
        )
        data = resp.json()
        assert len(data["reviews"]) == 1
        assert data["reviews"][0]["comments"] == "Fix it"

    @pytest.mark.asyncio
    async def test_get_history_nonexistent_returns_404(
        self, client, db_session
    ):
        await _seed_full(db_session)
        await db_session.commit()
        resp = await client.get(
            "/api/architectures/nonexistent/reviews"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_status_nonexistent_returns_404(
        self, client, db_session
    ):
        await _seed_full(db_session)
        await db_session.commit()
        resp = await client.get(
            "/api/architectures/nonexistent/reviews/status"
        )
        assert resp.status_code == 404

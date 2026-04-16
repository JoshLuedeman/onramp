"""Tests for the drift remediation service and routes."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.drift_remediation import (
    BatchRemediationResponse,
    RemediationAction,
    RemediationAuditEntry,
    RemediationAuditLog,
    RemediationResponse,
    RemediationStatus,
)
from app.services.drift_remediator import DriftRemediator, drift_remediator

client = TestClient(app)

FINDING_ID = "evt-test-001"
ACTOR = "test-user@example.com"


# ── Schema tests ─────────────────────────────────────────────────────────────


class TestRemediationSchemas:
    """Tests that schemas and enums are importable and correct."""

    def test_remediation_action_enum_values(self):
        assert RemediationAction.ACCEPT == "accept"
        assert RemediationAction.REVERT == "revert"
        assert RemediationAction.SUPPRESS == "suppress"

    def test_remediation_status_enum_values(self):
        assert RemediationStatus.PENDING == "pending"
        assert RemediationStatus.IN_PROGRESS == "in_progress"
        assert RemediationStatus.COMPLETED == "completed"
        assert RemediationStatus.FAILED == "failed"

    def test_remediation_response_from_dict(self):
        now = datetime.now(timezone.utc)
        resp = RemediationResponse(
            id="rem-1",
            finding_id=FINDING_ID,
            action="accept",
            status="completed",
            result_details={"action": "accept"},
            created_at=now,
        )
        assert resp.id == "rem-1"
        assert resp.finding_id == FINDING_ID
        assert resp.action == "accept"

    def test_audit_entry_schema(self):
        now = datetime.now(timezone.utc)
        entry = RemediationAuditEntry(
            id="aud-1",
            actor=ACTOR,
            action="suppress",
            finding_id=FINDING_ID,
            justification="Known change",
            timestamp=now,
        )
        assert entry.actor == ACTOR
        assert entry.justification == "Known change"


# ── Service unit tests: accept ───────────────────────────────────────────────


class TestRemediateAccept:
    """Tests for the accept remediation action."""

    @pytest.fixture
    def remediator(self):
        return DriftRemediator()

    @pytest.mark.asyncio
    async def test_accept_returns_completed(self, remediator):
        result = await remediator.remediate_finding(
            finding_id=FINDING_ID,
            action="accept",
            actor=ACTOR,
        )
        assert result.status == "completed"
        assert result.action == "accept"
        assert result.finding_id == FINDING_ID

    @pytest.mark.asyncio
    async def test_accept_result_details_has_iac_update(self, remediator):
        result = await remediator.remediate_finding(
            finding_id=FINDING_ID,
            action="accept",
            actor=ACTOR,
        )
        details = result.result_details
        assert details["action"] == "accept"
        assert "iac_update" in details
        assert details["iac_update"]["finding_id"] == FINDING_ID

    @pytest.mark.asyncio
    async def test_accept_generates_uuid_id(self, remediator):
        result = await remediator.remediate_finding(
            finding_id=FINDING_ID,
            action="accept",
            actor=ACTOR,
        )
        assert result.id  # Non-empty
        assert len(result.id) == 36  # UUID format


# ── Service unit tests: revert ───────────────────────────────────────────────


class TestRemediateRevert:
    """Tests for the revert remediation action."""

    @pytest.fixture
    def remediator(self):
        return DriftRemediator()

    @pytest.mark.asyncio
    async def test_revert_returns_completed(self, remediator):
        result = await remediator.remediate_finding(
            finding_id=FINDING_ID,
            action="revert",
            actor=ACTOR,
        )
        assert result.status == "completed"
        assert result.action == "revert"

    @pytest.mark.asyncio
    async def test_revert_has_redeployment_plan(self, remediator):
        result = await remediator.remediate_finding(
            finding_id=FINDING_ID,
            action="revert",
            actor=ACTOR,
        )
        details = result.result_details
        assert details["action"] == "revert"
        assert "redeployment_plan" in details
        plan = details["redeployment_plan"]
        assert "steps" in plan
        assert len(plan["steps"]) > 0


# ── Service unit tests: suppress ─────────────────────────────────────────────


class TestRemediateSuppress:
    """Tests for the suppress remediation action."""

    @pytest.fixture
    def remediator(self):
        return DriftRemediator()

    @pytest.mark.asyncio
    async def test_suppress_returns_completed(self, remediator):
        result = await remediator.remediate_finding(
            finding_id=FINDING_ID,
            action="suppress",
            actor=ACTOR,
            justification="Known dev change",
            expiration_days=30,
        )
        assert result.status == "completed"
        assert result.action == "suppress"

    @pytest.mark.asyncio
    async def test_suppress_with_expiration_30_days(self, remediator):
        result = await remediator.remediate_finding(
            finding_id=FINDING_ID,
            action="suppress",
            actor=ACTOR,
            expiration_days=30,
        )
        suppression = result.result_details["suppression"]
        assert suppression["expiration_days"] == 30
        assert suppression["expires_at"] is not None
        assert suppression["permanent"] is False

    @pytest.mark.asyncio
    async def test_suppress_with_expiration_90_days(self, remediator):
        result = await remediator.remediate_finding(
            finding_id=FINDING_ID,
            action="suppress",
            actor=ACTOR,
            expiration_days=90,
        )
        suppression = result.result_details["suppression"]
        assert suppression["expiration_days"] == 90

    @pytest.mark.asyncio
    async def test_suppress_permanent(self, remediator):
        result = await remediator.remediate_finding(
            finding_id=FINDING_ID,
            action="suppress",
            actor=ACTOR,
            expiration_days=None,
        )
        suppression = result.result_details["suppression"]
        assert suppression["permanent"] is True
        assert suppression["expires_at"] is None

    @pytest.mark.asyncio
    async def test_suppress_result_details_structure(self, remediator):
        result = await remediator.remediate_finding(
            finding_id=FINDING_ID,
            action="suppress",
            actor=ACTOR,
            justification="Intentional override",
            expiration_days=60,
        )
        details = result.result_details
        assert details["action"] == "suppress"
        assert "suppression" in details
        assert details["suppression"]["finding_id"] == FINDING_ID


# ── Service unit tests: batch ────────────────────────────────────────────────


class TestBatchRemediation:
    """Tests for batch remediation operations."""

    @pytest.fixture
    def remediator(self):
        return DriftRemediator()

    @pytest.mark.asyncio
    async def test_batch_accept_multiple(self, remediator):
        ids = ["evt-1", "evt-2", "evt-3"]
        result = await remediator.remediate_batch(
            finding_ids=ids,
            action="accept",
            actor=ACTOR,
        )
        assert result.total == 3
        assert result.succeeded == 3
        assert result.failed == 0
        assert len(result.results) == 3
        for r in result.results:
            assert r.action == "accept"
            assert r.status == "completed"

    @pytest.mark.asyncio
    async def test_batch_suppress_with_justification(self, remediator):
        ids = ["evt-1", "evt-2"]
        result = await remediator.remediate_batch(
            finding_ids=ids,
            action="suppress",
            actor=ACTOR,
            justification="Batch suppress",
            expiration_days=30,
        )
        assert result.total == 2
        assert result.succeeded == 2
        for r in result.results:
            assert r.result_details["suppression"]["expiration_days"] == 30

    @pytest.mark.asyncio
    async def test_batch_handles_failures_gracefully(self, remediator):
        """If one remediation fails, the batch continues and reports failure."""
        with patch.object(
            remediator,
            "_build_result_details",
            side_effect=[ValueError("boom"), {"action": "accept"}],
        ):
            result = await remediator.remediate_batch(
                finding_ids=["fail-1", "ok-1"],
                action="accept",
                actor=ACTOR,
            )
        assert result.total == 2
        assert result.failed == 1
        assert result.succeeded == 1
        failed = [r for r in result.results if r.status == "failed"]
        assert len(failed) == 1

    @pytest.mark.asyncio
    async def test_batch_single_item(self, remediator):
        result = await remediator.remediate_batch(
            finding_ids=["evt-solo"],
            action="revert",
            actor=ACTOR,
        )
        assert result.total == 1
        assert result.succeeded == 1


# ── Service unit tests: audit history (no DB) ───────────────────────────────


class TestAuditHistory:
    """Tests for remediation audit history."""

    @pytest.fixture
    def remediator(self):
        return DriftRemediator()

    @pytest.mark.asyncio
    async def test_history_empty_without_db(self, remediator):
        result = await remediator.get_remediation_history(db=None)
        assert isinstance(result, RemediationAuditLog)
        assert result.entries == []
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_get_remediation_returns_none_without_db(self, remediator):
        result = await remediator.get_remediation("rem-nonexistent", db=None)
        assert result is None


# ── Model tests ──────────────────────────────────────────────────────────────


class TestDriftRemediationModel:
    """Tests that the DriftRemediation model is importable and correct."""

    def test_model_importable(self):
        from app.models.drift_remediation import DriftRemediation

        assert DriftRemediation.__tablename__ == "drift_remediations"

    def test_model_has_expected_columns(self):
        from app.models.drift_remediation import DriftRemediation

        cols = {c.name for c in DriftRemediation.__table__.columns}
        expected = {
            "id",
            "finding_id",
            "action",
            "status",
            "actor",
            "justification",
            "expiration_days",
            "result_details",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(cols)

    def test_model_indexes(self):
        from app.models.drift_remediation import DriftRemediation

        index_names = {idx.name for idx in DriftRemediation.__table__.indexes}
        assert "ix_drift_remediations_finding" in index_names
        assert "ix_drift_remediations_status" in index_names
        assert "ix_drift_remediations_actor_created" in index_names

    def test_model_registered_in_init(self):
        from app.models import DriftRemediation

        assert DriftRemediation.__tablename__ == "drift_remediations"


# ── Route tests (via TestClient, dev mode — db=None) ────────────────────────


class TestRemediationRoutes:
    """Tests for the drift remediation HTTP endpoints."""

    @patch("app.auth.entra.get_current_user", return_value={"sub": "user-1", "name": "Test User"})
    def test_remediate_single_accept(self, _mock_user):
        response = client.post(
            "/api/governance/drift/remediate",
            json={"finding_id": FINDING_ID, "action": "accept"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "accept"
        assert data["status"] == "completed"
        assert data["finding_id"] == FINDING_ID

    @patch("app.auth.entra.get_current_user", return_value={"sub": "user-1", "name": "Test User"})
    def test_remediate_single_revert(self, _mock_user):
        response = client.post(
            "/api/governance/drift/remediate",
            json={"finding_id": FINDING_ID, "action": "revert"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "revert"

    @patch("app.auth.entra.get_current_user", return_value={"sub": "user-1", "name": "Test User"})
    def test_remediate_single_suppress(self, _mock_user):
        response = client.post(
            "/api/governance/drift/remediate",
            json={
                "finding_id": FINDING_ID,
                "action": "suppress",
                "justification": "Known change",
                "expiration_days": 30,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "suppress"
        assert data["result_details"]["suppression"]["expiration_days"] == 30

    @patch("app.auth.entra.get_current_user", return_value={"sub": "user-1", "name": "Test User"})
    def test_remediate_batch(self, _mock_user):
        response = client.post(
            "/api/governance/drift/remediate/batch",
            json={
                "finding_ids": ["evt-1", "evt-2", "evt-3"],
                "action": "accept",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["succeeded"] == 3
        assert data["failed"] == 0
        assert len(data["results"]) == 3

    @patch("app.auth.entra.get_current_user", return_value={"sub": "user-1", "name": "Test User"})
    def test_remediate_batch_suppress_with_expiry(self, _mock_user):
        response = client.post(
            "/api/governance/drift/remediate/batch",
            json={
                "finding_ids": ["evt-1", "evt-2"],
                "action": "suppress",
                "justification": "Batch suppress test",
                "expiration_days": 90,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        for r in data["results"]:
            assert r["result_details"]["suppression"]["expiration_days"] == 90

    @patch("app.auth.entra.get_current_user", return_value={"sub": "user-1", "name": "Test User"})
    def test_get_remediation_not_found(self, _mock_user):
        response = client.get("/api/governance/drift/remediation/nonexistent-id")
        assert response.status_code == 404

    @patch("app.auth.entra.get_current_user", return_value={"sub": "user-1", "name": "Test User"})
    def test_get_remediation_history_empty(self, _mock_user):
        response = client.get("/api/governance/drift/remediation/history")
        assert response.status_code == 200
        data = response.json()
        assert data["entries"] == []
        assert data["total"] == 0

    @patch("app.auth.entra.get_current_user", return_value={"sub": "user-1", "name": "Test User"})
    def test_remediate_invalid_action_rejected(self, _mock_user):
        response = client.post(
            "/api/governance/drift/remediate",
            json={"finding_id": FINDING_ID, "action": "invalid_action"},
        )
        assert response.status_code == 422  # Validation error

    @patch("app.auth.entra.get_current_user", return_value={"sub": "user-1", "name": "Test User"})
    def test_remediate_batch_empty_ids_rejected(self, _mock_user):
        response = client.post(
            "/api/governance/drift/remediate/batch",
            json={"finding_ids": [], "action": "accept"},
        )
        assert response.status_code == 422  # min_length=1


# ── Singleton tests ──────────────────────────────────────────────────────────


class TestSingleton:
    """Tests that the module-level singleton is the expected type."""

    def test_drift_remediator_is_instance(self):
        assert isinstance(drift_remediator, DriftRemediator)

    def test_drift_remediator_is_singleton(self):
        from app.services.drift_remediator import drift_remediator as r2

        assert drift_remediator is r2

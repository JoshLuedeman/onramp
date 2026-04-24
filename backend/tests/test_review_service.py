"""Tests for the ReviewService — dev-mode (no DB) paths and state machine."""

import pytest

from app.services.review_service import (
    VALID_ACTIONS,
    _VALID_TRANSITIONS,
    review_service,
)


class TestValidTransitions:
    """Test the state machine transitions map."""

    def test_draft_can_go_to_in_review(self):
        assert "in_review" in _VALID_TRANSITIONS["draft"]

    def test_in_review_can_go_to_approved(self):
        assert "approved" in _VALID_TRANSITIONS["in_review"]

    def test_in_review_can_go_to_rejected(self):
        assert "rejected" in _VALID_TRANSITIONS["in_review"]

    def test_approved_can_go_to_deployed(self):
        assert "deployed" in _VALID_TRANSITIONS["approved"]

    def test_deployed_is_terminal(self):
        assert len(_VALID_TRANSITIONS["deployed"]) == 0

    def test_valid_actions_set(self):
        assert VALID_ACTIONS == {"approved", "changes_requested", "rejected"}


class TestSubmitForReview:
    """Test submit_for_review with db=None (dev mode mock)."""

    @pytest.mark.asyncio
    async def test_submit_returns_in_review_status(self):
        result = await review_service.submit_for_review(
            db=None, architecture_id="arch-1", submitter_id="user-1"
        )
        assert result["status"] == "in_review"
        assert result["architecture_id"] == "arch-1"
        assert result["is_locked"] is True


class TestWithdrawReview:
    """Test withdraw_review with db=None (dev mode mock)."""

    @pytest.mark.asyncio
    async def test_withdraw_returns_draft_status(self):
        result = await review_service.withdraw_review(
            db=None, architecture_id="arch-1", submitter_id="user-1"
        )
        assert result["status"] == "draft"
        assert result["is_locked"] is False


class TestPerformReview:
    """Test perform_review with db=None (dev mode mock)."""

    @pytest.mark.asyncio
    async def test_approve_action(self):
        result = await review_service.perform_review(
            db=None,
            architecture_id="arch-1",
            reviewer_id="reviewer-1",
            action="approved",
            comments="Looks good",
        )
        assert result["action"] == "approved"
        assert result["reviewer_id"] == "reviewer-1"

    @pytest.mark.asyncio
    async def test_reject_action(self):
        result = await review_service.perform_review(
            db=None,
            architecture_id="arch-1",
            reviewer_id="reviewer-1",
            action="rejected",
        )
        assert result["action"] == "rejected"

    @pytest.mark.asyncio
    async def test_changes_requested_action(self):
        result = await review_service.perform_review(
            db=None,
            architecture_id="arch-1",
            reviewer_id="reviewer-1",
            action="changes_requested",
        )
        assert result["action"] == "changes_requested"

    @pytest.mark.asyncio
    async def test_invalid_action_raises(self):
        with pytest.raises(ValueError, match="Invalid review action"):
            await review_service.perform_review(
                db=None,
                architecture_id="arch-1",
                reviewer_id="reviewer-1",
                action="invalid_action",
            )


class TestGetReviewStatus:
    """Test get_review_status with db=None."""

    @pytest.mark.asyncio
    async def test_returns_status_dict(self):
        result = await review_service.get_review_status(
            db=None, architecture_id="arch-1"
        )
        assert result["status"] == "draft"
        assert result["is_locked"] is False
        assert result["can_deploy"] is False
        assert result["approvals_needed"] == 1
        assert result["approvals_received"] == 0


class TestCanDeploy:
    """Test can_deploy with db=None."""

    @pytest.mark.asyncio
    async def test_draft_is_not_deployable(self):
        result = await review_service.can_deploy(
            db=None, architecture_id="arch-1"
        )
        assert result is False

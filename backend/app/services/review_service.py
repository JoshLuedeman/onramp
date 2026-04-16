"""Review service — manages architecture review workflow and approval gates.

Provides a singleton service with async methods for submitting architectures
for review, recording review actions, and checking deployment readiness.
"""

from __future__ import annotations

import logging
from typing import Any

from app.models.base import generate_uuid

logger = logging.getLogger(__name__)

# Valid review status transitions
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"in_review"},
    "in_review": {"approved", "rejected", "draft"},
    "approved": {"deployed", "in_review"},
    "rejected": {"draft", "in_review"},
    "deployed": set(),
}

VALID_ACTIONS = {"approved", "changes_requested", "rejected"}


class ReviewService:
    """Singleton service for architecture review workflow."""

    # ──────────────────────────────────────────────────────────────────
    # Submit / Withdraw
    # ──────────────────────────────────────────────────────────────────

    async def submit_for_review(
        self,
        db: Any | None,
        architecture_id: str,
        submitter_id: str,
    ) -> dict:
        """Change architecture status to in_review and lock edits."""
        if db is not None:
            from sqlalchemy import select

            from app.models.architecture import Architecture

            result = await db.execute(
                select(Architecture).where(
                    Architecture.id == architecture_id
                )
            )
            arch = result.scalar_one_or_none()
            if arch is None:
                raise ValueError(
                    f"Architecture not found: {architecture_id}"
                )

            current = arch.review_status or "draft"
            if "in_review" not in _VALID_TRANSITIONS.get(current, set()):
                raise ValueError(
                    f"Cannot submit for review from status: {current}"
                )

            arch.review_status = "in_review"
            await db.flush()
            await db.refresh(arch)

            logger.info(
                "Architecture submitted for review: arch=%s by=%s",
                architecture_id, submitter_id,
            )
            return {
                "architecture_id": architecture_id,
                "status": arch.review_status,
                "is_locked": True,
            }

        # Dev mode mock
        logger.info(
            "Architecture submitted for review (mock): arch=%s",
            architecture_id,
        )
        return {
            "architecture_id": architecture_id,
            "status": "in_review",
            "is_locked": True,
        }

    async def withdraw_review(
        self,
        db: Any | None,
        architecture_id: str,
        submitter_id: str,
    ) -> dict:
        """Return architecture from in_review/rejected back to draft."""
        if db is not None:
            from sqlalchemy import select

            from app.models.architecture import Architecture

            result = await db.execute(
                select(Architecture).where(
                    Architecture.id == architecture_id
                )
            )
            arch = result.scalar_one_or_none()
            if arch is None:
                raise ValueError(
                    f"Architecture not found: {architecture_id}"
                )

            current = arch.review_status or "draft"
            if "draft" not in _VALID_TRANSITIONS.get(current, set()):
                raise ValueError(
                    f"Cannot withdraw from status: {current}"
                )

            arch.review_status = "draft"
            await db.flush()
            await db.refresh(arch)

            logger.info(
                "Architecture review withdrawn: arch=%s by=%s",
                architecture_id, submitter_id,
            )
            return {
                "architecture_id": architecture_id,
                "status": arch.review_status,
                "is_locked": False,
            }

        logger.info(
            "Architecture review withdrawn (mock): arch=%s",
            architecture_id,
        )
        return {
            "architecture_id": architecture_id,
            "status": "draft",
            "is_locked": False,
        }

    # ──────────────────────────────────────────────────────────────────
    # Review Actions
    # ──────────────────────────────────────────────────────────────────

    async def perform_review(
        self,
        db: Any | None,
        architecture_id: str,
        reviewer_id: str,
        action: str,
        comments: str | None = None,
    ) -> dict:
        """Record a review action on an architecture."""
        if action not in VALID_ACTIONS:
            raise ValueError(f"Invalid review action: {action}")

        if db is not None:
            from sqlalchemy import select

            from app.models.architecture import Architecture
            from app.models.review import ArchitectureReview

            result = await db.execute(
                select(Architecture).where(
                    Architecture.id == architecture_id
                )
            )
            arch = result.scalar_one_or_none()
            if arch is None:
                raise ValueError(
                    f"Architecture not found: {architecture_id}"
                )

            if arch.review_status != "in_review":
                raise ValueError(
                    "Architecture must be in_review to receive reviews"
                )

            review = ArchitectureReview(
                id=generate_uuid(),
                architecture_id=architecture_id,
                reviewer_id=reviewer_id,
                action=action,
                comments=comments,
            )
            db.add(review)

            # Auto-transition on rejection
            if action == "rejected":
                arch.review_status = "rejected"

            # Check if enough approvals to auto-approve
            if action == "approved":
                config = await self._get_config(db, arch.project_id)
                required = config.required_approvals if config else 1
                approval_count = await self._count_approvals(
                    db, architecture_id
                )
                # +1 for the current approval being added
                if approval_count + 1 >= required:
                    arch.review_status = "approved"

            await db.flush()
            await db.refresh(review)

            logger.info(
                "Review recorded: arch=%s reviewer=%s action=%s",
                architecture_id, reviewer_id, action,
            )
            return {
                "id": review.id,
                "architecture_id": review.architecture_id,
                "reviewer_id": review.reviewer_id,
                "action": review.action,
                "comments": review.comments,
                "created_at": review.created_at,
            }

        # Dev mode mock
        mock_id = generate_uuid()
        from datetime import datetime, timezone
        logger.info(
            "Review recorded (mock): arch=%s action=%s",
            architecture_id, action,
        )
        return {
            "id": mock_id,
            "architecture_id": architecture_id,
            "reviewer_id": reviewer_id,
            "action": action,
            "comments": comments,
            "created_at": datetime.now(timezone.utc),
        }

    # ──────────────────────────────────────────────────────────────────
    # Queries
    # ──────────────────────────────────────────────────────────────────

    async def get_review_status(
        self,
        db: Any | None,
        architecture_id: str,
    ) -> dict:
        """Get current review status with approval counts."""
        if db is not None:
            from sqlalchemy import select

            from app.models.architecture import Architecture

            result = await db.execute(
                select(Architecture).where(
                    Architecture.id == architecture_id
                )
            )
            arch = result.scalar_one_or_none()
            if arch is None:
                raise ValueError(
                    f"Architecture not found: {architecture_id}"
                )

            config = await self._get_config(db, arch.project_id)
            required = config.required_approvals if config else 1
            approvals = await self._count_approvals(
                db, architecture_id
            )

            status = arch.review_status or "draft"
            return {
                "status": status,
                "is_locked": status == "in_review",
                "can_deploy": status == "approved",
                "approvals_needed": required,
                "approvals_received": approvals,
            }

        return {
            "status": "draft",
            "is_locked": False,
            "can_deploy": False,
            "approvals_needed": 1,
            "approvals_received": 0,
        }

    async def get_review_history(
        self,
        db: Any | None,
        architecture_id: str,
    ) -> dict:
        """Get all reviews for an architecture."""
        if db is not None:
            from sqlalchemy import select

            from app.models.architecture import Architecture
            from app.models.review import ArchitectureReview

            # Verify architecture exists
            arch_result = await db.execute(
                select(Architecture).where(
                    Architecture.id == architecture_id
                )
            )
            arch = arch_result.scalar_one_or_none()
            if arch is None:
                raise ValueError(
                    f"Architecture not found: {architecture_id}"
                )

            result = await db.execute(
                select(ArchitectureReview)
                .where(
                    ArchitectureReview.architecture_id == architecture_id
                )
                .order_by(ArchitectureReview.created_at.desc())
            )
            rows = result.scalars().all()

            config = await self._get_config(db, arch.project_id)
            required = config.required_approvals if config else 1
            approvals = await self._count_approvals(
                db, architecture_id
            )

            reviews = [
                {
                    "id": r.id,
                    "architecture_id": r.architecture_id,
                    "reviewer_id": r.reviewer_id,
                    "action": r.action,
                    "comments": r.comments,
                    "created_at": r.created_at,
                }
                for r in rows
            ]

            return {
                "reviews": reviews,
                "current_status": arch.review_status or "draft",
                "required_approvals": required,
                "approvals_received": approvals,
            }

        return {
            "reviews": [],
            "current_status": "draft",
            "required_approvals": 1,
            "approvals_received": 0,
        }

    async def can_deploy(
        self,
        db: Any | None,
        architecture_id: str,
    ) -> bool:
        """Check if architecture is approved with enough approvals."""
        status = await self.get_review_status(db, architecture_id)
        return status["can_deploy"]

    # ──────────────────────────────────────────────────────────────────
    # Configuration
    # ──────────────────────────────────────────────────────────────────

    async def configure_requirements(
        self,
        db: Any | None,
        project_id: str,
        required_approvals: int,
    ) -> dict:
        """Set or update the review requirements for a project."""
        if required_approvals < 1:
            raise ValueError("required_approvals must be at least 1")

        if db is not None:
            from sqlalchemy import select

            from app.models.review import ReviewConfiguration

            result = await db.execute(
                select(ReviewConfiguration).where(
                    ReviewConfiguration.project_id == project_id
                )
            )
            config = result.scalar_one_or_none()

            if config is None:
                config = ReviewConfiguration(
                    id=generate_uuid(),
                    project_id=project_id,
                    required_approvals=required_approvals,
                )
                db.add(config)
            else:
                config.required_approvals = required_approvals

            await db.flush()
            await db.refresh(config)

            logger.info(
                "Review config updated: project=%s required=%d",
                project_id, required_approvals,
            )
            return {
                "id": config.id,
                "project_id": config.project_id,
                "required_approvals": config.required_approvals,
                "created_at": config.created_at,
                "updated_at": config.updated_at,
            }

        # Dev mode mock
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        mock_id = generate_uuid()
        return {
            "id": mock_id,
            "project_id": project_id,
            "required_approvals": required_approvals,
            "created_at": now,
            "updated_at": now,
        }

    # ──────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────

    async def _get_config(
        self,
        db: Any,
        project_id: str,
    ) -> Any | None:
        """Fetch ReviewConfiguration for a project."""
        from sqlalchemy import select

        from app.models.review import ReviewConfiguration

        result = await db.execute(
            select(ReviewConfiguration).where(
                ReviewConfiguration.project_id == project_id
            )
        )
        return result.scalar_one_or_none()

    async def _count_approvals(
        self,
        db: Any,
        architecture_id: str,
    ) -> int:
        """Count approved reviews for an architecture."""
        from sqlalchemy import func, select

        from app.models.review import ArchitectureReview

        result = await db.execute(
            select(func.count()).where(
                ArchitectureReview.architecture_id == architecture_id,
                ArchitectureReview.action == "approved",
            )
        )
        return result.scalar() or 0


# Singleton
review_service = ReviewService()

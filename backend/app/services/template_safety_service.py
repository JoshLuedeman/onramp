"""Marketplace template safety service — scanning, review workflow."""

import json
import logging
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template import Template
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

# Patterns considered dangerous in template JSON payloads.
_DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    (
        r"<script[\s>]",
        "Embedded <script> tag detected",
    ),
    (
        r"javascript\s*:",
        "JavaScript URI scheme detected",
    ),
    (
        r"on(click|load|error|mouseover)\s*=",
        "Inline event handler detected",
    ),
    (
        r"\beval\s*\(",
        "eval() call detected",
    ),
    (
        r"\bFunction\s*\(",
        "Function constructor detected",
    ),
    (
        r"\\x[0-9a-fA-F]{2}",
        "Hex-encoded escape sequence detected",
    ),
    (
        r"\"permissions\"\s*:\s*\[.*\"\*\"",
        "Wildcard permission grant detected",
    ),
    (
        r"\"role\"\s*:\s*\"(Owner|admin)\"",
        "Excessive role assignment detected",
    ),
]


class TemplateSafetyService:
    """Singleton service for template safety scanning and review."""

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def scan_template(self, template_json: str | None) -> dict:
        """Scan raw template JSON for dangerous patterns.

        Returns a dict with ``safe`` (bool) and ``findings`` (list).
        """
        findings: list[dict] = []
        if not template_json:
            return {"safe": True, "findings": []}

        text = template_json
        # If the caller passed a Python dict, serialise it first
        if isinstance(text, dict):
            text = json.dumps(text)

        for pattern, message in _DANGEROUS_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                findings.append({
                    "pattern": pattern,
                    "message": message,
                    "match_count": len(matches),
                })

        return {
            "safe": len(findings) == 0,
            "findings": findings,
        }

    # ------------------------------------------------------------------
    # Publisher verification
    # ------------------------------------------------------------------

    async def validate_publisher(
        self, db: AsyncSession, tenant_id: str,
    ) -> dict:
        """Check whether the tenant is an active, verified publisher."""
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if tenant is None:
            return {
                "verified": False,
                "reason": "Tenant not found",
            }
        if not tenant.is_active:
            return {
                "verified": False,
                "reason": "Tenant is deactivated",
            }
        return {"verified": True, "tenant_name": tenant.name}

    # ------------------------------------------------------------------
    # Review workflow
    # ------------------------------------------------------------------

    async def submit_for_review(
        self, db: AsyncSession, template_id: str,
    ) -> dict:
        """Put a template into the review queue."""
        template = await self._get_template(db, template_id)
        if template is None:
            return {"error": "Template not found"}

        template.visibility = "pending_review"
        await db.flush()
        logger.info(
            "Template '%s' submitted for review (id=%s)",
            template.name, template.id,
        )
        return {
            "template_id": template.id,
            "status": "pending_review",
        }

    async def approve_template(
        self,
        db: AsyncSession,
        template_id: str,
        reviewer_id: str,
    ) -> dict:
        """Approve a template after review — makes it public."""
        template = await self._get_template(db, template_id)
        if template is None:
            return {"error": "Template not found"}

        template.visibility = "public"
        await db.flush()
        logger.info(
            "Template '%s' approved by %s (id=%s)",
            template.name, reviewer_id, template.id,
        )
        return {
            "template_id": template.id,
            "status": "approved",
            "reviewer_id": reviewer_id,
            "approved_at": datetime.now(timezone.utc).isoformat(),
        }

    async def reject_template(
        self,
        db: AsyncSession,
        template_id: str,
        reviewer_id: str,
        reason: str,
    ) -> dict:
        """Reject a template — moves it back to private."""
        template = await self._get_template(db, template_id)
        if template is None:
            return {"error": "Template not found"}

        template.visibility = "rejected"
        await db.flush()
        logger.info(
            "Template '%s' rejected by %s: %s (id=%s)",
            template.name, reviewer_id, reason, template.id,
        )
        return {
            "template_id": template.id,
            "status": "rejected",
            "reviewer_id": reviewer_id,
            "reason": reason,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
        }

    async def list_pending_review(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
    ) -> dict:
        """List templates waiting for review."""
        stmt = (
            select(Template)
            .where(Template.visibility == "pending_review")
            .order_by(Template.created_at)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        templates = list(result.scalars().all())
        return {
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "industry": t.industry,
                    "visibility": t.visibility,
                }
                for t in templates
            ],
            "page": page,
            "page_size": page_size,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    async def _get_template(
        db: AsyncSession, template_id: str,
    ) -> Template | None:
        result = await db.execute(
            select(Template).where(Template.id == template_id)
        )
        return result.scalar_one_or_none()


# Module-level singleton
template_safety_service = TemplateSafetyService()

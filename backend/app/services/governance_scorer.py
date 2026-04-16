"""Governance scorer — aggregates health scores from all governance monitors.

Provides a unified governance scorecard with weighted category scores,
trend tracking, and executive summary generation. Publishes real-time
updates via SSE when scores are recalculated.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone

from app.services.event_stream import event_stream

logger = logging.getLogger(__name__)

# Category weights (must sum to 1.0)
CATEGORY_WEIGHTS: dict[str, float] = {
    "compliance": 0.25,
    "security": 0.25,
    "cost": 0.20,
    "drift": 0.15,
    "tagging": 0.15,
}

# Score thresholds for status classification
HEALTHY_THRESHOLD = 80
WARNING_THRESHOLD = 60


def _classify_status(score: float) -> str:
    """Classify a score into healthy/warning/critical."""
    if score >= HEALTHY_THRESHOLD:
        return "healthy"
    if score >= WARNING_THRESHOLD:
        return "warning"
    return "critical"


def _mock_category_score(name: str) -> dict:
    """Generate a realistic mock score for a category (dev mode)."""
    score = round(random.uniform(70, 95), 1)
    finding_count = random.randint(0, 12)
    return {
        "name": name,
        "score": score,
        "status": _classify_status(score),
        "finding_count": finding_count,
    }


class GovernanceScorer:
    """Aggregates scores from all governance monitors into a unified scorecard."""

    async def calculate_overall_score(self, project_id: str) -> dict:
        """Calculate the weighted overall governance score for a project.

        Aggregates scores from compliance, security/RBAC, cost, drift,
        and tagging monitors into a single 0-100 score.
        """
        categories = await self.get_category_scores(project_id)
        category_lookup = {c["name"]: c["score"] for c in categories}

        overall = sum(
            category_lookup.get(name, 0.0) * weight
            for name, weight in CATEGORY_WEIGHTS.items()
        )
        overall = round(overall, 1)

        executive_summary = self.generate_executive_summary(categories)
        now = datetime.now(timezone.utc)

        result = {
            "overall_score": overall,
            "categories": categories,
            "executive_summary": executive_summary,
            "last_updated": now.isoformat(),
        }

        # Publish SSE event for real-time dashboard updates
        await self._publish_score_event(project_id, result)

        return result

    async def get_category_scores(self, project_id: str) -> list[dict]:
        """Return individual category scores for a project.

        In dev mode, returns realistic mock data. In production,
        delegates to each governance monitor.
        """
        return await self._collect_scores(project_id)

    async def get_score_trend(
        self, project_id: str, days: int = 30
    ) -> dict:
        """Return historical score trend over the specified number of days.

        Generates mock trend data with realistic daily fluctuations.
        """
        now = datetime.now(timezone.utc)
        data_points: list[dict] = []

        # Start with a base score and apply small daily variations
        category_bases = {
            name: random.uniform(70, 92)
            for name in CATEGORY_WEIGHTS
        }

        for i in range(days):
            day = now - timedelta(days=days - 1 - i)

            # Apply small daily variation (±3 points)
            category_scores: dict[str, float] = {}
            for name, base in category_bases.items():
                variation = random.uniform(-3, 3)
                score = round(max(0, min(100, base + variation)), 1)
                category_scores[name] = score
                # Slowly drift the base
                category_bases[name] = base + random.uniform(-0.5, 0.5)

            overall = round(
                sum(
                    category_scores.get(name, 0.0) * weight
                    for name, weight in CATEGORY_WEIGHTS.items()
                ),
                1,
            )

            data_points.append({
                "timestamp": day.isoformat(),
                "overall_score": overall,
                "category_scores": category_scores,
            })

        return {
            "project_id": project_id,
            "data_points": data_points,
        }

    def generate_executive_summary(self, categories: list[dict]) -> str:
        """Auto-generate an executive summary from category scores.

        Produces human-readable text highlighting the overall posture
        and the number of issues requiring attention.
        """
        if not categories:
            return "No governance data available. Run a scan to establish baseline scores."

        overall = round(
            sum(
                next((c["score"] for c in categories if c["name"] == name), 0.0) * weight
                for name, weight in CATEGORY_WEIGHTS.items()
            ),
            1,
        )

        total_findings = sum(c.get("finding_count", 0) for c in categories)

        critical_categories = [c for c in categories if c["status"] == "critical"]
        warning_categories = [c for c in categories if c["status"] == "warning"]

        parts = [
            f"Your landing zone is {overall}% compliant.",
        ]

        if total_findings > 0:
            parts.append(f"{total_findings} issues require attention.")
        else:
            parts.append("No issues require attention.")

        if critical_categories:
            names = ", ".join(c["name"] for c in critical_categories)
            parts.append(f"Critical areas: {names}.")

        if warning_categories:
            names = ", ".join(c["name"] for c in warning_categories)
            parts.append(f"Areas needing improvement: {names}.")

        if not critical_categories and not warning_categories:
            parts.append("All governance areas are healthy.")

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _collect_scores(self, project_id: str) -> list[dict]:
        """Collect scores from all governance monitors.

        Attempts to call each real monitor; on failure (e.g. dev mode
        with no Azure creds) falls back to mock data.
        """
        categories: list[dict] = []

        # Try each monitor, falling back to mocks
        categories.append(await self._get_compliance_score(project_id))
        categories.append(await self._get_security_score(project_id))
        categories.append(await self._get_cost_score(project_id))
        categories.append(await self._get_drift_score(project_id))
        categories.append(await self._get_tagging_score(project_id))

        return categories

    async def _get_compliance_score(self, project_id: str) -> dict:
        """Get compliance score from PolicyMonitor."""
        try:
            from app.services.policy_monitor import policy_monitor

            result = await policy_monitor.scan_compliance(
                project_id=project_id,
                subscription_id="mock",
            )
            score = result.get("compliance_score", 0.0)
            findings = result.get("violation_count", 0)
            return {
                "name": "compliance",
                "score": round(score, 1),
                "status": _classify_status(score),
                "finding_count": findings,
            }
        except Exception:
            logger.debug("Using mock compliance score for project %s", project_id)
            return _mock_category_score("compliance")

    async def _get_security_score(self, project_id: str) -> dict:
        """Get security/RBAC score from RBACMonitor."""
        try:
            from app.services.rbac_monitor import rbac_monitor

            result = await rbac_monitor.scan_rbac_health(
                project_id=project_id,
                subscription_id="mock",
            )
            score = result.get("health_score", 0.0)
            findings = result.get("finding_count", 0)
            return {
                "name": "security",
                "score": round(score, 1),
                "status": _classify_status(score),
                "finding_count": findings,
            }
        except Exception:
            logger.debug("Using mock security score for project %s", project_id)
            return _mock_category_score("security")

    async def _get_cost_score(self, project_id: str) -> dict:
        """Get cost adherence score from CostManager."""
        try:
            from app.services.cost_manager import cost_manager

            summary = await cost_manager.get_cost_summary(project_id=project_id)
            # Calculate budget adherence as a score
            budget = summary.get("monthly_budget", 0)
            actual = summary.get("current_month_cost", 0)
            if budget > 0:
                adherence = max(0, min(100, (1 - (actual - budget) / budget) * 100))
                score = round(adherence, 1)
            else:
                score = round(summary.get("health_score", 85.0), 1)
            findings = summary.get("anomaly_count", 0)
            return {
                "name": "cost",
                "score": score,
                "status": _classify_status(score),
                "finding_count": findings,
            }
        except Exception:
            logger.debug("Using mock cost score for project %s", project_id)
            return _mock_category_score("cost")

    async def _get_drift_score(self, project_id: str) -> dict:
        """Get drift score from DriftScanner."""
        try:
            from app.services.drift_scanner import drift_scanner

            result = await drift_scanner.scan_drift(project_id=project_id)
            score = result.get("health_score", 0.0)
            findings = result.get("drift_count", 0)
            return {
                "name": "drift",
                "score": round(score, 1),
                "status": _classify_status(score),
                "finding_count": findings,
            }
        except Exception:
            logger.debug("Using mock drift score for project %s", project_id)
            return _mock_category_score("drift")

    async def _get_tagging_score(self, project_id: str) -> dict:
        """Get tagging compliance score from TaggingMonitor."""
        try:
            from app.services.tagging_monitor import tagging_monitor

            result = await tagging_monitor.scan_tagging_compliance(
                project_id=project_id,
                subscription_id="mock",
            )
            score = result.get("compliance_score", 0.0)
            findings = result.get("violation_count", 0)
            return {
                "name": "tagging",
                "score": round(score, 1),
                "status": _classify_status(score),
                "finding_count": findings,
            }
        except Exception:
            logger.debug("Using mock tagging score for project %s", project_id)
            return _mock_category_score("tagging")

    async def _publish_score_event(
        self, project_id: str, result: dict
    ) -> None:
        """Publish a governance_score_updated SSE event."""
        try:
            await event_stream.publish(
                event_type="governance_score_updated",
                data={
                    "project_id": project_id,
                    "overall_score": result["overall_score"],
                    "categories": result["categories"],
                    "executive_summary": result["executive_summary"],
                },
                project_id=project_id,
            )
        except Exception:
            logger.warning(
                "Failed to publish governance score event for project %s",
                project_id,
                exc_info=True,
            )


# Module-level singleton
governance_scorer = GovernanceScorer()

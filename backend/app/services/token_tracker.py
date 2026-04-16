"""Token usage tracker — records and aggregates AI API consumption.

Provides a singleton that stores token usage records.  In dev mode (no DB)
everything lives in an in-memory list.  When a DB session is available the
records are also persisted.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Rough cost per 1K tokens (USD) — used only for estimates
_COST_PER_1K: dict[str, dict[str, float]] = {
    "gpt-4o": {"prompt": 0.005, "completion": 0.015},
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
    "gpt-4": {"prompt": 0.03, "completion": 0.06},
    "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
}
_DEFAULT_COST = {"prompt": 0.01, "completion": 0.03}


def _estimate_cost(
    model: str, prompt_tokens: int, completion_tokens: int
) -> float:
    rates = _COST_PER_1K.get(model, _DEFAULT_COST)
    return round(
        (prompt_tokens / 1000) * rates["prompt"]
        + (completion_tokens / 1000) * rates["completion"],
        6,
    )


@dataclass
class UsageRecord:
    """In-memory token usage record."""

    feature: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model_name: str
    prompt_version: str
    cost_estimate: float
    user_id: str
    tenant_id: str
    project_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TokenTracker:
    """Singleton that records and queries token usage.

    In dev mode everything is kept in memory.
    """

    _instance: TokenTracker | None = None
    _lock = threading.Lock()

    def __new__(cls) -> TokenTracker:  # noqa: D102
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._records: list[UsageRecord] = []
                cls._instance = inst
            return cls._instance

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_usage(
        self,
        feature: str,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
        prompt_version: str,
        user_id: str,
        tenant_id: str,
        project_id: str | None = None,
    ) -> UsageRecord:
        """Record a single AI API invocation."""
        total = prompt_tokens + completion_tokens
        cost = _estimate_cost(model, prompt_tokens, completion_tokens)
        record = UsageRecord(
            feature=feature,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            model_name=model,
            prompt_version=prompt_version,
            cost_estimate=cost,
            user_id=user_id,
            tenant_id=tenant_id,
            project_id=project_id,
        )
        self._records.append(record)
        logger.debug(
            "Recorded %d tokens for %s (model=%s)", total, feature, model
        )
        return record

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def _filter(
        self,
        tenant_id: str | None = None,
        user_id: str | None = None,
        feature: str | None = None,
        days: int = 30,
    ) -> list[UsageRecord]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        results = []
        for r in self._records:
            if r.created_at < cutoff:
                continue
            if tenant_id and r.tenant_id != tenant_id:
                continue
            if user_id and r.user_id != user_id:
                continue
            if feature and r.feature != feature:
                continue
            results.append(r)
        return results

    def get_usage_summary(
        self,
        tenant_id: str | None = None,
        user_id: str | None = None,
        feature: str | None = None,
        days: int = 30,
    ) -> dict:
        """Return aggregate token stats for the given filters."""
        records = self._filter(tenant_id=tenant_id, user_id=user_id, feature=feature, days=days)
        return {
            "feature": feature,
            "total_requests": len(records),
            "total_prompt_tokens": sum(r.prompt_tokens for r in records),
            "total_completion_tokens": sum(r.completion_tokens for r in records),
            "total_tokens": sum(r.total_tokens for r in records),
            "total_cost_estimate": round(sum(r.cost_estimate for r in records), 6),
        }

    def get_usage_by_feature(
        self,
        tenant_id: str | None = None,
        days: int = 30,
    ) -> list[dict]:
        """Return per-feature usage summaries."""
        records = self._filter(tenant_id=tenant_id, days=days)
        grouped: dict[str, list[UsageRecord]] = defaultdict(list)
        for r in records:
            grouped[r.feature].append(r)

        summaries = []
        for feat, recs in sorted(grouped.items()):
            summaries.append(
                {
                    "feature": feat,
                    "total_requests": len(recs),
                    "total_prompt_tokens": sum(r.prompt_tokens for r in recs),
                    "total_completion_tokens": sum(r.completion_tokens for r in recs),
                    "total_tokens": sum(r.total_tokens for r in recs),
                    "total_cost_estimate": round(
                        sum(r.cost_estimate for r in recs), 6
                    ),
                }
            )
        return summaries

    # ------------------------------------------------------------------
    # Testing helpers
    # ------------------------------------------------------------------

    @classmethod
    def reset(cls) -> None:
        """Reset singleton — **tests only**."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance._records.clear()
            cls._instance = None


# Module-level convenience accessor
token_tracker = TokenTracker()

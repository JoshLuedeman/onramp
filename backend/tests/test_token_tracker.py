"""Tests for the TokenTracker service."""

import pytest

from app.services.token_tracker import TokenTracker, _estimate_cost


class TestEstimateCost:
    """Unit tests for the cost estimation helper."""

    def test_known_model_gpt4o(self):
        cost = _estimate_cost("gpt-4o", prompt_tokens=1000, completion_tokens=1000)
        # 1K prompt * 0.005 + 1K completion * 0.015 = 0.020
        assert cost == 0.02

    def test_known_model_gpt4o_mini(self):
        cost = _estimate_cost("gpt-4o-mini", prompt_tokens=1000, completion_tokens=1000)
        assert cost == pytest.approx(0.00075)

    def test_unknown_model_uses_defaults(self):
        cost = _estimate_cost("unknown-model", prompt_tokens=1000, completion_tokens=1000)
        # Default: 0.01 + 0.03 = 0.04
        assert cost == 0.04

    def test_zero_tokens(self):
        cost = _estimate_cost("gpt-4o", prompt_tokens=0, completion_tokens=0)
        assert cost == 0.0


class TestTokenTracker:
    """Tests for the TokenTracker singleton."""

    @pytest.fixture(autouse=True)
    def _reset_tracker(self):
        """Reset singleton state before each test."""
        TokenTracker.reset()
        yield
        TokenTracker.reset()

    def test_singleton_identity(self):
        t1 = TokenTracker()
        t2 = TokenTracker()
        assert t1 is t2

    def test_record_usage_returns_record(self):
        tracker = TokenTracker()
        record = tracker.record_usage(
            feature="architecture",
            prompt_tokens=100,
            completion_tokens=50,
            model="gpt-4o",
            prompt_version="v1",
            user_id="u1",
            tenant_id="t1",
        )
        assert record.feature == "architecture"
        assert record.total_tokens == 150
        assert record.cost_estimate > 0

    def test_record_usage_with_project_id(self):
        tracker = TokenTracker()
        record = tracker.record_usage(
            feature="compliance",
            prompt_tokens=200,
            completion_tokens=100,
            model="gpt-4o",
            prompt_version="v2",
            user_id="u1",
            tenant_id="t1",
            project_id="p1",
        )
        assert record.project_id == "p1"

    def test_get_usage_summary_empty(self):
        tracker = TokenTracker()
        summary = tracker.get_usage_summary()
        assert summary["total_requests"] == 0
        assert summary["total_tokens"] == 0

    def test_get_usage_summary_with_records(self):
        tracker = TokenTracker()
        tracker.record_usage("arch", 100, 50, "gpt-4o", "v1", "u1", "t1")
        tracker.record_usage("arch", 200, 100, "gpt-4o", "v1", "u1", "t1")
        summary = tracker.get_usage_summary()
        assert summary["total_requests"] == 2
        assert summary["total_prompt_tokens"] == 300
        assert summary["total_completion_tokens"] == 150
        assert summary["total_tokens"] == 450

    def test_get_usage_summary_filter_by_tenant(self):
        tracker = TokenTracker()
        tracker.record_usage("arch", 100, 50, "gpt-4o", "v1", "u1", "t1")
        tracker.record_usage("arch", 200, 100, "gpt-4o", "v1", "u2", "t2")
        summary = tracker.get_usage_summary(tenant_id="t1")
        assert summary["total_requests"] == 1

    def test_get_usage_summary_filter_by_feature(self):
        tracker = TokenTracker()
        tracker.record_usage("arch", 100, 50, "gpt-4o", "v1", "u1", "t1")
        tracker.record_usage("scoring", 200, 100, "gpt-4o", "v1", "u1", "t1")
        summary = tracker.get_usage_summary(feature="scoring")
        assert summary["total_requests"] == 1
        assert summary["total_prompt_tokens"] == 200

    def test_get_usage_by_feature(self):
        tracker = TokenTracker()
        tracker.record_usage("arch", 100, 50, "gpt-4o", "v1", "u1", "t1")
        tracker.record_usage("scoring", 200, 100, "gpt-4o", "v1", "u1", "t1")
        tracker.record_usage("arch", 300, 150, "gpt-4o", "v1", "u1", "t1")
        by_feature = tracker.get_usage_by_feature()
        assert len(by_feature) == 2
        arch_summary = next(f for f in by_feature if f["feature"] == "arch")
        assert arch_summary["total_requests"] == 2

    def test_get_usage_by_feature_filter_by_tenant(self):
        tracker = TokenTracker()
        tracker.record_usage("arch", 100, 50, "gpt-4o", "v1", "u1", "t1")
        tracker.record_usage("arch", 200, 100, "gpt-4o", "v1", "u2", "t2")
        by_feature = tracker.get_usage_by_feature(tenant_id="t1")
        assert len(by_feature) == 1
        assert by_feature[0]["total_requests"] == 1

    def test_reset_clears_records(self):
        tracker = TokenTracker()
        tracker.record_usage("arch", 100, 50, "gpt-4o", "v1", "u1", "t1")
        assert tracker.get_usage_summary()["total_requests"] == 1
        TokenTracker.reset()
        new_tracker = TokenTracker()
        assert new_tracker.get_usage_summary()["total_requests"] == 0

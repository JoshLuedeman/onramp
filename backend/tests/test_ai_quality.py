"""Tests for AI quality infrastructure — prompt versioning, feedback, token tracking.

Targets 80%+ coverage with 50+ tests covering:
- PromptRegistry service (register, get, list, bootstrap, reset)
- TokenTracker service (record, summarize, by-feature, filtering)
- Pydantic schemas (creation, validation, enums)
- SQLAlchemy models (importable, tablenames, columns)
- FastAPI routes (all 8 endpoints)
"""

import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.ai_quality import (
    AIFeedbackCreate,
    AIFeedbackResponse,
    FeedbackRating,
    FeedbackStatsItem,
    FeedbackStatsResponse,
    PromptListResponse,
    PromptVersionResponse,
    TokenUsageByFeature,
    TokenUsageSummary,
)
from app.services.prompt_registry import PromptRegistry, prompt_registry
from app.services.token_tracker import TokenTracker, token_tracker

client = TestClient(app)


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset singletons before each test so state doesn't leak."""
    # Clear data but keep the same singleton instances that routes reference
    prompt_registry._prompts.clear()
    prompt_registry._initialized = False
    token_tracker._records.clear()
    # Clear feedback store
    from app.api.routes.ai_quality import _feedback_store
    _feedback_store.clear()
    yield
    prompt_registry._prompts.clear()
    prompt_registry._initialized = False
    token_tracker._records.clear()


# ===================================================================
# 1. Prompt Registry — unit tests
# ===================================================================


class TestPromptRegistry:
    def test_register_prompt(self):
        reg = PromptRegistry()
        entry = reg.register_prompt("test_prompt", 1, "Hello {name}")
        assert entry.name == "test_prompt"
        assert entry.version == 1
        assert entry.template == "Hello {name}"

    def test_register_prompt_with_metadata(self):
        reg = PromptRegistry()
        entry = reg.register_prompt(
            "test_prompt", 1, "Hello", metadata={"author": "ai-team"}
        )
        assert entry.metadata == {"author": "ai-team"}

    def test_get_prompt_specific_version(self):
        reg = PromptRegistry()
        reg.register_prompt("p", 1, "v1 template")
        reg.register_prompt("p", 2, "v2 template")
        entry = reg.get_prompt("p", version=1)
        assert entry is not None
        assert entry.template == "v1 template"

    def test_get_prompt_latest(self):
        reg = PromptRegistry()
        reg.register_prompt("p", 1, "v1")
        reg.register_prompt("p", 2, "v2")
        entry = reg.get_prompt("p")
        assert entry is not None
        assert entry.version == 2
        assert entry.template == "v2"

    def test_get_prompt_nonexistent(self):
        reg = PromptRegistry()
        assert reg.get_prompt("nonexistent") is None

    def test_get_prompt_nonexistent_version(self):
        reg = PromptRegistry()
        reg.register_prompt("p", 1, "v1")
        assert reg.get_prompt("p", version=99) is None

    def test_get_latest_version(self):
        reg = PromptRegistry()
        reg.register_prompt("p", 1, "v1")
        reg.register_prompt("p", 3, "v3")
        assert reg.get_latest_version("p") == 3

    def test_get_latest_version_nonexistent(self):
        reg = PromptRegistry()
        assert reg.get_latest_version("ghost") is None

    def test_list_prompts_empty(self):
        reg = PromptRegistry()
        # After reset, no built-in loading (already reset in fixture)
        # Register nothing, list should include built-ins from lazy init
        # Actually after reset, _initialized is False, list_prompts triggers init
        prompts = reg.list_prompts()
        # Built-in prompts are loaded
        assert isinstance(prompts, list)

    def test_list_prompts_with_registered(self):
        reg = PromptRegistry()
        reg.register_prompt("a", 1, "template a")
        reg.register_prompt("b", 1, "template b")
        prompts = reg.list_prompts()
        names = {p.name for p in prompts}
        assert "a" in names
        assert "b" in names

    def test_is_active_updated_on_new_version(self):
        reg = PromptRegistry()
        reg.register_prompt("p", 1, "v1")
        reg.register_prompt("p", 2, "v2")
        v1 = reg.get_prompt("p", version=1)
        v2 = reg.get_prompt("p", version=2)
        assert v1 is not None and not v1.is_active
        assert v2 is not None and v2.is_active

    def test_builtin_prompts_loaded(self):
        reg = PromptRegistry()
        entry = reg.get_prompt("architecture_system")
        assert entry is not None
        assert entry.version == 1
        assert "Azure Solutions Architect" in entry.template

    def test_builtin_compliance_prompt(self):
        reg = PromptRegistry()
        entry = reg.get_prompt("compliance_evaluation")
        assert entry is not None
        assert "compliance" in entry.template.lower()

    def test_builtin_bicep_prompt(self):
        reg = PromptRegistry()
        entry = reg.get_prompt("bicep_generation")
        assert entry is not None
        assert "Bicep" in entry.template

    def test_builtin_cost_prompt(self):
        reg = PromptRegistry()
        entry = reg.get_prompt("cost_estimation")
        assert entry is not None
        assert "cost" in entry.template.lower()

    def test_builtin_refinement_prompt(self):
        reg = PromptRegistry()
        entry = reg.get_prompt("architecture_refinement")
        assert entry is not None

    def test_singleton_instance(self):
        a = PromptRegistry()
        b = PromptRegistry()
        assert a is b

    def test_reset_clears_state(self):
        reg = PromptRegistry()
        reg.register_prompt("x", 1, "temp")
        PromptRegistry.reset()
        reg2 = PromptRegistry()
        # After reset + new instance, lazy init will reload built-ins but not "x"
        assert reg2.get_prompt("x") is None


# ===================================================================
# 2. Token Tracker — unit tests
# ===================================================================


class TestTokenTracker:
    def test_record_usage(self):
        tracker = TokenTracker()
        record = tracker.record_usage(
            feature="architecture",
            prompt_tokens=100,
            completion_tokens=200,
            model="gpt-4o",
            prompt_version="architecture_v1",
            user_id="u1",
            tenant_id="t1",
        )
        assert record.total_tokens == 300
        assert record.cost_estimate > 0

    def test_record_usage_with_project(self):
        tracker = TokenTracker()
        record = tracker.record_usage(
            feature="bicep",
            prompt_tokens=50,
            completion_tokens=100,
            model="gpt-4o-mini",
            prompt_version="bicep_v1",
            user_id="u1",
            tenant_id="t1",
            project_id="proj-1",
        )
        assert record.project_id == "proj-1"

    def test_get_usage_summary_empty(self):
        tracker = TokenTracker()
        summary = tracker.get_usage_summary(tenant_id="t1")
        assert summary["total_requests"] == 0
        assert summary["total_tokens"] == 0

    def test_get_usage_summary_with_records(self):
        tracker = TokenTracker()
        tracker.record_usage("arch", 100, 200, "gpt-4o", "v1", "u1", "t1")
        tracker.record_usage("arch", 150, 250, "gpt-4o", "v1", "u1", "t1")
        summary = tracker.get_usage_summary(tenant_id="t1")
        assert summary["total_requests"] == 2
        assert summary["total_prompt_tokens"] == 250
        assert summary["total_completion_tokens"] == 450
        assert summary["total_tokens"] == 700

    def test_get_usage_summary_filter_by_feature(self):
        tracker = TokenTracker()
        tracker.record_usage("arch", 100, 200, "gpt-4o", "v1", "u1", "t1")
        tracker.record_usage("bicep", 50, 100, "gpt-4o", "v1", "u1", "t1")
        summary = tracker.get_usage_summary(tenant_id="t1", feature="arch")
        assert summary["total_requests"] == 1

    def test_get_usage_summary_filter_by_user(self):
        tracker = TokenTracker()
        tracker.record_usage("arch", 100, 200, "gpt-4o", "v1", "u1", "t1")
        tracker.record_usage("arch", 50, 100, "gpt-4o", "v1", "u2", "t1")
        summary = tracker.get_usage_summary(tenant_id="t1", user_id="u1")
        assert summary["total_requests"] == 1

    def test_get_usage_by_feature(self):
        tracker = TokenTracker()
        tracker.record_usage("arch", 100, 200, "gpt-4o", "v1", "u1", "t1")
        tracker.record_usage("bicep", 50, 100, "gpt-4o", "v1", "u1", "t1")
        tracker.record_usage("arch", 80, 160, "gpt-4o", "v1", "u1", "t1")
        by_feature = tracker.get_usage_by_feature(tenant_id="t1")
        assert len(by_feature) == 2
        arch = next(s for s in by_feature if s["feature"] == "arch")
        assert arch["total_requests"] == 2

    def test_get_usage_by_feature_empty(self):
        tracker = TokenTracker()
        result = tracker.get_usage_by_feature(tenant_id="t1")
        assert result == []

    def test_cost_estimation_known_model(self):
        tracker = TokenTracker()
        record = tracker.record_usage(
            "test", 1000, 1000, "gpt-4o", "v1", "u1", "t1"
        )
        # gpt-4o: prompt=0.005/1K, completion=0.015/1K → 0.005 + 0.015 = 0.02
        assert record.cost_estimate == pytest.approx(0.02, abs=0.001)

    def test_cost_estimation_unknown_model(self):
        tracker = TokenTracker()
        record = tracker.record_usage(
            "test", 1000, 1000, "custom-model", "v1", "u1", "t1"
        )
        # Uses default rates
        assert record.cost_estimate > 0

    def test_singleton(self):
        a = TokenTracker()
        b = TokenTracker()
        assert a is b

    def test_reset(self):
        tracker = TokenTracker()
        tracker.record_usage("test", 10, 20, "gpt-4o", "v1", "u1", "t1")
        TokenTracker.reset()
        tracker2 = TokenTracker()
        summary = tracker2.get_usage_summary()
        assert summary["total_requests"] == 0


# ===================================================================
# 3. Pydantic Schemas — unit tests
# ===================================================================


class TestSchemas:
    def test_feedback_rating_enum_values(self):
        assert FeedbackRating.POSITIVE == "positive"
        assert FeedbackRating.NEGATIVE == "negative"

    def test_feedback_create_minimal(self):
        fb = AIFeedbackCreate(
            feature="architecture",
            output_id="out-1",
            rating=FeedbackRating.POSITIVE,
        )
        assert fb.comment is None
        assert fb.rating == FeedbackRating.POSITIVE

    def test_feedback_create_with_comment(self):
        fb = AIFeedbackCreate(
            feature="compliance",
            output_id="out-2",
            rating=FeedbackRating.NEGATIVE,
            comment="Needs more detail",
        )
        assert fb.comment == "Needs more detail"

    def test_feedback_response_from_dict(self):
        data = {
            "id": str(uuid.uuid4()),
            "feature": "bicep",
            "output_id": "b-1",
            "rating": "positive",
            "prompt_version": "bicep_v1",
            "user_id": "u1",
            "tenant_id": "t1",
            "created_at": datetime.now(),
        }
        resp = AIFeedbackResponse(**data)
        assert resp.feature == "bicep"
        assert resp.comment is None

    def test_token_usage_summary_defaults(self):
        s = TokenUsageSummary()
        assert s.total_requests == 0
        assert s.total_tokens == 0
        assert s.total_cost_estimate == 0.0

    def test_token_usage_by_feature_default(self):
        t = TokenUsageByFeature()
        assert t.summaries == []

    def test_prompt_version_response(self):
        resp = PromptVersionResponse(
            id=str(uuid.uuid4()),
            name="test",
            version=1,
            template="Hello",
            is_active=True,
            created_at=datetime.now(),
        )
        assert resp.name == "test"
        assert resp.metadata_json is None

    def test_prompt_list_response(self):
        plr = PromptListResponse()
        assert plr.prompts == []

    def test_feedback_stats_item(self):
        item = FeedbackStatsItem(
            feature="arch", total=10, positive=7, negative=3, positive_rate=0.7
        )
        assert item.positive_rate == 0.7

    def test_feedback_stats_response(self):
        resp = FeedbackStatsResponse()
        assert resp.stats == []


# ===================================================================
# 4. Models — import and tablename tests
# ===================================================================


class TestModels:
    def test_prompt_version_importable(self):
        from app.models.prompt_version import PromptVersion
        assert PromptVersion.__tablename__ == "prompt_versions"

    def test_ai_feedback_importable(self):
        from app.models.ai_feedback import AIFeedback
        assert AIFeedback.__tablename__ == "ai_feedback"

    def test_token_usage_importable(self):
        from app.models.token_usage import TokenUsage
        assert TokenUsage.__tablename__ == "token_usage"

    def test_models_in_init(self):
        from app.models import AIFeedback, PromptVersion, TokenUsage
        assert AIFeedback.__tablename__ == "ai_feedback"
        assert PromptVersion.__tablename__ == "prompt_versions"
        assert TokenUsage.__tablename__ == "token_usage"

    def test_models_in_base_metadata(self):
        from app.models import Base
        table_names = set(Base.metadata.tables.keys())
        assert "prompt_versions" in table_names
        assert "ai_feedback" in table_names
        assert "token_usage" in table_names


# ===================================================================
# 5. API Routes — integration tests
# ===================================================================


class TestFeedbackRoutes:
    def test_submit_positive_feedback(self):
        r = client.post(
            "/api/ai/feedback",
            json={
                "feature": "architecture",
                "output_id": "out-1",
                "rating": "positive",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["rating"] == "positive"
        assert data["feature"] == "architecture"
        assert "id" in data

    def test_submit_negative_feedback_with_comment(self):
        r = client.post(
            "/api/ai/feedback",
            json={
                "feature": "compliance",
                "output_id": "out-2",
                "rating": "negative",
                "comment": "Score seems low",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["rating"] == "negative"
        assert data["comment"] == "Score seems low"

    def test_submit_feedback_invalid_rating(self):
        r = client.post(
            "/api/ai/feedback",
            json={
                "feature": "bicep",
                "output_id": "b-1",
                "rating": "neutral",
            },
        )
        assert r.status_code == 422  # Validation error

    def test_list_feedback_empty(self):
        r = client.get("/api/ai/feedback")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_feedback_after_submit(self):
        client.post(
            "/api/ai/feedback",
            json={"feature": "arch", "output_id": "o1", "rating": "positive"},
        )
        r = client.get("/api/ai/feedback")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1

    def test_list_feedback_filter_by_feature(self):
        client.post(
            "/api/ai/feedback",
            json={"feature": "arch", "output_id": "o1", "rating": "positive"},
        )
        client.post(
            "/api/ai/feedback",
            json={"feature": "bicep", "output_id": "o2", "rating": "negative"},
        )
        r = client.get("/api/ai/feedback", params={"feature": "arch"})
        assert r.status_code == 200
        data = r.json()
        assert all(d["feature"] == "arch" for d in data)

    def test_list_feedback_filter_by_rating(self):
        client.post(
            "/api/ai/feedback",
            json={"feature": "arch", "output_id": "o1", "rating": "positive"},
        )
        client.post(
            "/api/ai/feedback",
            json={"feature": "arch", "output_id": "o2", "rating": "negative"},
        )
        r = client.get("/api/ai/feedback", params={"rating": "positive"})
        assert r.status_code == 200
        data = r.json()
        assert all(d["rating"] == "positive" for d in data)

    def test_feedback_stats_empty(self):
        r = client.get("/api/ai/feedback/stats")
        assert r.status_code == 200
        data = r.json()
        assert "stats" in data
        assert isinstance(data["stats"], list)

    def test_feedback_stats_with_data(self):
        client.post(
            "/api/ai/feedback",
            json={"feature": "arch", "output_id": "o1", "rating": "positive"},
        )
        client.post(
            "/api/ai/feedback",
            json={"feature": "arch", "output_id": "o2", "rating": "negative"},
        )
        r = client.get("/api/ai/feedback/stats")
        assert r.status_code == 200
        data = r.json()
        assert len(data["stats"]) >= 1
        arch_stat = next(
            (s for s in data["stats"] if s["feature"] == "arch"), None
        )
        assert arch_stat is not None
        assert arch_stat["total"] == 2
        assert arch_stat["positive"] == 1
        assert arch_stat["negative"] == 1


class TestTokenRoutes:
    def test_token_usage_summary_empty(self):
        r = client.get("/api/ai/tokens/usage")
        assert r.status_code == 200
        data = r.json()
        assert data["total_requests"] == 0

    def test_token_usage_by_feature_empty(self):
        r = client.get("/api/ai/tokens/usage/by-feature")
        assert r.status_code == 200
        data = r.json()
        assert data["summaries"] == []

    def test_token_usage_summary_with_data(self):
        # Seed data via the module-level tracker (same instance routes use)
        token_tracker.record_usage(
            "arch", 100, 200, "gpt-4o", "v1", "dev-user-id", "dev-tenant"
        )
        r = client.get("/api/ai/tokens/usage")
        assert r.status_code == 200
        data = r.json()
        assert data["total_requests"] >= 1

    def test_token_usage_by_feature_with_data(self):
        token_tracker.record_usage(
            "arch", 100, 200, "gpt-4o", "v1", "dev-user-id", "dev-tenant"
        )
        token_tracker.record_usage(
            "bicep", 50, 100, "gpt-4o", "v1", "dev-user-id", "dev-tenant"
        )
        r = client.get("/api/ai/tokens/usage/by-feature")
        assert r.status_code == 200
        data = r.json()
        assert len(data["summaries"]) >= 2

    def test_token_usage_summary_filter_by_feature(self):
        token_tracker.record_usage(
            "arch", 100, 200, "gpt-4o", "v1", "dev-user-id", "dev-tenant"
        )
        token_tracker.record_usage(
            "bicep", 50, 100, "gpt-4o", "v1", "dev-user-id", "dev-tenant"
        )
        r = client.get("/api/ai/tokens/usage", params={"feature": "arch"})
        assert r.status_code == 200
        data = r.json()
        assert data["total_requests"] == 1


class TestPromptRoutes:
    def test_list_prompts(self):
        r = client.get("/api/ai/prompts")
        assert r.status_code == 200
        data = r.json()
        assert "prompts" in data
        assert isinstance(data["prompts"], list)

    def test_list_prompts_has_builtins(self):
        r = client.get("/api/ai/prompts")
        assert r.status_code == 200
        data = r.json()
        names = {p["name"] for p in data["prompts"]}
        assert "architecture_system" in names

    def test_get_prompt_latest(self):
        r = client.get("/api/ai/prompts/architecture_system")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "architecture_system"
        assert data["version"] == 1
        assert "Azure Solutions Architect" in data["template"]

    def test_get_prompt_specific_version(self):
        r = client.get("/api/ai/prompts/architecture_system/1")
        assert r.status_code == 200
        data = r.json()
        assert data["version"] == 1

    def test_get_prompt_not_found(self):
        r = client.get("/api/ai/prompts/nonexistent_prompt")
        assert r.status_code == 404

    def test_get_prompt_version_not_found(self):
        r = client.get("/api/ai/prompts/architecture_system/99")
        assert r.status_code == 404

    def test_prompt_response_has_required_fields(self):
        r = client.get("/api/ai/prompts/cost_estimation")
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        assert "name" in data
        assert "version" in data
        assert "template" in data
        assert "is_active" in data
        assert "created_at" in data

    def test_all_builtin_prompts_accessible(self):
        builtins = [
            "architecture_system",
            "compliance_evaluation",
            "bicep_generation",
            "cost_estimation",
            "architecture_refinement",
        ]
        for name in builtins:
            r = client.get(f"/api/ai/prompts/{name}")
            assert r.status_code == 200, f"Failed to get prompt: {name}"

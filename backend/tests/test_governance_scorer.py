"""Tests for governance scorer — schemas, service, SSE events, and routes."""

import random
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PROJECT_ID = "proj-test-governance"


# ── Schema tests ─────────────────────────────────────────────────────────────


class TestGovernanceScorecardSchemas:
    """Verify governance scorecard Pydantic schemas."""

    def test_category_status_enum(self):
        from app.schemas.governance_scorecard import CategoryStatus

        assert CategoryStatus.HEALTHY == "healthy"
        assert CategoryStatus.WARNING == "warning"
        assert CategoryStatus.CRITICAL == "critical"

    def test_category_score_schema(self):
        from app.schemas.governance_scorecard import CategoryScore

        score = CategoryScore(
            name="compliance",
            score=85.0,
            status="healthy",
            finding_count=3,
        )
        assert score.name == "compliance"
        assert score.score == 85.0
        assert score.status == "healthy"
        assert score.finding_count == 3

    def test_category_score_defaults(self):
        from app.schemas.governance_scorecard import CategoryScore

        score = CategoryScore(name="drift", score=50.0, status="warning")
        assert score.finding_count == 0

    def test_category_score_boundary_zero(self):
        from app.schemas.governance_scorecard import CategoryScore

        score = CategoryScore(name="test", score=0, status="critical")
        assert score.score == 0

    def test_category_score_boundary_hundred(self):
        from app.schemas.governance_scorecard import CategoryScore

        score = CategoryScore(name="test", score=100, status="healthy")
        assert score.score == 100

    def test_category_score_invalid_score_above(self):
        from pydantic import ValidationError

        from app.schemas.governance_scorecard import CategoryScore

        with pytest.raises(ValidationError):
            CategoryScore(name="test", score=101, status="healthy")

    def test_category_score_invalid_score_below(self):
        from pydantic import ValidationError

        from app.schemas.governance_scorecard import CategoryScore

        with pytest.raises(ValidationError):
            CategoryScore(name="test", score=-1, status="healthy")

    def test_governance_score_response(self):
        from app.schemas.governance_scorecard import (
            CategoryScore,
            GovernanceScoreResponse,
        )

        now = datetime.now(timezone.utc)
        response = GovernanceScoreResponse(
            overall_score=82.5,
            categories=[
                CategoryScore(name="compliance", score=85.0, status="healthy"),
                CategoryScore(name="security", score=80.0, status="healthy"),
            ],
            executive_summary="Your landing zone is 82.5% compliant.",
            last_updated=now,
        )
        assert response.overall_score == 82.5
        assert len(response.categories) == 2
        assert response.executive_summary.startswith("Your landing zone")
        assert response.last_updated == now

    def test_governance_score_response_defaults(self):
        from app.schemas.governance_scorecard import GovernanceScoreResponse

        response = GovernanceScoreResponse(overall_score=0)
        assert response.categories == []
        assert response.executive_summary == ""
        assert response.last_updated is None

    def test_score_trend_point(self):
        from app.schemas.governance_scorecard import ScoreTrendPoint

        now = datetime.now(timezone.utc)
        point = ScoreTrendPoint(
            timestamp=now,
            overall_score=78.5,
            category_scores={"compliance": 80.0, "security": 77.0},
        )
        assert point.timestamp == now
        assert point.overall_score == 78.5
        assert point.category_scores["compliance"] == 80.0

    def test_score_trend_point_defaults(self):
        from app.schemas.governance_scorecard import ScoreTrendPoint

        now = datetime.now(timezone.utc)
        point = ScoreTrendPoint(timestamp=now, overall_score=50.0)
        assert point.category_scores == {}

    def test_score_trend_response(self):
        from app.schemas.governance_scorecard import (
            ScoreTrendPoint,
            ScoreTrendResponse,
        )

        now = datetime.now(timezone.utc)
        response = ScoreTrendResponse(
            project_id="proj-1",
            data_points=[
                ScoreTrendPoint(timestamp=now, overall_score=80.0),
            ],
        )
        assert response.project_id == "proj-1"
        assert len(response.data_points) == 1

    def test_score_trend_response_empty(self):
        from app.schemas.governance_scorecard import ScoreTrendResponse

        response = ScoreTrendResponse(project_id="proj-1")
        assert response.data_points == []

    def test_governance_score_response_serialization(self):
        from app.schemas.governance_scorecard import GovernanceScoreResponse

        response = GovernanceScoreResponse(
            overall_score=75.0,
            executive_summary="Test summary",
        )
        data = response.model_dump()
        assert data["overall_score"] == 75.0
        assert data["executive_summary"] == "Test summary"
        assert data["categories"] == []


# ── Service: classify_status ─────────────────────────────────────────────────


class TestClassifyStatus:
    """Test the _classify_status helper."""

    def test_healthy_at_threshold(self):
        from app.services.governance_scorer import _classify_status

        assert _classify_status(80) == "healthy"

    def test_healthy_above_threshold(self):
        from app.services.governance_scorer import _classify_status

        assert _classify_status(95) == "healthy"

    def test_warning_at_threshold(self):
        from app.services.governance_scorer import _classify_status

        assert _classify_status(60) == "warning"

    def test_warning_between_thresholds(self):
        from app.services.governance_scorer import _classify_status

        assert _classify_status(75) == "warning"

    def test_critical_below_threshold(self):
        from app.services.governance_scorer import _classify_status

        assert _classify_status(59) == "critical"

    def test_critical_zero(self):
        from app.services.governance_scorer import _classify_status

        assert _classify_status(0) == "critical"

    def test_healthy_perfect(self):
        from app.services.governance_scorer import _classify_status

        assert _classify_status(100) == "healthy"


# ── Service: mock_category_score ─────────────────────────────────────────────


class TestMockCategoryScore:
    """Test the _mock_category_score helper."""

    def test_returns_expected_keys(self):
        from app.services.governance_scorer import _mock_category_score

        result = _mock_category_score("compliance")
        assert "name" in result
        assert "score" in result
        assert "status" in result
        assert "finding_count" in result

    def test_name_matches(self):
        from app.services.governance_scorer import _mock_category_score

        result = _mock_category_score("security")
        assert result["name"] == "security"

    def test_score_in_range(self):
        from app.services.governance_scorer import _mock_category_score

        random.seed(42)
        for _ in range(20):
            result = _mock_category_score("test")
            assert 70 <= result["score"] <= 95

    def test_status_consistent_with_score(self):
        from app.services.governance_scorer import _mock_category_score

        random.seed(42)
        for _ in range(20):
            result = _mock_category_score("test")
            if result["score"] >= 80:
                assert result["status"] == "healthy"
            elif result["score"] >= 60:
                assert result["status"] == "warning"
            else:
                assert result["status"] == "critical"


# ── Service: calculate_overall_score ─────────────────────────────────────────


class TestCalculateOverallScore:
    """Test the overall score calculation with weighted components."""

    @pytest.mark.asyncio
    async def test_returns_expected_structure(self):
        from app.services.governance_scorer import governance_scorer

        result = await governance_scorer.calculate_overall_score(PROJECT_ID)
        assert "overall_score" in result
        assert "categories" in result
        assert "executive_summary" in result
        assert "last_updated" in result

    @pytest.mark.asyncio
    async def test_overall_score_in_valid_range(self):
        from app.services.governance_scorer import governance_scorer

        result = await governance_scorer.calculate_overall_score(PROJECT_ID)
        assert 0 <= result["overall_score"] <= 100

    @pytest.mark.asyncio
    async def test_returns_five_categories(self):
        from app.services.governance_scorer import governance_scorer

        result = await governance_scorer.calculate_overall_score(PROJECT_ID)
        assert len(result["categories"]) == 5

    @pytest.mark.asyncio
    async def test_category_names(self):
        from app.services.governance_scorer import governance_scorer

        result = await governance_scorer.calculate_overall_score(PROJECT_ID)
        names = {c["name"] for c in result["categories"]}
        assert names == {"compliance", "security", "cost", "drift", "tagging"}

    @pytest.mark.asyncio
    async def test_weighted_score_calculation(self):
        """Verify overall score equals weighted sum of category scores."""
        from app.services.governance_scorer import CATEGORY_WEIGHTS, governance_scorer

        mock_categories = [
            {"name": "compliance", "score": 90.0, "status": "healthy", "finding_count": 1},
            {"name": "security", "score": 80.0, "status": "healthy", "finding_count": 2},
            {"name": "cost", "score": 70.0, "status": "warning", "finding_count": 3},
            {"name": "drift", "score": 85.0, "status": "healthy", "finding_count": 0},
            {"name": "tagging", "score": 75.0, "status": "warning", "finding_count": 4},
        ]

        with patch.object(
            governance_scorer, "get_category_scores", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_categories
            result = await governance_scorer.calculate_overall_score(PROJECT_ID)

        expected = round(
            90.0 * 0.25 + 80.0 * 0.25 + 70.0 * 0.20 + 85.0 * 0.15 + 75.0 * 0.15,
            1,
        )
        assert result["overall_score"] == expected

    @pytest.mark.asyncio
    async def test_perfect_scores(self):
        """All categories at 100 should give overall 100."""
        from app.services.governance_scorer import governance_scorer

        mock_categories = [
            {"name": name, "score": 100.0, "status": "healthy", "finding_count": 0}
            for name in ["compliance", "security", "cost", "drift", "tagging"]
        ]

        with patch.object(
            governance_scorer, "get_category_scores", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_categories
            result = await governance_scorer.calculate_overall_score(PROJECT_ID)

        assert result["overall_score"] == 100.0

    @pytest.mark.asyncio
    async def test_zero_scores(self):
        """All categories at 0 should give overall 0."""
        from app.services.governance_scorer import governance_scorer

        mock_categories = [
            {"name": name, "score": 0.0, "status": "critical", "finding_count": 10}
            for name in ["compliance", "security", "cost", "drift", "tagging"]
        ]

        with patch.object(
            governance_scorer, "get_category_scores", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_categories
            result = await governance_scorer.calculate_overall_score(PROJECT_ID)

        assert result["overall_score"] == 0.0

    @pytest.mark.asyncio
    async def test_last_updated_is_recent(self):
        from app.services.governance_scorer import governance_scorer

        before = datetime.now(timezone.utc)
        result = await governance_scorer.calculate_overall_score(PROJECT_ID)
        after = datetime.now(timezone.utc)

        last_updated = datetime.fromisoformat(result["last_updated"])
        assert before <= last_updated <= after


# ── Service: get_category_scores ─────────────────────────────────────────────


class TestGetCategoryScores:
    """Test individual category score retrieval."""

    @pytest.mark.asyncio
    async def test_returns_list(self):
        from app.services.governance_scorer import governance_scorer

        result = await governance_scorer.get_category_scores(PROJECT_ID)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_each_category_has_required_keys(self):
        from app.services.governance_scorer import governance_scorer

        result = await governance_scorer.get_category_scores(PROJECT_ID)
        for cat in result:
            assert "name" in cat
            assert "score" in cat
            assert "status" in cat
            assert "finding_count" in cat

    @pytest.mark.asyncio
    async def test_scores_are_numeric(self):
        from app.services.governance_scorer import governance_scorer

        result = await governance_scorer.get_category_scores(PROJECT_ID)
        for cat in result:
            assert isinstance(cat["score"], float)
            assert 0 <= cat["score"] <= 100

    @pytest.mark.asyncio
    async def test_statuses_are_valid(self):
        from app.services.governance_scorer import governance_scorer

        result = await governance_scorer.get_category_scores(PROJECT_ID)
        valid_statuses = {"healthy", "warning", "critical"}
        for cat in result:
            assert cat["status"] in valid_statuses


# ── Service: get_score_trend ─────────────────────────────────────────────────


class TestGetScoreTrend:
    """Test score trend data generation."""

    @pytest.mark.asyncio
    async def test_returns_project_id(self):
        from app.services.governance_scorer import governance_scorer

        result = await governance_scorer.get_score_trend(PROJECT_ID, days=7)
        assert result["project_id"] == PROJECT_ID

    @pytest.mark.asyncio
    async def test_returns_correct_number_of_days(self):
        from app.services.governance_scorer import governance_scorer

        result = await governance_scorer.get_score_trend(PROJECT_ID, days=7)
        assert len(result["data_points"]) == 7

    @pytest.mark.asyncio
    async def test_default_30_days(self):
        from app.services.governance_scorer import governance_scorer

        result = await governance_scorer.get_score_trend(PROJECT_ID)
        assert len(result["data_points"]) == 30

    @pytest.mark.asyncio
    async def test_data_points_have_expected_structure(self):
        from app.services.governance_scorer import governance_scorer

        result = await governance_scorer.get_score_trend(PROJECT_ID, days=3)
        for point in result["data_points"]:
            assert "timestamp" in point
            assert "overall_score" in point
            assert "category_scores" in point
            assert isinstance(point["category_scores"], dict)

    @pytest.mark.asyncio
    async def test_trend_scores_in_valid_range(self):
        from app.services.governance_scorer import governance_scorer

        result = await governance_scorer.get_score_trend(PROJECT_ID, days=10)
        for point in result["data_points"]:
            assert 0 <= point["overall_score"] <= 100
            for score in point["category_scores"].values():
                assert 0 <= score <= 100

    @pytest.mark.asyncio
    async def test_trend_has_all_categories(self):
        from app.services.governance_scorer import CATEGORY_WEIGHTS, governance_scorer

        result = await governance_scorer.get_score_trend(PROJECT_ID, days=5)
        for point in result["data_points"]:
            for name in CATEGORY_WEIGHTS:
                assert name in point["category_scores"]

    @pytest.mark.asyncio
    async def test_single_day_trend(self):
        from app.services.governance_scorer import governance_scorer

        result = await governance_scorer.get_score_trend(PROJECT_ID, days=1)
        assert len(result["data_points"]) == 1

    @pytest.mark.asyncio
    async def test_timestamps_are_chronological(self):
        from app.services.governance_scorer import governance_scorer

        result = await governance_scorer.get_score_trend(PROJECT_ID, days=5)
        timestamps = [
            datetime.fromisoformat(p["timestamp"])
            for p in result["data_points"]
        ]
        for i in range(1, len(timestamps)):
            assert timestamps[i] > timestamps[i - 1]


# ── Service: generate_executive_summary ──────────────────────────────────────


class TestGenerateExecutiveSummary:
    """Test executive summary text generation."""

    def test_empty_categories(self):
        from app.services.governance_scorer import governance_scorer

        summary = governance_scorer.generate_executive_summary([])
        assert "No governance data available" in summary

    def test_all_healthy(self):
        from app.services.governance_scorer import governance_scorer

        categories = [
            {"name": name, "score": 90.0, "status": "healthy", "finding_count": 0}
            for name in ["compliance", "security", "cost", "drift", "tagging"]
        ]
        summary = governance_scorer.generate_executive_summary(categories)
        assert "compliant" in summary
        assert "No issues require attention" in summary
        assert "All governance areas are healthy" in summary

    def test_with_findings(self):
        from app.services.governance_scorer import governance_scorer

        categories = [
            {"name": "compliance", "score": 85.0, "status": "healthy", "finding_count": 3},
            {"name": "security", "score": 80.0, "status": "healthy", "finding_count": 2},
            {"name": "cost", "score": 90.0, "status": "healthy", "finding_count": 0},
            {"name": "drift", "score": 88.0, "status": "healthy", "finding_count": 1},
            {"name": "tagging", "score": 82.0, "status": "healthy", "finding_count": 0},
        ]
        summary = governance_scorer.generate_executive_summary(categories)
        assert "6 issues require attention" in summary

    def test_with_critical_areas(self):
        from app.services.governance_scorer import governance_scorer

        categories = [
            {"name": "compliance", "score": 40.0, "status": "critical", "finding_count": 10},
            {"name": "security", "score": 50.0, "status": "critical", "finding_count": 8},
            {"name": "cost", "score": 80.0, "status": "healthy", "finding_count": 0},
            {"name": "drift", "score": 90.0, "status": "healthy", "finding_count": 0},
            {"name": "tagging", "score": 85.0, "status": "healthy", "finding_count": 0},
        ]
        summary = governance_scorer.generate_executive_summary(categories)
        assert "Critical areas:" in summary
        assert "compliance" in summary
        assert "security" in summary

    def test_with_warning_areas(self):
        from app.services.governance_scorer import governance_scorer

        categories = [
            {"name": "compliance", "score": 85.0, "status": "healthy", "finding_count": 0},
            {"name": "security", "score": 85.0, "status": "healthy", "finding_count": 0},
            {"name": "cost", "score": 65.0, "status": "warning", "finding_count": 2},
            {"name": "drift", "score": 85.0, "status": "healthy", "finding_count": 0},
            {"name": "tagging", "score": 70.0, "status": "warning", "finding_count": 1},
        ]
        summary = governance_scorer.generate_executive_summary(categories)
        assert "Areas needing improvement:" in summary
        assert "cost" in summary
        assert "tagging" in summary

    def test_summary_contains_compliance_percentage(self):
        from app.services.governance_scorer import governance_scorer

        categories = [
            {"name": "compliance", "score": 80.0, "status": "healthy", "finding_count": 0},
            {"name": "security", "score": 80.0, "status": "healthy", "finding_count": 0},
            {"name": "cost", "score": 80.0, "status": "healthy", "finding_count": 0},
            {"name": "drift", "score": 80.0, "status": "healthy", "finding_count": 0},
            {"name": "tagging", "score": 80.0, "status": "healthy", "finding_count": 0},
        ]
        summary = governance_scorer.generate_executive_summary(categories)
        assert "80.0% compliant" in summary


# ── Service: SSE event publishing ────────────────────────────────────────────


class TestSSEEventPublishing:
    """Test that score recalculation publishes SSE events."""

    @pytest.mark.asyncio
    async def test_publishes_event_on_calculation(self):
        from app.services.governance_scorer import governance_scorer

        with patch("app.services.governance_scorer.event_stream") as mock_stream:
            mock_stream.publish = AsyncMock(return_value=0)
            await governance_scorer.calculate_overall_score(PROJECT_ID)

            mock_stream.publish.assert_called_once()
            call_kwargs = mock_stream.publish.call_args
            assert call_kwargs.kwargs.get("project_id") == PROJECT_ID
            assert call_kwargs[1].get("project_id") == PROJECT_ID

    @pytest.mark.asyncio
    async def test_event_type_is_governance_score_updated(self):
        from app.services.governance_scorer import governance_scorer

        with patch("app.services.governance_scorer.event_stream") as mock_stream:
            mock_stream.publish = AsyncMock(return_value=0)
            await governance_scorer.calculate_overall_score(PROJECT_ID)

            call_args = mock_stream.publish.call_args
            assert call_args[1]["event_type"] == "governance_score_updated"

    @pytest.mark.asyncio
    async def test_event_data_contains_score(self):
        from app.services.governance_scorer import governance_scorer

        with patch("app.services.governance_scorer.event_stream") as mock_stream:
            mock_stream.publish = AsyncMock(return_value=0)
            await governance_scorer.calculate_overall_score(PROJECT_ID)

            call_args = mock_stream.publish.call_args
            event_data = call_args[1]["data"]
            assert "overall_score" in event_data
            assert "categories" in event_data
            assert "executive_summary" in event_data

    @pytest.mark.asyncio
    async def test_sse_failure_does_not_break_calculation(self):
        from app.services.governance_scorer import governance_scorer

        with patch("app.services.governance_scorer.event_stream") as mock_stream:
            mock_stream.publish = AsyncMock(side_effect=Exception("SSE error"))
            # Should not raise even when SSE fails
            result = await governance_scorer.calculate_overall_score(PROJECT_ID)
            assert "overall_score" in result


# ── Service: category weight validation ──────────────────────────────────────


class TestCategoryWeights:
    """Validate category weight configuration."""

    def test_weights_sum_to_one(self):
        from app.services.governance_scorer import CATEGORY_WEIGHTS

        assert abs(sum(CATEGORY_WEIGHTS.values()) - 1.0) < 0.001

    def test_all_expected_categories(self):
        from app.services.governance_scorer import CATEGORY_WEIGHTS

        expected = {"compliance", "security", "cost", "drift", "tagging"}
        assert set(CATEGORY_WEIGHTS.keys()) == expected

    def test_compliance_weight(self):
        from app.services.governance_scorer import CATEGORY_WEIGHTS

        assert CATEGORY_WEIGHTS["compliance"] == 0.25

    def test_security_weight(self):
        from app.services.governance_scorer import CATEGORY_WEIGHTS

        assert CATEGORY_WEIGHTS["security"] == 0.25

    def test_cost_weight(self):
        from app.services.governance_scorer import CATEGORY_WEIGHTS

        assert CATEGORY_WEIGHTS["cost"] == 0.20

    def test_drift_weight(self):
        from app.services.governance_scorer import CATEGORY_WEIGHTS

        assert CATEGORY_WEIGHTS["drift"] == 0.15

    def test_tagging_weight(self):
        from app.services.governance_scorer import CATEGORY_WEIGHTS

        assert CATEGORY_WEIGHTS["tagging"] == 0.15


# ── Route tests ──────────────────────────────────────────────────────────────


class TestGovernanceScorecardRoutes:
    """Test governance scorecard HTTP endpoints."""

    def test_get_scorecard(self):
        response = client.get(f"/api/governance/scorecard/{PROJECT_ID}")
        assert response.status_code == 200
        data = response.json()
        assert "overall_score" in data
        assert "categories" in data
        assert "executive_summary" in data
        assert "last_updated" in data
        assert len(data["categories"]) == 5

    def test_get_scorecard_score_range(self):
        response = client.get(f"/api/governance/scorecard/{PROJECT_ID}")
        data = response.json()
        assert 0 <= data["overall_score"] <= 100
        for cat in data["categories"]:
            assert 0 <= cat["score"] <= 100

    def test_get_scorecard_category_structure(self):
        response = client.get(f"/api/governance/scorecard/{PROJECT_ID}")
        data = response.json()
        for cat in data["categories"]:
            assert "name" in cat
            assert "score" in cat
            assert "status" in cat
            assert "finding_count" in cat
            assert cat["status"] in {"healthy", "warning", "critical"}

    def test_get_score_trend(self):
        response = client.get(f"/api/governance/scorecard/{PROJECT_ID}/trend")
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == PROJECT_ID
        assert len(data["data_points"]) == 30

    def test_get_score_trend_custom_days(self):
        response = client.get(
            f"/api/governance/scorecard/{PROJECT_ID}/trend?days=7"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data_points"]) == 7

    def test_get_score_trend_data_point_structure(self):
        response = client.get(
            f"/api/governance/scorecard/{PROJECT_ID}/trend?days=3"
        )
        data = response.json()
        for point in data["data_points"]:
            assert "timestamp" in point
            assert "overall_score" in point
            assert "category_scores" in point
            assert 0 <= point["overall_score"] <= 100

    def test_refresh_scorecard(self):
        response = client.post(
            f"/api/governance/scorecard/{PROJECT_ID}/refresh"
        )
        assert response.status_code == 200
        data = response.json()
        assert "overall_score" in data
        assert "categories" in data
        assert len(data["categories"]) == 5

    def test_refresh_scorecard_returns_fresh_data(self):
        response = client.post(
            f"/api/governance/scorecard/{PROJECT_ID}/refresh"
        )
        data = response.json()
        assert data["last_updated"] is not None

    def test_get_executive_summary(self):
        response = client.get(
            f"/api/governance/scorecard/{PROJECT_ID}/summary"
        )
        assert response.status_code == 200
        data = response.json()
        assert "executive_summary" in data
        assert isinstance(data["executive_summary"], str)
        assert len(data["executive_summary"]) > 0

    def test_get_executive_summary_contains_compliance(self):
        response = client.get(
            f"/api/governance/scorecard/{PROJECT_ID}/summary"
        )
        data = response.json()
        assert "compliant" in data["executive_summary"]

    def test_different_project_ids(self):
        """Verify different project IDs are accepted."""
        for pid in ["proj-1", "proj-2", "abc-xyz"]:
            response = client.get(f"/api/governance/scorecard/{pid}")
            assert response.status_code == 200

    def test_trend_min_days(self):
        response = client.get(
            f"/api/governance/scorecard/{PROJECT_ID}/trend?days=1"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data_points"]) == 1

    def test_trend_invalid_days_zero(self):
        response = client.get(
            f"/api/governance/scorecard/{PROJECT_ID}/trend?days=0"
        )
        assert response.status_code == 422

    def test_trend_invalid_days_negative(self):
        response = client.get(
            f"/api/governance/scorecard/{PROJECT_ID}/trend?days=-1"
        )
        assert response.status_code == 422


# ── Singleton test ───────────────────────────────────────────────────────────


class TestGovernanceScorerSingleton:
    """Test that the module-level singleton works correctly."""

    def test_singleton_exists(self):
        from app.services.governance_scorer import governance_scorer

        assert governance_scorer is not None

    def test_singleton_is_governance_scorer(self):
        from app.services.governance_scorer import GovernanceScorer, governance_scorer

        assert isinstance(governance_scorer, GovernanceScorer)

    def test_singleton_same_instance(self):
        from app.services.governance_scorer import governance_scorer as gs1
        from app.services.governance_scorer import governance_scorer as gs2

        assert gs1 is gs2

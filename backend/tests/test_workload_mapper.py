"""Tests for WorkloadMapper service and mapping API routes."""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.workload_mapping import WorkloadMapping
from app.services.workload_mapper import (
    generate_mapping,
    validate_mappings,
    _rule_based_mapping,
)

client = TestClient(app)

PROJECT_ID = "proj-mapper-test"

# ---------------------------------------------------------------------------
# Helper data
# ---------------------------------------------------------------------------

SAMPLE_SUBSCRIPTIONS = [
    {"id": "sub-prod", "name": "sub-workload-prod", "purpose": "Production workloads"},
    {"id": "sub-dev", "name": "sub-workload-dev", "purpose": "Development and testing"},
    {"id": "sub-platform", "name": "sub-platform", "purpose": "Shared platform services"},
]

SAMPLE_ARCHITECTURE = {"subscriptions": SAMPLE_SUBSCRIPTIONS}

SAMPLE_WORKLOADS = [
    {
        "id": "wl-1",
        "name": "ProdWebApp",
        "type": "web-app",
        "criticality": "mission-critical",
        "compliance_requirements": [],
        "dependencies": [],
    },
    {
        "id": "wl-2",
        "name": "DevDB",
        "type": "database",
        "criticality": "dev-test",
        "compliance_requirements": [],
        "dependencies": [],
    },
    {
        "id": "wl-3",
        "name": "ComplianceApp",
        "type": "vm",
        "criticality": "business-critical",
        "compliance_requirements": ["HIPAA", "SOC2"],
        "dependencies": ["wl-1"],
    },
]


# ---------------------------------------------------------------------------
# WorkloadMapper service — rule-based mapping
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_mapping_empty_architecture():
    """Empty subscriptions list returns no mappings."""
    result = await generate_mapping(SAMPLE_WORKLOADS, {}, ai_client=None)
    assert result == []


@pytest.mark.asyncio
async def test_generate_mapping_returns_one_per_workload():
    result = await generate_mapping(SAMPLE_WORKLOADS, SAMPLE_ARCHITECTURE, ai_client=None)
    assert len(result) == len(SAMPLE_WORKLOADS)


@pytest.mark.asyncio
async def test_generate_mapping_workload_ids_preserved():
    result = await generate_mapping(SAMPLE_WORKLOADS, SAMPLE_ARCHITECTURE, ai_client=None)
    ids = {m.workload_id for m in result}
    assert ids == {"wl-1", "wl-2", "wl-3"}


@pytest.mark.asyncio
async def test_generate_mapping_mission_critical_goes_to_prod():
    result = await generate_mapping(SAMPLE_WORKLOADS, SAMPLE_ARCHITECTURE, ai_client=None)
    prod_mapping = next(m for m in result if m.workload_id == "wl-1")
    # Mission-critical workload should land in a production-like subscription
    assert "prod" in prod_mapping.recommended_subscription_name.lower()


@pytest.mark.asyncio
async def test_generate_mapping_dev_test_goes_to_dev():
    result = await generate_mapping(SAMPLE_WORKLOADS, SAMPLE_ARCHITECTURE, ai_client=None)
    dev_mapping = next(m for m in result if m.workload_id == "wl-2")
    assert "dev" in dev_mapping.recommended_subscription_name.lower()


@pytest.mark.asyncio
async def test_generate_mapping_confidence_in_range():
    result = await generate_mapping(SAMPLE_WORKLOADS, SAMPLE_ARCHITECTURE, ai_client=None)
    for m in result:
        assert 0.0 <= m.confidence_score <= 1.0


@pytest.mark.asyncio
async def test_generate_mapping_has_reasoning():
    result = await generate_mapping(SAMPLE_WORKLOADS, SAMPLE_ARCHITECTURE, ai_client=None)
    for m in result:
        assert len(m.reasoning) > 0


@pytest.mark.asyncio
async def test_generate_mapping_no_subscriptions():
    arch = {"subscriptions": []}
    result = await generate_mapping(SAMPLE_WORKLOADS, arch, ai_client=None)
    assert result == []


@pytest.mark.asyncio
async def test_generate_mapping_assigns_subscription_name():
    result = await generate_mapping(SAMPLE_WORKLOADS, SAMPLE_ARCHITECTURE, ai_client=None)
    for m in result:
        assert m.recommended_subscription_name != ""


# ---------------------------------------------------------------------------
# Rule-based mapping helper
# ---------------------------------------------------------------------------

def test_rule_based_mapping_mission_critical():
    wl = {"name": "ProdVM", "type": "vm", "criticality": "mission-critical", "compliance_requirements": []}
    sub, confidence, warnings = _rule_based_mapping(wl, SAMPLE_SUBSCRIPTIONS)
    assert "prod" in sub["name"].lower()
    assert confidence > 0


def test_rule_based_mapping_dev_test():
    wl = {"name": "TestVM", "type": "vm", "criticality": "dev-test", "compliance_requirements": []}
    sub, confidence, warnings = _rule_based_mapping(wl, SAMPLE_SUBSCRIPTIONS)
    assert "dev" in sub["name"].lower()


def test_rule_based_mapping_compliance_warning():
    wl = {
        "name": "HIPAAApp",
        "type": "vm",
        "criticality": "dev-test",
        "compliance_requirements": ["HIPAA"],
    }
    # Dev workload with compliance — warning expected
    _, _, warnings = _rule_based_mapping(wl, SAMPLE_SUBSCRIPTIONS)
    assert any("compliance" in w.lower() or "HIPAA" in w for w in warnings)


def test_rule_based_mapping_empty_subscriptions():
    wl = {"name": "NoSub", "type": "vm", "criticality": "standard", "compliance_requirements": []}
    sub, confidence, warnings = _rule_based_mapping(wl, [])
    assert confidence == 0.0
    assert len(warnings) > 0


# ---------------------------------------------------------------------------
# validate_mappings
# ---------------------------------------------------------------------------

def test_validate_mappings_no_warnings_clean():
    """Clean mappings with no issues should produce no warnings."""
    workloads = [
        {"id": "w1", "name": "VM1", "compliance_requirements": [], "dependencies": []},
    ]
    mappings = [
        WorkloadMapping(
            workload_id="w1",
            workload_name="VM1",
            recommended_subscription_id="sub-prod",
            recommended_subscription_name="sub-workload-prod",
            reasoning="test",
            confidence_score=0.9,
            warnings=[],
        )
    ]
    result = validate_mappings(mappings, workloads)
    assert result == []


def test_validate_mappings_subscription_overload():
    """More than 50 workloads in one subscription should produce a warning."""
    workloads = [{"id": f"w{i}", "name": f"VM{i}", "compliance_requirements": [], "dependencies": []} for i in range(55)]
    mappings = [
        WorkloadMapping(
            workload_id=f"w{i}",
            workload_name=f"VM{i}",
            recommended_subscription_id="sub-prod",
            recommended_subscription_name="sub-workload-prod",
            reasoning="test",
            confidence_score=0.9,
            warnings=[],
        )
        for i in range(55)
    ]
    result = validate_mappings(mappings, workloads)
    assert any("55" in w or "exceed" in w.lower() for w in result)


def test_validate_mappings_compliance_mismatch():
    """HIPAA workload in dev subscription should produce a warning."""
    workloads = [
        {"id": "w1", "name": "HIPAAApp", "compliance_requirements": ["HIPAA"], "dependencies": []},
    ]
    mappings = [
        WorkloadMapping(
            workload_id="w1",
            workload_name="HIPAAApp",
            recommended_subscription_id="sub-dev",
            recommended_subscription_name="sub-workload-dev",
            reasoning="test",
            confidence_score=0.5,
            warnings=[],
        )
    ]
    result = validate_mappings(mappings, workloads)
    assert any("HIPAA" in w or "compliance" in w.lower() for w in result)


def test_validate_mappings_split_dependencies():
    """Dependent workloads in different subscriptions should produce a warning."""
    workloads = [
        {"id": "w1", "name": "Frontend", "compliance_requirements": [], "dependencies": ["w2"]},
        {"id": "w2", "name": "Backend", "compliance_requirements": [], "dependencies": []},
    ]
    mappings = [
        WorkloadMapping(
            workload_id="w1",
            workload_name="Frontend",
            recommended_subscription_id="sub-prod",
            recommended_subscription_name="sub-workload-prod",
            reasoning="test",
            confidence_score=0.9,
            warnings=[],
        ),
        WorkloadMapping(
            workload_id="w2",
            workload_name="Backend",
            recommended_subscription_id="sub-dev",
            recommended_subscription_name="sub-workload-dev",
            reasoning="test",
            confidence_score=0.7,
            warnings=[],
        ),
    ]
    result = validate_mappings(mappings, workloads)
    assert any("depend" in w.lower() or "split" in w.lower() or "Frontend" in w for w in result)


def test_validate_mappings_hub_spoke_no_warning():
    """Dependencies across hub/platform subs should NOT produce network warning."""
    workloads = [
        {"id": "w1", "name": "App", "compliance_requirements": [], "dependencies": ["w2"]},
        {"id": "w2", "name": "SharedSvc", "compliance_requirements": [], "dependencies": []},
    ]
    mappings = [
        WorkloadMapping(
            workload_id="w1",
            workload_name="App",
            recommended_subscription_id="sub-workload",
            recommended_subscription_name="sub-workload-prod",
            reasoning="test",
            confidence_score=0.9,
            warnings=[],
        ),
        WorkloadMapping(
            workload_id="w2",
            workload_name="SharedSvc",
            recommended_subscription_id="sub-hub",
            recommended_subscription_name="sub-hub-platform",
            reasoning="test",
            confidence_score=0.8,
            warnings=[],
        ),
    ]
    result = validate_mappings(mappings, workloads)
    # hub/platform subscriptions are assumed peered — no network warning
    assert not any("network" in w.lower() or "peering" in w.lower() for w in result)


# ---------------------------------------------------------------------------
# AI fallback — mock AI client
# ---------------------------------------------------------------------------

class _MockAIClient:
    is_configured = True

    async def generate_completion_async(self, system_prompt: str, user_prompt: str) -> str:
        # Return valid JSON matching the expected schema
        return json.dumps(
            [
                {
                    "workload_id": "wl-1",
                    "workload_name": "ProdWebApp",
                    "recommended_subscription_id": "sub-prod",
                    "recommended_subscription_name": "sub-workload-prod",
                    "reasoning": "AI selected prod",
                    "confidence_score": 0.92,
                    "warnings": [],
                }
            ]
        )


class _BrokenAIClient:
    is_configured = True

    async def generate_completion_async(self, system_prompt: str, user_prompt: str) -> str:
        return "NOT_JSON_AT_ALL"


@pytest.mark.asyncio
async def test_generate_mapping_ai_mode():
    workloads = [SAMPLE_WORKLOADS[0]]
    result = await generate_mapping(workloads, SAMPLE_ARCHITECTURE, ai_client=_MockAIClient())  # type: ignore[arg-type]
    assert len(result) == 1
    assert result[0].recommended_subscription_id == "sub-prod"
    assert result[0].confidence_score == 0.92


@pytest.mark.asyncio
async def test_generate_mapping_ai_fallback_on_bad_json():
    """When AI returns bad JSON, falls back to rule-based."""
    result = await generate_mapping(SAMPLE_WORKLOADS, SAMPLE_ARCHITECTURE, ai_client=_BrokenAIClient())  # type: ignore[arg-type]
    assert len(result) == len(SAMPLE_WORKLOADS)


@pytest.mark.asyncio
async def test_generate_mapping_ai_fills_missing_workloads():
    """When AI omits workloads, rule-based mappings fill the gaps."""
    # AI only maps wl-1; wl-2 and wl-3 are omitted
    result = await generate_mapping(SAMPLE_WORKLOADS, SAMPLE_ARCHITECTURE, ai_client=_MockAIClient())  # type: ignore[arg-type]
    # Should have all 3 workloads mapped (1 from AI + 2 from rule-based fill)
    assert len(result) == len(SAMPLE_WORKLOADS)
    ids = {m.workload_id for m in result}
    assert ids == {"wl-1", "wl-2", "wl-3"}


# ---------------------------------------------------------------------------
# API routes — POST /api/workloads/map
# ---------------------------------------------------------------------------

def test_map_workloads_no_db():
    """Without DB, returns 200 with empty mappings and a warning."""
    payload = {"project_id": PROJECT_ID, "architecture_id": "", "use_ai": False}
    r = client.post("/api/workloads/map", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "mappings" in data
    assert "warnings" in data
    assert isinstance(data["mappings"], list)
    # No workloads in DB → warning expected
    assert len(data["warnings"]) > 0


def test_map_workloads_missing_project_id():
    r = client.post("/api/workloads/map", json={"architecture_id": ""})
    assert r.status_code == 422


def test_map_workloads_returns_mapping_response_shape():
    payload = {"project_id": PROJECT_ID, "use_ai": False}
    r = client.post("/api/workloads/map", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert set(data.keys()) >= {"mappings", "warnings"}


# ---------------------------------------------------------------------------
# API routes — PATCH /api/workloads/{id}/mapping
# ---------------------------------------------------------------------------

def test_override_mapping_no_db():
    """Without DB, returns 404."""
    payload = {"target_subscription_id": "sub-prod", "reasoning": "Manual override"}
    r = client.patch("/api/workloads/nonexistent-id/mapping", json=payload)
    assert r.status_code == 404


def test_override_mapping_missing_subscription_id():
    r = client.patch("/api/workloads/some-id/mapping", json={"reasoning": "test"})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# WorkloadMapping schema validation
# ---------------------------------------------------------------------------

def test_workload_mapping_schema_confidence_bounds():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        WorkloadMapping(
            workload_id="w1",
            workload_name="VM",
            recommended_subscription_id="sub",
            recommended_subscription_name="sub",
            reasoning="x",
            confidence_score=1.5,  # invalid
            warnings=[],
        )


def test_workload_mapping_schema_valid():
    m = WorkloadMapping(
        workload_id="w1",
        workload_name="VM",
        recommended_subscription_id="sub-prod",
        recommended_subscription_name="sub-workload-prod",
        reasoning="Matched production",
        confidence_score=0.85,
        warnings=["Check firewall"],
    )
    assert m.confidence_score == 0.85
    assert m.warnings == ["Check firewall"]

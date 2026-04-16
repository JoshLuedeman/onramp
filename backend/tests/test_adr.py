"""Tests for ADR generation service and API routes."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.adr import ADRRecord
from app.services.adr_generator import export_adrs, generate_adrs

client = TestClient(app)

# --- Sample architecture data for tests ---

SAMPLE_ARCHITECTURE = {
    "management_groups": {
        "root": {"children": ["platform", "workloads"]},
        "platform": {"children": ["connectivity", "identity"]},
        "workloads": {"children": ["prod", "dev"]},
    },
    "subscriptions": [
        {"name": "connectivity", "purpose": "Hub networking", "management_group": "platform"},
        {"name": "identity", "purpose": "Identity services", "management_group": "platform"},
        {"name": "production", "purpose": "Production workloads", "management_group": "workloads"},
        {"name": "development", "purpose": "Dev/test", "management_group": "workloads"},
    ],
    "network_topology": {
        "type": "hub-spoke",
        "primary_region": "eastus2",
        "secondary_region": "westus2",
    },
    "identity": {
        "provider": "Entra ID",
        "pim_enabled": True,
        "mfa_policy": "all_users",
    },
    "policies": {
        "CIS": {"version": "1.4"},
        "NIST_800_53": {"version": "5"},
    },
}

SAMPLE_ANSWERS = {
    "org_size": "enterprise",
    "identity_model": "centralized",
    "compliance_frameworks": ["CIS", "NIST 800-53", "SOC 2"],
    "network_topology": "hub_spoke",
}


# --- Service-level tests ---


class TestGenerateAdrs:
    """Tests for the generate_adrs service function."""

    def test_generates_six_adrs(self):
        """Should produce one ADR per major decision area."""
        adrs = generate_adrs(SAMPLE_ARCHITECTURE, SAMPLE_ANSWERS)
        assert len(adrs) == 6

    def test_adr_ids_are_sequential(self):
        """Each ADR should have a sequential ID like ADR-001."""
        adrs = generate_adrs(SAMPLE_ARCHITECTURE, SAMPLE_ANSWERS)
        for i, adr in enumerate(adrs, 1):
            assert adr.id == f"ADR-{i:03d}"

    def test_all_categories_present(self):
        """ADRs should cover governance, networking, identity, and compliance."""
        adrs = generate_adrs(SAMPLE_ARCHITECTURE, SAMPLE_ANSWERS)
        categories = {adr.category for adr in adrs}
        assert "governance" in categories
        assert "networking" in categories
        assert "identity" in categories
        assert "compliance" in categories

    def test_adr_titles_match_decision_areas(self):
        """Each ADR should have a descriptive title for its decision area."""
        adrs = generate_adrs(SAMPLE_ARCHITECTURE, SAMPLE_ANSWERS)
        titles = [adr.title for adr in adrs]
        assert "Management Group Hierarchy" in titles
        assert "Network Topology" in titles
        assert "Identity Model" in titles
        assert "Compliance Frameworks" in titles
        assert "Region Selection" in titles
        assert "Subscription Topology" in titles

    def test_adr_fields_are_populated(self):
        """Every ADR field should be non-empty."""
        adrs = generate_adrs(SAMPLE_ARCHITECTURE, SAMPLE_ANSWERS)
        for adr in adrs:
            assert adr.id
            assert adr.title
            assert adr.status == "Accepted"
            assert adr.context
            assert adr.decision
            assert adr.consequences
            assert adr.category
            assert adr.created_at

    def test_network_adr_uses_architecture_topology(self):
        """Network ADR should reference the topology type from architecture."""
        adrs = generate_adrs(SAMPLE_ARCHITECTURE, SAMPLE_ANSWERS)
        net_adr = next(a for a in adrs if a.title == "Network Topology")
        assert "hub-spoke" in net_adr.decision

    def test_region_adr_uses_architecture_regions(self):
        """Region ADR should reference primary and secondary regions."""
        adrs = generate_adrs(SAMPLE_ARCHITECTURE, SAMPLE_ANSWERS)
        region_adr = next(a for a in adrs if a.title == "Region Selection")
        assert "eastus2" in region_adr.decision
        assert "westus2" in region_adr.decision

    def test_compliance_adr_uses_answers(self):
        """Compliance ADR should reference selected frameworks from answers."""
        adrs = generate_adrs(SAMPLE_ARCHITECTURE, SAMPLE_ANSWERS)
        comp_adr = next(a for a in adrs if a.title == "Compliance Frameworks")
        assert "CIS" in comp_adr.decision
        assert "NIST 800-53" in comp_adr.decision

    def test_ai_mode_falls_back_to_templates(self):
        """use_ai=True should fall back to template mode when AI is not configured."""
        adrs = generate_adrs(SAMPLE_ARCHITECTURE, SAMPLE_ANSWERS, use_ai=True)
        assert len(adrs) == 6
        # Should still produce valid ADRs
        assert all(isinstance(a, ADRRecord) for a in adrs)

    def test_empty_architecture(self):
        """Should handle empty architecture gracefully."""
        adrs = generate_adrs({}, {})
        assert len(adrs) == 6
        # Should still produce ADRs with fallback values
        for adr in adrs:
            assert adr.context
            assert adr.decision

    def test_list_management_groups(self):
        """Should handle management groups provided as a list."""
        arch = {
            "management_groups": [
                {"name": "root"},
                {"name": "platform"},
            ],
        }
        adrs = generate_adrs(arch, {})
        mg_adr = next(a for a in adrs if a.title == "Management Group Hierarchy")
        assert "2" in mg_adr.decision
        assert "root" in mg_adr.decision


# --- Export tests ---


class TestExportAdrs:
    """Tests for the export_adrs function."""

    def test_combined_export_format(self):
        """Combined export should contain all ADRs separated by ---."""
        adrs = generate_adrs(SAMPLE_ARCHITECTURE, SAMPLE_ANSWERS)
        md = export_adrs(adrs, format="combined")
        assert "# Architecture Decision Records" in md
        assert "---" in md
        for adr in adrs:
            assert adr.title in md

    def test_individual_export_format(self):
        """Individual export should contain all ADRs as separate markdown sections."""
        adrs = generate_adrs(SAMPLE_ARCHITECTURE, SAMPLE_ANSWERS)
        md = export_adrs(adrs, format="individual")
        # Every ADR should be present in the output
        for adr in adrs:
            assert adr.title in md
        # Should not contain the combined header
        assert "# Architecture Decision Records" not in md
        # ADRs should be separated by ---
        assert "---" in md

    def test_export_empty_list(self):
        """Exporting with no ADRs should return a placeholder message."""
        md = export_adrs([], format="combined")
        assert "No ADRs generated yet" in md

    def test_export_markdown_structure(self):
        """Each ADR should include Status, Date, Category, Context, Decision, Consequences."""
        adrs = generate_adrs(SAMPLE_ARCHITECTURE, SAMPLE_ANSWERS)
        md = export_adrs(adrs, format="combined")
        assert "**Status:**" in md
        assert "**Date:**" in md
        assert "**Category:**" in md
        assert "## Context" in md
        assert "## Decision" in md
        assert "## Consequences" in md


# --- API route tests ---


class TestADRRoutes:
    """Tests for the ADR API endpoints."""

    def test_generate_endpoint_returns_adrs(self):
        """POST /api/architecture/adrs/generate should return ADR list."""
        response = client.post(
            "/api/architecture/adrs/generate",
            json={
                "architecture": SAMPLE_ARCHITECTURE,
                "answers": SAMPLE_ANSWERS,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "adrs" in data
        assert len(data["adrs"]) == 6

    def test_generate_endpoint_with_project_id(self):
        """Generate endpoint should echo back the project_id."""
        response = client.post(
            "/api/architecture/adrs/generate",
            json={
                "architecture": SAMPLE_ARCHITECTURE,
                "answers": {},
                "project_id": "proj-123",
            },
        )
        assert response.status_code == 200
        assert response.json()["project_id"] == "proj-123"

    def test_generate_endpoint_with_ai_flag(self):
        """Generate endpoint should accept use_ai flag without error."""
        response = client.post(
            "/api/architecture/adrs/generate",
            json={
                "architecture": SAMPLE_ARCHITECTURE,
                "answers": SAMPLE_ANSWERS,
                "use_ai": True,
            },
        )
        assert response.status_code == 200
        assert len(response.json()["adrs"]) == 6

    def test_export_endpoint_combined(self):
        """POST /api/architecture/adrs/export should return markdown content."""
        adrs = generate_adrs(SAMPLE_ARCHITECTURE, SAMPLE_ANSWERS)
        adr_dicts = [adr.model_dump() for adr in adrs]
        response = client.post(
            "/api/architecture/adrs/export",
            json={"adrs": adr_dicts, "format": "combined"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "Architecture Decision Records" in data["content"]

    def test_export_endpoint_individual(self):
        """Export with individual format returns all ADRs."""
        adrs = generate_adrs(SAMPLE_ARCHITECTURE, SAMPLE_ANSWERS)
        adr_dicts = [adr.model_dump() for adr in adrs]
        response = client.post(
            "/api/architecture/adrs/export",
            json={"adrs": adr_dicts, "format": "individual"},
        )
        assert response.status_code == 200
        content = response.json()["content"]
        for adr in adrs:
            assert adr.title in content

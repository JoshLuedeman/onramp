"""Shared constants and fixtures for backend tests."""

import os
import uuid

import pytest

# Enable debug mode for all tests so mock auth is active
# (matches pre-existing behavior where tests ran with mock auth).
os.environ.setdefault("ONRAMP_DEBUG", "true")

SQLITE_TEST_URL = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"

# ---------------------------------------------------------------------------
# Reusable auth headers (dev mode mock auth accepts any bearer token)
# ---------------------------------------------------------------------------
AUTH_HEADERS = {"Authorization": "Bearer test"}


# ---------------------------------------------------------------------------
# Factory helpers — return dicts suitable for ORM model constructors
# ---------------------------------------------------------------------------


def make_tenant(**overrides) -> dict:
    """Return a dict of Tenant fields with sensible defaults."""
    defaults = {
        "id": str(uuid.uuid4()),
        "name": "Test Tenant",
        "azure_tenant_id": str(uuid.uuid4()),
        "is_active": True,
    }
    defaults.update(overrides)
    return defaults


def make_user(tenant_id: str, **overrides) -> dict:
    """Return a dict of User fields with sensible defaults."""
    defaults = {
        "id": str(uuid.uuid4()),
        "entra_object_id": str(uuid.uuid4()),
        "email": f"test-{uuid.uuid4().hex[:6]}@onramp.local",
        "display_name": "Test User",
        "role": "viewer",
        "is_active": True,
        "tenant_id": tenant_id,
    }
    defaults.update(overrides)
    return defaults


def make_project(tenant_id: str, created_by: str, **overrides) -> dict:
    """Return a dict of Project fields with sensible defaults."""
    defaults = {
        "id": str(uuid.uuid4()),
        "name": "Test Project",
        "description": "A test project",
        "status": "draft",
        "tenant_id": tenant_id,
        "created_by": created_by,
    }
    defaults.update(overrides)
    return defaults


def make_architecture(**overrides) -> dict:
    """Return a minimal architecture dict for API payloads."""
    defaults = {
        "management_groups": {"platform": {}, "landing_zones": {}},
        "networking": {"hub_spoke": True, "regions": ["eastus2"]},
        "identity": {"provider": "entra_id"},
        "governance": {"policies": [], "blueprints": []},
    }
    defaults.update(overrides)
    return defaults


@pytest.fixture
def sample_answers() -> dict[str, str]:
    """Minimal set of questionnaire answers for architecture generation."""
    return {
        "org_size": "medium",
        "primary_region": "eastus2",
        "compliance_frameworks": "none",
        "workload_types": "web_apps",
        "networking_model": "hub_spoke",
    }

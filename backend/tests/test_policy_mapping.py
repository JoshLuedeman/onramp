"""Tests for Azure Policy mappings."""

from app.services.policy_mapping import (
    get_policy_definition,
    get_policies_for_controls,
    get_all_policy_keys,
)


def test_get_policy_definition():
    policy = get_policy_definition("require-mfa")
    assert policy is not None
    assert "MFA" in policy["display_name"]
    assert policy["effect"] in ["Audit", "AuditIfNotExists", "Deny", "DeployIfNotExists"]


def test_get_policy_not_found():
    policy = get_policy_definition("nonexistent-policy")
    assert policy is None


def test_get_policies_for_controls():
    policies = get_policies_for_controls(["require-mfa", "require-nsg", "nonexistent"])
    assert len(policies) == 2
    keys = [p["key"] for p in policies]
    assert "require-mfa" in keys
    assert "require-nsg" in keys


def test_all_policy_keys():
    keys = get_all_policy_keys()
    assert len(keys) >= 15
    assert "require-rbac" in keys
    assert "require-mfa" in keys
    assert "enable-defender" in keys

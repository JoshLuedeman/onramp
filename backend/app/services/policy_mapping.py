"""Azure Policy definition mappings for compliance controls."""

# Maps policy short names used in compliance controls to Azure Policy definition IDs
AZURE_POLICY_MAPPINGS: dict[str, dict] = {
    "require-rbac": {
        "policy_id": "/providers/Microsoft.Authorization/policyDefinitions/5744710e-cc2f-4ee8-8809-3b11e89f4bc9",
        "display_name": "Audit usage of custom RBAC roles",
        "description": "Audit built-in roles instead of custom to reduce complexity",
        "effect": "Audit",
    },
    "require-mfa": {
        "policy_id": "/providers/Microsoft.Authorization/policyDefinitions/e3e008c3-56b9-4133-8fd7-d3347377402a",
        "display_name": "Accounts with owner permissions should have MFA enabled",
        "description": "MFA should be enabled for all subscription accounts with owner permissions",
        "effect": "AuditIfNotExists",
    },
    "require-nsg": {
        "policy_id": "/providers/Microsoft.Authorization/policyDefinitions/e71308d3-144b-4262-b144-efdc3cc90517",
        "display_name": "Subnets should be associated with a Network Security Group",
        "description": "Protect your subnet from potential threats by restricting access with an NSG",
        "effect": "AuditIfNotExists",
    },
    "require-firewall": {
        "policy_id": "/providers/Microsoft.Authorization/policyDefinitions/ea0dfaed-95fb-448c-934e-d6e713ce393d",
        "display_name": "Azure Firewall should be deployed to protect virtual networks",
        "description": "Deploy Azure Firewall for network traffic filtering",
        "effect": "AuditIfNotExists",
    },
    "require-diagnostics": {
        "policy_id": "/providers/Microsoft.Authorization/policyDefinitions/7f89b1eb-583c-429a-8828-af049802c1d9",
        "display_name": "Diagnostic logs should be enabled",
        "description": "Audit diagnostic logs enabling on resources",
        "effect": "AuditIfNotExists",
    },
    "require-log-analytics": {
        "policy_id": "/providers/Microsoft.Authorization/policyDefinitions/d26f7642-7545-4e18-9b75-8c9bbdee3a9a",
        "display_name": "Log Analytics agent should be installed on VMs",
        "description": "Audit VMs for Log Analytics agent installation",
        "effect": "AuditIfNotExists",
    },
    "enable-defender": {
        "policy_id": "/providers/Microsoft.Authorization/policyDefinitions/a7aca53f-2ed4-4466-a25e-0b45ade68efd",
        "display_name": "Microsoft Defender for Cloud should be enabled",
        "description": "Enable Microsoft Defender for Cloud on subscriptions",
        "effect": "AuditIfNotExists",
    },
    "enable-sentinel": {
        "policy_id": "/providers/Microsoft.Authorization/policyDefinitions/sentinel-deployment",
        "display_name": "Microsoft Sentinel should be deployed",
        "description": "Deploy Microsoft Sentinel for SIEM and SOAR",
        "effect": "DeployIfNotExists",
    },
    "require-tags": {
        "policy_id": "/providers/Microsoft.Authorization/policyDefinitions/871b6d14-10aa-478d-b590-94f262e6899c",
        "display_name": "Require a tag on resources",
        "description": "Enforces existence of a tag on resources",
        "effect": "Deny",
    },
    "require-encryption-at-rest": {
        "policy_id": "/providers/Microsoft.Authorization/policyDefinitions/0961003e-5a0a-4549-abde-af6a37f2724d",
        "display_name": "Disk encryption should be applied on VMs",
        "description": "VMs without disk encryption will be monitored",
        "effect": "AuditIfNotExists",
    },
    "require-tls": {
        "policy_id": "/providers/Microsoft.Authorization/policyDefinitions/fe83a0eb-a853-422d-aac2-1bffd182c5d0",
        "display_name": "Latest TLS version should be used",
        "description": "Audit the latest TLS version for web apps",
        "effect": "AuditIfNotExists",
    },
    "require-backup": {
        "policy_id": "/providers/Microsoft.Authorization/policyDefinitions/013e242c-8828-4970-87b3-ab247555486d",
        "display_name": "Azure Backup should be enabled for VMs",
        "description": "Ensure Azure Backup is enabled for all VMs",
        "effect": "AuditIfNotExists",
    },
    "require-pim": {
        "policy_id": "/providers/Microsoft.Authorization/policyDefinitions/pim-required",
        "display_name": "PIM should be enabled for privileged roles",
        "description": "Privileged Identity Management should be configured",
        "effect": "Audit",
    },
    "require-key-vault": {
        "policy_id": "/providers/Microsoft.Authorization/policyDefinitions/1f6c26c6-1e8a-4c41-bb3e-587e52e10e7a",
        "display_name": "Key vaults should have soft delete enabled",
        "description": "Key vaults should be configured with soft delete",
        "effect": "Audit",
    },
    "deny-public-ip": {
        "policy_id": "/providers/Microsoft.Authorization/policyDefinitions/83a86a26-fd1f-447c-b59d-e51f44264114",
        "display_name": "Network interfaces should not have public IPs",
        "description": "Deny public IP addresses on network interfaces",
        "effect": "Deny",
    },
    "require-https": {
        "policy_id": "/providers/Microsoft.Authorization/policyDefinitions/a4af4a39-4135-47fb-b175-47fbdf85311d",
        "display_name": "Web Application should only be accessible over HTTPS",
        "description": "Use of HTTPS ensures server/service authentication",
        "effect": "Audit",
    },
}


def get_policy_definition(policy_key: str) -> dict | None:
    """Get a policy definition by its short key."""
    return AZURE_POLICY_MAPPINGS.get(policy_key)


def get_policies_for_controls(control_policy_keys: list[str]) -> list[dict]:
    """Get full policy definitions for a list of policy keys."""
    return [
        {**AZURE_POLICY_MAPPINGS[key], "key": key}
        for key in control_policy_keys
        if key in AZURE_POLICY_MAPPINGS
    ]


def get_all_policy_keys() -> list[str]:
    """Get all available policy mapping keys."""
    return list(AZURE_POLICY_MAPPINGS.keys())

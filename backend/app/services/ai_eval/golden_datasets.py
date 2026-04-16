"""Golden test datasets for AI evaluation.

Each dataset contains input/expected-output pairs for a specific AI feature.
Tests check *structure and validity*, not exact text matches.
"""

from __future__ import annotations

from app.schemas.ai_eval import GoldenTest

# ---------------------------------------------------------------------------
# Architecture generation golden tests
# ---------------------------------------------------------------------------

ARCHITECTURE_GOLDEN_TESTS: list[GoldenTest] = [
    GoldenTest(
        name="small-startup-eastus",
        feature="architecture",
        input_data={
            "organization_size": "small",
            "industry": "technology",
            "primary_region": "eastus",
            "workloads": ["web-app", "database"],
            "compliance_frameworks": [],
            "budget_usd": 5000,
        },
        expected_patterns={
            "has_management_groups": True,
            "has_subscriptions": True,
            "min_subscriptions": 1,
            "valid_network_type": ["hub-spoke", "vwan"],
            "valid_regions": ["eastus"],
            "has_security_config": True,
            "has_identity": True,
            "organization_size": "small",
        },
    ),
    GoldenTest(
        name="enterprise-financial-westeurope",
        feature="architecture",
        input_data={
            "organization_size": "enterprise",
            "industry": "financial-services",
            "primary_region": "westeurope",
            "workloads": ["trading-platform", "data-warehouse", "crm"],
            "compliance_frameworks": ["PCI-DSS", "SOX"],
            "budget_usd": 500000,
        },
        expected_patterns={
            "has_management_groups": True,
            "has_subscriptions": True,
            "min_subscriptions": 3,
            "valid_network_type": ["hub-spoke", "vwan"],
            "valid_regions": ["westeurope"],
            "has_security_config": True,
            "has_identity": True,
            "organization_size": "enterprise",
            "has_compliance_frameworks": True,
        },
    ),
    GoldenTest(
        name="medium-healthcare-uksouth",
        feature="architecture",
        input_data={
            "organization_size": "medium",
            "industry": "healthcare",
            "primary_region": "uksouth",
            "workloads": ["ehr-system", "patient-portal"],
            "compliance_frameworks": ["HIPAA", "ISO27001"],
            "budget_usd": 50000,
        },
        expected_patterns={
            "has_management_groups": True,
            "has_subscriptions": True,
            "min_subscriptions": 2,
            "valid_network_type": ["hub-spoke", "vwan"],
            "valid_regions": ["uksouth"],
            "has_security_config": True,
            "has_identity": True,
            "organization_size": "medium",
        },
    ),
    GoldenTest(
        name="large-government-usgovvirginia",
        feature="architecture",
        input_data={
            "organization_size": "large",
            "industry": "government",
            "primary_region": "eastus2",
            "workloads": ["citizen-portal", "case-management", "analytics"],
            "compliance_frameworks": ["FedRAMP", "NIST-800-53"],
            "budget_usd": 200000,
        },
        expected_patterns={
            "has_management_groups": True,
            "has_subscriptions": True,
            "min_subscriptions": 2,
            "valid_network_type": ["hub-spoke", "vwan"],
            "valid_regions": ["eastus2"],
            "has_security_config": True,
            "has_identity": True,
            "organization_size": "large",
        },
    ),
    GoldenTest(
        name="small-retail-southeastasia",
        feature="architecture",
        input_data={
            "organization_size": "small",
            "industry": "retail",
            "primary_region": "southeastasia",
            "workloads": ["ecommerce", "inventory"],
            "compliance_frameworks": ["PCI-DSS"],
            "budget_usd": 10000,
        },
        expected_patterns={
            "has_management_groups": True,
            "has_subscriptions": True,
            "min_subscriptions": 1,
            "valid_network_type": ["hub-spoke", "vwan"],
            "valid_regions": ["southeastasia"],
            "has_security_config": True,
            "has_identity": True,
            "organization_size": "small",
        },
    ),
    GoldenTest(
        name="enterprise-manufacturing-japaneast",
        feature="architecture",
        input_data={
            "organization_size": "enterprise",
            "industry": "manufacturing",
            "primary_region": "japaneast",
            "workloads": ["iot-platform", "scada", "erp", "analytics"],
            "compliance_frameworks": ["ISO27001"],
            "budget_usd": 300000,
        },
        expected_patterns={
            "has_management_groups": True,
            "has_subscriptions": True,
            "min_subscriptions": 3,
            "valid_network_type": ["hub-spoke", "vwan"],
            "valid_regions": ["japaneast"],
            "has_security_config": True,
            "has_identity": True,
            "organization_size": "enterprise",
        },
    ),
]


# ---------------------------------------------------------------------------
# Policy generation golden tests
# ---------------------------------------------------------------------------

POLICY_GOLDEN_TESTS: list[GoldenTest] = [
    GoldenTest(
        name="deny-public-storage",
        feature="policy",
        input_data={
            "description": "Deny creation of storage accounts with public blob access enabled",
            "scope": "subscription",
        },
        expected_patterns={
            "has_name": True,
            "has_policy_rule": True,
            "valid_mode": ["All", "Indexed"],
            "valid_effect": [
                "Deny", "deny", "Audit", "audit",
                "DeployIfNotExists", "deployifnotexists",
            ],
            "has_description": True,
        },
    ),
    GoldenTest(
        name="require-tags",
        feature="policy",
        input_data={
            "description": "Require Environment and CostCenter tags on all resource groups",
            "scope": "management-group",
        },
        expected_patterns={
            "has_name": True,
            "has_policy_rule": True,
            "valid_mode": ["All", "Indexed"],
            "valid_effect": [
                "Deny", "deny", "Audit", "audit",
                "Append", "append", "Modify", "modify",
            ],
            "has_description": True,
        },
    ),
    GoldenTest(
        name="enforce-https",
        feature="policy",
        input_data={
            "description": "Ensure all web apps use HTTPS only",
            "scope": "subscription",
        },
        expected_patterns={
            "has_name": True,
            "has_policy_rule": True,
            "valid_mode": ["All", "Indexed"],
            "valid_effect": [
                "Deny", "deny", "Audit", "audit",
                "DeployIfNotExists", "deployifnotexists",
            ],
            "has_description": True,
        },
    ),
    GoldenTest(
        name="restrict-vm-skus",
        feature="policy",
        input_data={
            "description": "Only allow D-series and E-series VMs in production subscriptions",
            "scope": "subscription",
        },
        expected_patterns={
            "has_name": True,
            "has_policy_rule": True,
            "valid_mode": ["All", "Indexed"],
            "valid_effect": ["Deny", "deny", "Audit", "audit"],
            "has_parameters": True,
        },
    ),
    GoldenTest(
        name="audit-unencrypted-sql",
        feature="policy",
        input_data={
            "description": "Audit SQL databases that do not have transparent data encryption enabled",
            "scope": "subscription",
        },
        expected_patterns={
            "has_name": True,
            "has_policy_rule": True,
            "valid_mode": ["All", "Indexed"],
            "valid_effect": [
                "AuditIfNotExists", "auditifnotexists",
                "Audit", "audit",
            ],
            "has_description": True,
        },
    ),
    GoldenTest(
        name="restrict-regions",
        feature="policy",
        input_data={
            "description": "Only allow resource deployment in US East and West Europe regions",
            "scope": "management-group",
        },
        expected_patterns={
            "has_name": True,
            "has_policy_rule": True,
            "valid_mode": ["All", "Indexed"],
            "valid_effect": ["Deny", "deny"],
            "has_parameters": True,
        },
    ),
]


# ---------------------------------------------------------------------------
# Right-sizing / SKU recommendation golden tests
# ---------------------------------------------------------------------------

SIZING_GOLDEN_TESTS: list[GoldenTest] = [
    GoldenTest(
        name="web-app-low-traffic",
        feature="sizing",
        input_data={
            "workload": "web-application",
            "cpu_avg_percent": 15,
            "memory_avg_percent": 30,
            "iops": 500,
            "network_bandwidth_mbps": 50,
            "environment": "production",
        },
        expected_patterns={
            "has_workload": True,
            "has_recommended_sku": True,
            "valid_sku_families": [
                "Standard_B", "Standard_D", "Standard_Dv3",
                "Standard_DSv3", "Standard_Dv4", "Standard_DSv4",
                "Standard_Dv5", "Standard_DSv5",
            ],
            "has_reasoning": True,
            "has_cost_estimate": True,
        },
    ),
    GoldenTest(
        name="database-server-heavy",
        feature="sizing",
        input_data={
            "workload": "sql-database",
            "cpu_avg_percent": 70,
            "memory_avg_percent": 85,
            "iops": 20000,
            "network_bandwidth_mbps": 200,
            "environment": "production",
        },
        expected_patterns={
            "has_workload": True,
            "has_recommended_sku": True,
            "valid_sku_families": [
                "Standard_E", "Standard_Ev3", "Standard_ESv3",
                "Standard_Ev4", "Standard_ESv4", "Standard_Ev5",
                "Standard_ESv5", "Standard_M", "Standard_MS",
            ],
            "has_reasoning": True,
            "has_cost_estimate": True,
        },
    ),
    GoldenTest(
        name="batch-compute-gpu",
        feature="sizing",
        input_data={
            "workload": "machine-learning-training",
            "cpu_avg_percent": 90,
            "memory_avg_percent": 60,
            "gpu_required": True,
            "iops": 5000,
            "network_bandwidth_mbps": 1000,
            "environment": "development",
        },
        expected_patterns={
            "has_workload": True,
            "has_recommended_sku": True,
            "valid_sku_families": [
                "Standard_NC", "Standard_NCv2", "Standard_NCv3",
                "Standard_NCSv3", "Standard_NCasT4_v3",
                "Standard_ND", "Standard_NDv2",
                "Standard_NV", "Standard_NVv3", "Standard_NVv4",
            ],
            "has_reasoning": True,
            "has_cost_estimate": True,
        },
    ),
    GoldenTest(
        name="microservices-burstable",
        feature="sizing",
        input_data={
            "workload": "microservices-api",
            "cpu_avg_percent": 5,
            "memory_avg_percent": 20,
            "iops": 200,
            "network_bandwidth_mbps": 10,
            "environment": "development",
        },
        expected_patterns={
            "has_workload": True,
            "has_recommended_sku": True,
            "valid_sku_families": [
                "Standard_B", "Standard_D", "Standard_Dv3",
                "Standard_Dv4", "Standard_Dv5",
            ],
            "has_reasoning": True,
            "has_cost_estimate": True,
        },
    ),
    GoldenTest(
        name="hpc-simulation",
        feature="sizing",
        input_data={
            "workload": "hpc-simulation",
            "cpu_avg_percent": 95,
            "memory_avg_percent": 50,
            "iops": 50000,
            "network_bandwidth_mbps": 5000,
            "environment": "production",
        },
        expected_patterns={
            "has_workload": True,
            "has_recommended_sku": True,
            "valid_sku_families": [
                "Standard_H", "Standard_HB", "Standard_HC",
                "Standard_F", "Standard_FS", "Standard_Fv2",
                "Standard_FSv2",
            ],
            "has_reasoning": True,
            "has_cost_estimate": True,
        },
    ),
    GoldenTest(
        name="storage-optimized-analytics",
        feature="sizing",
        input_data={
            "workload": "data-analytics",
            "cpu_avg_percent": 40,
            "memory_avg_percent": 55,
            "iops": 100000,
            "network_bandwidth_mbps": 500,
            "environment": "production",
        },
        expected_patterns={
            "has_workload": True,
            "has_recommended_sku": True,
            "valid_sku_families": [
                "Standard_L", "Standard_Lv2", "Standard_Lsv2",
                "Standard_Lsv3", "Standard_Lasv3",
                "Standard_E", "Standard_Ev5",
            ],
            "has_reasoning": True,
            "has_cost_estimate": True,
        },
    ),
]


# ---------------------------------------------------------------------------
# Security finding golden tests
# ---------------------------------------------------------------------------

SECURITY_GOLDEN_TESTS: list[GoldenTest] = [
    GoldenTest(
        name="public-storage-account",
        feature="security",
        input_data={
            "architecture": {
                "resources": [
                    {
                        "type": "Microsoft.Storage/storageAccounts",
                        "name": "publicdata01",
                        "public_access": True,
                    }
                ],
            },
        },
        expected_patterns={
            "has_severity": True,
            "valid_severities": ["critical", "high", "medium", "low", "informational"],
            "has_category": True,
            "has_resource": True,
            "has_finding": True,
            "has_remediation": True,
            "severity_min": "high",
        },
    ),
    GoldenTest(
        name="no-nsg-on-subnet",
        feature="security",
        input_data={
            "architecture": {
                "resources": [
                    {
                        "type": "Microsoft.Network/virtualNetworks",
                        "name": "vnet-prod",
                        "subnets": [
                            {"name": "default", "nsg": None},
                        ],
                    }
                ],
            },
        },
        expected_patterns={
            "has_severity": True,
            "valid_severities": ["critical", "high", "medium", "low", "informational"],
            "has_category": True,
            "has_finding": True,
            "has_remediation": True,
        },
    ),
    GoldenTest(
        name="sql-no-tde",
        feature="security",
        input_data={
            "architecture": {
                "resources": [
                    {
                        "type": "Microsoft.Sql/servers/databases",
                        "name": "sqldb-prod",
                        "transparent_data_encryption": False,
                    }
                ],
            },
        },
        expected_patterns={
            "has_severity": True,
            "valid_severities": ["critical", "high", "medium", "low", "informational"],
            "has_category": True,
            "has_finding": True,
            "has_remediation": True,
        },
    ),
    GoldenTest(
        name="keyvault-no-soft-delete",
        feature="security",
        input_data={
            "architecture": {
                "resources": [
                    {
                        "type": "Microsoft.KeyVault/vaults",
                        "name": "kv-secrets",
                        "soft_delete_enabled": False,
                        "purge_protection_enabled": False,
                    }
                ],
            },
        },
        expected_patterns={
            "has_severity": True,
            "valid_severities": ["critical", "high", "medium", "low", "informational"],
            "has_category": True,
            "has_finding": True,
            "has_remediation": True,
            "severity_min": "medium",
        },
    ),
    GoldenTest(
        name="vm-no-managed-identity",
        feature="security",
        input_data={
            "architecture": {
                "resources": [
                    {
                        "type": "Microsoft.Compute/virtualMachines",
                        "name": "vm-app-01",
                        "managed_identity": False,
                        "password_auth": True,
                    }
                ],
            },
        },
        expected_patterns={
            "has_severity": True,
            "valid_severities": ["critical", "high", "medium", "low", "informational"],
            "has_category": True,
            "has_finding": True,
            "has_remediation": True,
        },
    ),
    GoldenTest(
        name="no-defender-enabled",
        feature="security",
        input_data={
            "architecture": {
                "security": {
                    "defender_for_cloud": False,
                    "sentinel": False,
                    "ddos_protection": False,
                },
            },
        },
        expected_patterns={
            "has_severity": True,
            "valid_severities": ["critical", "high", "medium", "low", "informational"],
            "has_category": True,
            "has_finding": True,
            "has_remediation": True,
            "severity_min": "high",
        },
    ),
]


# ---------------------------------------------------------------------------
# Regulatory / compliance prediction golden tests
# ---------------------------------------------------------------------------

REGULATORY_GOLDEN_TESTS: list[GoldenTest] = [
    GoldenTest(
        name="us-healthcare",
        feature="regulatory",
        input_data={
            "industry": "healthcare",
            "geography": "United States",
            "data_types": ["PHI", "patient-records"],
        },
        expected_patterns={
            "expected_frameworks": ["HIPAA"],
            "has_framework": True,
            "has_control_id": True,
            "has_status": True,
            "valid_statuses": [
                "compliant", "non_compliant", "partial", "not_assessed",
            ],
        },
    ),
    GoldenTest(
        name="eu-financial-services",
        feature="regulatory",
        input_data={
            "industry": "financial-services",
            "geography": "European Union",
            "data_types": ["PII", "financial-transactions"],
        },
        expected_patterns={
            "expected_frameworks": ["GDPR", "PCI-DSS"],
            "has_framework": True,
            "has_control_id": True,
            "has_status": True,
            "valid_statuses": [
                "compliant", "non_compliant", "partial", "not_assessed",
            ],
        },
    ),
    GoldenTest(
        name="us-government",
        feature="regulatory",
        input_data={
            "industry": "government",
            "geography": "United States",
            "data_types": ["CUI", "citizen-data"],
        },
        expected_patterns={
            "expected_frameworks": ["FedRAMP", "NIST-800-53"],
            "has_framework": True,
            "has_control_id": True,
            "has_status": True,
            "valid_statuses": [
                "compliant", "non_compliant", "partial", "not_assessed",
            ],
        },
    ),
    GoldenTest(
        name="global-ecommerce",
        feature="regulatory",
        input_data={
            "industry": "retail",
            "geography": "global",
            "data_types": ["PII", "payment-cards"],
        },
        expected_patterns={
            "expected_frameworks": ["PCI-DSS"],
            "has_framework": True,
            "has_control_id": True,
            "has_status": True,
            "valid_statuses": [
                "compliant", "non_compliant", "partial", "not_assessed",
            ],
        },
    ),
    GoldenTest(
        name="uk-education",
        feature="regulatory",
        input_data={
            "industry": "education",
            "geography": "United Kingdom",
            "data_types": ["student-records", "PII"],
        },
        expected_patterns={
            "expected_frameworks": ["ISO27001"],
            "has_framework": True,
            "has_control_id": True,
            "has_status": True,
            "valid_statuses": [
                "compliant", "non_compliant", "partial", "not_assessed",
            ],
        },
    ),
    GoldenTest(
        name="australia-banking",
        feature="regulatory",
        input_data={
            "industry": "banking",
            "geography": "Australia",
            "data_types": ["financial-records", "PII"],
        },
        expected_patterns={
            "expected_frameworks": ["ISO27001"],
            "has_framework": True,
            "has_control_id": True,
            "has_status": True,
            "valid_statuses": [
                "compliant", "non_compliant", "partial", "not_assessed",
            ],
        },
    ),
]


# ---------------------------------------------------------------------------
# Aggregated mapping
# ---------------------------------------------------------------------------

ALL_GOLDEN_TESTS: dict[str, list[GoldenTest]] = {
    "architecture": ARCHITECTURE_GOLDEN_TESTS,
    "policy": POLICY_GOLDEN_TESTS,
    "sizing": SIZING_GOLDEN_TESTS,
    "security": SECURITY_GOLDEN_TESTS,
    "regulatory": REGULATORY_GOLDEN_TESTS,
}

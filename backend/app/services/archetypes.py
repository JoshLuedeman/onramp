"""Landing zone archetype templates — pre-built architecture patterns by org size."""

from copy import deepcopy


ARCHETYPES: dict[str, dict] = {
    "small": {
        "name": "Small Organization Landing Zone",
        "description": "Simplified landing zone for organizations with 1-5 subscriptions. Minimal management group hierarchy with essential governance.",
        "organization_size": "small",
        "management_groups": {
            "root": {
                "display_name": "Tenant Root Group",
                "children": {
                    "platform": {
                        "display_name": "Platform",
                        "children": {},
                    },
                    "workloads": {
                        "display_name": "Workloads",
                        "children": {},
                    },
                    "sandbox": {
                        "display_name": "Sandbox",
                        "children": {},
                    },
                },
            }
        },
        "subscriptions": [
            {"name": "sub-platform", "purpose": "Shared platform services (identity, networking, monitoring)", "management_group": "platform", "budget_usd": 500},
            {"name": "sub-workload-prod", "purpose": "Production workloads", "management_group": "workloads", "budget_usd": 1000},
            {"name": "sub-workload-dev", "purpose": "Development and testing", "management_group": "sandbox", "budget_usd": 300},
        ],
        "network_topology": {
            "type": "hub-spoke",
            "primary_region": "eastus2",
            "hub": {"vnet_cidr": "10.0.0.0/16", "subnets": [
                {"name": "AzureFirewallSubnet", "cidr": "10.0.1.0/24"},
                {"name": "GatewaySubnet", "cidr": "10.0.2.0/24"},
                {"name": "SharedServicesSubnet", "cidr": "10.0.3.0/24"},
            ]},
            "spokes": [
                {"name": "prod", "vnet_cidr": "10.1.0.0/16"},
            ],
            "dns": {"type": "azure_dns"},
            "hybrid_connectivity": None,
        },
        "identity": {
            "provider": "Microsoft Entra ID",
            "rbac_model": "Azure RBAC",
            "pim_enabled": False,
            "conditional_access": True,
            "mfa_policy": "all_users",
        },
        "security": {
            "defender_for_cloud": True,
            "defender_plans": ["Servers", "AppService", "KeyVaults"],
            "sentinel": False,
            "ddos_protection": False,
            "azure_firewall": True,
            "waf": False,
            "key_vault_per_subscription": True,
        },
        "governance": {
            "policies": [
                {"name": "Require resource tags", "scope": "root", "effect": "deny"},
                {"name": "Allowed regions", "scope": "root", "effect": "deny"},
                {"name": "Require secure transfer for storage", "scope": "root", "effect": "deny"},
            ],
            "tagging_strategy": {
                "mandatory_tags": ["Environment", "Owner", "CostCenter"],
                "optional_tags": ["Application", "Project"],
            },
            "naming_convention": "Azure CAF recommended",
            "cost_management": {"budgets_enabled": True, "alerts_enabled": True, "optimization_recommendations": True},
        },
        "management": {
            "log_analytics": {"workspace_count": 1, "retention_days": 30},
            "monitoring": {"azure_monitor": True, "alerts": True},
            "backup": {"enabled": True, "geo_redundant": False},
            "update_management": True,
        },
        "compliance_frameworks": [],
        "platform_automation": {"iac_tool": "bicep", "cicd_platform": "github_actions", "repo_structure": "mono-repo"},
        "recommendations": [
            "Start with a single hub-spoke topology",
            "Enable MFA for all users",
            "Use Azure Policy to enforce tagging",
            "Set up cost alerts on all subscriptions",
        ],
        "estimated_monthly_cost_usd": 800,
    },
    "medium": {
        "name": "Medium Organization Landing Zone",
        "description": "Standard CAF enterprise-scale landing zone for organizations with 5-20 subscriptions. Full management group hierarchy with platform and landing zone separation.",
        "organization_size": "medium",
        "management_groups": {
            "root": {
                "display_name": "Tenant Root Group",
                "children": {
                    "platform": {
                        "display_name": "Platform",
                        "children": {
                            "identity": {"display_name": "Identity", "children": {}},
                            "management": {"display_name": "Management", "children": {}},
                            "connectivity": {"display_name": "Connectivity", "children": {}},
                        },
                    },
                    "landing_zones": {
                        "display_name": "Landing Zones",
                        "children": {
                            "corp": {"display_name": "Corp", "children": {}},
                            "online": {"display_name": "Online", "children": {}},
                        },
                    },
                    "sandbox": {"display_name": "Sandbox", "children": {}},
                    "decommissioned": {"display_name": "Decommissioned", "children": {}},
                },
            }
        },
        "subscriptions": [
            {"name": "sub-identity", "purpose": "Identity and access management", "management_group": "identity", "budget_usd": 300},
            {"name": "sub-management", "purpose": "Monitoring and management", "management_group": "management", "budget_usd": 500},
            {"name": "sub-connectivity", "purpose": "Hub networking and DNS", "management_group": "connectivity", "budget_usd": 800},
            {"name": "sub-corp-prod", "purpose": "Corp production workloads", "management_group": "corp", "budget_usd": 2000},
            {"name": "sub-corp-dev", "purpose": "Corp development", "management_group": "corp", "budget_usd": 500},
            {"name": "sub-online-prod", "purpose": "Public-facing workloads", "management_group": "online", "budget_usd": 1500},
        ],
        "network_topology": {
            "type": "hub-spoke",
            "primary_region": "eastus2",
            "hub": {"vnet_cidr": "10.0.0.0/16", "subnets": [
                {"name": "AzureFirewallSubnet", "cidr": "10.0.1.0/24"},
                {"name": "GatewaySubnet", "cidr": "10.0.2.0/24"},
                {"name": "AzureBastionSubnet", "cidr": "10.0.3.0/24"},
                {"name": "SharedServicesSubnet", "cidr": "10.0.4.0/24"},
            ]},
            "spokes": [
                {"name": "identity", "vnet_cidr": "10.1.0.0/16"},
                {"name": "corp-prod", "vnet_cidr": "10.10.0.0/16"},
                {"name": "corp-dev", "vnet_cidr": "10.11.0.0/16"},
                {"name": "online-prod", "vnet_cidr": "10.20.0.0/16"},
            ],
            "dns": {"type": "azure_dns", "private_dns_zones": True},
            "hybrid_connectivity": {"type": "vpn"},
        },
        "identity": {
            "provider": "Microsoft Entra ID",
            "rbac_model": "Azure RBAC",
            "pim_enabled": True,
            "conditional_access": True,
            "mfa_policy": "all_users",
        },
        "security": {
            "defender_for_cloud": True,
            "defender_plans": ["Servers", "AppService", "KeyVaults", "Storage", "SQL", "Containers"],
            "sentinel": True,
            "ddos_protection": False,
            "azure_firewall": True,
            "waf": True,
            "key_vault_per_subscription": True,
        },
        "governance": {
            "policies": [
                {"name": "Require resource tags", "scope": "root", "effect": "deny"},
                {"name": "Allowed regions", "scope": "root", "effect": "deny"},
                {"name": "Require secure transfer", "scope": "root", "effect": "deny"},
                {"name": "Deny public IP on NICs", "scope": "corp", "effect": "deny"},
                {"name": "Audit VMs without backup", "scope": "landing_zones", "effect": "audit"},
                {"name": "Require NSG on subnets", "scope": "landing_zones", "effect": "deny"},
            ],
            "tagging_strategy": {
                "mandatory_tags": ["Environment", "Owner", "CostCenter", "Application"],
                "optional_tags": ["Project", "DataClassification", "BusinessUnit"],
            },
            "naming_convention": "Azure CAF recommended",
            "cost_management": {"budgets_enabled": True, "alerts_enabled": True, "optimization_recommendations": True},
        },
        "management": {
            "log_analytics": {"workspace_count": 1, "retention_days": 90},
            "monitoring": {"azure_monitor": True, "alerts": True, "action_groups": True},
            "backup": {"enabled": True, "geo_redundant": True},
            "update_management": True,
        },
        "compliance_frameworks": [],
        "platform_automation": {"iac_tool": "bicep", "cicd_platform": "github_actions", "repo_structure": "mono-repo"},
        "recommendations": [
            "Separate platform subscriptions from workload subscriptions",
            "Enable PIM for all privileged roles",
            "Deploy Microsoft Sentinel for threat detection",
            "Use private endpoints for PaaS services in the Corp landing zone",
            "Implement Azure Firewall for centralized egress control",
        ],
        "estimated_monthly_cost_usd": 3500,
    },
    "enterprise": {
        "name": "Enterprise Landing Zone",
        "description": "Full CAF enterprise-scale landing zone for large organizations with 20+ subscriptions. Complete management group hierarchy, multiple regions, and comprehensive governance.",
        "organization_size": "enterprise",
        "management_groups": {
            "root": {
                "display_name": "Tenant Root Group",
                "children": {
                    "platform": {
                        "display_name": "Platform",
                        "children": {
                            "identity": {"display_name": "Identity", "children": {}},
                            "management": {"display_name": "Management", "children": {}},
                            "connectivity": {"display_name": "Connectivity", "children": {}},
                        },
                    },
                    "landing_zones": {
                        "display_name": "Landing Zones",
                        "children": {
                            "corp": {"display_name": "Corp", "children": {}},
                            "online": {"display_name": "Online", "children": {}},
                            "confidential_corp": {"display_name": "Confidential Corp", "children": {}},
                            "confidential_online": {"display_name": "Confidential Online", "children": {}},
                        },
                    },
                    "sandbox": {"display_name": "Sandbox", "children": {}},
                    "decommissioned": {"display_name": "Decommissioned", "children": {}},
                },
            }
        },
        "subscriptions": [
            {"name": "sub-identity-prod", "purpose": "Identity services (prod)", "management_group": "identity", "budget_usd": 500},
            {"name": "sub-management-prod", "purpose": "Central monitoring and management", "management_group": "management", "budget_usd": 1000},
            {"name": "sub-connectivity-prod", "purpose": "Hub networking (primary region)", "management_group": "connectivity", "budget_usd": 2000},
            {"name": "sub-connectivity-dr", "purpose": "Hub networking (DR region)", "management_group": "connectivity", "budget_usd": 1000},
            {"name": "sub-corp-prod-001", "purpose": "Corp workloads - production", "management_group": "corp", "budget_usd": 5000},
            {"name": "sub-corp-nonprod-001", "purpose": "Corp workloads - non-production", "management_group": "corp", "budget_usd": 2000},
            {"name": "sub-online-prod-001", "purpose": "Public-facing production", "management_group": "online", "budget_usd": 3000},
            {"name": "sub-online-nonprod-001", "purpose": "Public-facing non-production", "management_group": "online", "budget_usd": 1000},
            {"name": "sub-confidential-001", "purpose": "Regulated workloads", "management_group": "confidential_corp", "budget_usd": 3000},
            {"name": "sub-sandbox-001", "purpose": "Developer sandbox", "management_group": "sandbox", "budget_usd": 500},
        ],
        "network_topology": {
            "type": "hub-spoke",
            "primary_region": "eastus2",
            "secondary_region": "westus2",
            "hub": {"vnet_cidr": "10.0.0.0/16", "subnets": [
                {"name": "AzureFirewallSubnet", "cidr": "10.0.1.0/24"},
                {"name": "AzureFirewallManagementSubnet", "cidr": "10.0.2.0/24"},
                {"name": "GatewaySubnet", "cidr": "10.0.3.0/24"},
                {"name": "AzureBastionSubnet", "cidr": "10.0.4.0/24"},
                {"name": "SharedServicesSubnet", "cidr": "10.0.5.0/24"},
                {"name": "DNSResolverInbound", "cidr": "10.0.6.0/24"},
                {"name": "DNSResolverOutbound", "cidr": "10.0.7.0/24"},
            ]},
            "spokes": [
                {"name": "identity", "vnet_cidr": "10.1.0.0/16"},
                {"name": "corp-prod", "vnet_cidr": "10.10.0.0/16"},
                {"name": "corp-nonprod", "vnet_cidr": "10.11.0.0/16"},
                {"name": "online-prod", "vnet_cidr": "10.20.0.0/16"},
                {"name": "online-nonprod", "vnet_cidr": "10.21.0.0/16"},
                {"name": "confidential", "vnet_cidr": "10.30.0.0/16"},
            ],
            "dns": {"type": "hybrid_dns", "private_dns_zones": True, "dns_resolver": True},
            "hybrid_connectivity": {"type": "expressroute", "redundant_vpn": True},
        },
        "identity": {
            "provider": "Microsoft Entra ID",
            "rbac_model": "Azure RBAC",
            "pim_enabled": True,
            "conditional_access": True,
            "mfa_policy": "all_users",
            "access_reviews": True,
            "break_glass_accounts": 2,
        },
        "security": {
            "defender_for_cloud": True,
            "defender_plans": ["Servers", "AppService", "KeyVaults", "Storage", "SQL", "Containers", "DNS", "ARM"],
            "sentinel": True,
            "ddos_protection": True,
            "azure_firewall": True,
            "azure_firewall_premium": True,
            "waf": True,
            "key_vault_per_subscription": True,
            "private_endpoints_required": True,
        },
        "governance": {
            "policies": [
                {"name": "Require resource tags", "scope": "root", "effect": "deny"},
                {"name": "Allowed regions", "scope": "root", "effect": "deny"},
                {"name": "Require secure transfer", "scope": "root", "effect": "deny"},
                {"name": "Deny public IP on NICs", "scope": "corp", "effect": "deny"},
                {"name": "Deny public IP on NICs", "scope": "confidential_corp", "effect": "deny"},
                {"name": "Require private endpoints", "scope": "confidential_corp", "effect": "deny"},
                {"name": "Audit VMs without backup", "scope": "landing_zones", "effect": "audit"},
                {"name": "Require NSG on subnets", "scope": "landing_zones", "effect": "deny"},
                {"name": "Deny classic resources", "scope": "root", "effect": "deny"},
                {"name": "Require diagnostic settings", "scope": "root", "effect": "deployIfNotExists"},
                {"name": "Enforce HTTPS only", "scope": "root", "effect": "deny"},
            ],
            "tagging_strategy": {
                "mandatory_tags": ["Environment", "Owner", "CostCenter", "Application", "DataClassification", "BusinessUnit"],
                "optional_tags": ["Project", "Compliance", "SLA"],
            },
            "naming_convention": "Azure CAF recommended",
            "cost_management": {"budgets_enabled": True, "alerts_enabled": True, "optimization_recommendations": True, "reserved_instances": True},
        },
        "management": {
            "log_analytics": {"workspace_count": 1, "retention_days": 365},
            "monitoring": {"azure_monitor": True, "alerts": True, "action_groups": True, "workbooks": True},
            "backup": {"enabled": True, "geo_redundant": True, "cross_region_restore": True},
            "update_management": True,
        },
        "compliance_frameworks": [],
        "platform_automation": {"iac_tool": "bicep", "cicd_platform": "github_actions", "repo_structure": "multi-repo"},
        "recommendations": [
            "Deploy multi-region hub-spoke with ExpressRoute",
            "Enable DDoS Protection Standard on hub VNets",
            "Use Azure Firewall Premium for TLS inspection",
            "Implement Confidential Computing for regulated workloads",
            "Enable PIM with quarterly access reviews",
            "Deploy Microsoft Sentinel with custom detection rules",
            "Use private endpoints for all PaaS services",
            "Implement break-glass emergency access accounts",
        ],
        "estimated_monthly_cost_usd": 15000,
    },
}


def get_archetype(size: str) -> dict | None:
    """Get a landing zone archetype by organization size."""
    return deepcopy(ARCHETYPES.get(size))


def get_archetype_for_answers(answers: dict) -> dict:
    """Select and customize an archetype based on questionnaire answers."""
    org_size = answers.get("org_size", "medium")

    # Map org sizes to archetype keys
    size_map = {
        "small": "small",
        "medium": "medium",
        "large": "enterprise",
        "enterprise": "enterprise",
    }

    archetype = get_archetype(size_map.get(org_size, "medium"))
    if archetype is None:
        archetype = get_archetype("medium")

    # Customize based on answers
    if answers.get("primary_region"):
        archetype["network_topology"]["primary_region"] = answers["primary_region"]

    if answers.get("network_topology"):
        topo = answers["network_topology"]
        if topo == "vwan":
            archetype["network_topology"]["type"] = "vwan"
        elif topo == "hub_spoke":
            archetype["network_topology"]["type"] = "hub-spoke"

    if answers.get("hybrid_connectivity"):
        hc = answers["hybrid_connectivity"]
        if hc == "no":
            archetype["network_topology"]["hybrid_connectivity"] = None
        elif hc == "expressroute":
            archetype["network_topology"]["hybrid_connectivity"] = {"type": "expressroute"}
        elif hc == "vpn":
            archetype["network_topology"]["hybrid_connectivity"] = {"type": "vpn"}
        elif hc == "both":
            archetype["network_topology"]["hybrid_connectivity"] = {"type": "expressroute", "redundant_vpn": True}

    if answers.get("pim_required") == "yes":
        archetype["identity"]["pim_enabled"] = True
    elif answers.get("pim_required") == "no":
        archetype["identity"]["pim_enabled"] = False

    if answers.get("mfa_requirement"):
        archetype["identity"]["mfa_policy"] = answers["mfa_requirement"]

    if answers.get("siem_integration") == "sentinel":
        archetype["security"]["sentinel"] = True
    elif answers.get("siem_integration") == "no":
        archetype["security"]["sentinel"] = False

    if answers.get("compliance_frameworks"):
        frameworks = answers["compliance_frameworks"]
        if isinstance(frameworks, list) and "none" not in frameworks:
            archetype["compliance_frameworks"] = [
                {"name": f, "controls_applied": 0, "coverage_percent": 0}
                for f in frameworks
            ]

    if answers.get("tagging_strategy") and isinstance(answers["tagging_strategy"], list):
        tag_labels = {
            "environment": "Environment",
            "cost_center": "CostCenter",
            "owner": "Owner",
            "application": "Application",
            "data_classification": "DataClassification",
            "business_unit": "BusinessUnit",
            "project": "Project",
        }
        archetype["governance"]["tagging_strategy"]["mandatory_tags"] = [
            tag_labels.get(t, t) for t in answers["tagging_strategy"]
        ]

    if answers.get("iac_tool"):
        archetype["platform_automation"]["iac_tool"] = answers["iac_tool"]

    if answers.get("cicd_platform"):
        archetype["platform_automation"]["cicd_platform"] = answers["cicd_platform"]

    return archetype


def list_archetypes() -> list[dict]:
    """List available archetypes with summary info."""
    return [
        {
            "size": key,
            "name": val["name"],
            "description": val["description"],
            "subscription_count": len(val["subscriptions"]),
            "estimated_monthly_cost_usd": val["estimated_monthly_cost_usd"],
        }
        for key, val in ARCHETYPES.items()
    ]

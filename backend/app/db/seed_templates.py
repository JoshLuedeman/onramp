"""Curated industry templates for the marketplace."""

import json
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

CURATED_TEMPLATES: list[dict] = [
    {
        "id": "curated-healthcare-hipaa",
        "name": "Healthcare (HIPAA Compliant)",
        "description": (
            "Hub-spoke network with private endpoints, diagnostic "
            "logging, Key Vault for secrets, and HIPAA compliance "
            "controls. Designed for healthcare workloads handling PHI."
        ),
        "industry": "Healthcare",
        "tags": [
            "hipaa", "healthcare", "private-endpoints",
            "key-vault", "diagnostic-logging",
        ],
        "architecture_json": json.dumps({
            "archetype": "healthcare-hipaa",
            "network": {
                "topology": "hub-spoke",
                "hub": {
                    "firewall": True,
                    "bastion": True,
                    "vpn_gateway": True,
                },
                "spokes": [
                    {"name": "prod-spoke", "address_space": "10.1.0.0/16"},
                    {"name": "dev-spoke", "address_space": "10.2.0.0/16"},
                ],
                "private_endpoints": True,
                "private_dns_zones": True,
            },
            "security": {
                "key_vault": {
                    "sku": "premium",
                    "purge_protection": True,
                    "soft_delete": True,
                },
                "encryption": "platform-managed",
                "defender_for_cloud": True,
            },
            "monitoring": {
                "diagnostic_logging": True,
                "log_analytics": True,
                "retention_days": 365,
            },
            "compliance": ["HIPAA", "HITRUST"],
        }),
        "visibility": "curated",
    },
    {
        "id": "curated-financial-pci",
        "name": "Financial Services (PCI-DSS/SOX)",
        "description": (
            "Isolated VNets with WAF, audit logging, HSM-backed "
            "Key Vault, and strict network segmentation for PCI-DSS "
            "and SOX compliance in financial services."
        ),
        "industry": "Financial Services",
        "tags": [
            "pci-dss", "sox", "financial", "waf",
            "hsm", "audit-logging",
        ],
        "architecture_json": json.dumps({
            "archetype": "financial-pci-sox",
            "network": {
                "topology": "hub-spoke",
                "hub": {
                    "firewall": True,
                    "waf": True,
                    "bastion": True,
                },
                "spokes": [
                    {
                        "name": "cardholder-data",
                        "address_space": "10.10.0.0/16",
                        "nsg_rules": "pci-restricted",
                    },
                    {
                        "name": "internal",
                        "address_space": "10.20.0.0/16",
                    },
                ],
                "private_endpoints": True,
            },
            "security": {
                "key_vault": {
                    "sku": "premium",
                    "hsm_backed": True,
                    "purge_protection": True,
                },
                "encryption": "customer-managed-key",
                "defender_for_cloud": True,
                "sentinel": True,
            },
            "monitoring": {
                "audit_logging": True,
                "log_analytics": True,
                "retention_days": 730,
                "immutable_logs": True,
            },
            "compliance": ["PCI-DSS", "SOX"],
        }),
        "visibility": "curated",
    },
    {
        "id": "curated-government-fedramp",
        "name": "Government (FedRAMP/NIST)",
        "description": (
            "Sovereign region deployment with customer-managed key "
            "encryption, Azure Policy enforcement, Sentinel SIEM, "
            "and FedRAMP/NIST 800-53 compliance controls."
        ),
        "industry": "Government",
        "tags": [
            "fedramp", "nist", "government", "sovereign",
            "cmk", "sentinel", "azure-policy",
        ],
        "architecture_json": json.dumps({
            "archetype": "government-fedramp",
            "network": {
                "topology": "hub-spoke",
                "hub": {
                    "firewall": True,
                    "bastion": True,
                    "ddos_protection": True,
                },
                "spokes": [
                    {
                        "name": "production",
                        "address_space": "10.100.0.0/16",
                    },
                    {
                        "name": "staging",
                        "address_space": "10.101.0.0/16",
                    },
                ],
                "private_endpoints": True,
                "express_route": True,
            },
            "security": {
                "key_vault": {
                    "sku": "premium",
                    "hsm_backed": True,
                    "purge_protection": True,
                },
                "encryption": "customer-managed-key",
                "defender_for_cloud": True,
                "sentinel": True,
                "azure_policy": {
                    "initiatives": [
                        "FedRAMP High",
                        "NIST SP 800-53 Rev 5",
                    ],
                },
            },
            "monitoring": {
                "diagnostic_logging": True,
                "log_analytics": True,
                "retention_days": 730,
                "sentinel_workspace": True,
            },
            "compliance": ["FedRAMP High", "NIST 800-53"],
            "region": "sovereign",
        }),
        "visibility": "curated",
    },
    {
        "id": "curated-retail-ha",
        "name": "Retail (PCI/High-Availability)",
        "description": (
            "Multi-region deployment with CDN, Redis caching, "
            "auto-scaling, and PCI compliance for high-availability "
            "retail and e-commerce workloads."
        ),
        "industry": "Retail",
        "tags": [
            "retail", "pci", "high-availability", "multi-region",
            "cdn", "redis", "auto-scaling",
        ],
        "architecture_json": json.dumps({
            "archetype": "retail-high-availability",
            "network": {
                "topology": "hub-spoke",
                "multi_region": True,
                "regions": ["eastus2", "westus2"],
                "hub": {
                    "firewall": True,
                    "waf": True,
                    "front_door": True,
                },
                "spokes": [
                    {
                        "name": "web-tier",
                        "address_space": "10.50.0.0/16",
                    },
                    {
                        "name": "data-tier",
                        "address_space": "10.51.0.0/16",
                    },
                ],
            },
            "compute": {
                "auto_scaling": True,
                "min_instances": 2,
                "max_instances": 20,
                "availability_zones": [1, 2, 3],
            },
            "caching": {
                "redis": True,
                "redis_sku": "Premium",
                "geo_replication": True,
            },
            "cdn": {
                "enabled": True,
                "provider": "Azure Front Door",
            },
            "monitoring": {
                "log_analytics": True,
                "application_insights": True,
            },
            "compliance": ["PCI-DSS"],
        }),
        "visibility": "curated",
    },
    {
        "id": "curated-startup-cost",
        "name": "Startup (Cost-Optimized)",
        "description": (
            "Single VNet with basic monitoring and consumption-based "
            "services. Designed for startups and small teams that "
            "need a secure foundation without enterprise costs."
        ),
        "industry": "Startup",
        "tags": [
            "startup", "cost-optimized", "small-team",
            "consumption", "basic-monitoring",
        ],
        "architecture_json": json.dumps({
            "archetype": "startup-cost-optimized",
            "network": {
                "topology": "single-vnet",
                "address_space": "10.0.0.0/16",
                "subnets": [
                    {
                        "name": "default",
                        "address_prefix": "10.0.1.0/24",
                    },
                    {
                        "name": "app-service",
                        "address_prefix": "10.0.2.0/24",
                    },
                ],
                "nsg": True,
            },
            "compute": {
                "app_service_plan": "B1",
                "consumption_functions": True,
            },
            "security": {
                "key_vault": {"sku": "standard"},
                "defender_for_cloud": False,
            },
            "monitoring": {
                "basic_monitoring": True,
                "application_insights": True,
                "log_analytics": False,
            },
            "compliance": [],
        }),
        "visibility": "curated",
    },
]


async def seed_curated_templates(session: AsyncSession) -> None:
    """Seed curated templates if not already present. Idempotent."""
    from app.models.template import Template

    count = await session.scalar(
        select(func.count()).select_from(Template)
    )
    if count and count > 0:
        logger.info(
            "Templates already seeded (%d rows)", count
        )
        return

    for tpl in CURATED_TEMPLATES:
        session.add(Template(
            id=tpl["id"],
            name=tpl["name"],
            description=tpl["description"],
            industry=tpl["industry"],
            tags=tpl["tags"],
            architecture_json=tpl["architecture_json"],
            visibility=tpl["visibility"],
            author_tenant_id=None,
        ))

    await session.flush()
    logger.info("Seeded %d curated templates", len(CURATED_TEMPLATES))

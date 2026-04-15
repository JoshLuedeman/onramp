"""ADR generation service.

Generates Architecture Decision Records from architecture data
and questionnaire answers using either static templates or AI.
"""

import logging
from datetime import datetime, timezone

from app.schemas.adr import ADRRecord

logger = logging.getLogger(__name__)


def _today() -> str:
    """Return today's date as ISO string."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


def _extract_mg_info(architecture: dict) -> dict:
    """Extract management group details from architecture data."""
    mg = architecture.get("management_groups", {})
    if isinstance(mg, list):
        names = [g.get("name", "unknown") for g in mg]
    elif isinstance(mg, dict):
        names = list(mg.keys()) if mg else ["root"]
    else:
        names = ["root"]
    return {"names": names, "count": len(names)}


def _extract_network_info(architecture: dict) -> dict:
    """Extract network topology details from architecture data."""
    net = architecture.get("network_topology", {})
    if isinstance(net, dict):
        return {
            "type": net.get("type", "hub-spoke"),
            "primary_region": net.get("primary_region", "eastus2"),
            "secondary_region": net.get("secondary_region"),
        }
    return {"type": "hub-spoke", "primary_region": "eastus2", "secondary_region": None}


def _extract_subscription_info(architecture: dict) -> dict:
    """Extract subscription topology details."""
    subs = architecture.get("subscriptions", [])
    if isinstance(subs, list):
        names = [s.get("name", "unknown") if isinstance(s, dict) else str(s) for s in subs]
    else:
        names = []
    return {"names": names, "count": len(names)}


def _generate_mg_adr(architecture: dict, adr_number: int) -> ADRRecord:
    """Generate ADR for management group hierarchy decision."""
    mg_info = _extract_mg_info(architecture)
    group_list = ", ".join(mg_info["names"][:5])
    return ADRRecord(
        id=f"ADR-{adr_number:03d}",
        title="Management Group Hierarchy",
        status="Accepted",
        context=(
            "The organization requires a management group hierarchy to organize "
            "Azure subscriptions, apply policies consistently, and enforce governance "
            "at scale. The hierarchy must balance granularity with operational simplicity."
        ),
        decision=(
            f"Adopt a management group hierarchy with {mg_info['count']} groups: "
            f"{group_list}. This structure aligns with the Cloud Adoption Framework "
            "recommended patterns and supports the organization's governance model."
        ),
        consequences=(
            "Policies applied at upper management groups cascade to child scopes, "
            "reducing per-subscription configuration. Teams must follow the established "
            "hierarchy when creating new subscriptions. Changes to the hierarchy "
            "require coordination across platform and workload teams."
        ),
        category="governance",
        created_at=_today(),
    )


def _generate_network_adr(architecture: dict, adr_number: int) -> ADRRecord:
    """Generate ADR for network topology decision."""
    net_info = _extract_network_info(architecture)
    topo_type = net_info["type"]
    region = net_info["primary_region"]
    return ADRRecord(
        id=f"ADR-{adr_number:03d}",
        title="Network Topology",
        status="Accepted",
        context=(
            "The landing zone requires a network topology that provides secure "
            "connectivity between workloads, on-premises resources, and the internet "
            "while supporting the organization's latency and compliance requirements."
        ),
        decision=(
            f"Use a {topo_type} network topology with the hub deployed in {region}. "
            "Central network virtual appliances and shared services reside in the hub, "
            "while workload VNets peer as spokes. This topology provides centralized "
            "traffic inspection and simplified network management."
        ),
        consequences=(
            "All inter-spoke traffic routes through the hub, enabling centralized "
            "firewall inspection but adding a potential bottleneck. Spoke teams depend "
            "on the platform team for peering and DNS configuration. Network latency "
            "between spokes is slightly higher than direct peering."
        ),
        category="networking",
        created_at=_today(),
    )


def _generate_identity_adr(
    architecture: dict, answers: dict, adr_number: int,
) -> ADRRecord:
    """Generate ADR for identity model decision."""
    identity = architecture.get("identity", {})
    provider = "Entra ID"
    if isinstance(identity, dict):
        provider = identity.get("provider", "Entra ID")
    model = answers.get("identity_model", "centralized")
    if isinstance(model, list):
        model = model[0] if model else "centralized"
    return ADRRecord(
        id=f"ADR-{adr_number:03d}",
        title="Identity Model",
        status="Accepted",
        context=(
            "The organization needs a consistent identity and access management "
            "strategy across all Azure landing zone subscriptions. The identity "
            "model must support least-privilege access, conditional access policies, "
            "and integration with existing directory services."
        ),
        decision=(
            f"Adopt a {model} identity model using {provider} as the primary "
            "identity provider. Privileged Identity Management (PIM) is enabled "
            "for just-in-time access to sensitive roles. Multi-factor authentication "
            "is enforced for all users via conditional access policies."
        ),
        consequences=(
            "All authentication flows route through the centralized identity provider, "
            "providing a single audit trail. Teams must request role assignments through "
            "PIM rather than permanent role grants. Federation with external identity "
            "providers requires additional configuration and approval."
        ),
        category="identity",
        created_at=_today(),
    )


def _generate_compliance_adr(
    architecture: dict, answers: dict, adr_number: int,
) -> ADRRecord:
    """Generate ADR for compliance framework selection."""
    frameworks = answers.get("compliance_frameworks", [])
    if isinstance(frameworks, str):
        frameworks = [frameworks]
    if not frameworks:
        policies = architecture.get("policies", {})
        if isinstance(policies, dict):
            frameworks = list(policies.keys())[:3]
    framework_str = ", ".join(frameworks) if frameworks else "Azure CIS Benchmark"
    return ADRRecord(
        id=f"ADR-{adr_number:03d}",
        title="Compliance Frameworks",
        status="Accepted",
        context=(
            "The organization operates in a regulated environment and must demonstrate "
            "compliance with industry standards and regulatory requirements. Azure Policy "
            "and Microsoft Defender for Cloud provide built-in compliance monitoring."
        ),
        decision=(
            f"Adopt the following compliance frameworks: {framework_str}. "
            "Azure Policy initiative assignments enforce these frameworks at the "
            "management group level. Continuous compliance monitoring is enabled "
            "through Microsoft Defender for Cloud regulatory compliance dashboard."
        ),
        consequences=(
            "Non-compliant resources are flagged automatically and may be denied "
            "deployment depending on policy effect (Deny vs Audit). Teams must remediate "
            "compliance findings within defined SLAs. Adding new frameworks requires "
            "policy initiative updates and potential resource reconfiguration."
        ),
        category="compliance",
        created_at=_today(),
    )


def _generate_region_adr(architecture: dict, adr_number: int) -> ADRRecord:
    """Generate ADR for region selection decision."""
    net_info = _extract_network_info(architecture)
    primary = net_info["primary_region"]
    secondary = net_info.get("secondary_region") or "westus2"
    return ADRRecord(
        id=f"ADR-{adr_number:03d}",
        title="Region Selection",
        status="Accepted",
        context=(
            "Choosing Azure regions impacts latency, data residency compliance, "
            "service availability, and disaster recovery capabilities. The landing "
            "zone must support business continuity requirements while meeting "
            "data sovereignty regulations."
        ),
        decision=(
            f"Deploy the primary landing zone in {primary} with {secondary} as the "
            "paired disaster recovery region. This pairing leverages Azure's built-in "
            "regional redundancy and ensures data residency compliance. Critical "
            "workloads use zone-redundant deployments within the primary region."
        ),
        consequences=(
            "Cross-region replication increases storage and egress costs. Failover "
            "to the secondary region requires tested runbooks and may involve brief "
            "service interruption. Some Azure services may have feature availability "
            "differences between regions."
        ),
        category="networking",
        created_at=_today(),
    )


def _generate_subscription_adr(architecture: dict, adr_number: int) -> ADRRecord:
    """Generate ADR for subscription topology decision."""
    sub_info = _extract_subscription_info(architecture)
    sub_list = ", ".join(sub_info["names"][:5]) if sub_info["names"] else "production, development"
    return ADRRecord(
        id=f"ADR-{adr_number:03d}",
        title="Subscription Topology",
        status="Accepted",
        context=(
            "Azure subscriptions serve as units of management, billing, and scale. "
            "The subscription topology must balance workload isolation, cost tracking, "
            "and administrative overhead while supporting the organization's growth."
        ),
        decision=(
            f"Organize subscriptions into {sub_info['count'] or 2} dedicated "
            f"subscriptions: {sub_list}. Each subscription maps to a specific "
            "environment or workload tier, enabling fine-grained RBAC, cost "
            "management, and policy enforcement per subscription."
        ),
        consequences=(
            "Each subscription has its own resource quotas and billing scope, "
            "simplifying cost attribution. Cross-subscription communication requires "
            "VNet peering or Private Link. Platform teams must manage subscription "
            "vending and decommissioning processes."
        ),
        category="governance",
        created_at=_today(),
    )


def generate_adrs(
    architecture: dict,
    answers: dict,
    use_ai: bool = False,
) -> list[ADRRecord]:
    """Generate ADRs from architecture data and questionnaire answers.

    Args:
        architecture: The generated landing zone architecture.
        answers: Questionnaire answers that informed the architecture.
        use_ai: Whether to enhance ADRs with AI-generated content.

    Returns:
        A list of ADRRecord instances, one per major decision area.
    """
    adrs = [
        _generate_mg_adr(architecture, 1),
        _generate_network_adr(architecture, 2),
        _generate_identity_adr(architecture, answers, 3),
        _generate_compliance_adr(architecture, answers, 4),
        _generate_region_adr(architecture, 5),
        _generate_subscription_adr(architecture, 6),
    ]

    if use_ai:
        try:
            from app.services.ai_foundry import ai_client

            if ai_client.is_configured:
                logger.info("Enhancing ADRs with AI")
                # AI enhancement would happen here in production
                # For now, log and return template ADRs
            else:
                logger.info("AI not configured — using template ADRs")
        except Exception as e:
            logger.warning("AI enhancement failed, falling back to templates: %s", e)

    return adrs


def _format_single_adr(adr: ADRRecord) -> str:
    """Format a single ADR as Markdown."""
    return (
        f"# {adr.id}: {adr.title}\n"
        f"\n"
        f"**Status:** {adr.status}\n"
        f"**Date:** {adr.created_at}\n"
        f"**Category:** {adr.category}\n"
        f"\n"
        f"## Context\n"
        f"\n"
        f"{adr.context}\n"
        f"\n"
        f"## Decision\n"
        f"\n"
        f"{adr.decision}\n"
        f"\n"
        f"## Consequences\n"
        f"\n"
        f"{adr.consequences}\n"
    )


def export_adrs(adrs: list[ADRRecord], format: str = "combined") -> str:
    """Export ADRs as Markdown.

    Args:
        adrs: List of ADR records to export.
        format: Export format — "combined" for single document,
                "individual" for first ADR only.

    Returns:
        Markdown string of the exported ADRs.
    """
    if not adrs:
        return "# Architecture Decision Records\n\nNo ADRs generated yet.\n"

    if format == "individual":
        return _format_single_adr(adrs[0])

    sections = [_format_single_adr(adr) for adr in adrs]
    header = "# Architecture Decision Records\n\n"
    return header + "\n---\n\n".join(sections)

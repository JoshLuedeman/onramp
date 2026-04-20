"""Architecture Comparison Service.

Generates multiple architecture variants (cost-optimised, balanced,
enterprise-grade) from the same set of questionnaire answers so users can
compare them side-by-side.
"""

from __future__ import annotations

import logging
from copy import deepcopy

from app.schemas.architecture_compare import ArchitectureVariant, ComparisonResult
from app.services.archetypes import get_archetype_for_answers

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_resources(architecture: dict) -> int:
    """Estimate the number of Azure resources in an architecture."""
    count = 0
    # Subscriptions
    subs = architecture.get("subscriptions", [])
    count += len(subs)
    # Network spokes
    topo = architecture.get("network_topology", {})
    count += len(topo.get("spokes", []))
    # Hub subnets
    hub = topo.get("hub", {})
    count += len(hub.get("subnets", []))
    # Governance policies
    gov = architecture.get("governance", {})
    count += len(gov.get("policies", []))
    # Security services (boolean flags)
    sec = architecture.get("security", {})
    for val in sec.values():
        if isinstance(val, bool) and val:
            count += 1
        elif isinstance(val, list):
            count += len(val)
    # Compliance frameworks
    count += len(architecture.get("compliance_frameworks", []))
    # Management components
    mgmt = architecture.get("management", {})
    for val in mgmt.values():
        if isinstance(val, bool) and val:
            count += 1
        elif isinstance(val, dict):
            count += 1
    return count


def _compute_compliance_scores(architecture: dict) -> dict[str, float]:
    """Return per-framework compliance coverage scores."""
    frameworks = architecture.get("compliance_frameworks", [])
    scores: dict[str, float] = {}
    for fw in frameworks:
        if isinstance(fw, dict):
            name = fw.get("name", "unknown")
            scores[name] = float(fw.get("coverage_percent", 0))
    return scores


def _derive_cost_range(
    architecture: dict,
    multiplier_low: float = 0.85,
    multiplier_high: float = 1.15,
) -> tuple[float, float]:
    """Compute min/max monthly cost from the base estimate."""
    base = float(architecture.get("estimated_monthly_cost_usd", 0))
    return round(base * multiplier_low, 2), round(base * multiplier_high, 2)


def _derive_complexity(architecture: dict) -> str:
    """Determine complexity rating from architecture shape."""
    subs = len(architecture.get("subscriptions", []))
    sec = architecture.get("security", {})
    has_sentinel = sec.get("sentinel", False)
    has_ddos = sec.get("ddos_protection", False)
    if subs <= 4 and not has_sentinel and not has_ddos:
        return "simple"
    if subs >= 8 or (has_sentinel and has_ddos):
        return "complex"
    return "moderate"


# ---------------------------------------------------------------------------
# Cost-optimised variant tweaks
# ---------------------------------------------------------------------------

def _make_cost_optimised(architecture: dict) -> dict:
    """Tweak an architecture to be as cheap as possible."""
    arch = deepcopy(architecture)
    arch["name"] = "Cost-Optimised"
    arch["description"] = (
        "Minimal resources with shared services and smaller SKUs. "
        "Ideal for proof-of-concept or budget-constrained environments."
    )
    # Reduce subscriptions – keep only platform + one workload + sandbox
    subs = arch.get("subscriptions", [])
    if len(subs) > 3:
        arch["subscriptions"] = subs[:3]
    # Reduce budgets by 40 %
    for sub in arch["subscriptions"]:
        if isinstance(sub, dict):
            sub["budget_usd"] = int(sub.get("budget_usd", 0) * 0.6)
    # Disable premium security
    sec = arch.get("security", {})
    sec["sentinel"] = False
    sec["ddos_protection"] = False
    sec.pop("azure_firewall_premium", None)
    arch["security"] = sec
    # Shorten log retention
    mgmt = arch.get("management", {})
    la = mgmt.get("log_analytics", {})
    if isinstance(la, dict):
        la["retention_days"] = 30
    mgmt["backup"] = {"enabled": True, "geo_redundant": False}
    arch["management"] = mgmt
    # Reduce cost estimate
    base = float(arch.get("estimated_monthly_cost_usd", 0))
    arch["estimated_monthly_cost_usd"] = int(base * 0.45)
    return arch


# ---------------------------------------------------------------------------
# Enterprise-grade variant tweaks
# ---------------------------------------------------------------------------

def _make_enterprise_grade(architecture: dict) -> dict:
    """Elevate architecture to full enterprise grade."""
    arch = deepcopy(architecture)
    arch["name"] = "Enterprise-Grade"
    arch["description"] = (
        "Maximum redundancy and isolation with premium SKUs. "
        "Designed for regulated industries with strict compliance requirements."
    )
    # Add extra subscriptions if < 8
    subs = arch.get("subscriptions", [])
    extras = [
        {"name": "sub-connectivity-dr", "purpose": "DR hub networking",
         "management_group": "connectivity", "budget_usd": 1500},
        {"name": "sub-confidential-prod", "purpose": "Regulated workloads",
         "management_group": "corp", "budget_usd": 3000},
        {"name": "sub-corp-nonprod", "purpose": "Non-production workloads",
         "management_group": "corp", "budget_usd": 1500},
    ]
    existing_names = {s.get("name") for s in subs if isinstance(s, dict)}
    for extra in extras:
        if extra["name"] not in existing_names and len(subs) < 10:
            subs.append(extra)
    arch["subscriptions"] = subs
    # Increase budgets by 80 %
    for sub in arch["subscriptions"]:
        if isinstance(sub, dict):
            sub["budget_usd"] = int(sub.get("budget_usd", 0) * 1.8)
    # Enable all premium security
    sec = arch.get("security", {})
    sec["sentinel"] = True
    sec["ddos_protection"] = True
    sec["azure_firewall"] = True
    sec["azure_firewall_premium"] = True
    sec["waf"] = True
    sec["private_endpoints_required"] = True
    arch["security"] = sec
    # Enable PIM + access reviews
    identity = arch.get("identity", {})
    identity["pim_enabled"] = True
    identity["access_reviews"] = True
    identity["break_glass_accounts"] = 2
    arch["identity"] = identity
    # Extended log retention and geo-redundant backup
    mgmt = arch.get("management", {})
    la = mgmt.get("log_analytics", {})
    if isinstance(la, dict):
        la["retention_days"] = 365
    mgmt["backup"] = {"enabled": True, "geo_redundant": True, "cross_region_restore": True}
    arch["management"] = mgmt
    # Add secondary region in network
    topo = arch.get("network_topology", {})
    if "secondary_region" not in topo:
        topo["secondary_region"] = "westus2"
    topo["dns"] = {"type": "hybrid_dns", "private_dns_zones": True, "dns_resolver": True}
    arch["network_topology"] = topo
    # Increase cost estimate
    base = float(arch.get("estimated_monthly_cost_usd", 0))
    arch["estimated_monthly_cost_usd"] = int(base * 2.5)
    return arch


# ---------------------------------------------------------------------------
# ArchitectureComparator
# ---------------------------------------------------------------------------

class ArchitectureComparator:
    """Generates and compares architecture variants."""

    _instance: ArchitectureComparator | None = None

    def __new__(cls) -> ArchitectureComparator:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # -- public API ----------------------------------------------------------

    def generate_variants(
        self,
        answers: dict,
        options: dict | None = None,
    ) -> list[ArchitectureVariant]:
        """Generate three architecture variants from the same answers.

        Returns [cost-optimised, balanced, enterprise-grade].
        """
        base = get_archetype_for_answers(answers)

        cost_arch = _make_cost_optimised(base)
        balanced_arch = deepcopy(base)
        balanced_arch["name"] = "Balanced"
        balanced_arch["description"] = (
            "The recommended default — a pragmatic balance of cost, "
            "security, and operational complexity."
        )
        enterprise_arch = _make_enterprise_grade(base)

        variants: list[ArchitectureVariant] = []
        for arch_dict in [cost_arch, balanced_arch, enterprise_arch]:
            cost_min, cost_max = _derive_cost_range(arch_dict)
            variants.append(ArchitectureVariant(
                name=arch_dict.get("name", "Unknown"),
                description=arch_dict.get("description", ""),
                architecture=arch_dict,
                resource_count=_count_resources(arch_dict),
                estimated_monthly_cost_min=cost_min,
                estimated_monthly_cost_max=cost_max,
                complexity=_derive_complexity(arch_dict),
                compliance_scores=_compute_compliance_scores(arch_dict),
            ))
        return variants

    def compare_variants(
        self,
        variants: list[ArchitectureVariant],
    ) -> ComparisonResult:
        """Build a ``ComparisonResult`` with a recommended index."""
        # Recommended index defaults to the balanced variant (index 1)
        recommended = 1
        if len(variants) < 2:
            recommended = 0

        tradeoff = self.generate_tradeoff_analysis(variants)
        return ComparisonResult(
            variants=variants,
            tradeoff_analysis=tradeoff,
            recommended_index=recommended,
        )

    def generate_tradeoff_analysis(
        self,
        variants: list[ArchitectureVariant],
    ) -> str:
        """Return an AI-generated or mock trade-off analysis.

        In dev mode (AI not configured) a deterministic mock string is
        returned so the feature is fully usable without Azure credentials.
        """
        from app.services.ai_foundry import ai_client as _ai

        if not _ai.is_configured:
            return self._mock_tradeoff_analysis(variants)

        # Real AI path — build prompt and call AI client
        try:
            from app.services.ai_foundry import ai_client

            variant_summaries = "\n".join(
                f"- **{v.name}**: {v.resource_count} resources, "
                f"${v.estimated_monthly_cost_min:,.0f}–${v.estimated_monthly_cost_max:,.0f}/mo, "
                f"complexity={v.complexity}"
                for v in variants
            )
            system_prompt = (
                "You are an Azure cloud architect. Given the following architecture "
                "variants, provide a concise trade-off analysis (3-5 sentences) "
                "highlighting the key differences in cost, security, and operational "
                "complexity. Recommend the balanced option for most organisations."
            )
            user_prompt = f"Architecture variants:\n{variant_summaries}"
            result = ai_client.generate_completion(
                system_prompt, user_prompt, temperature=0.4, max_tokens=512,
            )
            return result
        except Exception as exc:
            logger.warning("AI tradeoff analysis failed, falling back to mock: %s", exc)
            return self._mock_tradeoff_analysis(variants)

    # -- private helpers -----------------------------------------------------

    @staticmethod
    def _mock_tradeoff_analysis(variants: list[ArchitectureVariant]) -> str:
        if not variants:
            return "No variants provided for analysis."
        names = [v.name for v in variants]
        costs = [
            f"${v.estimated_monthly_cost_min:,.0f}–${v.estimated_monthly_cost_max:,.0f}"
            for v in variants
        ]
        lines = [
            f"The {names[0]} variant ({costs[0]}/mo) minimises spend by reducing "
            "redundancy and using shared services, but sacrifices advanced threat "
            "detection and geo-redundant backups.",
        ]
        if len(variants) > 1:
            lines.append(
                f"The {names[1]} variant ({costs[1]}/mo) is the recommended default — "
                "it provides a solid security posture with manageable operational overhead."
            )
        if len(variants) > 2:
            lines.append(
                f"The {names[2]} variant ({costs[2]}/mo) maximises isolation, premium "
                "SKUs, and compliance coverage at significantly higher cost — best "
                "suited for regulated industries."
            )
        lines.append(
            "For most organisations, the Balanced variant offers the best trade-off "
            "between cost, security, and complexity."
        )
        return " ".join(lines)


# Singleton instance
architecture_comparator = ArchitectureComparator()

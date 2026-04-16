"""Security posture advisor — rule-based + AI-enhanced analysis.

Analyses Azure landing zone architectures for security gaps, calculates a
weighted security score, and generates remediation guidance.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.schemas.security import (
    RemediationStep,
    SecurityAnalysisResult,
    SecurityCheck,
    SecurityFinding,
    Severity,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Severity weights used for score calculation
# ---------------------------------------------------------------------------
_SEVERITY_WEIGHTS: dict[Severity, int] = {
    Severity.critical: 25,
    Severity.high: 15,
    Severity.medium: 8,
    Severity.low: 3,
}

# ---------------------------------------------------------------------------
# Rule registry: each rule is (id, name, description, category, severity, check_fn)
# ---------------------------------------------------------------------------
RuleCheckFn = Any  # callable[[dict], SecurityFinding | None]


def _get(d: dict, *keys: str, default: Any = None) -> Any:
    """Safely traverse nested dicts."""
    current = d
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k, default)
        else:
            return default
    return current


# ── Individual rule checks ─────────────────────────────────────────────────


def _check_missing_nsg(arch: dict) -> SecurityFinding | None:
    """Rule 1 — Missing NSG rules on subnets."""
    network = _get(arch, "network_topology", default={})
    spokes = network.get("spokes", [])
    hub = network.get("hub", {})

    # Check hub subnets
    has_nsg_issue = False
    resource = "network_topology"

    for subnet in hub.get("subnets", []):
        if not subnet.get("nsg"):
            has_nsg_issue = True
            resource = f"hub/subnet/{subnet.get('name', 'unknown')}"
            break

    if not has_nsg_issue:
        for spoke in spokes:
            for subnet in spoke.get("subnets", []):
                if not subnet.get("nsg"):
                    has_nsg_issue = True
                    resource = f"spoke/{spoke.get('name', 'unknown')}/subnet/{subnet.get('name', 'unknown')}"
                    break
            if has_nsg_issue:
                break

    # Also flag if there are no NSG references at all in network config
    if not has_nsg_issue:
        nsg_refs = str(network).lower()
        if "nsg" not in nsg_refs and "network_security_group" not in nsg_refs and spokes:
            has_nsg_issue = True
            resource = "network_topology"

    if has_nsg_issue:
        return SecurityFinding(
            id=f"SEC-NSG-{uuid.uuid4().hex[:8]}",
            severity=Severity.high,
            category="networking",
            resource=resource,
            finding="Subnets without Network Security Groups (NSGs) allow unrestricted traffic flow.",
            remediation="Attach NSGs with deny-all inbound default rules to every subnet.",
            auto_fixable=True,
        )
    return None


def _check_public_endpoints_without_waf(arch: dict) -> SecurityFinding | None:
    """Rule 2 — Public endpoints without WAF/Front Door."""
    security = _get(arch, "security", default={})
    network = _get(arch, "network_topology", default={})

    has_waf = security.get("waf", False) or network.get("waf", False)
    has_front_door = security.get("front_door", False) or network.get("front_door", False)

    # Check if there are public-facing resources
    has_public = False
    spokes = network.get("spokes", [])
    for spoke in spokes:
        if spoke.get("public_ip") or spoke.get("public_endpoints"):
            has_public = True
            break

    if not has_public:
        # Check subscriptions for web/app workloads
        for sub in arch.get("subscriptions", []):
            purpose = (sub.get("purpose") or "").lower()
            if any(kw in purpose for kw in ["web", "app", "api", "public"]):
                has_public = True
                break

    if has_public and not has_waf and not has_front_door:
        return SecurityFinding(
            id=f"SEC-WAF-{uuid.uuid4().hex[:8]}",
            severity=Severity.high,
            category="networking",
            resource="public_endpoints",
            finding="Public-facing endpoints detected without WAF or Azure Front Door protection.",
            remediation="Deploy Azure WAF or Azure Front Door in front of all public endpoints.",
            auto_fixable=True,
        )
    return None


def _check_storage_encryption(arch: dict) -> SecurityFinding | None:
    """Rule 3 — Storage without encryption at rest."""
    # Check for explicit encryption settings
    management = _get(arch, "management", default={})
    security = _get(arch, "security", default={})

    storage_refs = []
    for sub in arch.get("subscriptions", []):
        purpose = (sub.get("purpose") or "").lower()
        if "storage" in purpose or "data" in purpose or "backup" in purpose:
            storage_refs.append(sub.get("name", "unknown"))

    if not storage_refs:
        return None

    encryption_mentioned = (
        security.get("encryption_at_rest", False)
        or management.get("encryption", False)
        or _get(arch, "governance", "policies", default=[])
        and any(
            "encrypt" in (p.get("name", "") + p.get("description", "")).lower()
            for p in _get(arch, "governance", "policies", default=[])
        )
    )

    if not encryption_mentioned:
        return SecurityFinding(
            id=f"SEC-ENC-{uuid.uuid4().hex[:8]}",
            severity=Severity.high,
            category="data_protection",
            resource=f"storage/{storage_refs[0]}",
            finding="Storage accounts may not have encryption at rest explicitly configured.",
            remediation="Enable Azure Storage Service Encryption with Microsoft-managed or customer-managed keys.",
            auto_fixable=True,
        )
    return None


def _check_sql_tde(arch: dict) -> SecurityFinding | None:
    """Rule 4 — SQL without Transparent Data Encryption (TDE)."""
    has_sql = False
    for sub in arch.get("subscriptions", []):
        purpose = (sub.get("purpose") or "").lower()
        if any(kw in purpose for kw in ["sql", "database", "data"]):
            has_sql = True
            break

    if not has_sql:
        return None

    security = _get(arch, "security", default={})
    policies = _get(arch, "governance", "policies", default=[])

    tde_enabled = security.get("sql_tde", False) or any(
        "tde" in (p.get("name", "") + p.get("description", "")).lower()
        or "transparent data encryption" in (p.get("name", "") + p.get("description", "")).lower()
        for p in policies
    )

    if not tde_enabled:
        return SecurityFinding(
            id=f"SEC-TDE-{uuid.uuid4().hex[:8]}",
            severity=Severity.high,
            category="data_protection",
            resource="sql_databases",
            finding="SQL databases without Transparent Data Encryption (TDE) leave data at rest unprotected.",
            remediation="Enable TDE on all Azure SQL databases using service-managed or customer-managed keys.",
            auto_fixable=True,
        )
    return None


def _check_defender_plans(arch: dict) -> SecurityFinding | None:
    """Rule 5 — Missing Defender for Cloud plans."""
    security = _get(arch, "security", default={})
    has_defender = security.get("defender_for_cloud", False)
    defender_plans = security.get("defender_plans", [])

    if not has_defender and not defender_plans:
        return SecurityFinding(
            id=f"SEC-DEF-{uuid.uuid4().hex[:8]}",
            severity=Severity.critical,
            category="threat_protection",
            resource="subscription",
            finding="Microsoft Defender for Cloud is not enabled — no threat detection or security recommendations.",
            remediation="Enable Defender for Cloud with plans for Servers, App Service, SQL, Storage, and Key Vault.",
            auto_fixable=True,
        )
    return None


def _check_overly_permissive_rbac(arch: dict) -> SecurityFinding | None:
    """Rule 6 — Owner role at subscription scope."""
    identity = _get(arch, "identity", default={})
    rbac_model = (identity.get("rbac_model") or "").lower()

    policies = _get(arch, "governance", "policies", default=[])
    has_least_privilege = any(
        "least privilege" in (p.get("description", "") + p.get("name", "")).lower()
        for p in policies
    )

    # Flag if no RBAC model specified or too broad
    if rbac_model in ("", "owner", "broad") and not has_least_privilege:
        return SecurityFinding(
            id=f"SEC-RBAC-{uuid.uuid4().hex[:8]}",
            severity=Severity.critical,
            category="identity",
            resource="subscription_rbac",
            finding="Overly permissive RBAC — Owner role at subscription scope grants excessive privileges.",
            remediation=(
                "Apply least-privilege RBAC: use built-in roles "
                "(Contributor, Reader) and custom roles scoped to resource groups."
            ),
            auto_fixable=False,
        )
    return None


def _check_ddos_protection(arch: dict) -> SecurityFinding | None:
    """Rule 7 — Missing DDoS protection on public-facing resources."""
    security = _get(arch, "security", default={})
    network = _get(arch, "network_topology", default={})

    ddos_enabled = security.get("ddos_protection", False) or network.get(
        "ddos_protection", False
    )

    if not ddos_enabled:
        return SecurityFinding(
            id=f"SEC-DDOS-{uuid.uuid4().hex[:8]}",
            severity=Severity.medium,
            category="networking",
            resource="virtual_network",
            finding="DDoS Protection Standard is not enabled on virtual networks with public endpoints.",
            remediation="Enable Azure DDoS Protection Standard on VNets hosting public-facing resources.",
            auto_fixable=True,
        )
    return None


def _check_private_endpoints(arch: dict) -> SecurityFinding | None:
    """Rule 8 — PaaS services without private endpoints."""
    network = _get(arch, "network_topology", default={})
    security = _get(arch, "security", default={})

    has_private_endpoints = (
        network.get("private_endpoints", False)
        or security.get("private_endpoints", False)
        or "private_endpoint" in str(network).lower()
        or "private_link" in str(network).lower()
    )

    # Check if PaaS services exist
    has_paas = False
    for sub in arch.get("subscriptions", []):
        purpose = (sub.get("purpose") or "").lower()
        if any(kw in purpose for kw in ["app", "sql", "storage", "key vault", "web"]):
            has_paas = True
            break

    if has_paas and not has_private_endpoints:
        return SecurityFinding(
            id=f"SEC-PEP-{uuid.uuid4().hex[:8]}",
            severity=Severity.medium,
            category="networking",
            resource="paas_services",
            finding="PaaS services are accessible over public internet without private endpoints.",
            remediation=(
                "Configure Azure Private Endpoints for all PaaS services "
                "(SQL, Storage, Key Vault, App Service)."
            ),
            auto_fixable=True,
        )
    return None


def _check_diagnostic_settings(arch: dict) -> SecurityFinding | None:
    """Rule 9 — Missing diagnostic settings / logging."""
    management = _get(arch, "management", default={})

    has_logging = (
        management.get("log_analytics")
        or management.get("monitoring")
        or management.get("diagnostic_settings")
    )

    if not has_logging:
        return SecurityFinding(
            id=f"SEC-LOG-{uuid.uuid4().hex[:8]}",
            severity=Severity.medium,
            category="monitoring",
            resource="management",
            finding="No diagnostic settings or Log Analytics workspace configured — security events are not collected.",
            remediation="Deploy a central Log Analytics workspace and enable diagnostic settings on all resources.",
            auto_fixable=True,
        )
    return None


def _check_key_vault(arch: dict) -> SecurityFinding | None:
    """Rule 10 — Missing Key Vault for secret management."""
    security = _get(arch, "security", default={})
    has_key_vault = security.get("key_vault_per_subscription", False) or security.get(
        "key_vault", False
    )

    # Also check if mentioned in subscriptions or policies
    if not has_key_vault:
        for sub in arch.get("subscriptions", []):
            if "key vault" in (sub.get("purpose") or "").lower():
                has_key_vault = True
                break

    if not has_key_vault:
        policies = _get(arch, "governance", "policies", default=[])
        has_key_vault = any(
            "key vault" in (p.get("name", "") + p.get("description", "")).lower()
            for p in policies
        )

    if not has_key_vault:
        return SecurityFinding(
            id=f"SEC-KV-{uuid.uuid4().hex[:8]}",
            severity=Severity.high,
            category="data_protection",
            resource="secrets_management",
            finding="No Azure Key Vault configured — secrets, keys, and certificates lack centralized management.",
            remediation="Deploy Azure Key Vault in each subscription for secret, key, and certificate management.",
            auto_fixable=True,
        )
    return None


# ── Rule registry ──────────────────────────────────────────────────────────

_RULES: list[tuple[str, str, str, str, Severity, RuleCheckFn]] = [
    (
        "nsg-check", "Missing NSG Rules",
        "Checks subnets for attached NSGs",
        "networking", Severity.high, _check_missing_nsg,
    ),
    (
        "waf-check", "Public Endpoints Without WAF",
        "Checks public endpoints for WAF/Front Door",
        "networking", Severity.high, _check_public_endpoints_without_waf,
    ),
    (
        "storage-encryption", "Storage Encryption",
        "Checks storage encryption at rest",
        "data_protection", Severity.high, _check_storage_encryption,
    ),
    (
        "sql-tde", "SQL TDE",
        "Checks SQL databases for TDE",
        "data_protection", Severity.high, _check_sql_tde,
    ),
    (
        "defender-plans", "Defender for Cloud",
        "Checks Defender for Cloud enablement",
        "threat_protection", Severity.critical, _check_defender_plans,
    ),
    (
        "rbac-permissions", "Overly Permissive RBAC",
        "Checks for overly broad RBAC assignments",
        "identity", Severity.critical, _check_overly_permissive_rbac,
    ),
    (
        "ddos-protection", "DDoS Protection",
        "Checks DDoS Protection Standard",
        "networking", Severity.medium, _check_ddos_protection,
    ),
    (
        "private-endpoints", "Private Endpoints",
        "Checks PaaS private endpoint usage",
        "networking", Severity.medium, _check_private_endpoints,
    ),
    (
        "diagnostic-settings", "Diagnostic Settings",
        "Checks logging and monitoring",
        "monitoring", Severity.medium, _check_diagnostic_settings,
    ),
    (
        "key-vault", "Key Vault",
        "Checks Key Vault for secret management",
        "data_protection", Severity.high, _check_key_vault,
    ),
]


# ── Remediation mapping ───────────────────────────────────────────────────

_REMEDIATION_MAP: dict[str, dict] = {
    "networking": {
        "description": "Apply network security controls",
        "architecture_changes": {
            "security.waf": True,
            "security.ddos_protection": True,
            "network_topology.private_endpoints": True,
        },
    },
    "data_protection": {
        "description": "Enable data protection controls",
        "architecture_changes": {
            "security.encryption_at_rest": True,
            "security.sql_tde": True,
            "security.key_vault_per_subscription": True,
        },
    },
    "threat_protection": {
        "description": "Enable threat detection and response",
        "architecture_changes": {
            "security.defender_for_cloud": True,
            "security.defender_plans": [
                "Servers",
                "AppService",
                "SqlServers",
                "Storage",
                "KeyVaults",
            ],
        },
    },
    "identity": {
        "description": "Harden identity and access controls",
        "architecture_changes": {
            "identity.rbac_model": "least-privilege",
            "identity.pim_enabled": True,
        },
    },
    "monitoring": {
        "description": "Enable logging and monitoring",
        "architecture_changes": {
            "management.log_analytics": {"enabled": True},
            "management.diagnostic_settings": True,
        },
    },
}


# ── SecurityAnalyzer class ─────────────────────────────────────────────────


class SecurityAnalyzer:
    """Singleton security posture analyzer with rule-based and AI-enhanced checks."""

    _instance: SecurityAnalyzer | None = None

    def __new__(cls) -> SecurityAnalyzer:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ── Public API ─────────────────────────────────────────────────────────

    def analyze(
        self, architecture: dict, use_ai: bool = False
    ) -> SecurityAnalysisResult:
        """Run security analysis on an architecture definition.

        Parameters
        ----------
        architecture:
            The Azure landing-zone architecture dict.
        use_ai:
            When *True*, supplements rule-based checks with AI-enhanced findings.
        """
        findings = self._run_rule_checks(architecture)

        if use_ai:
            ai_findings = self._run_ai_analysis(architecture)
            findings.extend(ai_findings)

        score = self.calculate_security_score(findings)

        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in findings:
            severity_counts[f.severity.value] += 1

        summary = (
            f"Security score: {score}/100. "
            f"Found {len(findings)} issue(s): "
            f"{severity_counts['critical']} critical, "
            f"{severity_counts['high']} high, "
            f"{severity_counts['medium']} medium, "
            f"{severity_counts['low']} low."
        )

        return SecurityAnalysisResult(
            score=score,
            findings=findings,
            summary=summary,
            analyzed_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def calculate_security_score(findings: list[SecurityFinding]) -> int:
        """Calculate a 0-100 security score weighted by severity.

        Starts at 100 and subtracts per finding:
        Critical = -25, High = -15, Medium = -8, Low = -3.
        """
        score = 100
        for f in findings:
            score -= _SEVERITY_WEIGHTS.get(f.severity, 0)
        return max(0, min(100, score))

    @staticmethod
    def get_remediation(finding: SecurityFinding) -> RemediationStep:
        """Generate a remediation step for the given finding."""
        category_remediation = _REMEDIATION_MAP.get(finding.category, {})
        return RemediationStep(
            finding_id=finding.id,
            description=category_remediation.get(
                "description", finding.remediation
            ),
            architecture_changes=category_remediation.get(
                "architecture_changes", {}
            ),
        )

    @staticmethod
    def get_available_checks() -> list[SecurityCheck]:
        """Return the list of available rule-based security checks."""
        return [
            SecurityCheck(
                id=rule_id,
                name=name,
                description=desc,
                category=cat,
                severity=sev,
            )
            for rule_id, name, desc, cat, sev, _fn in _RULES
        ]

    def apply_auto_fix(
        self, finding: SecurityFinding, architecture: dict
    ) -> dict:
        """Apply an auto-fix to the architecture for a given finding.

        Returns a *new* architecture dict with the fix applied.
        Only works for findings where ``auto_fixable`` is ``True``.
        """
        if not finding.auto_fixable:
            return architecture

        arch = {**architecture}  # shallow copy
        remediation = _REMEDIATION_MAP.get(finding.category, {})
        changes = remediation.get("architecture_changes", {})

        for dotted_key, value in changes.items():
            parts = dotted_key.split(".")
            target = arch
            for part in parts[:-1]:
                if part not in target or not isinstance(target[part], dict):
                    target[part] = {}
                target = target[part]
            target[parts[-1]] = value

        return arch

    # ── Internal helpers ───────────────────────────────────────────────────

    @staticmethod
    def _run_rule_checks(architecture: dict) -> list[SecurityFinding]:
        """Execute all registered rule checks against the architecture."""
        findings: list[SecurityFinding] = []
        for _rule_id, _name, _desc, _cat, _sev, check_fn in _RULES:
            try:
                result = check_fn(architecture)
                if result is not None:
                    findings.append(result)
            except Exception:
                logger.exception("Rule check %s failed", _rule_id)
        return findings

    @staticmethod
    def _run_ai_analysis(architecture: dict) -> list[SecurityFinding]:
        """Run AI-enhanced analysis (dev-mode returns mock findings)."""
        try:
            from app.config import settings

            if settings.is_dev_mode:
                return _mock_ai_findings()

            from app.services.ai_foundry import AIFoundryClient
            from app.services.prompts import (
                SECURITY_ANALYSIS_SYSTEM_PROMPT,
                SECURITY_ANALYSIS_USER_TEMPLATE,
            )

            client = AIFoundryClient()
            import json

            user_prompt = SECURITY_ANALYSIS_USER_TEMPLATE.format(
                architecture_json=json.dumps(architecture, indent=2)
            )
            raw = client.generate_completion(
                system_prompt=SECURITY_ANALYSIS_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=4096,
            )

            data = json.loads(raw)
            findings: list[SecurityFinding] = []
            for item in data.get("findings", []):
                findings.append(
                    SecurityFinding(
                        id=f"SEC-AI-{uuid.uuid4().hex[:8]}",
                        severity=Severity(item.get("severity", "medium")),
                        category=item.get("category", "general"),
                        resource=item.get("resource", "architecture"),
                        finding=item.get("finding", ""),
                        remediation=item.get("remediation", ""),
                        auto_fixable=False,
                    )
                )
            return findings
        except Exception:
            logger.exception("AI-enhanced analysis failed — returning mock findings")
            return _mock_ai_findings()


def _mock_ai_findings() -> list[SecurityFinding]:
    """Return enhanced mock findings for dev/fallback mode."""
    return [
        SecurityFinding(
            id=f"SEC-AI-{uuid.uuid4().hex[:8]}",
            severity=Severity.medium,
            category="networking",
            resource="architecture",
            finding="Consider implementing Azure Firewall Premium for TLS inspection on east-west traffic.",
            remediation=(
                "Deploy Azure Firewall Premium with IDPS and TLS inspection enabled. "
                "Ref: Microsoft Well-Architected Framework — Security pillar."
            ),
            auto_fixable=False,
        ),
        SecurityFinding(
            id=f"SEC-AI-{uuid.uuid4().hex[:8]}",
            severity=Severity.low,
            category="identity",
            resource="entra_id",
            finding="Conditional Access policies should enforce compliant device requirements for admin access.",
            remediation=(
                "Create Conditional Access policies requiring compliant/hybrid-joined devices for privileged roles. "
                "Ref: Microsoft Zero Trust deployment guide."
            ),
            auto_fixable=False,
        ),
    ]


# Module-level singleton instance
security_analyzer = SecurityAnalyzer()

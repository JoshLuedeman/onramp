"""Sovereign compliance frameworks for Azure sovereign & specialized clouds."""

import logging

logger = logging.getLogger(__name__)

# ── Framework Data ───────────────────────────────────────────────────────────

SOVEREIGN_FRAMEWORKS: list[dict] = [
    {
        "short_name": "FedRAMP_High",
        "name": "FedRAMP High",
        "description": (
            "Federal Risk and Authorization Management Program — High baseline"
            " for US Government workloads requiring the strictest security controls."
        ),
        "version": "Rev 5",
        "cloud_environments": ["government"],
        "control_families": [
            {
                "id": "AC",
                "name": "Access Control",
                "description": "Policies for managing access to systems and data.",
                "control_count": 25,
            },
            {
                "id": "AU",
                "name": "Audit and Accountability",
                "description": "Requirements for audit logging and accountability.",
                "control_count": 16,
            },
            {
                "id": "CA",
                "name": "Assessment, Authorization, and Monitoring",
                "description": "Security assessment and continuous monitoring.",
                "control_count": 9,
            },
            {
                "id": "CM",
                "name": "Configuration Management",
                "description": "Baseline configuration and change management.",
                "control_count": 12,
            },
            {
                "id": "CP",
                "name": "Contingency Planning",
                "description": "Business continuity and disaster recovery.",
                "control_count": 13,
            },
            {
                "id": "IA",
                "name": "Identification and Authentication",
                "description": "Identity verification and authentication controls.",
                "control_count": 12,
            },
            {
                "id": "IR",
                "name": "Incident Response",
                "description": "Incident detection, reporting, and response.",
                "control_count": 10,
            },
            {
                "id": "MA",
                "name": "Maintenance",
                "description": "System maintenance procedures and controls.",
                "control_count": 6,
            },
            {
                "id": "MP",
                "name": "Media Protection",
                "description": "Protection of digital and physical media.",
                "control_count": 8,
            },
            {
                "id": "PE",
                "name": "Physical and Environmental Protection",
                "description": "Physical security of facilities and equipment.",
                "control_count": 20,
            },
            {
                "id": "PL",
                "name": "Planning",
                "description": "Security planning and rules of behavior.",
                "control_count": 4,
            },
            {
                "id": "PS",
                "name": "Personnel Security",
                "description": "Screening and personnel termination procedures.",
                "control_count": 8,
            },
            {
                "id": "RA",
                "name": "Risk Assessment",
                "description": "Risk identification, analysis, and mitigation.",
                "control_count": 7,
            },
            {
                "id": "SA",
                "name": "System and Services Acquisition",
                "description": "Secure development and supply chain controls.",
                "control_count": 22,
            },
            {
                "id": "SC",
                "name": "System and Communications Protection",
                "description": "Network and communications security controls.",
                "control_count": 44,
            },
            {
                "id": "SI",
                "name": "System and Information Integrity",
                "description": "Flaw remediation, monitoring, and integrity.",
                "control_count": 20,
            },
            {
                "id": "PM",
                "name": "Program Management",
                "description": "Organization-wide information security program.",
                "control_count": 16,
            },
        ],
    },
    {
        "short_name": "FedRAMP_Moderate",
        "name": "FedRAMP Moderate",
        "description": (
            "Federal Risk and Authorization Management Program — Moderate baseline"
            " for US Government workloads with moderate-impact data."
        ),
        "version": "Rev 5",
        "cloud_environments": ["government"],
        "control_families": [
            {
                "id": "AC",
                "name": "Access Control",
                "description": "Policies for managing access to systems and data.",
                "control_count": 18,
            },
            {
                "id": "AU",
                "name": "Audit and Accountability",
                "description": "Requirements for audit logging and accountability.",
                "control_count": 12,
            },
            {
                "id": "CA",
                "name": "Assessment, Authorization, and Monitoring",
                "description": "Security assessment and continuous monitoring.",
                "control_count": 7,
            },
            {
                "id": "CM",
                "name": "Configuration Management",
                "description": "Baseline configuration and change management.",
                "control_count": 9,
            },
            {
                "id": "CP",
                "name": "Contingency Planning",
                "description": "Business continuity and disaster recovery.",
                "control_count": 10,
            },
            {
                "id": "IA",
                "name": "Identification and Authentication",
                "description": "Identity verification and authentication controls.",
                "control_count": 8,
            },
            {
                "id": "IR",
                "name": "Incident Response",
                "description": "Incident detection, reporting, and response.",
                "control_count": 8,
            },
            {
                "id": "SC",
                "name": "System and Communications Protection",
                "description": "Network and communications security controls.",
                "control_count": 28,
            },
            {
                "id": "SI",
                "name": "System and Information Integrity",
                "description": "Flaw remediation, monitoring, and integrity.",
                "control_count": 14,
            },
        ],
    },
    {
        "short_name": "CMMC_L2",
        "name": "CMMC Level 2",
        "description": (
            "Cybersecurity Maturity Model Certification Level 2 — Advanced"
            " cyber hygiene for defense contractors handling Controlled"
            " Unclassified Information (CUI)."
        ),
        "version": "2.0",
        "cloud_environments": ["government"],
        "control_families": [
            {
                "id": "AC",
                "name": "Access Control",
                "description": "Limit system access to authorized users.",
                "control_count": 22,
            },
            {
                "id": "AM",
                "name": "Audit and Accountability",
                "description": "Create and retain audit logs.",
                "control_count": 9,
            },
            {
                "id": "AT",
                "name": "Awareness and Training",
                "description": "Security awareness for personnel.",
                "control_count": 4,
            },
            {
                "id": "CM",
                "name": "Configuration Management",
                "description": "Establish and maintain baseline configurations.",
                "control_count": 9,
            },
            {
                "id": "IA",
                "name": "Identification and Authentication",
                "description": "Identify and authenticate users and devices.",
                "control_count": 11,
            },
            {
                "id": "IR",
                "name": "Incident Response",
                "description": "Incident handling capabilities.",
                "control_count": 3,
            },
            {
                "id": "MA",
                "name": "Maintenance",
                "description": "Perform maintenance on systems.",
                "control_count": 6,
            },
            {
                "id": "MP",
                "name": "Media Protection",
                "description": "Protect and control media.",
                "control_count": 4,
            },
            {
                "id": "PE",
                "name": "Physical Protection",
                "description": "Limit physical access to systems.",
                "control_count": 6,
            },
            {
                "id": "PS",
                "name": "Personnel Security",
                "description": "Screen individuals prior to access.",
                "control_count": 2,
            },
            {
                "id": "RA",
                "name": "Risk Assessment",
                "description": "Assess risk to operations and assets.",
                "control_count": 3,
            },
            {
                "id": "CA",
                "name": "Security Assessment",
                "description": "Assess security controls periodically.",
                "control_count": 4,
            },
            {
                "id": "SC",
                "name": "System and Communications Protection",
                "description": "Monitor and protect communications.",
                "control_count": 16,
            },
            {
                "id": "SI",
                "name": "System and Information Integrity",
                "description": "Identify, report, and correct flaws.",
                "control_count": 7,
            },
        ],
    },
    {
        "short_name": "MLPS_L3",
        "name": "MLPS Level 3",
        "description": (
            "Multi-Level Protection Scheme (网络安全等级保护) Level 3 —"
            " China's cybersecurity standard for systems whose compromise"
            " would cause serious damage to social order or public interest."
        ),
        "version": "2.0",
        "cloud_environments": ["china"],
        "control_families": [
            {
                "id": "PS",
                "name": "Physical Security",
                "description": "Physical environment and equipment protection.",
                "control_count": 10,
            },
            {
                "id": "NS",
                "name": "Network Security",
                "description": "Network architecture, access control, and audit.",
                "control_count": 12,
            },
            {
                "id": "HS",
                "name": "Host Security",
                "description": "Operating system and database security.",
                "control_count": 10,
            },
            {
                "id": "AS",
                "name": "Application Security",
                "description": "Application-level access, audit, and integrity.",
                "control_count": 14,
            },
            {
                "id": "DS",
                "name": "Data Security",
                "description": "Data confidentiality, integrity, and backup.",
                "control_count": 8,
            },
            {
                "id": "SM",
                "name": "Security Management",
                "description": "Security management center and policy.",
                "control_count": 15,
            },
        ],
    },
    {
        "short_name": "GBT_22239",
        "name": "GB/T 22239",
        "description": (
            "Information Security Technology — Baseline for Classified"
            " Protection of Information Systems (GB/T 22239-2019)."
            " China's foundational information security standard."
        ),
        "version": "2019",
        "cloud_environments": ["china"],
        "control_families": [
            {
                "id": "TS",
                "name": "Technical Security",
                "description": "Technical security measures for information systems.",
                "control_count": 20,
            },
            {
                "id": "MS",
                "name": "Management Security",
                "description": "Management processes and organizational security.",
                "control_count": 15,
            },
            {
                "id": "PE",
                "name": "Physical Environment",
                "description": "Physical environment security requirements.",
                "control_count": 8,
            },
            {
                "id": "NS",
                "name": "Network and Communication",
                "description": "Network and communication security controls.",
                "control_count": 12,
            },
            {
                "id": "CS",
                "name": "Computing Security",
                "description": "Computing environment security measures.",
                "control_count": 10,
            },
        ],
    },
    {
        "short_name": "IRAP_Protected",
        "name": "IRAP Protected",
        "description": (
            "Information Security Registered Assessors Program — Protected"
            " level assessment for Australian Government workloads requiring"
            " protection of sensitive and classified information."
        ),
        "version": "2023",
        "cloud_environments": ["commercial"],
        "control_families": [
            {
                "id": "ISM_GOV",
                "name": "ISM Governance",
                "description": "Governance of information security programs.",
                "control_count": 12,
            },
            {
                "id": "ISM_PHY",
                "name": "Physical Security",
                "description": "Physical security of facilities.",
                "control_count": 8,
            },
            {
                "id": "ISM_PER",
                "name": "Personnel Security",
                "description": "Personnel screening and awareness.",
                "control_count": 6,
            },
            {
                "id": "ISM_ICT",
                "name": "ICT Security",
                "description": "Information and communications technology security.",
                "control_count": 25,
            },
            {
                "id": "ISM_NET",
                "name": "Network Security",
                "description": "Network infrastructure and communications.",
                "control_count": 15,
            },
            {
                "id": "ISM_CRYPTO",
                "name": "Cryptographic Security",
                "description": "Encryption and key management.",
                "control_count": 10,
            },
        ],
    },
]

# ── Scoring Mappings ─────────────────────────────────────────────────────────
# Maps control-family IDs to architecture keys checked during evaluation.

_CONTROL_CHECKS: dict[str, list[str]] = {
    "AC": ["security.rbac_model", "identity.mfa_policy", "identity.conditional_access"],
    "AU": ["management.log_analytics", "management.diagnostic_settings"],
    "CA": ["governance.policy_assignments", "governance.compliance_monitoring"],
    "CM": ["governance.resource_locks", "governance.tag_policies"],
    "CP": ["management.backup_policy", "management.disaster_recovery"],
    "IA": ["identity.mfa_policy", "identity.rbac_model", "identity.pim_enabled"],
    "IR": ["security.defender_enabled", "security.sentinel_enabled"],
    "MA": ["management.update_management", "management.patch_policy"],
    "MP": ["security.disk_encryption", "security.storage_encryption"],
    "PE": [],  # Physical controls — not evaluated via architecture
    "PL": ["governance.policy_assignments"],
    "PS": [],  # Personnel controls — not evaluated via architecture
    "RA": ["security.vulnerability_scanning", "security.threat_assessment"],
    "SA": ["governance.approved_services", "governance.service_catalog"],
    "SC": [
        "network.topology",
        "network.firewall_enabled",
        "network.nsg_enabled",
        "security.tls_policy",
    ],
    "SI": [
        "security.defender_enabled",
        "security.antimalware",
        "management.diagnostic_settings",
    ],
    "PM": ["governance.policy_assignments", "governance.compliance_monitoring"],
    # CMMC-specific
    "AM": ["management.log_analytics", "management.diagnostic_settings"],
    "AT": [],  # Training — not evaluated via architecture
    # MLPS / GBT
    "NS": ["network.topology", "network.firewall_enabled", "network.nsg_enabled"],
    "HS": ["security.os_hardening", "security.disk_encryption"],
    "AS": ["security.waf_enabled", "security.tls_policy"],
    "DS": ["security.storage_encryption", "management.backup_policy"],
    "SM": ["governance.policy_assignments", "management.log_analytics"],
    # GBT-specific
    "TS": [
        "security.tls_policy",
        "security.disk_encryption",
        "network.firewall_enabled",
    ],
    "MS": ["governance.policy_assignments", "governance.compliance_monitoring"],
    "CS": ["security.os_hardening", "security.antimalware"],
    # IRAP-specific
    "ISM_GOV": ["governance.policy_assignments", "governance.compliance_monitoring"],
    "ISM_PHY": [],  # Physical — not evaluated
    "ISM_PER": [],  # Personnel — not evaluated
    "ISM_ICT": [
        "security.defender_enabled",
        "security.disk_encryption",
        "management.update_management",
    ],
    "ISM_NET": [
        "network.topology",
        "network.firewall_enabled",
        "network.nsg_enabled",
    ],
    "ISM_CRYPTO": ["security.tls_policy", "security.key_vault_enabled"],
}


# ── Service ──────────────────────────────────────────────────────────────────


class SovereignComplianceService:
    """Evaluates architectures against sovereign-specific compliance frameworks."""

    def get_sovereign_frameworks(self) -> list[dict]:
        """Return all sovereign compliance frameworks."""
        return [
            {
                "short_name": fw["short_name"],
                "name": fw["name"],
                "description": fw["description"],
                "version": fw["version"],
                "cloud_environments": fw["cloud_environments"],
                "control_family_count": len(fw["control_families"]),
            }
            for fw in SOVEREIGN_FRAMEWORKS
        ]

    def get_framework(self, short_name: str) -> dict | None:
        """Return full details for a single framework by short_name."""
        for fw in SOVEREIGN_FRAMEWORKS:
            if fw["short_name"].lower() == short_name.lower():
                return {
                    "short_name": fw["short_name"],
                    "name": fw["name"],
                    "description": fw["description"],
                    "version": fw["version"],
                    "cloud_environments": fw["cloud_environments"],
                    "control_families": fw["control_families"],
                    "total_controls": sum(
                        cf["control_count"] for cf in fw["control_families"]
                    ),
                }
        return None

    def get_frameworks_for_environment(self, env: str) -> list[dict]:
        """Return frameworks applicable to a specific cloud environment."""
        env_lower = env.lower()
        return [
            {
                "short_name": fw["short_name"],
                "name": fw["name"],
                "description": fw["description"],
                "version": fw["version"],
                "cloud_environments": fw["cloud_environments"],
                "control_family_count": len(fw["control_families"]),
            }
            for fw in SOVEREIGN_FRAMEWORKS
            if env_lower in [e.lower() for e in fw["cloud_environments"]]
        ]

    def get_framework_controls(self, short_name: str) -> list[dict]:
        """Return control families for a framework."""
        for fw in SOVEREIGN_FRAMEWORKS:
            if fw["short_name"].lower() == short_name.lower():
                return fw["control_families"]
        return []

    def evaluate_sovereign_compliance(
        self, architecture: dict, framework: str
    ) -> dict:
        """Score an architecture against a sovereign compliance framework.

        Returns a dict with overall_score, status, per-family breakdown,
        and actionable recommendations.
        """
        fw = self.get_framework(framework)
        if fw is None:
            return {
                "framework": framework,
                "overall_score": 0,
                "status": "unknown",
                "message": f"Framework '{framework}' not found.",
                "family_scores": [],
                "recommendations": [],
            }

        family_scores: list[dict] = []
        total_met = 0
        total_controls = 0

        for family in fw["control_families"]:
            checks = _CONTROL_CHECKS.get(family["id"], [])
            met = 0
            for check_path in checks:
                if self._resolve_path(architecture, check_path):
                    met += 1
            # If no architecture checks exist for this family, treat as N/A
            if not checks:
                family_scores.append(
                    {
                        "family_id": family["id"],
                        "family_name": family["name"],
                        "score": None,
                        "status": "not_applicable",
                        "controls_evaluated": 0,
                        "controls_met": 0,
                    }
                )
                continue

            score = round((met / len(checks)) * 100) if checks else 0
            total_met += met
            total_controls += len(checks)
            family_scores.append(
                {
                    "family_id": family["id"],
                    "family_name": family["name"],
                    "score": score,
                    "status": (
                        "compliant"
                        if score >= 80
                        else ("partial" if score >= 40 else "non_compliant")
                    ),
                    "controls_evaluated": len(checks),
                    "controls_met": met,
                }
            )

        overall_score = (
            round((total_met / total_controls) * 100) if total_controls > 0 else 0
        )
        status = (
            "compliant"
            if overall_score >= 80
            else ("partial" if overall_score >= 40 else "non_compliant")
        )

        recommendations = self._generate_recommendations(family_scores, fw)

        return {
            "framework": fw["short_name"],
            "framework_name": fw["name"],
            "overall_score": overall_score,
            "status": status,
            "total_controls_evaluated": total_controls,
            "total_controls_met": total_met,
            "family_scores": family_scores,
            "recommendations": recommendations,
        }

    # ── Private Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _resolve_path(data: dict, path: str) -> bool:
        """Walk a dotted path like 'security.defender_enabled' into nested dicts."""
        parts = path.split(".")
        current = data
        for part in parts:
            if not isinstance(current, dict):
                return False
            current = current.get(part)
            if current is None:
                return False
        return bool(current)

    @staticmethod
    def _generate_recommendations(
        family_scores: list[dict], framework: dict
    ) -> list[str]:
        """Produce actionable recommendations for non-compliant families."""
        recs: list[str] = []
        for fs in family_scores:
            if fs["status"] == "non_compliant":
                recs.append(
                    f"[Critical] {fs['family_name']} ({fs['family_id']}): "
                    f"score {fs['score']}% — review and remediate "
                    f"controls for {framework['name']}."
                )
            elif fs["status"] == "partial":
                recs.append(
                    f"[Warning] {fs['family_name']} ({fs['family_id']}): "
                    f"score {fs['score']}% — additional controls needed "
                    f"for full {framework['name']} compliance."
                )
        return recs


# Singleton
sovereign_compliance_service = SovereignComplianceService()

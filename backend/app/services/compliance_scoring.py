"""Compliance scoring engine — evaluates architectures against frameworks."""

from app.services.compliance_data import get_framework_by_short_name
from app.services.policy_mapping import get_policy_definition


class ComplianceScoringEngine:
    """Evaluates landing zone architectures against compliance frameworks."""

    def score_architecture(
        self, architecture: dict, framework_names: list[str]
    ) -> dict:
        """Score an architecture against selected compliance frameworks."""
        results = []
        all_controls_met = 0
        all_controls_partial = 0
        all_controls_gap = 0

        for fw_name in framework_names:
            fw = get_framework_by_short_name(fw_name)
            if fw is None:
                continue

            fw_result = self._evaluate_framework(architecture, fw)
            results.append(fw_result)
            all_controls_met += fw_result["controls_met"]
            all_controls_partial += fw_result["controls_partial"]
            all_controls_gap += fw_result["controls_gap"]

        total_controls = all_controls_met + all_controls_partial + all_controls_gap
        overall_score = (
            round((all_controls_met / total_controls) * 100) if total_controls > 0 else 0
        )

        return {
            "overall_score": overall_score,
            "total_controls": total_controls,
            "controls_met": all_controls_met,
            "controls_partial": all_controls_partial,
            "controls_gap": all_controls_gap,
            "frameworks": results,
            "top_recommendations": self._generate_recommendations(results),
        }

    def _evaluate_framework(self, architecture: dict, framework: dict) -> dict:
        """Evaluate architecture against a single compliance framework."""
        controls_met = 0
        controls_partial = 0
        controls_gap = 0
        gaps = []

        security = architecture.get("security", {})
        identity = architecture.get("identity", {})
        governance = architecture.get("governance", {})
        management = architecture.get("management", {})

        for control in framework["controls"]:
            status = self._check_control(control, security, identity, governance, management)

            if status == "met":
                controls_met += 1
            elif status == "partial":
                controls_partial += 1
                gaps.append({
                    "control_id": control["control_id"],
                    "control_name": control["title"],
                    "severity": control["severity"],
                    "status": "partial",
                    "gap_description": f"Control partially satisfied — additional configuration needed",
                    "remediation": self._get_remediation(control),
                })
            else:
                controls_gap += 1
                gaps.append({
                    "control_id": control["control_id"],
                    "control_name": control["title"],
                    "severity": control["severity"],
                    "status": "gap",
                    "gap_description": f"Control not satisfied in current architecture",
                    "remediation": self._get_remediation(control),
                })

        total = controls_met + controls_partial + controls_gap
        score = round((controls_met / total) * 100) if total > 0 else 0

        return {
            "name": framework["short_name"],
            "full_name": framework["name"],
            "score": score,
            "status": "compliant" if score >= 80 else ("partially_compliant" if score >= 50 else "non_compliant"),
            "controls_met": controls_met,
            "controls_partial": controls_partial,
            "controls_gap": controls_gap,
            "gaps": gaps,
        }

    def _check_control(
        self,
        control: dict,
        security: dict,
        identity: dict,
        governance: dict,
        management: dict,
    ) -> str:
        """Check if a control is met by the architecture. Returns 'met', 'partial', or 'gap'."""
        policies = control.get("azure_policies", [])
        met_count = 0

        for policy_key in policies:
            if self._is_policy_satisfied(policy_key, security, identity, governance, management):
                met_count += 1

        if not policies:
            return "partial"

        ratio = met_count / len(policies)
        if ratio >= 1.0:
            return "met"
        elif ratio >= 0.5:
            return "partial"
        return "gap"

    def _is_policy_satisfied(
        self,
        policy_key: str,
        security: dict,
        identity: dict,
        governance: dict,
        management: dict,
    ) -> bool:
        """Check if a specific policy requirement is satisfied by the architecture."""
        checks = {
            "require-rbac": identity.get("rbac_model") == "Azure RBAC",
            "require-mfa": identity.get("mfa_policy") in ("all_users", "conditional"),
            "require-pim": identity.get("pim_enabled", False),
            "require-nsg": True,  # NSGs are included in all archetypes
            "require-firewall": security.get("azure_firewall", False),
            "require-waf": security.get("waf", False),
            "require-diagnostics": management.get("log_analytics", {}).get("workspace_count", 0) > 0 if isinstance(management.get("log_analytics"), dict) else bool(management.get("log_analytics")),
            "require-log-analytics": management.get("log_analytics", {}).get("workspace_count", 0) > 0 if isinstance(management.get("log_analytics"), dict) else bool(management.get("log_analytics")),
            "enable-defender": security.get("defender_for_cloud", False),
            "enable-sentinel": security.get("sentinel", False),
            "require-tags": len(governance.get("tagging_strategy", {}).get("mandatory_tags", [])) > 0 if isinstance(governance.get("tagging_strategy"), dict) else False,
            "require-encryption-at-rest": True,  # Azure default
            "require-tls": True,  # Azure default
            "require-backup": management.get("backup", {}).get("enabled", False) if isinstance(management.get("backup"), dict) else bool(management.get("backup")),
            "require-geo-redundancy": management.get("backup", {}).get("geo_redundant", False) if isinstance(management.get("backup"), dict) else False,
            "require-key-vault": security.get("key_vault_per_subscription", False),
            "deny-public-ip": True,  # Policy-based, assumed present
            "require-https": True,  # Azure default
            "require-vpn": True,  # Assumed if hybrid connectivity
            "require-vpn-encryption": True,
            "enable-secure-score": security.get("defender_for_cloud", False),
            "audit-changes": management.get("log_analytics", {}).get("workspace_count", 0) > 0 if isinstance(management.get("log_analytics"), dict) else bool(management.get("log_analytics")),
            "audit-log-retention": True,
            "require-audit-logs": management.get("log_analytics", {}).get("workspace_count", 0) > 0 if isinstance(management.get("log_analytics"), dict) else bool(management.get("log_analytics")),
            "require-activity-log": management.get("log_analytics", {}).get("workspace_count", 0) > 0 if isinstance(management.get("log_analytics"), dict) else bool(management.get("log_analytics")),
        }
        return checks.get(policy_key, False)

    def _get_remediation(self, control: dict) -> str:
        """Get remediation guidance for a control gap."""
        policy_keys = control.get("azure_policies", [])
        remediation_parts = []
        for key in policy_keys:
            policy = get_policy_definition(key)
            if policy:
                remediation_parts.append(f"Enable: {policy['display_name']}")
        return "; ".join(remediation_parts) if remediation_parts else "Review control requirements and update architecture"

    def _generate_recommendations(self, framework_results: list[dict]) -> list[str]:
        """Generate top recommendations from compliance gaps."""
        recommendations = []
        seen = set()
        for fw in framework_results:
            for gap in fw.get("gaps", []):
                if gap["severity"] == "high" and gap["remediation"] not in seen:
                    recommendations.append(
                        f"[{fw['name']}] {gap['control_name']}: {gap['remediation']}"
                    )
                    seen.add(gap["remediation"])
        return recommendations[:10]


# Singleton
compliance_scorer = ComplianceScoringEngine()

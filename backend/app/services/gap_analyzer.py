"""Gap analysis engine — compares discovery results against CAF best practices."""

import logging
import uuid

logger = logging.getLogger(__name__)

# Resource category constants (match discovery_service)
CATEGORY_RESOURCE = "resource"
CATEGORY_NETWORK = "network"
CATEGORY_POLICY = "policy"
CATEGORY_RBAC = "rbac"


class GapAnalyzer:
    """Analyzes discovered Azure environments against CAF landing zone best practices."""

    def analyze(
        self,
        scan_summary: dict,
        resources: list[dict],
    ) -> dict:
        """Run gap analysis comparing discovery results to CAF best practices.

        Args:
            scan_summary: The scan results summary from DiscoveryScan.results.
            resources: List of discovered resource dicts from DiscoveredResource rows.

        Returns:
            Gap analysis result with findings, counts, and area status.
        """
        findings: list[dict] = []
        areas_checked: list[str] = []
        areas_skipped: list[str] = []

        # Check each CAF area, skipping if scan had errors for that area
        if "resource_error" not in scan_summary:
            areas_checked.append("management_groups")
            findings.extend(self._check_management_groups(scan_summary, resources))
        else:
            areas_skipped.append("management_groups")

        if "resource_error" not in scan_summary:
            areas_checked.append("naming")
            findings.extend(self._check_naming(resources))
        else:
            areas_skipped.append("naming")

        if "policy_error" not in scan_summary:
            areas_checked.append("policy")
            findings.extend(self._check_policies(scan_summary, resources))
        else:
            areas_skipped.append("policy")

        if "rbac_error" not in scan_summary:
            areas_checked.append("rbac")
            findings.extend(self._check_rbac(scan_summary, resources))
        else:
            areas_skipped.append("rbac")

        if "network_error" not in scan_summary:
            areas_checked.append("networking")
            findings.extend(self._check_networking(scan_summary, resources))
        else:
            areas_skipped.append("networking")

        # Monitoring — inferred from resource types present
        if "resource_error" not in scan_summary:
            areas_checked.append("monitoring")
            findings.extend(self._check_monitoring(scan_summary, resources))
        else:
            areas_skipped.append("monitoring")

        # Security — inferred from resource types and policies
        if "resource_error" not in scan_summary:
            areas_checked.append("security")
            findings.extend(self._check_security(scan_summary, resources))
        else:
            areas_skipped.append("security")

        # Count by severity
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in findings:
            severity_counts[f["severity"]] = severity_counts.get(f["severity"], 0) + 1

        return {
            "total_findings": len(findings),
            "critical_count": severity_counts["critical"],
            "high_count": severity_counts["high"],
            "medium_count": severity_counts["medium"],
            "low_count": severity_counts["low"],
            "findings": findings,
            "areas_checked": areas_checked,
            "areas_skipped": areas_skipped,
        }

    def _finding(
        self,
        category: str,
        severity: str,
        title: str,
        description: str,
        remediation: str,
        caf_reference: str | None = None,
        can_auto_remediate: bool = False,
    ) -> dict:
        """Create a standardized gap finding dict."""
        return {
            "id": str(uuid.uuid4()),
            "category": category,
            "severity": severity,
            "title": title,
            "description": description,
            "remediation": remediation,
            "caf_reference": caf_reference,
            "can_auto_remediate": can_auto_remediate,
        }

    # -----------------------------------------------------------------------
    # CAF Area Checks
    # -----------------------------------------------------------------------

    def _check_management_groups(
        self, summary: dict, resources: list[dict]
    ) -> list[dict]:
        """Check for management group structure gaps."""
        findings = []
        rg_count = summary.get("total_resource_groups", 0)

        # If multiple resource groups but no management group hierarchy detected
        # (Discovery scans at subscription scope — management groups are above that)
        if rg_count > 3:
            findings.append(self._finding(
                category="management_groups",
                severity="high",
                title="Management group hierarchy recommended",
                description=(
                    f"Found {rg_count} resource groups in a single subscription. "
                    "CAF recommends organizing subscriptions under a management group "
                    "hierarchy (Platform, Landing Zones, Sandbox, Decommissioned) "
                    "for governance at scale."
                ),
                remediation=(
                    "Create a management group hierarchy following the CAF "
                    "recommended structure. Use OnRamp to generate the "
                    "appropriate Bicep templates."
                ),
                caf_reference=(
                    "https://learn.microsoft.com/en-us/azure/cloud-adoption-framework"
                    "/ready/landing-zone/design-area/resource-org-management-groups"
                ),
                can_auto_remediate=True,
            ))

        return findings

    def _check_policies(
        self, summary: dict, resources: list[dict]
    ) -> list[dict]:
        """Check for missing or insufficient Azure Policy coverage."""
        findings = []
        policy_count = summary.get("total_policies", 0)
        policy_resources = [r for r in resources if r.get("category") == CATEGORY_POLICY]

        if policy_count == 0:
            findings.append(self._finding(
                category="policy",
                severity="critical",
                title="No Azure Policy assignments found",
                description=(
                    "The subscription has no policy assignments. Azure Policy is "
                    "essential for enforcing governance standards, ensuring compliance, "
                    "and preventing misconfigurations."
                ),
                remediation=(
                    "Assign CAF baseline policy initiatives including: "
                    "allowed locations, required tags, allowed VM SKUs, "
                    "and diagnostic settings policies."
                ),
                caf_reference=(
                    "https://learn.microsoft.com/en-us/azure/cloud-adoption-framework"
                    "/ready/landing-zone/design-area/governance"
                ),
                can_auto_remediate=True,
            ))
        elif policy_count < 5:
            findings.append(self._finding(
                category="policy",
                severity="high",
                title="Minimal Azure Policy coverage",
                description=(
                    f"Only {policy_count} policy assignments found. CAF recommends "
                    "comprehensive policy coverage including tag enforcement, "
                    "allowed locations, resource type restrictions, and "
                    "diagnostic settings."
                ),
                remediation=(
                    "Review and expand policy assignments to cover CAF baseline "
                    "governance areas. Consider assigning the Azure Landing Zone "
                    "policy initiative."
                ),
                caf_reference=(
                    "https://learn.microsoft.com/en-us/azure/cloud-adoption-framework"
                    "/ready/landing-zone/design-area/governance"
                ),
            ))

        # Check for tag enforcement policies
        tag_policies = [
            p for p in policy_resources
            if "tag" in (p.get("name", "") or "").lower()
        ]
        if not tag_policies and policy_count > 0:
            findings.append(self._finding(
                category="policy",
                severity="medium",
                title="No tag enforcement policies detected",
                description=(
                    "No policies enforcing resource tagging were found. "
                    "Tags are essential for cost management, ownership tracking, "
                    "and resource organization."
                ),
                remediation=(
                    "Create policies to require tags such as: Environment, "
                    "CostCenter, Owner, and Application on all resources."
                ),
                can_auto_remediate=True,
            ))

        return findings

    def _check_rbac(
        self, summary: dict, resources: list[dict]
    ) -> list[dict]:
        """Check for RBAC best-practice gaps."""
        findings = []
        ra_count = summary.get("total_role_assignments", 0)
        rbac_resources = [r for r in resources if r.get("category") == CATEGORY_RBAC]

        if ra_count == 0:
            findings.append(self._finding(
                category="rbac",
                severity="critical",
                title="No RBAC role assignments found",
                description=(
                    "No custom role assignments detected at subscription scope. "
                    "Proper RBAC is essential for least-privilege access control."
                ),
                remediation=(
                    "Configure role assignments following the principle of "
                    "least privilege. Use built-in roles where possible and "
                    "consider enabling Privileged Identity Management (PIM) "
                    "for elevated access."
                ),
                caf_reference=(
                    "https://learn.microsoft.com/en-us/azure/cloud-adoption-framework"
                    "/ready/landing-zone/design-area/identity-access"
                ),
            ))

        # Check for over-privileged assignments (Owner role at subscription scope)
        # Known built-in Owner role definition ID suffix
        owner_role_suffix = "8e3af657-a8ff-443c-a75c-2fe8c4bcb635"
        owner_assignments = [
            r for r in rbac_resources
            if (
                # Check role_definition_name (enriched data or mock)
                "owner" == (
                    r.get("properties", {})
                    .get("role_definition_name", "")
                ).lower()
                # Or check role_definition_id against known Owner GUID
                or owner_role_suffix in (
                    r.get("properties", {})
                    .get("role_definition_id", "")
                ).lower()
            )
        ]
        if len(owner_assignments) > 3:
            findings.append(self._finding(
                category="rbac",
                severity="high",
                title="Multiple Owner-level role assignments",
                description=(
                    f"Found {len(owner_assignments)} Owner role assignments at "
                    "subscription scope. Owner grants full access including "
                    "RBAC management, which should be strictly limited."
                ),
                remediation=(
                    "Reduce Owner assignments to a minimum (ideally 2-3 break-glass "
                    "accounts). Use Contributor or custom roles for regular "
                    "administrators. Enable PIM for just-in-time elevation."
                ),
                caf_reference=(
                    "https://learn.microsoft.com/en-us/azure/cloud-adoption-framework"
                    "/ready/landing-zone/design-area/identity-access"
                ),
            ))

        return findings

    def _check_networking(
        self, summary: dict, resources: list[dict]
    ) -> list[dict]:
        """Check for networking best-practice gaps."""
        findings = []
        vnet_count = summary.get("total_vnets", 0)
        nsg_count = summary.get("total_nsgs", 0)

        if vnet_count == 0:
            findings.append(self._finding(
                category="networking",
                severity="high",
                title="No virtual networks found",
                description=(
                    "No VNets detected in the subscription. A well-designed "
                    "network topology is fundamental for security and connectivity."
                ),
                remediation=(
                    "Design and deploy a hub-spoke or Virtual WAN network "
                    "topology. The hub VNet should host shared services "
                    "(firewall, DNS, VPN gateway)."
                ),
                caf_reference=(
                    "https://learn.microsoft.com/en-us/azure/cloud-adoption-framework"
                    "/ready/landing-zone/design-area/network-topology-and-connectivity"
                ),
                can_auto_remediate=True,
            ))

        if vnet_count > 0 and nsg_count == 0:
            findings.append(self._finding(
                category="networking",
                severity="critical",
                title="No Network Security Groups found",
                description=(
                    f"Found {vnet_count} VNet(s) but no NSGs. Network Security "
                    "Groups are essential for controlling traffic flow and "
                    "enforcing network segmentation."
                ),
                remediation=(
                    "Create NSGs for each subnet and configure rules following "
                    "the principle of least privilege. Block all inbound traffic "
                    "by default and allow only required flows."
                ),
                caf_reference=(
                    "https://learn.microsoft.com/en-us/azure/cloud-adoption-framework"
                    "/ready/landing-zone/design-area/network-topology-and-connectivity"
                ),
                can_auto_remediate=True,
            ))

        # Check for single VNet (no hub-spoke)
        if vnet_count == 1:
            findings.append(self._finding(
                category="networking",
                severity="medium",
                title="Single VNet topology — consider hub-spoke",
                description=(
                    "Only one VNet found. For production workloads, CAF "
                    "recommends a hub-spoke topology to separate shared "
                    "services from workload networks."
                ),
                remediation=(
                    "Evaluate if a hub-spoke topology would benefit your "
                    "architecture. The hub hosts shared services (firewall, "
                    "VPN, DNS) while spokes isolate workloads."
                ),
                caf_reference=(
                    "https://learn.microsoft.com/en-us/azure/cloud-adoption-framework"
                    "/ready/landing-zone/design-area/network-topology-and-connectivity"
                ),
                can_auto_remediate=True,
            ))

        return findings

    def _check_monitoring(
        self, summary: dict, resources: list[dict]
    ) -> list[dict]:
        """Check for monitoring and observability gaps."""
        findings = []
        all_resources = [r for r in resources if r.get("category") == CATEGORY_RESOURCE]

        # Check for Log Analytics workspace
        log_analytics = [
            r for r in all_resources
            if (r.get("resource_type") or "").lower()
            == "microsoft.operationalinsights/workspaces"
        ]

        if not log_analytics:
            findings.append(self._finding(
                category="monitoring",
                severity="high",
                title="No Log Analytics workspace found",
                description=(
                    "No Log Analytics workspace detected. A central workspace "
                    "is required for collecting logs, metrics, and enabling "
                    "Azure Monitor alerts."
                ),
                remediation=(
                    "Create a Log Analytics workspace and configure diagnostic "
                    "settings on all resources to send logs and metrics to it. "
                    "Consider enabling Azure Monitor insights."
                ),
                caf_reference=(
                    "https://learn.microsoft.com/en-us/azure/cloud-adoption-framework"
                    "/ready/landing-zone/design-area/management"
                ),
                can_auto_remediate=True,
            ))

        # Check for Application Insights
        app_insights = [
            r for r in all_resources
            if (r.get("resource_type") or "").lower()
            == "microsoft.insights/components"
        ]
        resource_count = summary.get("total_resources", 0)
        if not app_insights and resource_count > 5:
            findings.append(self._finding(
                category="monitoring",
                severity="medium",
                title="No Application Insights found",
                description=(
                    "No Application Insights resources detected. APM is "
                    "recommended for monitoring application performance, "
                    "detecting anomalies, and diagnosing issues."
                ),
                remediation=(
                    "Create Application Insights resources for your applications "
                    "and configure telemetry collection."
                ),
            ))

        return findings

    def _check_security(
        self, summary: dict, resources: list[dict]
    ) -> list[dict]:
        """Check for security best-practice gaps."""
        findings = []
        all_resources = [r for r in resources if r.get("category") == CATEGORY_RESOURCE]

        # Check for Key Vault
        key_vaults = [
            r for r in all_resources
            if (r.get("resource_type") or "").lower()
            == "microsoft.keyvault/vaults"
        ]
        if not key_vaults:
            findings.append(self._finding(
                category="security",
                severity="high",
                title="No Azure Key Vault found",
                description=(
                    "No Key Vault detected. Secrets, keys, and certificates "
                    "should be stored in Key Vault, not in code or config files."
                ),
                remediation=(
                    "Create an Azure Key Vault for each environment and migrate "
                    "all secrets, connection strings, and certificates into it. "
                    "Use managed identities for access."
                ),
                caf_reference=(
                    "https://learn.microsoft.com/en-us/azure/cloud-adoption-framework"
                    "/ready/landing-zone/design-area/security"
                ),
                can_auto_remediate=True,
            ))

        # Check for resources with public endpoints
        # (simplified heuristic — check for public IPs)
        public_ips = [
            r for r in all_resources
            if (r.get("resource_type") or "").lower()
            == "microsoft.network/publicipaddresses"
        ]
        if len(public_ips) > 3:
            findings.append(self._finding(
                category="security",
                severity="medium",
                title="Multiple public IP addresses detected",
                description=(
                    f"Found {len(public_ips)} public IP addresses. Excessive "
                    "public endpoints increase the attack surface. Consider "
                    "using private endpoints and Azure Firewall."
                ),
                remediation=(
                    "Review public IP usage and migrate to private endpoints "
                    "where possible. Use Azure Firewall or Application Gateway "
                    "with WAF to protect publicly exposed services."
                ),
                caf_reference=(
                    "https://learn.microsoft.com/en-us/azure/cloud-adoption-framework"
                    "/ready/landing-zone/design-area/security"
                ),
            ))

        return findings

    def _check_naming(self, resources: list[dict]) -> list[dict]:
        """Check for naming convention compliance."""
        findings = []
        all_resources = [r for r in resources if r.get("category") == CATEGORY_RESOURCE]

        if not all_resources:
            return findings

        # Check if resources follow a consistent naming pattern
        # CAF recommends: {resource-type}-{workload}-{environment}-{region}-{instance}
        # Simplified check: look for common prefixes that suggest a convention
        names = [r.get("name", "") for r in all_resources if r.get("name")]
        if not names:
            return findings

        # Check for resources without standard prefixes
        caf_prefixes = {
            "rg-", "vnet-", "snet-", "nsg-", "pip-", "nic-", "vm-",
            "st", "kv-", "acr", "aks-", "app-", "func-", "sql",
            "log-", "appi-", "id-", "cr-",
        }
        resources_with_prefix = sum(
            1 for n in names
            if any(n.lower().startswith(p) for p in caf_prefixes)
        )
        prefix_ratio = resources_with_prefix / len(names) if names else 0

        if prefix_ratio < 0.3 and len(names) > 3:
            findings.append(self._finding(
                category="naming",
                severity="medium",
                title="Resource naming does not follow CAF convention",
                description=(
                    f"Only {resources_with_prefix} of {len(names)} resources "
                    "use CAF-recommended naming prefixes. Consistent naming "
                    "improves discoverability and management."
                ),
                remediation=(
                    "Adopt the Azure CAF naming convention: "
                    "{resource-type}-{workload}-{environment}-{region}-{instance}. "
                    "Example: vm-web-prod-eastus2-001."
                ),
                caf_reference=(
                    "https://learn.microsoft.com/en-us/azure/cloud-adoption-framework"
                    "/ready/azure-best-practices/resource-naming"
                ),
            ))

        # Check for resources without tags
        untagged = sum(
            1 for r in all_resources
            if not r.get("properties", {}).get("tags")
        )
        if untagged > len(all_resources) * 0.5 and len(all_resources) > 3:
            findings.append(self._finding(
                category="naming",
                severity="low",
                title="Many resources lack tags",
                description=(
                    f"{untagged} of {len(all_resources)} resources have no tags. "
                    "Tags are essential for cost management, ownership, and "
                    "operational visibility."
                ),
                remediation=(
                    "Define and enforce a minimum tagging standard. "
                    "Recommended tags: Environment, CostCenter, Owner, Application."
                ),
                caf_reference=(
                    "https://learn.microsoft.com/en-us/azure/cloud-adoption-framework"
                    "/ready/azure-best-practices/resource-tagging"
                ),
            ))

        return findings

    def get_brownfield_context(
        self, scan_summary: dict, resources: list[dict]
    ) -> dict:
        """Derive brownfield questionnaire context from discovery results.

        Returns discovered answer suggestions with confidence levels.
        Only infers answers that are directly observable from the scan.

        Args:
            scan_summary: The DiscoveryScan.results summary dict.
            resources: List of discovered resource dicts.

        Returns:
            Dict with discovered_answers and gap_summary.
        """
        discovered_answers: dict[str, dict] = {}
        all_resources = [r for r in resources if r.get("category") == CATEGORY_RESOURCE]

        # Infer network topology from VNet count
        vnet_count = scan_summary.get("total_vnets", 0)
        if "network_error" not in scan_summary:
            if vnet_count == 0:
                discovered_answers["network_topology"] = {
                    "value": "hub_spoke",
                    "confidence": "low",
                    "evidence": "No VNets found — recommending hub-spoke as default",
                    "source": "discovered",
                }
            elif vnet_count == 1:
                discovered_answers["network_topology"] = {
                    "value": "hub_spoke",
                    "confidence": "medium",
                    "evidence": "Found 1 VNet — single-VNet topology detected",
                    "source": "discovered",
                }
            elif vnet_count > 1:
                discovered_answers["network_topology"] = {
                    "value": "hub_spoke",
                    "confidence": "medium",
                    "evidence": (
                        f"Found {vnet_count} VNets — likely hub-spoke or mesh"
                    ),
                    "source": "discovered",
                }

        # Infer security level from policies and Key Vaults
        policy_count = scan_summary.get("total_policies", 0)
        kv_exists = any(
            (r.get("resource_type") or "").lower() == "microsoft.keyvault/vaults"
            for r in all_resources
        )
        if "policy_error" not in scan_summary:
            if policy_count > 10 and kv_exists:
                discovered_answers["security_level"] = {
                    "value": "enhanced",
                    "confidence": "medium",
                    "evidence": (
                        f"{policy_count} policies + Key Vault present"
                    ),
                    "source": "discovered",
                }
            elif policy_count > 0:
                discovered_answers["security_level"] = {
                    "value": "standard",
                    "confidence": "medium",
                    "evidence": f"{policy_count} policies found",
                    "source": "discovered",
                }

        # Infer monitoring strategy from Log Analytics presence
        la_exists = any(
            (r.get("resource_type") or "").lower()
            == "microsoft.operationalinsights/workspaces"
            for r in all_resources
        )
        if "resource_error" not in scan_summary:
            if la_exists:
                discovered_answers["monitoring_strategy"] = {
                    "value": "azure_native",
                    "confidence": "high",
                    "evidence": "Log Analytics workspace found",
                    "source": "discovered",
                }

        # Infer naming convention from prefix analysis
        names = [r.get("name", "") for r in all_resources if r.get("name")]
        caf_prefixes = {"rg-", "vnet-", "snet-", "nsg-", "kv-", "vm-", "st"}
        if names:
            has_prefix = sum(
                1 for n in names
                if any(n.lower().startswith(p) for p in caf_prefixes)
            )
            if has_prefix / len(names) > 0.5:
                discovered_answers["naming_convention"] = {
                    "value": "existing",
                    "confidence": "high",
                    "evidence": (
                        f"{has_prefix}/{len(names)} resources use CAF prefixes"
                    ),
                    "source": "discovered",
                }

        # Run gap analysis for summary
        gap_result = self.analyze(scan_summary, resources)

        return {
            "scan_id": scan_summary.get("scan_id", ""),
            "discovered_answers": discovered_answers,
            "gap_summary": {
                "critical": gap_result["critical_count"],
                "high": gap_result["high_count"],
                "medium": gap_result["medium_count"],
                "low": gap_result["low_count"],
                "total": gap_result["total_findings"],
            },
        }


# Singleton
gap_analyzer = GapAnalyzer()

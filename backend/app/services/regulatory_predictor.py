"""Regulatory gap predictor — predicts applicable frameworks and analyses gaps.

Uses industry, geography, and data-type mappings for rule-based prediction,
with optional AI-enhanced analysis via AIFoundryClient.
"""

import json
import logging

from app.schemas.regulatory import (
    ControlGap,
    ControlStatus,
    FrameworkGapAnalysis,
    PredictedFramework,
    Recommendation,
)

logger = logging.getLogger(__name__)


class RegulatoryPredictor:
    """Predict regulatory frameworks and analyse compliance gaps."""

    # -----------------------------------------------------------------------
    # Industry → Frameworks
    # -----------------------------------------------------------------------
    INDUSTRY_FRAMEWORK_MAP: dict[str, list[str]] = {
        "healthcare": ["HIPAA", "HITRUST"],
        "finance": ["PCI-DSS", "SOX", "GLBA"],
        "government": ["FedRAMP", "NIST 800-171"],
        "retail": ["PCI-DSS", "CCPA"],
        "technology": ["SOC 2", "ISO 27001"],
        "education": ["FERPA"],
    }

    # -----------------------------------------------------------------------
    # Geography → Frameworks
    # -----------------------------------------------------------------------
    GEOGRAPHY_FRAMEWORK_MAP: dict[str, list[str]] = {
        "EU": ["GDPR"],
        "California": ["CCPA"],
        "Brazil": ["LGPD"],
        "Canada": ["PIPEDA"],
        "global": ["ISO 27001"],
    }

    # -----------------------------------------------------------------------
    # Data Type → Required Controls
    # -----------------------------------------------------------------------
    DATA_TYPE_CONTROLS: dict[str, list[str]] = {
        "PII": ["encryption", "access_controls", "audit_logging"],
        "PHI": ["HIPAA_controls", "audit_logging", "encryption"],
        "financial": ["PCI_controls", "tokenization", "encryption"],
    }

    # -----------------------------------------------------------------------
    # Framework descriptions (for the /frameworks listing)
    # -----------------------------------------------------------------------
    FRAMEWORK_DESCRIPTIONS: dict[str, str] = {
        "HIPAA": "Health Insurance Portability and Accountability Act — US healthcare data protection",
        "HITRUST": "HITRUST Common Security Framework — healthcare information security",
        "PCI-DSS": "Payment Card Industry Data Security Standard — credit card data protection",
        "SOX": "Sarbanes-Oxley Act — US financial reporting and auditing controls",
        "GLBA": "Gramm-Leach-Bliley Act — US financial institution data privacy",
        "FedRAMP": "Federal Risk and Authorization Management Program — US government cloud security",
        "NIST 800-171": "NIST SP 800-171 — protecting controlled unclassified information",
        "CCPA": "California Consumer Privacy Act — California data privacy rights",
        "SOC 2": "Service Organization Control 2 — trust services criteria for security and privacy",
        "ISO 27001": "ISO/IEC 27001 — international information security management standard",
        "FERPA": "Family Educational Rights and Privacy Act — US student records protection",
        "GDPR": "General Data Protection Regulation — EU data protection and privacy",
        "LGPD": "Lei Geral de Proteção de Dados — Brazil data protection law",
        "PIPEDA": "Personal Information Protection and Electronic Documents Act — Canada privacy law",
    }

    # -----------------------------------------------------------------------
    # Framework → Controls (for gap analysis)
    # -----------------------------------------------------------------------
    FRAMEWORK_CONTROLS: dict[str, list[dict[str, str]]] = {
        "HIPAA": [
            {"id": "HIPAA-1", "name": "Access controls", "check": "identity"},
            {"id": "HIPAA-2", "name": "Audit logging", "check": "management"},
            {"id": "HIPAA-3", "name": "Data encryption at rest", "check": "security"},
            {"id": "HIPAA-4", "name": "Data encryption in transit", "check": "security"},
            {"id": "HIPAA-5", "name": "Backup and recovery", "check": "management"},
        ],
        "HITRUST": [
            {"id": "HITRUST-1", "name": "Information protection", "check": "security"},
            {"id": "HITRUST-2", "name": "Access management", "check": "identity"},
            {"id": "HITRUST-3", "name": "Risk management", "check": "governance"},
        ],
        "PCI-DSS": [
            {"id": "PCI-1", "name": "Firewall configuration", "check": "security"},
            {"id": "PCI-2", "name": "Encryption of cardholder data", "check": "security"},
            {"id": "PCI-3", "name": "Access restriction", "check": "identity"},
            {"id": "PCI-4", "name": "Network monitoring", "check": "management"},
            {"id": "PCI-5", "name": "Vulnerability management", "check": "security"},
        ],
        "SOX": [
            {"id": "SOX-1", "name": "Internal controls over financial reporting", "check": "governance"},
            {"id": "SOX-2", "name": "Audit trail", "check": "management"},
            {"id": "SOX-3", "name": "Access controls", "check": "identity"},
        ],
        "GLBA": [
            {"id": "GLBA-1", "name": "Customer data protection", "check": "security"},
            {"id": "GLBA-2", "name": "Access controls", "check": "identity"},
            {"id": "GLBA-3", "name": "Risk assessment", "check": "governance"},
        ],
        "FedRAMP": [
            {"id": "FED-1", "name": "Access control (AC)", "check": "identity"},
            {"id": "FED-2", "name": "Audit and accountability (AU)", "check": "management"},
            {"id": "FED-3", "name": "Security assessment (CA)", "check": "governance"},
            {"id": "FED-4", "name": "System and communications protection (SC)", "check": "security"},
            {"id": "FED-5", "name": "Incident response (IR)", "check": "security"},
        ],
        "NIST 800-171": [
            {"id": "NIST-1", "name": "Access control", "check": "identity"},
            {"id": "NIST-2", "name": "Audit and accountability", "check": "management"},
            {"id": "NIST-3", "name": "Configuration management", "check": "governance"},
            {"id": "NIST-4", "name": "Identification and authentication", "check": "identity"},
        ],
        "CCPA": [
            {"id": "CCPA-1", "name": "Consumer data access rights", "check": "governance"},
            {"id": "CCPA-2", "name": "Data deletion capability", "check": "governance"},
            {"id": "CCPA-3", "name": "Data encryption", "check": "security"},
        ],
        "SOC 2": [
            {"id": "SOC2-1", "name": "Logical access controls", "check": "identity"},
            {"id": "SOC2-2", "name": "System monitoring", "check": "management"},
            {"id": "SOC2-3", "name": "Change management", "check": "governance"},
            {"id": "SOC2-4", "name": "Incident response", "check": "security"},
        ],
        "ISO 27001": [
            {"id": "ISO-1", "name": "Information security policies", "check": "governance"},
            {"id": "ISO-2", "name": "Access control", "check": "identity"},
            {"id": "ISO-3", "name": "Cryptography", "check": "security"},
            {"id": "ISO-4", "name": "Operations security", "check": "management"},
            {"id": "ISO-5", "name": "Communications security", "check": "security"},
        ],
        "FERPA": [
            {"id": "FERPA-1", "name": "Student records access control", "check": "identity"},
            {"id": "FERPA-2", "name": "Audit logging of record access", "check": "management"},
            {"id": "FERPA-3", "name": "Data protection", "check": "security"},
        ],
        "GDPR": [
            {"id": "GDPR-1", "name": "Data protection by design", "check": "security"},
            {"id": "GDPR-2", "name": "Right to erasure", "check": "governance"},
            {"id": "GDPR-3", "name": "Data breach notification", "check": "management"},
            {"id": "GDPR-4", "name": "Data encryption", "check": "security"},
        ],
        "LGPD": [
            {"id": "LGPD-1", "name": "Data subject rights", "check": "governance"},
            {"id": "LGPD-2", "name": "Data protection officer", "check": "governance"},
            {"id": "LGPD-3", "name": "Security measures", "check": "security"},
        ],
        "PIPEDA": [
            {"id": "PIPEDA-1", "name": "Consent management", "check": "governance"},
            {"id": "PIPEDA-2", "name": "Data safeguards", "check": "security"},
            {"id": "PIPEDA-3", "name": "Individual access rights", "check": "identity"},
        ],
    }

    # -----------------------------------------------------------------------
    # Predict frameworks
    # -----------------------------------------------------------------------

    def predict_frameworks(
        self,
        industry: str,
        geography: str,
        data_types: list[str] | None = None,
    ) -> list[PredictedFramework]:
        """Return predicted regulatory frameworks for the given context."""
        predictions: dict[str, PredictedFramework] = {}

        # --- Industry ---
        industry_lower = industry.lower()
        for ind_key, frameworks in self.INDUSTRY_FRAMEWORK_MAP.items():
            if ind_key == industry_lower:
                for fw in frameworks:
                    predictions[fw] = PredictedFramework(
                        framework_name=fw,
                        confidence="high",
                        reason=f"Required for {industry} industry",
                        applicable_controls=self._controls_for_framework(fw),
                    )

        # --- Geography ---
        geo_key = self._normalise_geography(geography)
        for g_key, frameworks in self.GEOGRAPHY_FRAMEWORK_MAP.items():
            if g_key.lower() == geo_key.lower():
                for fw in frameworks:
                    if fw in predictions:
                        # Already present — bump confidence if not already high
                        predictions[fw].confidence = "high"
                        predictions[fw].reason += f"; also required in {geography} geography"
                    else:
                        predictions[fw] = PredictedFramework(
                            framework_name=fw,
                            confidence="high",
                            reason=f"Required in {geography} geography",
                            applicable_controls=self._controls_for_framework(fw),
                        )

        # --- Data types ---
        if data_types:
            for dt in data_types:
                dt_lower = dt.lower()
                for dt_key, controls in self.DATA_TYPE_CONTROLS.items():
                    if dt_key.lower() == dt_lower:
                        # Data types may imply additional frameworks
                        implied = self._frameworks_for_data_type(dt_key)
                        for fw in implied:
                            if fw not in predictions:
                                predictions[fw] = PredictedFramework(
                                    framework_name=fw,
                                    confidence="medium",
                                    reason=f"Implied by handling {dt_key} data",
                                    applicable_controls=controls,
                                )

        return list(predictions.values())

    # -----------------------------------------------------------------------
    # Gap analysis
    # -----------------------------------------------------------------------

    def analyze_gaps(
        self,
        architecture: dict,
        frameworks: list[str],
    ) -> list[FrameworkGapAnalysis]:
        """Analyse architecture against a list of frameworks, returning gap details."""
        results: list[FrameworkGapAnalysis] = []

        for fw_name in frameworks:
            controls = self.FRAMEWORK_CONTROLS.get(fw_name, [])
            if not controls:
                results.append(
                    FrameworkGapAnalysis(
                        framework_name=fw_name,
                        total_controls=0,
                        satisfied=0,
                        partial=0,
                        gaps=0,
                        gap_details=[],
                    )
                )
                continue

            satisfied_count = 0
            partial_count = 0
            gap_count = 0
            gap_details: list[ControlGap] = []

            for ctrl in controls:
                status = self._check_control(architecture, ctrl)
                if status == ControlStatus.satisfied:
                    satisfied_count += 1
                elif status == ControlStatus.partial:
                    partial_count += 1
                    gap_details.append(
                        ControlGap(
                            control_id=ctrl["id"],
                            control_name=ctrl["name"],
                            status=ControlStatus.partial,
                            gap_description=f"{ctrl['name']} is partially configured",
                            remediation=self._remediation_for_control(ctrl),
                        )
                    )
                else:
                    gap_count += 1
                    gap_details.append(
                        ControlGap(
                            control_id=ctrl["id"],
                            control_name=ctrl["name"],
                            status=ControlStatus.gap,
                            gap_description=f"{ctrl['name']} is not implemented",
                            remediation=self._remediation_for_control(ctrl),
                        )
                    )

            results.append(
                FrameworkGapAnalysis(
                    framework_name=fw_name,
                    total_controls=len(controls),
                    satisfied=satisfied_count,
                    partial=partial_count,
                    gaps=gap_count,
                    gap_details=gap_details,
                )
            )

        return results

    # -----------------------------------------------------------------------
    # Remediation recommendations
    # -----------------------------------------------------------------------

    def get_remediation_recommendations(
        self,
        gaps: list[FrameworkGapAnalysis],
    ) -> list[Recommendation]:
        """Generate remediation recommendations from gap analysis results."""
        recommendations: list[Recommendation] = []
        seen_remediations: set[str] = set()

        for analysis in gaps:
            for detail in analysis.gap_details:
                if detail.status == ControlStatus.satisfied:
                    continue
                # Deduplicate similar remediations
                key = detail.remediation
                if key in seen_remediations:
                    # Update existing recommendation to address this framework too
                    for rec in recommendations:
                        if rec.description == detail.remediation:
                            if analysis.framework_name not in rec.frameworks_addressed:
                                rec.frameworks_addressed.append(analysis.framework_name)
                            break
                    continue
                seen_remediations.add(key)

                priority = "high" if detail.status == ControlStatus.gap else "medium"
                recommendations.append(
                    Recommendation(
                        priority=priority,
                        description=detail.remediation,
                        architecture_changes=self._architecture_change_for(detail),
                        frameworks_addressed=[analysis.framework_name],
                    )
                )

        # Sort: high priority first
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda r: priority_order.get(r.priority, 2))
        return recommendations

    # -----------------------------------------------------------------------
    # AI-enhanced prediction
    # -----------------------------------------------------------------------

    async def predict_with_ai(
        self,
        industry: str,
        geography: str,
        data_types: list[str] | None = None,
    ) -> dict:
        """Return AI-enhanced predictions with overlapping framework analysis."""
        # Always start with rule-based predictions
        base_predictions = self.predict_frameworks(industry, geography, data_types)

        try:
            from app.services.ai_foundry import ai_client

            if not ai_client.is_configured:
                return self._mock_ai_enhanced(base_predictions, industry, geography)

            from app.services.prompts import (
                REGULATORY_ANALYSIS_SYSTEM_PROMPT,
                REGULATORY_ANALYSIS_USER_TEMPLATE,
            )

            user_prompt = REGULATORY_ANALYSIS_USER_TEMPLATE.format(
                industry=industry,
                geography=geography,
                data_types=", ".join(data_types) if data_types else "none specified",
                base_frameworks=", ".join(p.framework_name for p in base_predictions),
            )

            response = ai_client.generate_completion(
                REGULATORY_ANALYSIS_SYSTEM_PROMPT,
                user_prompt,
                temperature=0.1,
            )

            ai_result = json.loads(response)
            return {
                "predictions": [p.model_dump() for p in base_predictions],
                "ai_enhanced": True,
                "overlapping_controls": ai_result.get("overlapping_controls", []),
                "risk_prioritization": ai_result.get("risk_prioritization", []),
                "additional_recommendations": ai_result.get("additional_recommendations", []),
            }
        except Exception as exc:
            logger.error("AI-enhanced regulatory prediction failed: %s", exc)
            return self._mock_ai_enhanced(base_predictions, industry, geography)

    # -----------------------------------------------------------------------
    # Auto-apply policies
    # -----------------------------------------------------------------------

    def auto_apply_policies(
        self,
        architecture: dict,
        frameworks: list[str],
    ) -> dict:
        """Add Azure Policy assignments to architecture for the given frameworks."""
        result = dict(architecture)
        governance = dict(result.get("governance", {}))
        existing_policies = list(governance.get("policies", []))

        existing_names = {p.get("name", "") for p in existing_policies}

        for fw_name in frameworks:
            policies = self._policies_for_framework(fw_name)
            for pol in policies:
                if pol["name"] not in existing_names:
                    existing_policies.append(pol)
                    existing_names.add(pol["name"])

        governance["policies"] = existing_policies
        result["governance"] = governance

        return result

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _controls_for_framework(self, framework: str) -> list[str]:
        """Return control IDs for a framework."""
        controls = self.FRAMEWORK_CONTROLS.get(framework, [])
        return [c["id"] for c in controls]

    @staticmethod
    def _normalise_geography(geography: str) -> str:
        """Normalise geography input to match map keys."""
        mapping = {
            "eu": "EU",
            "europe": "EU",
            "european union": "EU",
            "california": "California",
            "ca": "California",
            "brazil": "Brazil",
            "br": "Brazil",
            "canada": "Canada",
            "ca-country": "Canada",
            "global": "global",
            "worldwide": "global",
        }
        return mapping.get(geography.lower(), geography)

    @staticmethod
    def _frameworks_for_data_type(data_type: str) -> list[str]:
        """Return frameworks implied by a data type."""
        mapping = {
            "PII": ["GDPR", "CCPA"],
            "PHI": ["HIPAA"],
            "financial": ["PCI-DSS", "SOX"],
        }
        return mapping.get(data_type, [])

    def _check_control(self, architecture: dict, control: dict) -> ControlStatus:
        """Check if a control is satisfied by the architecture."""
        check_area = control.get("check", "")

        if check_area == "security":
            security = architecture.get("security", {})
            if not security:
                return ControlStatus.gap
            # Check basic security posture
            has_defender = security.get("defender_for_cloud", False)
            has_firewall = security.get("azure_firewall", False)
            has_encryption = security.get("key_vault_per_subscription", False)
            score = sum([has_defender, has_firewall, has_encryption])
            if score >= 2:
                return ControlStatus.satisfied
            if score >= 1:
                return ControlStatus.partial
            return ControlStatus.gap

        if check_area == "identity":
            identity = architecture.get("identity", {})
            if not identity:
                return ControlStatus.gap
            has_rbac = bool(identity.get("rbac_model"))
            has_mfa = bool(identity.get("mfa_policy")) or identity.get("conditional_access", False)
            if has_rbac and has_mfa:
                return ControlStatus.satisfied
            if has_rbac or has_mfa:
                return ControlStatus.partial
            return ControlStatus.gap

        if check_area == "management":
            management = architecture.get("management", {})
            if not management:
                return ControlStatus.gap
            has_logging = bool(management.get("log_analytics"))
            has_monitoring = bool(management.get("monitoring"))
            has_backup = bool(management.get("backup"))
            score = sum([has_logging, has_monitoring, has_backup])
            if score >= 2:
                return ControlStatus.satisfied
            if score >= 1:
                return ControlStatus.partial
            return ControlStatus.gap

        if check_area == "governance":
            governance = architecture.get("governance", {})
            if not governance:
                return ControlStatus.gap
            has_policies = bool(governance.get("policies"))
            has_tags = bool(governance.get("tagging_strategy"))
            if has_policies and has_tags:
                return ControlStatus.satisfied
            if has_policies or has_tags:
                return ControlStatus.partial
            return ControlStatus.gap

        return ControlStatus.gap

    @staticmethod
    def _remediation_for_control(control: dict) -> str:
        """Return a remediation suggestion for a control."""
        check = control.get("check", "")
        remediations = {
            "security": (
                "Enable Azure Defender, configure Azure Firewall, "
                "and ensure Key Vault is deployed per subscription"
            ),
            "identity": "Configure RBAC with least-privilege model and enable MFA via conditional access policies",
            "management": "Deploy Log Analytics workspace, enable Azure Monitor, and configure backup policies",
            "governance": "Define Azure Policy assignments and enforce mandatory tagging strategy",
        }
        return remediations.get(check, f"Review and implement {control.get('name', 'control')}")

    @staticmethod
    def _architecture_change_for(detail: ControlGap) -> str:
        """Describe the architecture change needed to close a gap."""
        name_lower = detail.control_name.lower()
        if "encrypt" in name_lower or "cryptograph" in name_lower:
            return "Add Key Vault resource and enable encryption at rest for all storage and database resources"
        if "access" in name_lower or "rbac" in name_lower:
            return "Configure Entra ID with RBAC, PIM, and conditional access policies"
        if "audit" in name_lower or "log" in name_lower or "monitor" in name_lower:
            return "Deploy Log Analytics workspace and enable diagnostic settings on all resources"
        if "firewall" in name_lower or "network" in name_lower:
            return "Deploy Azure Firewall and configure NSG rules for all subnets"
        if "backup" in name_lower or "recovery" in name_lower:
            return "Enable Azure Backup with appropriate retention policies"
        if "policy" in name_lower or "governance" in name_lower or "change" in name_lower:
            return "Define and assign Azure Policy definitions for required compliance controls"
        return f"Implement {detail.control_name} in the architecture"

    @staticmethod
    def _mock_ai_enhanced(
        base_predictions: list[PredictedFramework],
        industry: str,
        geography: str,
    ) -> dict:
        """Return mock AI-enhanced results for dev mode."""
        framework_names = [p.framework_name for p in base_predictions]
        return {
            "predictions": [p.model_dump() for p in base_predictions],
            "ai_enhanced": True,
            "overlapping_controls": [
                {
                    "control_area": "Access Control",
                    "frameworks": framework_names[:2] if len(framework_names) >= 2 else framework_names,
                    "description": "Multiple frameworks require identity and access management controls",
                },
                {
                    "control_area": "Encryption",
                    "frameworks": framework_names[:3] if len(framework_names) >= 3 else framework_names,
                    "description": "Data encryption requirements overlap across frameworks",
                },
            ],
            "risk_prioritization": [
                {
                    "framework": fw,
                    "risk_level": "high" if i == 0 else "medium",
                    "reason": f"Primary regulatory requirement for {industry} in {geography}",
                }
                for i, fw in enumerate(framework_names)
            ],
            "additional_recommendations": [
                "Consider unified compliance monitoring with Azure Policy compliance dashboard",
                "Implement automated compliance evidence collection for audit readiness",
            ],
        }

    @staticmethod
    def _policies_for_framework(framework: str) -> list[dict]:
        """Return Azure Policy definitions applicable to a framework."""
        policies: dict[str, list[dict]] = {
            "HIPAA": [
                {
                    "name": "hipaa-encryption-at-rest",
                    "scope": "/",
                    "effect": "Audit",
                    "description": "Ensure encryption at rest for HIPAA compliance",
                },
                {
                    "name": "hipaa-audit-logging",
                    "scope": "/",
                    "effect": "AuditIfNotExists",
                    "description": "Ensure diagnostic logging for HIPAA compliance",
                },
            ],
            "HITRUST": [
                {
                    "name": "hitrust-information-protection",
                    "scope": "/",
                    "effect": "Audit",
                    "description": "HITRUST information protection controls",
                },
            ],
            "PCI-DSS": [
                {
                    "name": "pci-firewall-config",
                    "scope": "/",
                    "effect": "Deny",
                    "description": "Enforce firewall for PCI-DSS requirement 1",
                },
                {
                    "name": "pci-encryption",
                    "scope": "/",
                    "effect": "Audit",
                    "description": "Ensure cardholder data encryption for PCI-DSS",
                },
            ],
            "SOX": [
                {
                    "name": "sox-audit-trail",
                    "scope": "/",
                    "effect": "AuditIfNotExists",
                    "description": "Ensure audit trail for SOX compliance",
                },
            ],
            "GLBA": [
                {
                    "name": "glba-data-protection",
                    "scope": "/",
                    "effect": "Audit",
                    "description": "GLBA customer data protection controls",
                },
            ],
            "FedRAMP": [
                {
                    "name": "fedramp-access-control",
                    "scope": "/",
                    "effect": "Audit",
                    "description": "FedRAMP access control (AC) family",
                },
                {
                    "name": "fedramp-audit-accountability",
                    "scope": "/",
                    "effect": "AuditIfNotExists",
                    "description": "FedRAMP audit and accountability (AU) family",
                },
            ],
            "NIST 800-171": [
                {
                    "name": "nist-171-access-control",
                    "scope": "/",
                    "effect": "Audit",
                    "description": "NIST 800-171 access control requirements",
                },
            ],
            "CCPA": [
                {
                    "name": "ccpa-data-encryption",
                    "scope": "/",
                    "effect": "Audit",
                    "description": "Ensure data encryption for CCPA compliance",
                },
            ],
            "SOC 2": [
                {
                    "name": "soc2-logical-access",
                    "scope": "/",
                    "effect": "Audit",
                    "description": "SOC 2 logical access controls",
                },
                {
                    "name": "soc2-monitoring",
                    "scope": "/",
                    "effect": "AuditIfNotExists",
                    "description": "SOC 2 system monitoring requirements",
                },
            ],
            "ISO 27001": [
                {
                    "name": "iso27001-security-policies",
                    "scope": "/",
                    "effect": "Audit",
                    "description": "ISO 27001 information security policy controls",
                },
            ],
            "FERPA": [
                {
                    "name": "ferpa-access-control",
                    "scope": "/",
                    "effect": "Audit",
                    "description": "FERPA student records access controls",
                },
            ],
            "GDPR": [
                {
                    "name": "gdpr-data-protection",
                    "scope": "/",
                    "effect": "Audit",
                    "description": "GDPR data protection by design controls",
                },
                {
                    "name": "gdpr-encryption",
                    "scope": "/",
                    "effect": "Audit",
                    "description": "GDPR data encryption requirements",
                },
            ],
            "LGPD": [
                {
                    "name": "lgpd-security-measures",
                    "scope": "/",
                    "effect": "Audit",
                    "description": "LGPD security measures controls",
                },
            ],
            "PIPEDA": [
                {
                    "name": "pipeda-safeguards",
                    "scope": "/",
                    "effect": "Audit",
                    "description": "PIPEDA data safeguard requirements",
                },
            ],
        }
        return policies.get(framework, [])


# Module-level singleton
regulatory_predictor = RegulatoryPredictor()

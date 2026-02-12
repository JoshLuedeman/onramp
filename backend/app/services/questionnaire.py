"""Adaptive questionnaire engine for CAF landing zone design."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# CAF Design Areas and their questions
CAF_QUESTIONS: list[dict[str, Any]] = [
    # --- 1. Organization & Billing ---
    {
        "id": "org_name",
        "category": "organization",
        "caf_area": "billing_tenant",
        "text": "What is your organization's name?",
        "type": "text",
        "required": True,
        "order": 1,
    },
    {
        "id": "org_size",
        "category": "organization",
        "caf_area": "billing_tenant",
        "text": "How would you describe your organization's size?",
        "type": "single_choice",
        "options": [
            {"value": "small", "label": "Small (1-100 employees)"},
            {"value": "medium", "label": "Medium (100-1,000 employees)"},
            {"value": "large", "label": "Large (1,000-10,000 employees)"},
            {"value": "enterprise", "label": "Enterprise (10,000+ employees)"},
        ],
        "required": True,
        "order": 2,
    },
    {
        "id": "azure_experience",
        "category": "organization",
        "caf_area": "billing_tenant",
        "text": "What is your organization's current experience with Azure?",
        "type": "single_choice",
        "options": [
            {"value": "none", "label": "No Azure experience — starting fresh"},
            {"value": "poc", "label": "Proof of concept / sandbox only"},
            {"value": "some", "label": "Some workloads in Azure (< 10 subscriptions)"},
            {"value": "significant", "label": "Significant presence (10+ subscriptions)"},
        ],
        "required": True,
        "order": 3,
    },
    {
        "id": "subscription_count",
        "category": "organization",
        "caf_area": "billing_tenant",
        "text": "How many Azure subscriptions do you anticipate needing?",
        "type": "single_choice",
        "options": [
            {"value": "1-3", "label": "1-3 subscriptions"},
            {"value": "4-10", "label": "4-10 subscriptions"},
            {"value": "11-50", "label": "11-50 subscriptions"},
            {"value": "50+", "label": "50+ subscriptions"},
        ],
        "required": True,
        "order": 4,
    },
    # --- 2. Identity & Access ---
    {
        "id": "identity_provider",
        "category": "identity",
        "caf_area": "identity_access",
        "text": "What identity provider does your organization currently use?",
        "type": "single_choice",
        "options": [
            {"value": "entra_id", "label": "Microsoft Entra ID (Azure AD)"},
            {"value": "on_prem_ad", "label": "On-premises Active Directory"},
            {"value": "hybrid", "label": "Hybrid (AD + Entra ID synced)"},
            {"value": "third_party", "label": "Third-party IdP (Okta, Ping, etc.)"},
            {"value": "none", "label": "No centralized identity provider"},
        ],
        "required": True,
        "order": 10,
    },
    {
        "id": "pim_required",
        "category": "identity",
        "caf_area": "identity_access",
        "text": "Do you need Privileged Identity Management (PIM) for just-in-time admin access?",
        "type": "single_choice",
        "options": [
            {"value": "yes", "label": "Yes — require PIM for all privileged roles"},
            {"value": "later", "label": "Not now, but plan to enable later"},
            {"value": "no", "label": "No — not required"},
        ],
        "required": True,
        "order": 11,
    },
    {
        "id": "mfa_requirement",
        "category": "identity",
        "caf_area": "identity_access",
        "text": "What is your multi-factor authentication (MFA) requirement?",
        "type": "single_choice",
        "options": [
            {"value": "all_users", "label": "MFA required for all users"},
            {"value": "admins_only", "label": "MFA required for administrators only"},
            {"value": "conditional", "label": "Conditional — based on risk/location"},
            {"value": "none", "label": "No MFA requirement currently"},
        ],
        "required": True,
        "order": 12,
    },
    # --- 3. Resource Organization ---
    {
        "id": "management_group_strategy",
        "category": "resource_organization",
        "caf_area": "resource_organization",
        "text": "How do you want to organize your management group hierarchy?",
        "type": "single_choice",
        "options": [
            {"value": "caf_recommended", "label": "CAF recommended (Platform + Landing Zones + Sandbox)"},
            {"value": "by_business_unit", "label": "By business unit / department"},
            {"value": "by_environment", "label": "By environment (Dev/Test/Prod)"},
            {"value": "help_decide", "label": "Help me decide based on my requirements"},
        ],
        "required": True,
        "order": 20,
    },
    {
        "id": "naming_convention",
        "category": "resource_organization",
        "caf_area": "resource_organization",
        "text": "Do you have an existing resource naming convention?",
        "type": "single_choice",
        "options": [
            {"value": "existing", "label": "Yes — we have an established convention"},
            {"value": "caf_standard", "label": "No — use Azure CAF recommended naming"},
            {"value": "custom", "label": "No — help us define a custom convention"},
        ],
        "required": True,
        "order": 21,
    },
    # --- 4. Network Topology ---
    {
        "id": "network_topology",
        "category": "networking",
        "caf_area": "network_connectivity",
        "text": "What network topology do you prefer?",
        "type": "single_choice",
        "options": [
            {"value": "hub_spoke", "label": "Hub-spoke (traditional, most common)"},
            {"value": "vwan", "label": "Azure Virtual WAN (managed hub, global transit)"},
            {"value": "mesh", "label": "Full mesh (direct peering between VNets)"},
            {"value": "help_decide", "label": "Help me decide"},
        ],
        "required": True,
        "order": 30,
    },
    {
        "id": "hybrid_connectivity",
        "category": "networking",
        "caf_area": "network_connectivity",
        "text": "Do you need hybrid connectivity to on-premises networks?",
        "type": "single_choice",
        "options": [
            {"value": "expressroute", "label": "Yes — via ExpressRoute (dedicated circuit)"},
            {"value": "vpn", "label": "Yes — via Site-to-Site VPN"},
            {"value": "both", "label": "Yes — both ExpressRoute and VPN (redundancy)"},
            {"value": "no", "label": "No — cloud-only deployment"},
        ],
        "required": True,
        "order": 31,
    },
    {
        "id": "dns_strategy",
        "category": "networking",
        "caf_area": "network_connectivity",
        "text": "How will you manage DNS?",
        "type": "single_choice",
        "options": [
            {"value": "azure_dns", "label": "Azure DNS (cloud-native)"},
            {"value": "hybrid_dns", "label": "Hybrid DNS (Azure + on-premises resolution)"},
            {"value": "external", "label": "External DNS provider"},
            {"value": "help_decide", "label": "Help me decide"},
        ],
        "required": True,
        "order": 32,
    },
    # --- 5. Security ---
    {
        "id": "security_level",
        "category": "security",
        "caf_area": "security",
        "text": "What level of security controls do you need?",
        "type": "single_choice",
        "options": [
            {"value": "standard", "label": "Standard — Microsoft recommended baselines"},
            {"value": "enhanced", "label": "Enhanced — additional controls and monitoring"},
            {"value": "high", "label": "High security — strict controls, air-gapped where possible"},
        ],
        "required": True,
        "order": 40,
    },
    {
        "id": "siem_integration",
        "category": "security",
        "caf_area": "security",
        "text": "Do you need SIEM (Security Information and Event Management)?",
        "type": "single_choice",
        "options": [
            {"value": "sentinel", "label": "Yes — Microsoft Sentinel"},
            {"value": "existing_siem", "label": "Yes — integrate with existing SIEM (Splunk, QRadar, etc.)"},
            {"value": "both", "label": "Yes — Sentinel + existing SIEM"},
            {"value": "no", "label": "Not at this time"},
        ],
        "required": True,
        "order": 41,
    },
    # --- 6. Management ---
    {
        "id": "monitoring_strategy",
        "category": "management",
        "caf_area": "management",
        "text": "How do you want to handle monitoring and observability?",
        "type": "single_choice",
        "options": [
            {"value": "azure_native", "label": "Azure Monitor + Log Analytics (recommended)"},
            {"value": "third_party", "label": "Third-party tools (Datadog, New Relic, etc.)"},
            {"value": "hybrid", "label": "Both Azure native and third-party"},
        ],
        "required": True,
        "order": 50,
    },
    {
        "id": "backup_dr",
        "category": "management",
        "caf_area": "management",
        "text": "What are your backup and disaster recovery requirements?",
        "type": "single_choice",
        "options": [
            {"value": "basic", "label": "Basic — standard Azure Backup policies"},
            {"value": "geo_redundant", "label": "Geo-redundant — cross-region backup and DR"},
            {"value": "comprehensive", "label": "Comprehensive — multi-region active-active"},
            {"value": "help_decide", "label": "Help me decide"},
        ],
        "required": True,
        "order": 51,
    },
    # --- 7. Governance ---
    {
        "id": "tagging_strategy",
        "category": "governance",
        "caf_area": "governance",
        "text": "What mandatory resource tags do you need?",
        "type": "multi_choice",
        "options": [
            {"value": "environment", "label": "Environment (Dev/Test/Prod)"},
            {"value": "cost_center", "label": "Cost Center"},
            {"value": "owner", "label": "Owner / Team"},
            {"value": "application", "label": "Application Name"},
            {"value": "data_classification", "label": "Data Classification"},
            {"value": "business_unit", "label": "Business Unit"},
            {"value": "project", "label": "Project / Initiative"},
        ],
        "required": True,
        "order": 60,
    },
    {
        "id": "cost_management",
        "category": "governance",
        "caf_area": "governance",
        "text": "How important is cost management and optimization?",
        "type": "single_choice",
        "options": [
            {"value": "critical", "label": "Critical — need budgets, alerts, and optimization recommendations"},
            {"value": "important", "label": "Important — need budgets and basic alerts"},
            {"value": "standard", "label": "Standard — track costs but no strict budgets"},
        ],
        "required": True,
        "order": 61,
    },
    # --- 8. Platform Automation ---
    {
        "id": "iac_tool",
        "category": "automation",
        "caf_area": "platform_automation",
        "text": "What Infrastructure as Code (IaC) tooling does your team prefer?",
        "type": "single_choice",
        "options": [
            {"value": "bicep", "label": "Bicep (Azure-native, recommended)"},
            {"value": "terraform", "label": "Terraform"},
            {"value": "arm", "label": "ARM Templates"},
            {"value": "none", "label": "No IaC experience — help us choose"},
        ],
        "required": True,
        "order": 70,
    },
    {
        "id": "cicd_platform",
        "category": "automation",
        "caf_area": "platform_automation",
        "text": "What CI/CD platform do you use or plan to use?",
        "type": "single_choice",
        "options": [
            {"value": "github_actions", "label": "GitHub Actions"},
            {"value": "azure_devops", "label": "Azure DevOps Pipelines"},
            {"value": "gitlab", "label": "GitLab CI/CD"},
            {"value": "jenkins", "label": "Jenkins"},
            {"value": "none", "label": "No CI/CD platform yet"},
        ],
        "required": True,
        "order": 71,
    },
    # --- Compliance / Industry ---
    {
        "id": "industry",
        "category": "compliance",
        "caf_area": "governance",
        "text": "What industry does your organization operate in?",
        "type": "single_choice",
        "options": [
            {"value": "healthcare", "label": "Healthcare"},
            {"value": "financial_services", "label": "Financial Services / Banking"},
            {"value": "government", "label": "Government / Public Sector"},
            {"value": "retail", "label": "Retail / E-Commerce"},
            {"value": "manufacturing", "label": "Manufacturing"},
            {"value": "technology", "label": "Technology / SaaS"},
            {"value": "education", "label": "Education"},
            {"value": "other", "label": "Other"},
        ],
        "required": True,
        "order": 80,
    },
    {
        "id": "compliance_frameworks",
        "category": "compliance",
        "caf_area": "governance",
        "text": "Which compliance frameworks must your Azure environment comply with?",
        "type": "multi_choice",
        "options": [
            {"value": "soc2", "label": "SOC 2"},
            {"value": "hipaa", "label": "HIPAA"},
            {"value": "pci_dss", "label": "PCI-DSS"},
            {"value": "fedramp", "label": "FedRAMP"},
            {"value": "nist_800_53", "label": "NIST 800-53"},
            {"value": "iso_27001", "label": "ISO 27001"},
            {"value": "gdpr", "label": "GDPR"},
            {"value": "none", "label": "No specific compliance requirements"},
        ],
        "required": True,
        "order": 81,
    },
    {
        "id": "data_residency",
        "category": "compliance",
        "caf_area": "governance",
        "text": "Do you have data residency requirements?",
        "type": "single_choice",
        "options": [
            {"value": "us_only", "label": "United States only"},
            {"value": "eu_only", "label": "European Union only"},
            {"value": "specific_region", "label": "Specific region(s) — will specify"},
            {"value": "no", "label": "No data residency requirements"},
        ],
        "required": True,
        "order": 82,
    },
    # --- Primary Azure Region ---
    {
        "id": "primary_region",
        "category": "organization",
        "caf_area": "network_connectivity",
        "text": "What is your primary Azure region?",
        "type": "single_choice",
        "options": [
            {"value": "eastus", "label": "East US"},
            {"value": "eastus2", "label": "East US 2"},
            {"value": "westus2", "label": "West US 2"},
            {"value": "westus3", "label": "West US 3"},
            {"value": "centralus", "label": "Central US"},
            {"value": "northeurope", "label": "North Europe"},
            {"value": "westeurope", "label": "West Europe"},
            {"value": "uksouth", "label": "UK South"},
            {"value": "southeastasia", "label": "Southeast Asia"},
            {"value": "australiaeast", "label": "Australia East"},
        ],
        "required": True,
        "order": 5,
    },
]


class QuestionnaireService:
    """Service for managing the adaptive questionnaire flow."""

    def get_all_questions(self) -> list[dict]:
        """Get all questions sorted by order."""
        return sorted(CAF_QUESTIONS, key=lambda q: q["order"])

    def get_categories(self) -> list[dict]:
        """Get question categories with counts."""
        categories: dict[str, dict] = {}
        for q in CAF_QUESTIONS:
            cat = q["category"]
            if cat not in categories:
                categories[cat] = {
                    "id": cat,
                    "name": cat.replace("_", " ").title(),
                    "caf_area": q["caf_area"],
                    "question_count": 0,
                }
            categories[cat]["question_count"] += 1
        return list(categories.values())

    def get_questions_for_category(self, category: str) -> list[dict]:
        """Get questions for a specific category."""
        return sorted(
            [q for q in CAF_QUESTIONS if q["category"] == category],
            key=lambda q: q["order"],
        )

    def get_next_question(
        self, answered_questions: dict[str, str], org_size: str | None = None
    ) -> dict | None:
        """Get the next unanswered question based on current answers and branching logic."""
        all_questions = self.get_all_questions()

        for question in all_questions:
            if question["id"] in answered_questions:
                continue

            # Check org size filtering
            if question.get("min_org_size"):
                size_order = {"small": 0, "medium": 1, "large": 2, "enterprise": 3}
                if org_size and size_order.get(org_size, 0) < size_order.get(
                    question["min_org_size"], 0
                ):
                    continue

            return question

        return None  # All questions answered

    def get_progress(self, answered_questions: dict[str, str]) -> dict:
        """Calculate questionnaire completion progress."""
        total = len(CAF_QUESTIONS)
        answered = len(
            [q for q in CAF_QUESTIONS if q["id"] in answered_questions]
        )
        return {
            "total": total,
            "answered": answered,
            "remaining": total - answered,
            "percent_complete": round((answered / total) * 100) if total > 0 else 0,
        }

    def validate_answer(self, question_id: str, answer: str | list[str]) -> bool:
        """Validate an answer against a question's constraints."""
        question = next((q for q in CAF_QUESTIONS if q["id"] == question_id), None)
        if question is None:
            return False

        if question["type"] == "text":
            return isinstance(answer, str) and len(answer.strip()) > 0

        if question["type"] == "single_choice":
            valid_values = [opt["value"] for opt in question.get("options", [])]
            return answer in valid_values

        if question["type"] == "multi_choice":
            if not isinstance(answer, list):
                return False
            valid_values = [opt["value"] for opt in question.get("options", [])]
            return all(a in valid_values for a in answer)

        return True


# Singleton
questionnaire_service = QuestionnaireService()

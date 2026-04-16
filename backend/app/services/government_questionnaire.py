"""Government-specific questionnaire extensions.

Provides additional questions for users who select Azure Government cloud,
covering Impact Level, DoD classification, FedRAMP authorization, ITAR
compliance, and Government region selection.  Also applies Government
constraints to generated architectures.
"""

from __future__ import annotations

import logging

from app.services.government_regions import government_region_service

logger = logging.getLogger(__name__)

# ── Government-Specific Questions ────────────────────────────────────────────

GOVERNMENT_QUESTIONS: list[dict] = [
    {
        "id": "gov_impact_level",
        "text": "What is your Impact Level (IL)?",
        "type": "single_choice",
        "options": [
            {"value": "IL2", "label": "IL2 — Non-Controlled Unclassified Information"},
            {"value": "IL4", "label": "IL4 — Controlled Unclassified Information"},
            {"value": "IL5", "label": "IL5 — Higher Sensitivity CUI & National Security Systems"},
            {"value": "IL6", "label": "IL6 — Classified (SECRET)"},
        ],
        "required": True,
        "category": "government",
        "help_text": "Impact Level determines the security controls applied.",
    },
    {
        "id": "gov_dod_workload",
        "text": "Is this a DoD workload?",
        "type": "single_choice",
        "options": [
            {"value": "yes", "label": "Yes"},
            {"value": "no", "label": "No"},
        ],
        "required": True,
        "category": "government",
        "help_text": "DoD workloads require DoD-specific regions and controls.",
    },
    {
        "id": "gov_fedramp_level",
        "text": "FedRAMP authorization level?",
        "type": "single_choice",
        "options": [
            {"value": "high", "label": "High"},
            {"value": "moderate", "label": "Moderate"},
            {"value": "low", "label": "Low"},
        ],
        "required": True,
        "category": "government",
        "help_text": "Determines the baseline set of security controls.",
    },
    {
        "id": "gov_itar",
        "text": "Do you need ITAR compliance?",
        "type": "single_choice",
        "options": [
            {"value": "yes", "label": "Yes"},
            {"value": "no", "label": "No"},
        ],
        "required": True,
        "category": "government",
        "help_text": (
            "International Traffic in Arms Regulations — restricts data "
            "access to US persons only."
        ),
    },
    {
        "id": "gov_region",
        "text": "Which Government region?",
        "type": "single_choice",
        "options": [
            {
                "value": r["name"],
                "label": r["display_name"],
                "group": "DoD" if r["restricted"] else "Non-DoD",
            }
            for r in government_region_service.get_regions()
        ],
        "required": True,
        "category": "government",
        "help_text": "Select the Azure Government region for deployment.",
    },
]


class GovernmentQuestionnaireService:
    """Extends the base questionnaire with Government-specific questions."""

    def get_government_questions(self) -> list[dict]:
        """Return the full list of Government-specific questions.

        Returns:
            List of question dicts ready for the questionnaire engine.
        """
        return [dict(q) for q in GOVERNMENT_QUESTIONS]

    def should_show_government_questions(self, answers: dict) -> bool:
        """Determine whether Government questions should be displayed.

        Args:
            answers: Current user answers from the questionnaire.

        Returns:
            ``True`` if the user selected the Government cloud environment.
        """
        cloud_env = answers.get("cloud_environment", "")
        if isinstance(cloud_env, str):
            return cloud_env.lower() == "government"
        return False

    def apply_government_constraints(
        self,
        architecture: dict,
        gov_answers: dict,
    ) -> dict:
        """Modify an architecture based on Government questionnaire answers.

        Applies region restrictions, compliance settings, DoD requirements,
        and ITAR constraints to the supplied architecture dict.

        Args:
            architecture: Base architecture dict to modify.
            gov_answers: Government-specific questionnaire answers.

        Returns:
            Updated architecture dict with Government constraints applied.
        """
        result = dict(architecture)

        # Apply impact level
        impact_level = gov_answers.get("gov_impact_level", "IL2")
        result.setdefault("compliance", {})
        result["compliance"]["impact_level"] = impact_level

        # Apply FedRAMP level
        fedramp_level = gov_answers.get("gov_fedramp_level", "high")
        result["compliance"]["fedramp_level"] = fedramp_level

        # Apply region
        region = gov_answers.get("gov_region", "usgovvirginia")
        result["region"] = region
        paired = government_region_service.get_paired_region(region)
        if paired:
            result["paired_region"] = paired

        # Apply DoD constraints
        is_dod = gov_answers.get("gov_dod_workload", "no").lower() == "yes"
        result["compliance"]["dod_workload"] = is_dod
        if is_dod:
            region_info = government_region_service.get_region(region)
            if region_info and not region_info["restricted"]:
                # Recommend a DoD region when DoD workload in non-DoD region
                dod_regions = government_region_service.get_dod_regions()
                if dod_regions:
                    result.setdefault("warnings", []).append(
                        f"DoD workload in non-DoD region '{region}'. "
                        f"Consider using '{dod_regions[0]['name']}' instead."
                    )

        # Apply ITAR constraints
        is_itar = gov_answers.get("gov_itar", "no").lower() == "yes"
        result["compliance"]["itar_required"] = is_itar
        if is_itar:
            result.setdefault("security", {})
            result["security"]["data_residency"] = "us_only"
            result["security"]["access_restriction"] = "us_persons_only"

        # IL5+ requires encryption at rest and in transit
        if impact_level in ("IL5", "IL6"):
            result.setdefault("security", {})
            result["security"]["encryption_at_rest"] = True
            result["security"]["encryption_in_transit"] = True
            result["security"]["double_encryption"] = True

        # IL6 requires dedicated HSM
        if impact_level == "IL6":
            result.setdefault("security", {})
            result["security"]["dedicated_hsm"] = True
            result["security"]["classification_level"] = "SECRET"

        result["cloud_environment"] = "government"
        return result


government_questionnaire_service = GovernmentQuestionnaireService()

"""Azure China (21Vianet) questionnaire extensions.

Provides additional questions and constraint application logic for
users deploying to Azure China.  Questions cover ICP licensing,
MLPS certification, data residency, region selection, and 21Vianet
support tiers.
"""

import logging

from app.services.china_regions import china_region_service

logger = logging.getLogger(__name__)

# ── Question Definitions ─────────────────────────────────────────────────────

_CHINA_QUESTIONS: list[dict] = [
    {
        "id": "china_icp_license",
        "text": "Do you have an ICP license?",
        "description": (
            "An ICP (Internet Content Provider) license is required for "
            "any website or web-facing service hosted in mainland China."
        ),
        "type": "single_choice",
        "options": [
            {"value": "yes", "label": "Yes"},
            {"value": "no", "label": "No"},
            {"value": "in_progress", "label": "In progress"},
        ],
        "required": True,
        "category": "compliance",
    },
    {
        "id": "china_mlps_level",
        "text": "MLPS certification level?",
        "description": (
            "Multi-Level Protection Scheme (MLPS 2.0) certification level "
            "required for your information systems under GB/T 22239."
        ),
        "type": "single_choice",
        "options": [
            {"value": "level2", "label": "Level 2 - General systems"},
            {"value": "level3", "label": "Level 3 - Important systems"},
            {"value": "level4", "label": "Level 4 - Critical systems"},
        ],
        "required": True,
        "category": "compliance",
    },
    {
        "id": "china_data_residency",
        "text": "Data residency requirement?",
        "description": (
            "Specify where your data must be stored. Mainland China is "
            "required by most regulations; Hong Kong may be included "
            "for certain workloads."
        ),
        "type": "single_choice",
        "options": [
            {
                "value": "mainland_only",
                "label": "Mainland China only",
            },
            {
                "value": "include_hongkong",
                "label": "Hong Kong included",
            },
        ],
        "required": True,
        "category": "data_residency",
    },
    {
        "id": "china_region",
        "text": "Which China region?",
        "description": "Select the primary Azure China region for deployment.",
        "type": "single_choice",
        "options": [
            {"value": r["name"], "label": r["display_name"]}
            for r in china_region_service.get_regions()
        ],
        "required": True,
        "category": "infrastructure",
    },
    {
        "id": "china_support_tier",
        "text": "21Vianet support tier?",
        "description": (
            "Choose the 21Vianet support plan for your Azure China "
            "subscription."
        ),
        "type": "single_choice",
        "options": [
            {"value": "standard", "label": "Standard"},
            {"value": "professional", "label": "Professional"},
            {"value": "premier", "label": "Premier"},
        ],
        "required": False,
        "category": "operations",
    },
]


# ── Service ──────────────────────────────────────────────────────────────────


class ChinaQuestionnaireService:
    """Extends the questionnaire with China-specific questions.

    Determines when China questions should be shown and applies
    China-specific constraints to the generated architecture.
    """

    def get_china_questions(self) -> list[dict]:
        """Return all China-specific questionnaire questions.

        Returns:
            A list of question dicts with ``id``, ``text``,
            ``description``, ``type``, ``options``, ``required``,
            and ``category`` keys.
        """
        return [dict(q) for q in _CHINA_QUESTIONS]

    def should_show_china_questions(self, answers: dict) -> bool:
        """Determine whether the China questions should be displayed.

        Args:
            answers: Current questionnaire answers.  The check looks
                for ``cloud_environment`` equal to ``"china"`` or
                ``environment`` equal to ``"china"``.

        Returns:
            ``True`` if the user selected Azure China, ``False`` otherwise.
        """
        env = answers.get("cloud_environment", answers.get("environment", ""))
        return str(env).lower() == "china"

    def apply_china_constraints(
        self, architecture: dict, china_answers: dict
    ) -> dict:
        """Apply China-specific constraints to an architecture.

        Modifies the architecture in-place by setting region, compliance
        metadata, data residency rules, and ICP status based on the
        user's China-specific answers.

        Args:
            architecture: The architecture dict to modify.
            china_answers: Answers to the China-specific questions.

        Returns:
            The modified architecture dict.
        """
        result = dict(architecture)

        # Set region
        region = china_answers.get("china_region", "chinanorth2")
        if china_region_service.validate_region(region):
            result["region"] = region
            result["paired_region"] = china_region_service.get_paired_region(
                region
            )
        else:
            result["region"] = "chinanorth2"
            result["paired_region"] = "chinaeast2"

        # Set compliance metadata
        mlps_level = china_answers.get("china_mlps_level", "level3")
        result["compliance"] = {
            "framework": "MLPS",
            "level": mlps_level,
            "standard": "GB/T 22239-2019",
        }

        # Set data residency
        residency = china_answers.get(
            "china_data_residency", "mainland_only"
        )
        result["data_residency"] = {
            "requirement": residency,
            "allowed_regions": (
                china_region_service.get_regions()
                if residency == "mainland_only"
                else china_region_service.get_regions()
            ),
        }

        # Set ICP status
        icp_status = china_answers.get("china_icp_license", "no")
        result["icp_license"] = {
            "status": icp_status,
            "required": True,
            "warning": (
                "ICP license is required before deploying web-facing "
                "resources in mainland China"
                if icp_status != "yes"
                else None
            ),
        }

        # Set support tier
        support = china_answers.get("china_support_tier", "standard")
        result["support_tier"] = support

        # Set cloud environment
        result["cloud_environment"] = "china"
        result["operator"] = "21Vianet"

        return result


# Singleton
china_questionnaire_service = ChinaQuestionnaireService()

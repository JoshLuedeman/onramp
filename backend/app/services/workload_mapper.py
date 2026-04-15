"""WorkloadMapper service — maps workloads to target Azure subscriptions."""

import json
import logging
from typing import TYPE_CHECKING

from app.schemas.workload_mapping import WorkloadMapping

if TYPE_CHECKING:
    from app.services.ai_foundry import AIFoundryClient

logger = logging.getLogger(__name__)

# Maximum workloads allowed per subscription before a warning is raised
MAX_WORKLOADS_PER_SUBSCRIPTION = 50

# Criticality → preferred subscription purpose keywords (ordered by preference)
_CRITICALITY_SUBSCRIPTION_HINTS: dict[str, list[str]] = {
    "mission-critical": ["prod", "production", "critical"],
    "business-critical": ["prod", "production", "workload"],
    "standard": ["workload", "prod", "standard"],
    "dev-test": ["dev", "test", "sandbox", "non-prod"],
}

# Compliance requirements that indicate sensitive data subscriptions
_COMPLIANCE_SENSITIVE: set[str] = {"HIPAA", "PCI-DSS", "FedRAMP", "ITAR", "SOC2", "ISO27001"}


def _subscription_id(subscription: dict) -> str:
    """Return a stable identifier for a subscription dict."""
    return subscription.get("id") or subscription.get("name", "unknown")


def _rule_based_mapping(
    workload: dict,
    subscriptions: list[dict],
) -> tuple[dict, float, list[str]]:
    """Map a workload to a subscription using rule-based logic.

    Returns (best_subscription, confidence_score, warnings).
    """
    warnings: list[str] = []
    criticality: str = workload.get("criticality", "standard")
    compliance_reqs: list[str] = workload.get("compliance_requirements") or []
    workload_type: str = workload.get("type", "other")

    # Score each subscription
    scores: dict[str, float] = {}
    for sub in subscriptions:
        sub_name = sub.get("name", "").lower()
        sub_purpose = sub.get("purpose", "").lower()
        sub_text = f"{sub_name} {sub_purpose}"
        score = 0.0

        # Criticality hint matching
        hints = _CRITICALITY_SUBSCRIPTION_HINTS.get(criticality, ["workload"])
        for i, hint in enumerate(hints):
            if hint in sub_text:
                score += 0.4 - i * 0.05  # First hint worth more
                break

        # Workload type matching
        if workload_type in ("database",) and "data" in sub_text:
            score += 0.2
        elif workload_type in ("web-app", "container") and ("app" in sub_text or "web" in sub_text):
            score += 0.15

        # Compliance matching — prefer subscriptions tagged for regulated workloads
        if compliance_reqs:
            if any(kw in sub_text for kw in ("regulated", "secure", "compliance", "hipaa", "pci")):
                score += 0.2
            # Penalise sandbox/dev for compliance workloads
            if any(kw in sub_text for kw in ("dev", "test", "sandbox")):
                score -= 0.3

        # Network requirements — penalise sandbox for mission-critical
        if criticality == "mission-critical" and any(kw in sub_text for kw in ("dev", "sandbox")):
            score -= 0.4

        scores[_subscription_id(sub)] = score

    if not scores:
        # No subscriptions available — return first or a dummy
        fallback = subscriptions[0] if subscriptions else {"name": "unknown", "id": "unknown"}
        return fallback, 0.0, ["No subscriptions available in architecture"]

    best_id = max(scores, key=lambda k: scores[k])
    best_sub = next(s for s in subscriptions if _subscription_id(s) == best_id)
    best_score = scores[best_id]

    # Generate warnings based on the selected subscription only
    best_sub_text = f"{best_sub.get('name', '').lower()} {best_sub.get('purpose', '').lower()}"
    if compliance_reqs and any(kw in best_sub_text for kw in ("dev", "test", "sandbox")):
        warnings.append(
            f"Workload '{workload.get('name')}' has compliance requirements "
            f"({', '.join(compliance_reqs)}) but may be mapped to a non-production subscription."
        )

    # Normalise score to 0–1
    confidence = min(max(0.4 + best_score, 0.1), 0.95)
    return best_sub, round(confidence, 2), warnings


async def generate_mapping(
    workloads: list[dict],
    architecture: dict,
    ai_client: "AIFoundryClient | None" = None,
) -> list[WorkloadMapping]:
    """Generate workload-to-subscription mappings.

    Uses AI when ``ai_client`` is provided and configured; falls back to
    deterministic rule-based logic otherwise.

    Args:
        workloads: List of workload dicts (from DB or API response).
        architecture: Architecture dict containing a ``subscriptions`` key.
        ai_client: Optional AI Foundry client for AI-powered mapping.

    Returns:
        List of :class:`WorkloadMapping` instances.
    """
    subscriptions: list[dict] = architecture.get("subscriptions") or []
    if not subscriptions:
        logger.warning("No subscriptions found in architecture — returning empty mappings")
        return []

    # Normalise subscriptions to ensure they have an "id" field
    for i, sub in enumerate(subscriptions):
        if not sub.get("id"):
            sub["id"] = sub.get("name", f"sub-{i}")

    use_ai = ai_client is not None and ai_client.is_configured

    if use_ai:
        logger.info("Generating AI-powered workload mappings for %d workloads", len(workloads))
        mappings = await _ai_generate_mapping(workloads, subscriptions, ai_client)  # type: ignore[arg-type]
    else:
        logger.info("Generating rule-based workload mappings for %d workloads", len(workloads))
        mappings = _rule_based_generate_mapping(workloads, subscriptions)

    return mappings


def _rule_based_generate_mapping(
    workloads: list[dict],
    subscriptions: list[dict],
) -> list[WorkloadMapping]:
    """Apply deterministic rules to map each workload to a subscription."""
    mappings: list[WorkloadMapping] = []
    for wl in workloads:
        best_sub, confidence, warnings = _rule_based_mapping(wl, subscriptions)
        mappings.append(
            WorkloadMapping(
                workload_id=wl.get("id", ""),
                workload_name=wl.get("name", "Unknown"),
                recommended_subscription_id=_subscription_id(best_sub),
                recommended_subscription_name=best_sub.get("name", "Unknown"),
                reasoning=_build_rule_reasoning(wl, best_sub),
                confidence_score=confidence,
                warnings=warnings,
            )
        )
    return mappings


def _build_rule_reasoning(workload: dict, subscription: dict) -> str:
    """Construct a human-readable reasoning string for a rule-based mapping."""
    parts: list[str] = []
    criticality = workload.get("criticality", "standard")
    workload_type = workload.get("type", "other")
    compliance_reqs = workload.get("compliance_requirements") or []

    parts.append(
        f"Workload type '{workload_type}' with criticality '{criticality}' "
        f"maps to subscription '{subscription.get('name')}' "
        f"(purpose: {subscription.get('purpose', 'unknown')})."
    )
    if compliance_reqs:
        parts.append(f"Compliance requirements: {', '.join(compliance_reqs)}.")
    return " ".join(parts)


async def _ai_generate_mapping(
    workloads: list[dict],
    subscriptions: list[dict],
    ai_client: "AIFoundryClient",
) -> list[WorkloadMapping]:
    """Use AI to generate workload-to-subscription mappings."""
    system_prompt = (
        "You are an Azure cloud architect expert. Given a list of workloads and available "
        "Azure subscriptions, map each workload to the most appropriate subscription. "
        "Consider: workload type, criticality, compliance requirements, and subscription purpose. "
        "Respond ONLY with a valid JSON array of mapping objects. Each object must have: "
        "workload_id (string), workload_name (string), recommended_subscription_id (string), "
        "recommended_subscription_name (string), reasoning (string), confidence_score (float 0-1), "
        "warnings (array of strings)."
    )

    workloads_summary = [
        {
            "id": w.get("id", ""),
            "name": w.get("name", ""),
            "type": w.get("type", "other"),
            "criticality": w.get("criticality", "standard"),
            "compliance_requirements": w.get("compliance_requirements") or [],
        }
        for w in workloads
    ]
    subscriptions_summary = [
        {"id": _subscription_id(s), "name": s.get("name", ""), "purpose": s.get("purpose", "")}
        for s in subscriptions
    ]

    user_prompt = (
        f"Workloads:\n{json.dumps(workloads_summary, indent=2)}\n\n"
        f"Available subscriptions:\n{json.dumps(subscriptions_summary, indent=2)}\n\n"
        "Respond with a JSON array of mappings."
    )

    try:
        raw = await ai_client.generate_completion_async(system_prompt, user_prompt)
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            mappings: list[WorkloadMapping] = []
            mapped_ids: set[str] = set()
            for item in parsed:
                try:
                    m = WorkloadMapping(**item)
                    mappings.append(m)
                    mapped_ids.add(m.workload_id)
                except Exception as exc:
                    logger.warning("Skipping invalid mapping item from AI: %s — %s", item, exc)

            # Fill in any workloads the AI omitted with rule-based fallbacks
            unmapped = [w for w in workloads if w.get("id", "") not in mapped_ids]
            if unmapped:
                logger.info(
                    "AI omitted %d workload(s) — filling with rule-based mappings", len(unmapped)
                )
                mappings.extend(_rule_based_generate_mapping(unmapped, subscriptions))

            logger.info("AI returned %d mappings (after fill)", len(mappings))
            return mappings
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning("AI mapping parse failed (%s) — falling back to rule-based", exc)

    # Fallback to rule-based
    return _rule_based_generate_mapping(workloads, subscriptions)


def validate_mappings(mappings: list[WorkloadMapping], workloads: list[dict]) -> list[str]:
    """Validate generated mappings and return warning messages.

    Checks for:
    - Compliance mismatches (high-compliance workload in dev/sandbox subscription)
    - Subscription overload (>50 workloads in one subscription)
    - Dependent workloads split across subscriptions with no network path
    """
    warnings: list[str] = []

    # Build lookup by workload_id
    workload_by_id: dict[str, dict] = {w.get("id", ""): w for w in workloads}

    # Count workloads per subscription
    sub_workload_counts: dict[str, int] = {}
    for m in mappings:
        sub_workload_counts[m.recommended_subscription_id] = (
            sub_workload_counts.get(m.recommended_subscription_id, 0) + 1
        )

    # Check subscription overload
    for sub_id, count in sub_workload_counts.items():
        if count > MAX_WORKLOADS_PER_SUBSCRIPTION:
            warnings.append(
                f"Subscription '{sub_id}' has {count} workloads assigned, "
                f"which exceeds the recommended maximum of {MAX_WORKLOADS_PER_SUBSCRIPTION}."
            )

    # Check compliance mismatches
    for m in mappings:
        wl = workload_by_id.get(m.workload_id, {})
        compliance_reqs: list[str] = wl.get("compliance_requirements") or []
        sensitive = [r for r in compliance_reqs if r in _COMPLIANCE_SENSITIVE]
        sub_name = m.recommended_subscription_name.lower()
        if sensitive and any(kw in sub_name for kw in ("dev", "test", "sandbox")):
            warnings.append(
                f"Workload '{m.workload_name}' has sensitive compliance requirements "
                f"({', '.join(sensitive)}) but is mapped to a non-production subscription "
                f"('{m.recommended_subscription_name}'). Consider moving to a regulated subscription."
            )

    # Check dependent workloads split across subscriptions
    mapping_by_id: dict[str, WorkloadMapping] = {m.workload_id: m for m in mappings}
    for m in mappings:
        wl = workload_by_id.get(m.workload_id, {})
        deps: list[str] = wl.get("dependencies") or []
        for dep_id in deps:
            dep_mapping = mapping_by_id.get(dep_id)
            if dep_mapping is None:
                continue
            if dep_mapping.recommended_subscription_id != m.recommended_subscription_id:
                # Check if the subscriptions have names suggesting a peered network
                src_sub = m.recommended_subscription_name.lower()
                dep_sub = dep_mapping.recommended_subscription_name.lower()
                # Hub-spoke peering keywords
                peered = any(kw in src_sub or kw in dep_sub for kw in ("hub", "shared", "platform"))
                if not peered:
                    warnings.append(
                        f"Workload '{m.workload_name}' depends on '{dep_mapping.workload_name}' "
                        f"but they are in different subscriptions "
                        f"('{m.recommended_subscription_name}' vs '{dep_mapping.recommended_subscription_name}') "
                        f"with no confirmed network path. Verify VNet peering is in place."
                    )

    return warnings

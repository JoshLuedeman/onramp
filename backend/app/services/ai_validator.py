"""AI output schema validation and hallucination detection.

Validates JSON returned by the AI client against Pydantic models and
Azure reference data so we can catch malformed or hallucinated outputs
before they reach the user.
"""

import logging
from collections import Counter
from datetime import datetime, timezone

from pydantic import ValidationError as PydanticValidationError

from app.schemas.ai_output_models import (
    ArchitectureOutput,
    ComplianceGapOutput,
    PolicyDefinitionOutput,
    SecurityFindingOutput,
    SKURecommendationOutput,
)
from app.schemas.ai_validation import (
    AIOutputType,
    ValidationError,
    ValidationMetrics,
    ValidationResult,
)
from app.services.azure_reference import azure_reference

logger = logging.getLogger(__name__)


class AIOutputValidator:
    """Validates AI-generated JSON against expected schemas.

    Also tracks validation metrics (pass/fail rates) per feature to enable
    observability into AI output quality over time.
    """

    def __init__(self) -> None:
        # Metrics storage: feature -> list of (passed, errors, timestamp)
        self._metrics: dict[str, list[dict]] = {}

    # ------------------------------------------------------------------
    # Public validation methods
    # ------------------------------------------------------------------

    def validate_architecture(self, data: dict) -> ValidationResult:
        """Validate architecture JSON against the expected schema."""
        result = self._validate_with_model(ArchitectureOutput, data)

        # Extra domain-specific checks
        if result.success and result.validated_data:
            warnings = self._check_architecture_warnings(result.validated_data)
            result.warnings.extend(warnings)

            # Validate Azure resources embedded in the architecture
            resource_errors = self.validate_azure_resources(result.validated_data)
            if resource_errors:
                result.warnings.extend(
                    f"{e.field}: {e.message}" for e in resource_errors
                )

        self.track_validation_metrics(
            AIOutputType.architecture,
            result.success,
            [e.message for e in result.errors],
        )
        return result

    def validate_policy(self, data: dict) -> ValidationResult:
        """Validate an Azure Policy definition."""
        result = self._validate_with_model(PolicyDefinitionOutput, data)

        if result.success and result.validated_data:
            warnings = self._check_policy_warnings(result.validated_data)
            result.warnings.extend(warnings)

        self.track_validation_metrics(
            AIOutputType.policy,
            result.success,
            [e.message for e in result.errors],
        )
        return result

    def validate_sku_recommendation(self, data: dict) -> ValidationResult:
        """Validate a SKU recommendation, checking for hallucinated SKUs."""
        result = self._validate_with_model(SKURecommendationOutput, data)

        if result.success and result.validated_data:
            sku = result.validated_data.get("recommended_sku", "")
            if sku and not azure_reference.is_valid_sku(sku):
                result.warnings.append(
                    f"SKU '{sku}' does not match any known Azure VM SKU family"
                )

        self.track_validation_metrics(
            AIOutputType.sku_recommendation,
            result.success,
            [e.message for e in result.errors],
        )
        return result

    def validate_security_finding(self, data: dict) -> ValidationResult:
        """Validate a security finding output."""
        result = self._validate_with_model(SecurityFindingOutput, data)

        if result.success and result.validated_data:
            severity = result.validated_data.get("severity", "")
            valid_severities = {"critical", "high", "medium", "low", "informational"}
            if severity.lower() not in valid_severities:
                result.warnings.append(
                    f"Severity '{severity}' is not a standard severity level"
                )

        self.track_validation_metrics(
            AIOutputType.security_finding,
            result.success,
            [e.message for e in result.errors],
        )
        return result

    def validate_compliance_gap(self, data: dict) -> ValidationResult:
        """Validate a compliance gap prediction."""
        result = self._validate_with_model(ComplianceGapOutput, data)

        if result.success and result.validated_data:
            status = result.validated_data.get("status", "")
            valid_statuses = {"compliant", "non_compliant", "partial", "not_assessed"}
            if status.lower() not in valid_statuses:
                result.warnings.append(
                    f"Status '{status}' is not a recognized compliance status"
                )

        self.track_validation_metrics(
            AIOutputType.compliance_gap,
            result.success,
            [e.message for e in result.errors],
        )
        return result

    def validate_azure_resources(self, data: dict) -> list[ValidationError]:
        """Check resource types, regions, and SKUs in *data* against known values."""
        errors: list[ValidationError] = []

        # Check network_topology.primary_region
        network = data.get("network_topology", {})
        if isinstance(network, dict):
            region = network.get("primary_region", "")
            if region and not azure_reference.is_valid_region(region):
                errors.append(
                    ValidationError(
                        field="network_topology.primary_region",
                        message=f"Region '{region}' is not a known Azure region",
                        expected="A valid Azure region (e.g. eastus, westeurope)",
                        received=region,
                    )
                )

        # Check subscriptions for extremely high budgets (possible hallucination)
        subscriptions = data.get("subscriptions", [])
        if isinstance(subscriptions, list):
            for i, sub in enumerate(subscriptions):
                if isinstance(sub, dict):
                    budget = sub.get("budget_usd", 0)
                    if isinstance(budget, (int, float)) and budget > 10_000_000:
                        errors.append(
                            ValidationError(
                                field=f"subscriptions[{i}].budget_usd",
                                message=(
                                    f"Budget ${budget:,.0f} seems unreasonably high"
                                ),
                                expected="Reasonable budget under $10,000,000",
                                received=str(budget),
                            )
                        )

        return errors

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def track_validation_metrics(
        self, feature: str | AIOutputType, passed: bool, errors: list[str]
    ) -> None:
        """Record a validation result for the given feature."""
        key = feature.value if isinstance(feature, AIOutputType) else feature
        if key not in self._metrics:
            self._metrics[key] = []
        self._metrics[key].append(
            {
                "passed": passed,
                "errors": errors,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def get_metrics(self, feature: str | None = None) -> list[ValidationMetrics]:
        """Return validation metrics, optionally filtered by *feature*."""
        keys = [feature] if feature and feature in self._metrics else list(self._metrics)
        results: list[ValidationMetrics] = []
        for key in keys:
            entries = self._metrics.get(key, [])
            if not entries:
                continue
            passed = sum(1 for e in entries if e["passed"])
            failed = len(entries) - passed
            total = len(entries)
            all_errors: list[str] = []
            for e in entries:
                all_errors.extend(e["errors"])
            common = [err for err, _ in Counter(all_errors).most_common(5)]
            results.append(
                ValidationMetrics(
                    feature=key,
                    total_validations=total,
                    passed=passed,
                    failed=failed,
                    failure_rate=round(failed / total, 4) if total else 0.0,
                    common_errors=common,
                )
            )
        return results

    def reset_metrics(self) -> None:
        """Clear all recorded metrics (useful for testing)."""
        self._metrics.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_with_model(self, model_cls, data: dict) -> ValidationResult:
        """Validate *data* against a Pydantic *model_cls*."""
        try:
            obj = model_cls.model_validate(data)
            return ValidationResult(
                success=True,
                validated_data=obj.model_dump(),
            )
        except PydanticValidationError as exc:
            errors = [
                ValidationError(
                    field=".".join(str(loc) for loc in e["loc"]),
                    message=e["msg"],
                    expected=e.get("type", ""),
                    received=str(e.get("input", "")),
                )
                for e in exc.errors()
            ]
            return ValidationResult(
                success=False,
                errors=errors,
                validated_data=None,
            )

    @staticmethod
    def _check_architecture_warnings(data: dict) -> list[str]:
        """Return domain-specific warnings for architecture data."""
        warnings: list[str] = []

        org_size = data.get("organization_size", "")
        valid_sizes = {"small", "medium", "large", "enterprise"}
        if org_size and org_size.lower() not in valid_sizes:
            warnings.append(
                f"organization_size '{org_size}' is not one of: "
                f"{', '.join(sorted(valid_sizes))}"
            )

        subs = data.get("subscriptions", [])
        if not subs:
            warnings.append("No subscriptions defined in the architecture")

        mg = data.get("management_groups", {})
        if not mg:
            warnings.append("No management groups defined in the architecture")

        network = data.get("network_topology", {})
        if isinstance(network, dict):
            net_type = network.get("type", "")
            if net_type and net_type.lower() not in {"hub-spoke", "vwan"}:
                warnings.append(
                    f"network_topology.type '{net_type}' is not hub-spoke or vwan"
                )

        cost = data.get("estimated_monthly_cost_usd", 0)
        if isinstance(cost, (int, float)) and cost <= 0:
            warnings.append("estimated_monthly_cost_usd is zero or negative")

        return warnings

    @staticmethod
    def _check_policy_warnings(data: dict) -> list[str]:
        """Return domain-specific warnings for a policy definition."""
        warnings: list[str] = []

        valid_modes = {"all", "indexed", "microsoft.kubernetes.data",
                       "microsoft.keyvault.data",
                       "microsoft.network.data"}
        mode = data.get("mode", "")
        if mode and mode.lower() not in valid_modes:
            warnings.append(f"Policy mode '{mode}' is not a known Azure Policy mode")

        valid_effects = {"deny", "audit", "append", "modify",
                         "deployifnotexists", "auditifnotexists",
                         "disabled", "denyaction"}
        rule = data.get("policy_rule", {})
        if isinstance(rule, dict):
            then = rule.get("then", {})
            if isinstance(then, dict):
                effect = then.get("effect", "")
                if effect and effect.lower() not in valid_effects:
                    warnings.append(
                        f"Policy effect '{effect}' is not a known Azure Policy effect"
                    )

        return warnings


# Module-level singleton
ai_validator = AIOutputValidator()

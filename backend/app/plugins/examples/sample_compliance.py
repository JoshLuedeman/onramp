"""Sample compliance plugin — CIS Azure Benchmark (subset).

Demonstrates how to implement the CompliancePlugin protocol and
register with the OnRamp plugin system.
"""

from __future__ import annotations

from typing import Any


class CISAzureBenchmarkPlugin:
    """A sample compliance plugin implementing CIS Azure Benchmark controls."""

    name = "CIS Azure Benchmark"
    version = "1.0.0"
    description = "CIS Microsoft Azure Foundations Benchmark v2.0 (sample subset)"

    _controls = [
        {
            "id": "CIS-1.1",
            "title": "Ensure MFA is enabled for all privileged users",
            "category": "Identity",
            "severity": "critical",
        },
        {
            "id": "CIS-2.1",
            "title": "Ensure network segmentation is properly configured",
            "category": "Networking",
            "severity": "high",
        },
        {
            "id": "CIS-3.1",
            "title": "Ensure encryption at rest is enabled for storage accounts",
            "category": "Data Protection",
            "severity": "high",
        },
        {
            "id": "CIS-4.1",
            "title": "Ensure audit logging is enabled",
            "category": "Logging",
            "severity": "medium",
        },
        {
            "id": "CIS-5.1",
            "title": "Ensure key vault is used for secret management",
            "category": "Key Management",
            "severity": "high",
        },
    ]

    def get_controls(self) -> list[dict[str, Any]]:
        """Return the list of controls in this benchmark."""
        return list(self._controls)

    def evaluate(self, architecture: dict[str, Any]) -> dict[str, Any]:
        """Evaluate an architecture dict against CIS controls.

        Returns a dict with ``controls`` (per-control pass/fail) and an
        overall ``score`` percentage.
        """
        results: list[dict[str, Any]] = []
        for control in self._controls:
            passed = self._check_control(control["id"], architecture)
            results.append({
                "control_id": control["id"],
                "title": control["title"],
                "passed": passed,
                "severity": control["severity"],
            })

        total = len(results)
        passed_count = sum(1 for r in results if r["passed"])
        score = round((passed_count / total) * 100, 1) if total else 0.0

        return {
            "plugin": self.name,
            "version": self.version,
            "controls": results,
            "passed": passed_count,
            "failed": total - passed_count,
            "score": score,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_control(control_id: str, architecture: dict[str, Any]) -> bool:
        """Heuristic check for a single control against the architecture."""
        if control_id == "CIS-1.1":
            # Check if MFA / identity settings exist
            identity = architecture.get("identity", {})
            return bool(identity.get("mfa_enabled"))

        if control_id == "CIS-2.1":
            # Check for network segmentation
            network = architecture.get("network_topology", {})
            return bool(network.get("hub_spoke") or network.get("segmentation"))

        if control_id == "CIS-3.1":
            # Check for encryption at rest
            security = architecture.get("security", {})
            return bool(security.get("encryption_at_rest"))

        if control_id == "CIS-4.1":
            # Check for audit/logging
            logging_cfg = architecture.get("logging", {})
            return bool(logging_cfg.get("audit_enabled") or logging_cfg.get("enabled"))

        if control_id == "CIS-5.1":
            # Check for key vault usage
            security = architecture.get("security", {})
            return bool(security.get("key_vault"))

        return False


def register(registry: Any) -> None:
    """Entry point called by the plugin loader."""
    plugin = CISAzureBenchmarkPlugin()
    registry.register_compliance(plugin)

"""Plugin system for extending OnRamp with custom compliance, architecture, and output formats."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CompliancePlugin(Protocol):
    """Protocol for custom compliance framework plugins."""

    name: str
    version: str
    description: str

    def get_controls(self) -> list[dict[str, Any]]: ...
    def evaluate(self, architecture: dict[str, Any]) -> dict[str, Any]: ...


@runtime_checkable
class ArchitecturePlugin(Protocol):
    """Protocol for custom architecture pattern plugins."""

    name: str
    version: str
    description: str

    def get_archetype(self) -> dict[str, Any]: ...
    def get_questions(self) -> list[dict[str, Any]]: ...


@runtime_checkable
class OutputFormatPlugin(Protocol):
    """Protocol for custom IaC output format plugins."""

    name: str
    version: str
    format_name: str

    def generate(self, architecture: dict[str, Any]) -> list[dict[str, str]]: ...


class PluginInfo:
    """Metadata about a registered plugin."""

    def __init__(
        self,
        name: str,
        version: str,
        plugin_type: str,
        description: str = "",
        enabled: bool = True,
    ):
        self.name = name
        self.version = version
        self.plugin_type = plugin_type
        self.description = description
        self.enabled = enabled

    def to_dict(self) -> dict[str, Any]:
        """Serialize plugin info to a dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "plugin_type": self.plugin_type,
            "description": self.description,
            "enabled": self.enabled,
        }

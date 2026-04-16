"""Plugin discovery, registration, and lifecycle management."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import logging
import sys
from pathlib import Path

from app.plugins import (
    ArchitecturePlugin,
    CompliancePlugin,
    OutputFormatPlugin,
    PluginInfo,
)

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Central registry for all OnRamp plugins.

    Manages discovery, validation, and access to compliance,
    architecture, and output-format plugins.
    """

    def __init__(self) -> None:
        self._compliance_plugins: dict[str, CompliancePlugin] = {}
        self._architecture_plugins: dict[str, ArchitecturePlugin] = {}
        self._output_plugins: dict[str, OutputFormatPlugin] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Remove all registered plugins.

        Primarily intended for test isolation — resets the registry to its
        initial empty state.
        """
        self._compliance_plugins.clear()
        self._architecture_plugins.clear()
        self._output_plugins.clear()

    def register_compliance(self, plugin: CompliancePlugin) -> None:
        """Register a compliance-framework plugin after protocol validation."""
        if not isinstance(plugin, CompliancePlugin):
            raise TypeError(
                f"Plugin {getattr(plugin, 'name', '?')} does not satisfy CompliancePlugin protocol"
            )
        name = plugin.name
        self._compliance_plugins[name] = plugin
        logger.info("Registered compliance plugin: %s v%s", name, plugin.version)

    def register_architecture(self, plugin: ArchitecturePlugin) -> None:
        """Register an architecture-pattern plugin after protocol validation."""
        if not isinstance(plugin, ArchitecturePlugin):
            raise TypeError(
                f"Plugin {getattr(plugin, 'name', '?')} does not satisfy ArchitecturePlugin protocol"
            )
        name = plugin.name
        self._architecture_plugins[name] = plugin
        logger.info("Registered architecture plugin: %s v%s", name, plugin.version)

    def register_output(self, plugin: OutputFormatPlugin) -> None:
        """Register an output-format plugin after protocol validation."""
        if not isinstance(plugin, OutputFormatPlugin):
            raise TypeError(
                f"Plugin {getattr(plugin, 'name', '?')} does not satisfy OutputFormatPlugin protocol"
            )
        name = plugin.name
        self._output_plugins[name] = plugin
        logger.info("Registered output plugin: %s v%s", name, plugin.version)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_all_plugins(self) -> list[PluginInfo]:
        """Return metadata for every registered plugin."""
        plugins: list[PluginInfo] = []
        for p in self._compliance_plugins.values():
            plugins.append(
                PluginInfo(
                    name=p.name,
                    version=p.version,
                    plugin_type="compliance",
                    description=p.description,
                )
            )
        for p in self._architecture_plugins.values():
            plugins.append(
                PluginInfo(
                    name=p.name,
                    version=p.version,
                    plugin_type="architecture",
                    description=p.description,
                )
            )
        for p in self._output_plugins.values():
            plugins.append(
                PluginInfo(
                    name=p.name,
                    version=p.version,
                    plugin_type="output",
                    description=getattr(p, "description", ""),
                )
            )
        return plugins

    def get_compliance_plugins(self) -> list[CompliancePlugin]:
        """Return all registered compliance plugins."""
        return list(self._compliance_plugins.values())

    def get_architecture_plugins(self) -> list[ArchitecturePlugin]:
        """Return all registered architecture plugins."""
        return list(self._architecture_plugins.values())

    def get_output_plugins(self) -> list[OutputFormatPlugin]:
        """Return all registered output-format plugins."""
        return list(self._output_plugins.values())

    def get_plugin(self, name: str) -> PluginInfo | None:
        """Look up a single plugin by name across all types."""
        for p in self._compliance_plugins.values():
            if p.name == name:
                return PluginInfo(
                    name=p.name,
                    version=p.version,
                    plugin_type="compliance",
                    description=p.description,
                )
        for p in self._architecture_plugins.values():
            if p.name == name:
                return PluginInfo(
                    name=p.name,
                    version=p.version,
                    plugin_type="architecture",
                    description=p.description,
                )
        for p in self._output_plugins.values():
            if p.name == name:
                return PluginInfo(
                    name=p.name,
                    version=p.version,
                    plugin_type="output",
                    description=getattr(p, "description", ""),
                )
        return None

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_plugins(self, plugins_dir: str) -> None:
        """Scan a directory for Python modules containing a ``register(registry)`` function.

        Each module found is imported and its ``register`` callable is
        invoked with *this* registry instance.
        """
        path = Path(plugins_dir)
        if not path.is_dir():
            logger.debug("Plugin directory '%s' does not exist — skipping", plugins_dir)
            return

        for py_file in sorted(path.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            module_name = f"onramp_plugins.{py_file.stem}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)  # type: ignore[union-attr]
                register_fn = getattr(module, "register", None)
                if callable(register_fn):
                    register_fn(self)
                    logger.info("Loaded plugin module: %s", py_file.name)
                else:
                    logger.warning("Module %s has no register() function — skipped", py_file.name)
            except Exception:
                logger.exception("Failed to load plugin from %s", py_file.name)

    def load_entry_points(self) -> None:
        """Discover plugins installed via ``onramp.plugins`` entry-point group."""
        try:
            eps = importlib.metadata.entry_points(group="onramp.plugins")
        except TypeError:
            # Python <3.12 compat: entry_points() may not accept group kwarg
            eps = importlib.metadata.entry_points().get("onramp.plugins", [])  # type: ignore[assignment]

        for ep in eps:
            try:
                register_fn = ep.load()
                if callable(register_fn):
                    register_fn(self)
                    logger.info("Loaded entry-point plugin: %s", ep.name)
            except Exception:
                logger.exception("Failed to load entry-point plugin: %s", ep.name)


# Module-level singleton
plugin_registry = PluginRegistry()


def get_plugin_registry() -> PluginRegistry:
    """Return the global plugin registry (useful as a FastAPI dependency)."""
    return plugin_registry

"""Tests for the plugin system — protocols, registry, discovery, and API routes."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.plugins import (
    ArchitecturePlugin,
    CompliancePlugin,
    OutputFormatPlugin,
    PluginInfo,
)
from app.plugins.examples.sample_compliance import CISAzureBenchmarkPlugin
from app.plugins.loader import PluginRegistry

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers — minimal classes that satisfy protocols
# ---------------------------------------------------------------------------

class _FakeCompliance:
    name = "fake-compliance"
    version = "0.1.0"
    description = "Unit-test compliance plugin"

    def get_controls(self):
        return [{"id": "C1", "title": "Test control"}]

    def evaluate(self, architecture):
        return {"passed": 1, "failed": 0, "score": 100.0}


class _FakeArchitecture:
    name = "fake-architecture"
    version = "0.2.0"
    description = "Unit-test architecture plugin"

    def get_archetype(self):
        return {"name": "test"}

    def get_questions(self):
        return [{"id": "q1", "text": "Question?"}]


class _FakeOutput:
    name = "fake-output"
    version = "0.3.0"
    format_name = "test-fmt"

    def generate(self, architecture):
        return [{"filename": "test.tf", "content": "# test"}]


class _BadPlugin:
    """Does NOT satisfy any plugin protocol."""

    name = "bad"


# ---------------------------------------------------------------------------
# Protocol validation
# ---------------------------------------------------------------------------

class TestProtocols:
    def test_compliance_protocol_satisfied(self):
        assert isinstance(_FakeCompliance(), CompliancePlugin)

    def test_architecture_protocol_satisfied(self):
        assert isinstance(_FakeArchitecture(), ArchitecturePlugin)

    def test_output_protocol_satisfied(self):
        assert isinstance(_FakeOutput(), OutputFormatPlugin)

    def test_bad_plugin_rejected_by_compliance_protocol(self):
        assert not isinstance(_BadPlugin(), CompliancePlugin)

    def test_bad_plugin_rejected_by_architecture_protocol(self):
        assert not isinstance(_BadPlugin(), ArchitecturePlugin)

    def test_bad_plugin_rejected_by_output_protocol(self):
        assert not isinstance(_BadPlugin(), OutputFormatPlugin)


# ---------------------------------------------------------------------------
# PluginInfo
# ---------------------------------------------------------------------------

class TestPluginInfo:
    def test_to_dict(self):
        info = PluginInfo(
            name="test",
            version="1.0",
            plugin_type="compliance",
            description="desc",
            enabled=True,
        )
        d = info.to_dict()
        assert d["name"] == "test"
        assert d["version"] == "1.0"
        assert d["plugin_type"] == "compliance"
        assert d["description"] == "desc"
        assert d["enabled"] is True

    def test_defaults(self):
        info = PluginInfo(name="x", version="0", plugin_type="output")
        assert info.description == ""
        assert info.enabled is True


# ---------------------------------------------------------------------------
# PluginRegistry — registration
# ---------------------------------------------------------------------------

class TestRegistryRegistration:
    def test_register_compliance(self):
        registry = PluginRegistry()
        registry.register_compliance(_FakeCompliance())
        assert len(registry.get_compliance_plugins()) == 1

    def test_register_architecture(self):
        registry = PluginRegistry()
        registry.register_architecture(_FakeArchitecture())
        assert len(registry.get_architecture_plugins()) == 1

    def test_register_output(self):
        registry = PluginRegistry()
        registry.register_output(_FakeOutput())
        assert len(registry.get_output_plugins()) == 1

    def test_register_compliance_rejects_bad_plugin(self):
        registry = PluginRegistry()
        with pytest.raises(TypeError):
            registry.register_compliance(_BadPlugin())  # type: ignore[arg-type]

    def test_register_architecture_rejects_bad_plugin(self):
        registry = PluginRegistry()
        with pytest.raises(TypeError):
            registry.register_architecture(_BadPlugin())  # type: ignore[arg-type]

    def test_register_output_rejects_bad_plugin(self):
        registry = PluginRegistry()
        with pytest.raises(TypeError):
            registry.register_output(_BadPlugin())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# PluginRegistry — accessors
# ---------------------------------------------------------------------------

class TestRegistryAccessors:
    def test_get_all_plugins(self):
        registry = PluginRegistry()
        registry.register_compliance(_FakeCompliance())
        registry.register_architecture(_FakeArchitecture())
        registry.register_output(_FakeOutput())
        all_plugins = registry.get_all_plugins()
        assert len(all_plugins) == 3
        names = {p.name for p in all_plugins}
        assert names == {"fake-compliance", "fake-architecture", "fake-output"}

    def test_get_plugin_found(self):
        registry = PluginRegistry()
        registry.register_compliance(_FakeCompliance())
        info = registry.get_plugin("fake-compliance")
        assert info is not None
        assert info.plugin_type == "compliance"

    def test_get_plugin_not_found(self):
        registry = PluginRegistry()
        assert registry.get_plugin("nonexistent") is None

    def test_get_plugin_across_types(self):
        registry = PluginRegistry()
        registry.register_architecture(_FakeArchitecture())
        registry.register_output(_FakeOutput())
        assert registry.get_plugin("fake-architecture") is not None
        assert registry.get_plugin("fake-output") is not None


# ---------------------------------------------------------------------------
# Sample compliance plugin
# ---------------------------------------------------------------------------

class TestSampleCompliancePlugin:
    def test_get_controls(self):
        plugin = CISAzureBenchmarkPlugin()
        controls = plugin.get_controls()
        assert len(controls) == 5
        ids = [c["id"] for c in controls]
        assert "CIS-1.1" in ids
        assert "CIS-3.1" in ids

    def test_evaluate_all_pass(self):
        plugin = CISAzureBenchmarkPlugin()
        arch = {
            "identity": {"mfa_enabled": True},
            "network_topology": {"hub_spoke": True},
            "security": {"encryption_at_rest": True, "key_vault": True},
            "logging": {"audit_enabled": True},
        }
        result = plugin.evaluate(arch)
        assert result["score"] == 100.0
        assert result["passed"] == 5
        assert result["failed"] == 0

    def test_evaluate_partial(self):
        plugin = CISAzureBenchmarkPlugin()
        arch = {
            "identity": {"mfa_enabled": True},
            "network_topology": {},
            "security": {},
            "logging": {},
        }
        result = plugin.evaluate(arch)
        assert result["passed"] == 1
        assert result["failed"] == 4
        assert 0 < result["score"] < 100

    def test_evaluate_empty_architecture(self):
        plugin = CISAzureBenchmarkPlugin()
        result = plugin.evaluate({})
        assert result["passed"] == 0
        assert result["failed"] == 5
        assert result["score"] == 0.0

    def test_satisfies_compliance_protocol(self):
        assert isinstance(CISAzureBenchmarkPlugin(), CompliancePlugin)


# ---------------------------------------------------------------------------
# Discovery — directory scanning
# ---------------------------------------------------------------------------

class TestDiscovery:
    def test_discover_plugins_from_directory(self, tmp_path: Path):
        """Write a minimal plugin module and verify discover_plugins loads it."""
        plugin_file = tmp_path / "my_plugin.py"
        plugin_file.write_text(
            "class P:\n"
            "    name = 'discovered'\n"
            "    version = '0.1.0'\n"
            "    description = 'Disc plugin'\n"
            "    def get_controls(self): return []\n"
            "    def evaluate(self, arch): return {}\n"
            "\n"
            "def register(registry):\n"
            "    registry.register_compliance(P())\n"
        )
        registry = PluginRegistry()
        registry.discover_plugins(str(tmp_path))
        assert len(registry.get_compliance_plugins()) == 1
        assert registry.get_compliance_plugins()[0].name == "discovered"

    def test_discover_skips_missing_directory(self):
        registry = PluginRegistry()
        # Should not raise
        registry.discover_plugins("/nonexistent/path/42")
        assert len(registry.get_all_plugins()) == 0

    def test_discover_skips_underscore_files(self, tmp_path: Path):
        (tmp_path / "__init__.py").write_text("# noop")
        (tmp_path / "_private.py").write_text(
            "def register(registry): registry.register_compliance(None)"
        )
        registry = PluginRegistry()
        registry.discover_plugins(str(tmp_path))
        assert len(registry.get_all_plugins()) == 0

    def test_discover_handles_import_error(self, tmp_path: Path):
        bad_file = tmp_path / "broken.py"
        bad_file.write_text("raise RuntimeError('boom')")
        registry = PluginRegistry()
        # Should not raise, just log
        registry.discover_plugins(str(tmp_path))
        assert len(registry.get_all_plugins()) == 0


# ---------------------------------------------------------------------------
# Entry-point loading
# ---------------------------------------------------------------------------

class TestEntryPoints:
    def test_load_entry_points(self):
        mock_register = MagicMock()
        mock_ep = MagicMock()
        mock_ep.name = "test-ep"
        mock_ep.load.return_value = mock_register

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            registry = PluginRegistry()
            registry.load_entry_points()

        mock_register.assert_called_once_with(registry)

    def test_load_entry_points_handles_error(self):
        mock_ep = MagicMock()
        mock_ep.name = "bad-ep"
        mock_ep.load.side_effect = ImportError("missing")

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            registry = PluginRegistry()
            # Should not raise
            registry.load_entry_points()
        assert len(registry.get_all_plugins()) == 0


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

class TestPluginAPI:
    def test_list_plugins(self):
        response = client.get("/api/plugins/")
        assert response.status_code == 200
        data = response.json()
        assert "plugins" in data
        assert "total" in data
        assert isinstance(data["plugins"], list)

    def test_get_plugin_not_found(self):
        response = client.get("/api/plugins/nonexistent-plugin")
        assert response.status_code == 404

    def test_get_plugin_found(self):
        """Register a plugin then fetch it by name via the API."""
        from app.plugins.loader import plugin_registry

        # Ensure a known plugin is registered
        plugin = _FakeCompliance()
        plugin_registry._compliance_plugins[plugin.name] = plugin

        response = client.get(f"/api/plugins/{plugin.name}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "fake-compliance"
        assert data["plugin_type"] == "compliance"

        # Cleanup
        del plugin_registry._compliance_plugins[plugin.name]

    def test_list_plugins_returns_registered(self):
        """Verify the list endpoint includes a freshly registered plugin."""
        from app.plugins.loader import plugin_registry

        plugin = _FakeArchitecture()
        plugin_registry._architecture_plugins[plugin.name] = plugin

        response = client.get("/api/plugins/")
        assert response.status_code == 200
        data = response.json()
        names = [p["name"] for p in data["plugins"]]
        assert "fake-architecture" in names

        # Cleanup
        del plugin_registry._architecture_plugins[plugin.name]
